from __future__ import annotations

from DyMaskRefactor.metric_runtime import MetricRunner


class MetricService:
    def __init__(self, runtime, metric_config) -> None:
        self.runner = MetricRunner(runtime, metric_config)

    def compute_psnr(self, *args, **kwargs):
        return self.runner.compute_psnr(*args, **kwargs)

    def compute_lpips(self, *args, **kwargs):
        return self.runner.compute_lpips(*args, **kwargs)

    def evaluate_case(self, *args, **kwargs):
        return self.runner.evaluate_case(*args, **kwargs)

    def summarize(self, *args, **kwargs):
        return self.runner.summarize(*args, **kwargs)
