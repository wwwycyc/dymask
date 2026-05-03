from __future__ import annotations

from DyMaskRefactor.nti_inversion import NTIInversionBackend
from DyMaskRefactor.v1 import DDIMInversionBackend


def build_inversion_backend(pipe, runtime):
    backend_name = str(runtime.inversion_backend).lower()
    if backend_name == "nti":
        return NTIInversionBackend(pipe, runtime)
    if backend_name == "ddim":
        return DDIMInversionBackend(pipe, runtime)
    raise ValueError(f"Unsupported inversion backend: {runtime.inversion_backend}")
