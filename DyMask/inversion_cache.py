from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import torch
from PIL import Image

from .config import RuntimeConfig
from .schemas import InversionOutput, MaterializedSample
from .utils import save_image, save_json


class InversionCacheError(RuntimeError):
    pass


class InversionCacheMiss(InversionCacheError):
    pass


class InversionCacheMismatch(InversionCacheError):
    pass


@dataclass(frozen=True)
class InversionCacheEntry:
    sample_id: str
    row_index: int
    record_id: str | None
    sample_dir: Path


class InversionCacheIndex:
    def __init__(self, run_dir: Path, entries: list[InversionCacheEntry]) -> None:
        self.run_dir = run_dir
        self.entries = entries
        self.by_sample_id = {entry.sample_id: entry for entry in entries}
        self.by_row_index = {entry.row_index: entry for entry in entries}
        self.by_record_id = {entry.record_id: entry for entry in entries if entry.record_id}

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "InversionCacheIndex":
        resolved_run_dir = Path(run_dir).resolve()
        manifest_path = _find_manifest_csv(resolved_run_dir)
        entries: list[InversionCacheEntry] = []
        with manifest_path.open('r', encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if not row.get('sample_id'):
                    continue
                sample_id = str(row['sample_id'])
                row_index = int(row['row_index'])
                record_id = row.get('record_id') or None
                sample_dir = resolved_run_dir / 'samples' / sample_id
                if not sample_dir.exists():
                    source_image_path = row.get('source_image_path')
                    if source_image_path:
                        source_parent = Path(source_image_path).expanduser()
                        if source_parent.exists():
                            sample_dir = source_parent.parent
                entries.append(
                    InversionCacheEntry(
                        sample_id=sample_id,
                        row_index=row_index,
                        record_id=record_id,
                        sample_dir=sample_dir,
                    )
                )
        if not entries:
            raise InversionCacheError(f'No samples found in inversion cache manifest: {manifest_path}')
        return cls(resolved_run_dir, entries)

    def resolve_entry(self, sample: MaterializedSample) -> InversionCacheEntry | None:
        entry = self.by_sample_id.get(sample.sample_id)
        if entry is not None:
            return entry
        entry = self.by_row_index.get(int(sample.row_index))
        if entry is not None:
            return entry
        record_id = _read_sample_record_id(sample)
        if record_id:
            return self.by_record_id.get(record_id)
        return None


def maybe_load_inversion_cache_index(runtime: RuntimeConfig) -> InversionCacheIndex | None:
    if runtime.inversion_cache_run_dir is None:
        return None
    return InversionCacheIndex.from_run_dir(Path(runtime.inversion_cache_run_dir))


def save_inversion_artifacts(sample: MaterializedSample, inversion: InversionOutput, save_tensors: bool) -> None:
    save_image(sample.sample_dir / 'source_reconstruction.png', inversion.reconstruction_image)
    save_json(sample.sample_dir / 'inversion.json', inversion.metadata)
    if not save_tensors:
        return
    torch.save(inversion.zt_src.detach().cpu(), sample.sample_dir / 'zt_src.pt')
    torch.save([latent.detach().cpu() for latent in inversion.src_latents], sample.sample_dir / 'src_latents.pt')
    if inversion.null_embeddings is not None:
        torch.save([embedding.detach().cpu() for embedding in inversion.null_embeddings], sample.sample_dir / 'null_embeddings.pt')


def prepare_inversion_for_sample(
    *,
    sample: MaterializedSample,
    runtime: RuntimeConfig,
    load_source_image: Callable[[Path], np.ndarray],
    inversion_backend,
    save_tensors: bool,
    cache_index: InversionCacheIndex | None = None,
    on_after_invert: Callable[[], None] | None = None,
) -> InversionOutput:
    require_cache = bool(runtime.require_inversion_cache)
    if cache_index is not None:
        try:
            inversion, entry = load_cached_inversion(sample, runtime, cache_index)
        except InversionCacheError as exc:
            if require_cache:
                raise
            print(f'[inversion-cache][{sample.sample_id}] {exc}; recomputing inversion')
        else:
            metadata = dict(inversion.metadata)
            metadata.update(
                {
                    'cache_reused': True,
                    'cache_source_run_dir': str(cache_index.run_dir),
                    'cache_source_sample_id': entry.sample_id,
                    'cache_source_row_index': entry.row_index,
                }
            )
            inversion = InversionOutput(
                zt_src=inversion.zt_src,
                src_latents=inversion.src_latents,
                reconstruction_image=inversion.reconstruction_image,
                null_embeddings=inversion.null_embeddings,
                metadata=metadata,
            )
            save_inversion_artifacts(sample, inversion, save_tensors)
            print(f'[inversion-cache][{sample.sample_id}] reused cached inversion from {entry.sample_dir}')
            return inversion

    if require_cache and cache_index is None:
        raise InversionCacheError('require_inversion_cache was set but no inversion_cache_run_dir was provided')

    source_image = load_source_image(sample.source_image_path)
    try:
        inversion = inversion_backend.invert(source_image, source_prompt=sample.source_prompt)
    except TypeError:
        inversion = inversion_backend.invert(source_image)
    finally:
        if on_after_invert is not None:
            on_after_invert()

    metadata = dict(inversion.metadata)
    metadata['cache_reused'] = False
    inversion = InversionOutput(
        zt_src=inversion.zt_src,
        src_latents=inversion.src_latents,
        reconstruction_image=inversion.reconstruction_image,
        null_embeddings=inversion.null_embeddings,
        metadata=metadata,
    )
    save_inversion_artifacts(sample, inversion, save_tensors)
    return inversion


def load_cached_inversion(
    sample: MaterializedSample,
    runtime: RuntimeConfig,
    cache_index: InversionCacheIndex,
) -> tuple[InversionOutput, InversionCacheEntry]:
    entry = cache_index.resolve_entry(sample)
    if entry is None:
        raise InversionCacheMiss(f'cache entry not found for row_index={sample.row_index}')

    sample_dir = entry.sample_dir
    inversion_json_path = sample_dir / 'inversion.json'
    reconstruction_path = sample_dir / 'source_reconstruction.png'
    zt_src_path = sample_dir / 'zt_src.pt'
    src_latents_path = sample_dir / 'src_latents.pt'
    null_embeddings_path = sample_dir / 'null_embeddings.pt'

    missing_paths = [
        path
        for path in (inversion_json_path, reconstruction_path, zt_src_path, src_latents_path)
        if not path.exists()
    ]
    if missing_paths:
        raise InversionCacheMiss(
            'cache entry is incomplete: ' + ', '.join(str(path) for path in missing_paths)
        )

    metadata = json.loads(inversion_json_path.read_text(encoding='utf-8'))
    reconstruction_image = np.asarray(Image.open(reconstruction_path).convert('RGB'))
    zt_src = torch.load(zt_src_path, map_location='cpu')
    src_latents = _ensure_tensor_list(torch.load(src_latents_path, map_location='cpu'), src_latents_path)
    null_embeddings = None
    if null_embeddings_path.exists():
        null_embeddings = _ensure_tensor_list(torch.load(null_embeddings_path, map_location='cpu'), null_embeddings_path)

    _validate_cached_inversion(
        sample=sample,
        runtime=runtime,
        metadata=metadata,
        reconstruction_image=reconstruction_image,
        src_latents=src_latents,
        null_embeddings=null_embeddings,
        cache_sample_dir=sample_dir,
    )
    return (
        InversionOutput(
            zt_src=zt_src.detach().cpu(),
            src_latents=[latent.detach().cpu() for latent in src_latents],
            reconstruction_image=reconstruction_image,
            null_embeddings=[embedding.detach().cpu() for embedding in null_embeddings] if null_embeddings is not None else None,
            metadata=metadata,
        ),
        entry,
    )


def _find_manifest_csv(run_dir: Path) -> Path:
    direct = run_dir / 'sample_manifest.csv'
    if direct.exists():
        return direct
    candidates = sorted(run_dir.glob('*manifest*.csv'))
    if candidates:
        return candidates[0]
    raise InversionCacheError(f'Could not find a manifest CSV under inversion cache run dir: {run_dir}')


def _read_sample_record_id(sample: MaterializedSample) -> str | None:
    sample_json = sample.sample_dir / 'sample.json'
    if not sample_json.exists():
        return None
    try:
        payload = json.loads(sample_json.read_text(encoding='utf-8'))
    except Exception:
        return None
    return payload.get('record_id') or payload.get('key')


def _ensure_tensor_list(payload, path: Path) -> list[torch.Tensor]:
    if isinstance(payload, tuple):
        payload = list(payload)
    if not isinstance(payload, list):
        raise InversionCacheMismatch(f'Expected a tensor list in {path}, got {type(payload).__name__}')
    tensors: list[torch.Tensor] = []
    for idx, item in enumerate(payload):
        if not isinstance(item, torch.Tensor):
            raise InversionCacheMismatch(
                f'Expected tensor #{idx} in {path}, got {type(item).__name__}'
            )
        tensors.append(item)
    return tensors


def _validate_cached_inversion(
    *,
    sample: MaterializedSample,
    runtime: RuntimeConfig,
    metadata: dict,
    reconstruction_image: np.ndarray,
    src_latents: list[torch.Tensor],
    null_embeddings: list[torch.Tensor] | None,
    cache_sample_dir: Path,
) -> None:
    backend = metadata.get('backend')
    if backend and backend != runtime.inversion_backend:
        raise InversionCacheMismatch(
            f'cache backend mismatch at {cache_sample_dir}: expected {runtime.inversion_backend}, got {backend}'
        )

    num_inversion_steps = metadata.get('num_inversion_steps')
    if num_inversion_steps is not None and int(num_inversion_steps) != int(runtime.num_inversion_steps):
        raise InversionCacheMismatch(
            f'cache inversion step mismatch at {cache_sample_dir}: expected {runtime.num_inversion_steps}, got {num_inversion_steps}'
        )

    if reconstruction_image.shape[0] != runtime.image_size or reconstruction_image.shape[1] != runtime.image_size:
        raise InversionCacheMismatch(
            f'cache image size mismatch at {cache_sample_dir}: expected {runtime.image_size}, got {tuple(reconstruction_image.shape[:2])}'
        )

    expected_latent_count = int(runtime.num_inversion_steps)
    if len(src_latents) != expected_latent_count:
        raise InversionCacheMismatch(
            f'cache latent trajectory mismatch at {cache_sample_dir}: expected {expected_latent_count} latents, got {len(src_latents)}'
        )

    if metadata.get('source_prompt_used_for_inversion'):
        cached_prompt = str(metadata.get('source_prompt') or '').strip()
        current_prompt = (sample.source_prompt or '').strip()
        if cached_prompt != current_prompt:
            raise InversionCacheMismatch(
                f'cache source prompt mismatch at {cache_sample_dir}: expected {current_prompt!r}, got {cached_prompt!r}'
            )

    if runtime.inversion_backend == 'nti':
        if null_embeddings is None:
            raise InversionCacheMismatch(f'NTI cache missing null_embeddings.pt at {cache_sample_dir}')
        if len(null_embeddings) != expected_latent_count:
            raise InversionCacheMismatch(
                f'NTI null embedding count mismatch at {cache_sample_dir}: expected {expected_latent_count}, got {len(null_embeddings)}'
            )
        nti_num_inner_steps = metadata.get('nti_num_inner_steps')
        if nti_num_inner_steps is not None and int(nti_num_inner_steps) != int(runtime.nti_num_inner_steps):
            raise InversionCacheMismatch(
                f'NTI inner step mismatch at {cache_sample_dir}: expected {runtime.nti_num_inner_steps}, got {nti_num_inner_steps}'
            )
        nti_eps = metadata.get('nti_early_stop_epsilon')
        if nti_eps is not None and abs(float(nti_eps) - float(runtime.nti_early_stop_epsilon)) > 1e-12:
            raise InversionCacheMismatch(
                f'NTI epsilon mismatch at {cache_sample_dir}: expected {runtime.nti_early_stop_epsilon}, got {nti_eps}'
            )
