from __future__ import annotations

from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path

from DyMaskRefactor.diffedit import DiffEditConfig
from DyMaskRefactor.logging_utils import MarkdownExperimentLogger
from DyMaskRefactor.utils import make_timestamped_run_dir, save_json

from DyMaskRefactor.config import ExperimentConfig
from DyMaskRefactor.datasets import LoadedSamples, load_materialized_samples, write_manifest
from DyMaskRefactor.inversion import build_inversion_backend
from DyMaskRefactor.metrics import MetricService
from DyMaskRefactor.reporting import collect_case_rows, write_run_reports
from DyMaskRefactor.runtime import build_pipeline
from DyMaskRefactor.support_line.configuration import build_config, build_diffedit_config
from DyMaskRefactor.support_line.registry import get_support_variant
from DyMaskRefactor.support_line.specs import SupportVariantSpec


@dataclass
class PreparedSupportRun:
    args: Namespace
    spec: SupportVariantSpec
    config: ExperimentConfig
    diffedit_config: DiffEditConfig
    run_dir: Path
    logger: MarkdownExperimentLogger
    loaded: LoadedSamples


def prepare_support_run(args: Namespace) -> PreparedSupportRun:
    spec = get_support_variant(args.variant)
    config = build_config(args, spec)
    diffedit_config = build_diffedit_config(args)

    run_dir = make_timestamped_run_dir(config.sampling.output_root, prefix=spec.run_prefix)
    logger = MarkdownExperimentLogger(Path(args.log_path))

    sample_output_dir = run_dir / "samples"
    loaded = load_materialized_samples(
        config,
        output_dir=sample_output_dir,
        sample_json=args.sample_json,
        row_indices=args.row_indices,
    )
    write_manifest(run_dir, config.sampling.manifest_name, loaded.manifest)
    save_json(run_dir / "config.json", config.to_dict())
    save_json(run_dir / "variant.json", spec.variant_payload(args, diffedit_config))

    logger.log(
        stage="support_refactor",
        operation="prepare run",
        inputs={
            "variant": spec.key,
            "methods": list(config.methods),
            "run_dir": str(run_dir),
            "output_root": str(config.sampling.output_root),
            "editor_kwargs": spec.editor_kwargs(args),
            "diffedit": diffedit_config.to_dict(),
        },
        result={
            "sample_count": len(loaded.samples),
            "sample_ids": [sample.sample_id for sample in loaded.samples[: min(8, len(loaded.samples))]],
        },
        conclusion="modular support-line run prepared",
        next_step="build pipeline and execute editing",
    )
    return PreparedSupportRun(
        args=args,
        spec=spec,
        config=config,
        diffedit_config=diffedit_config,
        run_dir=run_dir,
        logger=logger,
        loaded=loaded,
    )


def execute_support_run(args: Namespace) -> PreparedSupportRun:
    prepared = prepare_support_run(args)
    if prepared.config.dry_run:
        return prepared

    pipe = build_pipeline(prepared.config.runtime)
    inversion_backend = build_inversion_backend(pipe, prepared.config.runtime)
    editor = prepared.spec.editor_cls(
        pipe,
        prepared.config,
        diffedit_config=prepared.diffedit_config,
        inversion_backend=inversion_backend,
        **prepared.spec.editor_kwargs(prepared.args),
    )
    metric_service = None if prepared.config.skip_metrics else MetricService(prepared.config.runtime, prepared.config.metrics)

    run_samples = prepared.loaded.samples[: prepared.config.sampling.run_limit]
    batch_results = editor.run_samples(run_samples)
    case_rows = collect_case_rows(run_samples, batch_results, metric_service, prepared.spec.variant_name)
    write_run_reports(
        prepared.run_dir,
        run_samples,
        batch_results,
        case_rows,
        metric_service,
        prepared.config.methods,
        prepared.config.runtime.image_size,
    )

    prepared.logger.log(
        stage="support_refactor",
        operation="complete run",
        inputs={"run_dir": str(prepared.run_dir), "variant": prepared.spec.key},
        result={
            "case_metrics_csv": str(prepared.run_dir / "metrics_case_level.csv"),
            "summary_csv": str(prepared.run_dir / "metrics_summary.csv") if metric_service is not None else None,
        },
        conclusion="modular support-line run finished",
        next_step="compare baseline and variant metrics from one unified runner",
    )
    return prepared
