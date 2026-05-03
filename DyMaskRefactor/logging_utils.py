from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .utils import ensure_parent, timestamp_to_minute


class MarkdownExperimentLogger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._bootstrap()

    def _bootstrap(self) -> None:
        if self.path.exists():
            return
        ensure_parent(self.path)
        template = [
            "# DyMask 实验日志",
            "",
            "说明：",
            "- 使用 UTF-8 编码",
            "- 每条记录时间精确到分钟",
            "- 优先记录阶段、输入、结果、结论、下一步",
            "",
        ]
        self.path.write_text("\n".join(template), encoding="utf-8-sig")

    def _format_mapping(self, payload: Any) -> str:
        if payload is None:
            return "无"
        if isinstance(payload, str):
            return payload
        return json.dumps(payload, ensure_ascii=False, indent=2, default=str)

    def log(
        self,
        stage: str,
        operation: str,
        inputs: Any = None,
        result: Any = None,
        conclusion: str = "",
        next_step: str = "",
    ) -> None:
        entry = [
            "",
            f"## {timestamp_to_minute()}",
            f"阶段：{stage}",
            f"操作：{operation}",
            "输入：",
            "```json",
            self._format_mapping(inputs),
            "```",
            "结果：",
            "```json",
            self._format_mapping(result),
            "```",
            f"结论：{conclusion or '待补充'}",
            f"下一步：{next_step or '待补充'}",
            "",
        ]
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(entry))
