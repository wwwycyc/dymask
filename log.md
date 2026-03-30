# DyMask 实验日志

说明：
- 使用 UTF-8 编码
- 每条记录时间精确到分钟
- 以中文记录为主
- 重点记录阶段、输入、结果、结论、下一步


## 2026-03-28 09:53
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000001D6A7FABCC0>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可直接用于 source/target 配对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 09:54
阶段：样本抽样
操作：生成 V1 样本清单并导出图片缓存
输入：
```json
{
  "sample_count": 4,
  "sample_seed": 42
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260328-0953",
  "manifest_json": "runs\\dymask_v1\\v1_20260328-0953\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260328-0953\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000051",
    "sample_001_row_000228",
    "sample_002_row_000501",
    "sample_003_row_000563"
  ]
}
```
结论：样本清单已固化，后续对比和消融将复用同一批样本。
下一步：根据 run_limit 决定是否进入模型推理。

## 2026-03-28 09:54
阶段：执行控制
操作：dry-run 结束
输入：
```json
{
  "dry_run": true
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260328-0953"
}
```
结论：本次仅验证了数据抽样、样本留存与日志链路。
下一步：取消 dry-run 后再执行 V1 编辑与评测。

## 2026-03-28 09:54
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x0000029A539E0640>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可直接用于 source/target 配对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 09:55
阶段：样本抽样
操作：生成 V1 样本清单并导出图片缓存
输入：
```json
{
  "sample_count": 1,
  "sample_seed": 42
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260328-0954",
  "manifest_json": "runs\\dymask_v1\\v1_20260328-0954\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260328-0954\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000228"
  ]
}
```
结论：样本清单已固化，后续对比和消融将复用同一批样本。
下一步：根据 run_limit 决定是否进入模型推理。

## 2026-03-28 09:55
阶段：样本执行
操作：开始运行单样本 V1 编辑
输入：
```json
{
  "sample_id": "sample_000_row_000228",
  "source_prompt": "painting of tree on river banks by Janine Robertson",
  "edit_prompt": "as a cubist painting",
  "target_prompt": "cubist painting of tree on river banks by Janine Robertson",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-0954\\samples\\sample_000_row_000228"
}
```
结论：进入 inversion 与多方法对比阶段。
下一步：完成单样本方法输出并计算指标。

## 2026-03-28 09:55
阶段：样本完成
操作：完成单样本多方法编辑
输入：
```json
{
  "sample_id": "sample_000_row_000228"
}
```
结果：
```json
{
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-0954\\samples\\sample_000_row_000228\\target_only\\edited.png"
  ]
}
```
结论：该样本的结果图、mask 汇总和调试信息均已落盘。
下一步：进入下一样本或汇总指标。

## 2026-03-28 09:55
阶段：实验汇总
操作：落盘 case-level 与 summary 指标
输入：
```json
{
  "run_limit": 1,
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260328-0954\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260328-0954\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260328-0954\\metrics_summary.json"
}
```
结论：V1 首轮实验产物已具备样本留存、方法输出、指标汇总和中文日志。
下一步：先用 run_limit=1 做烟雾验证，稳定后再扩到 8-16 个样本。

## 2026-03-28 09:55
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x0000015E5DF70640>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可直接用于 source/target 配对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 09:55
阶段：样本抽样
操作：生成 V1 样本清单并导出图片缓存
输入：
```json
{
  "sample_count": 1,
  "sample_seed": 42
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260328-0955",
  "manifest_json": "runs\\dymask_v1\\v1_20260328-0955\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260328-0955\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000228"
  ]
}
```
结论：样本清单已固化，后续对比和消融将复用同一批样本。
下一步：根据 run_limit 决定是否进入模型推理。

## 2026-03-28 09:56
阶段：样本执行
操作：开始运行单样本 V1 编辑
输入：
```json
{
  "sample_id": "sample_000_row_000228",
  "source_prompt": "painting of tree on river banks by Janine Robertson",
  "edit_prompt": "as a cubist painting",
  "target_prompt": "cubist painting of tree on river banks by Janine Robertson",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-0955\\samples\\sample_000_row_000228"
}
```
结论：进入 inversion 与多方法对比阶段。
下一步：完成单样本方法输出并计算指标。

## 2026-03-28 09:59
阶段：样本完成
操作：完成单样本多方法编辑
输入：
```json
{
  "sample_id": "sample_000_row_000228"
}
```
结果：
```json
{
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-0955\\samples\\sample_000_row_000228\\target_only\\edited.png"
  ]
}
```
结论：该样本的结果图、mask 汇总和调试信息均已落盘。
下一步：进入下一样本或汇总指标。

## 2026-03-28 09:59
阶段：实验汇总
操作：落盘 case-level 与 summary 指标
输入：
```json
{
  "run_limit": 1,
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260328-0955\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260328-0955\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260328-0955\\metrics_summary.json"
}
```
结论：V1 首轮实验产物已具备样本留存、方法输出、指标汇总和中文日志。
下一步：先用 run_limit=1 做烟雾验证，稳定后再扩到 8-16 个样本。

## 2026-03-28 10:13
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x00000167F5A94980>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可直接用于 source/target 配对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 10:13
阶段：样本抽样
操作：生成 V1 样本清单并导出图片缓存
输入：
```json
{
  "sample_count": 1,
  "sample_seed": 42
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260328-1013",
  "manifest_json": "runs\\dymask_v1\\v1_20260328-1013\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260328-1013\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000228"
  ]
}
```
结论：样本清单已固化，后续对比和消融将复用同一批样本。
下一步：根据 run_limit 决定是否进入模型推理。

## 2026-03-28 10:13
阶段：样本执行
操作：开始运行单样本 V1 编辑
输入：
```json
{
  "sample_id": "sample_000_row_000228",
  "source_prompt": "painting of tree on river banks by Janine Robertson",
  "edit_prompt": "as a cubist painting",
  "target_prompt": "cubist painting of tree on river banks by Janine Robertson",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-1013\\samples\\sample_000_row_000228"
}
```
结论：进入 inversion 与多方法对比阶段。
下一步：完成单样本方法输出并计算指标。

## 2026-03-28 10:13
阶段：样本完成
操作：完成单样本多方法编辑
输入：
```json
{
  "sample_id": "sample_000_row_000228"
}
```
结果：
```json
{
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-1013\\samples\\sample_000_row_000228\\target_only\\edited.png"
  ]
}
```
结论：该样本的结果图、mask 汇总和调试信息均已落盘。
下一步：进入下一样本或汇总指标。

## 2026-03-28 10:13
阶段：实验汇总
操作：落盘 case-level 与 summary 指标
输入：
```json
{
  "run_limit": 1,
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260328-1013\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260328-1013\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260328-1013\\metrics_summary.json"
}
```
结论：V1 首轮实验产物已具备样本留存、方法输出、指标汇总和中文日志。
下一步：先用 run_limit=1 做烟雾验证，稳定后再扩到 8-16 个样本。

## 2026-03-28 10:14
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x00000114EAD9E280>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可直接用于 source/target 配对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 10:14
阶段：样本抽样
操作：生成 V1 样本清单并导出图片缓存
输入：
```json
{
  "sample_count": 1,
  "sample_seed": 42
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260328-1014",
  "manifest_json": "runs\\dymask_v1\\v1_20260328-1014\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260328-1014\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000228"
  ]
}
```
结论：样本清单已固化，后续对比和消融将复用同一批样本。
下一步：根据 run_limit 决定是否进入模型推理。

## 2026-03-28 10:14
阶段：样本执行
操作：开始运行单样本 V1 编辑
输入：
```json
{
  "sample_id": "sample_000_row_000228",
  "source_prompt": "painting of tree on river banks by Janine Robertson",
  "edit_prompt": "as a cubist painting",
  "target_prompt": "cubist painting of tree on river banks by Janine Robertson",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-1014\\samples\\sample_000_row_000228"
}
```
结论：进入 inversion 与多方法对比阶段。
下一步：完成单样本方法输出并计算指标。

## 2026-03-28 10:14
阶段：样本完成
操作：完成单样本多方法编辑
输入：
```json
{
  "sample_id": "sample_000_row_000228"
}
```
结果：
```json
{
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-1014\\samples\\sample_000_row_000228\\target_only\\edited.png"
  ]
}
```
结论：该样本的结果图、mask 汇总和调试信息均已落盘。
下一步：进入下一样本或汇总指标。

## 2026-03-28 10:14
阶段：实验汇总
操作：落盘 case-level 与 summary 指标
输入：
```json
{
  "run_limit": 1,
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260328-1014\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260328-1014\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260328-1014\\metrics_summary.json"
}
```
结论：V1 首轮实验产物已具备样本留存、方法输出、指标汇总和中文日志。
下一步：先用 run_limit=1 做烟雾验证，稳定后再扩到 8-16 个样本。

## 2026-03-28 10:16
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000002007CC707C0>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可直接用于 source/target 配对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 10:16
阶段：样本抽样
操作：生成 V1 样本清单并导出图片缓存
输入：
```json
{
  "sample_count": 1,
  "sample_seed": 42
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260328-1016",
  "manifest_json": "runs\\dymask_v1\\v1_20260328-1016\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260328-1016\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000228"
  ]
}
```
结论：样本清单已固化，后续对比和消融将复用同一批样本。
下一步：根据 run_limit 决定是否进入模型推理。

## 2026-03-28 10:16
阶段：样本执行
操作：开始运行单样本 V1 编辑
输入：
```json
{
  "sample_id": "sample_000_row_000228",
  "source_prompt": "painting of tree on river banks by Janine Robertson",
  "edit_prompt": "as a cubist painting",
  "target_prompt": "cubist painting of tree on river banks by Janine Robertson",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-1016\\samples\\sample_000_row_000228"
}
```
结论：进入 inversion 与多方法对比阶段。
下一步：完成单样本方法输出并计算指标。

## 2026-03-28 10:16
阶段：样本完成
操作：完成单样本多方法编辑
输入：
```json
{
  "sample_id": "sample_000_row_000228"
}
```
结果：
```json
{
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-1016\\samples\\sample_000_row_000228\\target_only\\edited.png"
  ]
}
```
结论：该样本的结果图、mask 汇总和调试信息均已落盘。
下一步：进入下一样本或汇总指标。

## 2026-03-28 10:16
阶段：实验汇总
操作：落盘 case-level 与 summary 指标
输入：
```json
{
  "run_limit": 1,
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260328-1016\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260328-1016\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260328-1016\\metrics_summary.json"
}
```
结论：V1 首轮实验产物已具备样本留存、方法输出、指标汇总和中文日志。
下一步：先用 run_limit=1 做烟雾验证，稳定后再扩到 8-16 个样本。

## 2026-03-28 10:17
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x0000024B060B0B40>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可直接用于 source/target 配对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 10:17
阶段：样本抽样
操作：生成 V1 样本清单并导出图片缓存
输入：
```json
{
  "sample_count": 1,
  "sample_seed": 42
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260328-1017",
  "manifest_json": "runs\\dymask_v1\\v1_20260328-1017\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260328-1017\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000228"
  ]
}
```
结论：样本清单已固化，后续对比和消融将复用同一批样本。
下一步：根据 run_limit 决定是否进入模型推理。

## 2026-03-28 10:17
阶段：样本执行
操作：开始运行单样本 V1 编辑
输入：
```json
{
  "sample_id": "sample_000_row_000228",
  "source_prompt": "painting of tree on river banks by Janine Robertson",
  "edit_prompt": "as a cubist painting",
  "target_prompt": "cubist painting of tree on river banks by Janine Robertson",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-1017\\samples\\sample_000_row_000228"
}
```
结论：进入 inversion 与多方法对比阶段。
下一步：完成单样本方法输出并计算指标。

## 2026-03-28 10:17
阶段：样本完成
操作：完成单样本多方法编辑
输入：
```json
{
  "sample_id": "sample_000_row_000228"
}
```
结果：
```json
{
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-1017\\samples\\sample_000_row_000228\\target_only\\edited.png"
  ]
}
```
结论：该样本的结果图、mask 汇总和调试信息均已落盘。
下一步：进入下一样本或汇总指标。

## 2026-03-28 10:17
阶段：实验汇总
操作：落盘 case-level 与 summary 指标
输入：
```json
{
  "run_limit": 1,
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260328-1017\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260328-1017\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260328-1017\\metrics_summary.json"
}
```
结论：V1 首轮实验产物已具备样本留存、方法输出、指标汇总和中文日志。
下一步：先用 run_limit=1 做烟雾验证，稳定后再扩到 8-16 个样本。

## 2026-03-28 10:50
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x0000028EBA006B40>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 10:50
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 2,
  "sample_seed": 42,
  "phase": "phase0",
  "methods": []
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase0_20260328-1050",
  "manifest_json": "runs\\dymask_v1\\phase0_20260328-1050\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase0_20260328-1050\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000051",
    "sample_001_row_000228"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 10:50
阶段：执行控制
操作：dry-run 结束
输入：
```json
{
  "dry_run": true,
  "phase": "phase0"
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase0_20260328-1050"
}
```
结论：本次仅验证数据抽样、样本留存和日志链路。
下一步：取消 dry-run 后再执行对应 phase。

## 2026-03-28 10:51
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x0000022648A86B00>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 10:51
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 1,
  "sample_seed": 42,
  "phase": "phase0",
  "methods": []
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase0_20260328-1051",
  "manifest_json": "runs\\dymask_v1\\phase0_20260328-1051\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase0_20260328-1051\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000228"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 10:51
阶段：Phase 0 反演与重建
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000228",
  "source_prompt": "painting of tree on river banks by Janine Robertson",
  "edit_prompt": "as a cubist painting",
  "target_prompt": "cubist painting of tree on river banks by Janine Robertson",
  "methods": []
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase0_20260328-1051\\samples\\sample_000_row_000228"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 10:51
阶段：Phase 0 反演与重建
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000228",
  "phase": "phase0"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase0_20260328-1051\\samples\\sample_000_row_000228\\source_reconstruction.png",
  "methods": [],
  "artifacts": []
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 10:51
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase0",
  "run_limit": 1,
  "methods": []
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase0_20260328-1051\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase0_20260328-1051\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase0_20260328-1051\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 10:51
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000001F5C7DF2E40>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 10:51
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 1,
  "sample_seed": 42,
  "phase": "phase2",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase2_20260328-1051",
  "manifest_json": "runs\\dymask_v1\\phase2_20260328-1051\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase2_20260328-1051\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000228"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 10:51
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000228",
  "source_prompt": "painting of tree on river banks by Janine Robertson",
  "edit_prompt": "as a cubist painting",
  "target_prompt": "cubist painting of tree on river banks by Janine Robertson",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1051\\samples\\sample_000_row_000228"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 10:51
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000228",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1051\\samples\\sample_000_row_000228\\source_reconstruction.png",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1051\\samples\\sample_000_row_000228\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1051\\samples\\sample_000_row_000228\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1051\\samples\\sample_000_row_000228\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 10:51
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase2",
  "run_limit": 1,
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase2_20260328-1051\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase2_20260328-1051\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase2_20260328-1051\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 11:09
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x0000022F95AA70C0>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 11:09
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "phase": "phase0",
  "methods": []
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase0_20260328-1109",
  "manifest_json": "runs\\dymask_v1\\phase0_20260328-1109\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase0_20260328-1109\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000051",
    "sample_001_row_000209",
    "sample_002_row_000228",
    "sample_003_row_000285",
    "sample_004_row_000457",
    "sample_005_row_000501",
    "sample_006_row_000563",
    "sample_007_row_001116"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 11:09
阶段：Phase 0 反演与重建
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "source_prompt": "Picture leaves, berries, table, kettle, window, the tea party, Cup, dishes, still life, blind, basket, jam",
  "edit_prompt": "Turn the leaves into pine needles",
  "target_prompt": "Picture pine needles, berries, table, kettle, window, the tea party, Cup, dishes, still life, blind, basket, jam",
  "methods": []
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase0_20260328-1109\\samples\\sample_000_row_000051"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:09
阶段：Phase 0 反演与重建
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "phase": "phase0"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase0_20260328-1109\\samples\\sample_000_row_000051\\source_reconstruction.png",
  "methods": [],
  "artifacts": []
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:09
阶段：Phase 0 反演与重建
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000209",
  "source_prompt": "John Atkinson Grimshaw, Moonlight On The Lake, Roundhay Park, Leeds, 1872",
  "edit_prompt": "make the lake full of lava",
  "target_prompt": "John Atkinson Grimshaw, Moonlight On The Lava Lake, Roundhay Park, Leeds, 1872",
  "methods": []
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase0_20260328-1109\\samples\\sample_001_row_000209"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:09
阶段：Phase 0 反演与重建
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000209",
  "phase": "phase0"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase0_20260328-1109\\samples\\sample_001_row_000209\\source_reconstruction.png",
  "methods": [],
  "artifacts": []
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:09
阶段：Phase 0 反演与重建
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000228",
  "source_prompt": "painting of tree on river banks by Janine Robertson",
  "edit_prompt": "as a cubist painting",
  "target_prompt": "cubist painting of tree on river banks by Janine Robertson",
  "methods": []
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase0_20260328-1109\\samples\\sample_002_row_000228"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:09
阶段：Phase 0 反演与重建
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000228",
  "phase": "phase0"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase0_20260328-1109\\samples\\sample_002_row_000228\\source_reconstruction.png",
  "methods": [],
  "artifacts": []
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:09
阶段：Phase 0 反演与重建
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000285",
  "source_prompt": "Central Park Winter - San Remo Through Trees - New York City",
  "edit_prompt": "have the trees be palm trees",
  "target_prompt": "Central Park Winter - San Remo Through Palm Trees - New York City",
  "methods": []
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase0_20260328-1109\\samples\\sample_003_row_000285"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:09
阶段：Phase 0 反演与重建
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000285",
  "phase": "phase0"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase0_20260328-1109\\samples\\sample_003_row_000285\\source_reconstruction.png",
  "methods": [],
  "artifacts": []
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:09
阶段：Phase 0 反演与重建
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000457",
  "source_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting",
  "edit_prompt": "Make the sky purple",
  "target_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting, Purple Sky",
  "methods": []
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase0_20260328-1109\\samples\\sample_004_row_000457"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:09
阶段：Phase 0 反演与重建
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000457",
  "phase": "phase0"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase0_20260328-1109\\samples\\sample_004_row_000457\\source_reconstruction.png",
  "methods": [],
  "artifacts": []
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:09
阶段：Phase 0 反演与重建
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000501",
  "source_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities",
  "edit_prompt": "add a tornado",
  "target_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities with Tornado",
  "methods": []
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase0_20260328-1109\\samples\\sample_005_row_000501"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:10
阶段：Phase 0 反演与重建
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000501",
  "phase": "phase0"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase0_20260328-1109\\samples\\sample_005_row_000501\\source_reconstruction.png",
  "methods": [],
  "artifacts": []
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:10
阶段：Phase 0 反演与重建
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000563",
  "source_prompt": "\"\"\"Peach Packing, Spartanburg County\"\" by Wenonah Day Bell (1890–1981), 1938. Oil on canvas, 38-  by 48-  inches.\"",
  "edit_prompt": "make it a photo",
  "target_prompt": "\"\"Peach Packing, Spartanburg County\" by Wenonah Day Bell (1890–1981), 1938. Photographic print, 38-  by 48-  inches.\"",
  "methods": []
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase0_20260328-1109\\samples\\sample_006_row_000563"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:10
阶段：Phase 0 反演与重建
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000563",
  "phase": "phase0"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase0_20260328-1109\\samples\\sample_006_row_000563\\source_reconstruction.png",
  "methods": [],
  "artifacts": []
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:10
阶段：Phase 0 反演与重建
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_001116",
  "source_prompt": "January 7, path in the snow at Saint Vincent",
  "edit_prompt": "make it a beach",
  "target_prompt": "January 7, path in the sand at Saint Vincent",
  "methods": []
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase0_20260328-1109\\samples\\sample_007_row_001116"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:10
阶段：Phase 0 反演与重建
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_001116",
  "phase": "phase0"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase0_20260328-1109\\samples\\sample_007_row_001116\\source_reconstruction.png",
  "methods": [],
  "artifacts": []
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:10
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase0",
  "run_limit": 8,
  "methods": []
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase0_20260328-1109\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase0_20260328-1109\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase0_20260328-1109\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 11:19
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000001B823436B00>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 11:19
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "phase": "phase1",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase1_20260328-1119",
  "manifest_json": "runs\\dymask_v1\\phase1_20260328-1119\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase1_20260328-1119\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000051",
    "sample_001_row_000209",
    "sample_002_row_000228",
    "sample_003_row_000285",
    "sample_004_row_000457",
    "sample_005_row_000501",
    "sample_006_row_000563",
    "sample_007_row_001116"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 11:19
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "source_prompt": "Picture leaves, berries, table, kettle, window, the tea party, Cup, dishes, still life, blind, basket, jam",
  "edit_prompt": "Turn the leaves into pine needles",
  "target_prompt": "Picture pine needles, berries, table, kettle, window, the tea party, Cup, dishes, still life, blind, basket, jam",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_000_row_000051"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:19
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_000_row_000051\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_000_row_000051\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:19
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000209",
  "source_prompt": "John Atkinson Grimshaw, Moonlight On The Lake, Roundhay Park, Leeds, 1872",
  "edit_prompt": "make the lake full of lava",
  "target_prompt": "John Atkinson Grimshaw, Moonlight On The Lava Lake, Roundhay Park, Leeds, 1872",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_001_row_000209"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:20
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000209",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_001_row_000209\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_001_row_000209\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:20
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000228",
  "source_prompt": "painting of tree on river banks by Janine Robertson",
  "edit_prompt": "as a cubist painting",
  "target_prompt": "cubist painting of tree on river banks by Janine Robertson",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_002_row_000228"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:20
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000228",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_002_row_000228\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_002_row_000228\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:20
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000285",
  "source_prompt": "Central Park Winter - San Remo Through Trees - New York City",
  "edit_prompt": "have the trees be palm trees",
  "target_prompt": "Central Park Winter - San Remo Through Palm Trees - New York City",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_003_row_000285"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:20
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000285",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_003_row_000285\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_003_row_000285\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:20
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000457",
  "source_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting",
  "edit_prompt": "Make the sky purple",
  "target_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting, Purple Sky",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_004_row_000457"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:20
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000457",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_004_row_000457\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_004_row_000457\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:20
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000501",
  "source_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities",
  "edit_prompt": "add a tornado",
  "target_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities with Tornado",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_005_row_000501"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:20
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000501",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_005_row_000501\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_005_row_000501\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:20
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000563",
  "source_prompt": "\"\"\"Peach Packing, Spartanburg County\"\" by Wenonah Day Bell (1890–1981), 1938. Oil on canvas, 38-  by 48-  inches.\"",
  "edit_prompt": "make it a photo",
  "target_prompt": "\"\"Peach Packing, Spartanburg County\" by Wenonah Day Bell (1890–1981), 1938. Photographic print, 38-  by 48-  inches.\"",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_006_row_000563"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:20
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000563",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_006_row_000563\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_006_row_000563\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:20
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_001116",
  "source_prompt": "January 7, path in the snow at Saint Vincent",
  "edit_prompt": "make it a beach",
  "target_prompt": "January 7, path in the sand at Saint Vincent",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_007_row_001116"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:20
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_001116",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_007_row_001116\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_007_row_001116\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:20
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase1",
  "run_limit": 8,
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase1_20260328-1119\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase1_20260328-1119\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase1_20260328-1119\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 11:24
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000001F3C673A300>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 11:24
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "phase": "phase1",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase1_20260328-1124",
  "manifest_json": "runs\\dymask_v1\\phase1_20260328-1124\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase1_20260328-1124\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000051",
    "sample_001_row_000209",
    "sample_002_row_000228",
    "sample_003_row_000285",
    "sample_004_row_000457",
    "sample_005_row_000501",
    "sample_006_row_000563",
    "sample_007_row_001116"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 11:24
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "source_prompt": "Picture leaves, berries, table, kettle, window, the tea party, Cup, dishes, still life, blind, basket, jam",
  "edit_prompt": "Turn the leaves into pine needles",
  "target_prompt": "Picture pine needles, berries, table, kettle, window, the tea party, Cup, dishes, still life, blind, basket, jam",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_000_row_000051"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:24
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_000_row_000051\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_000_row_000051\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:24
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000209",
  "source_prompt": "John Atkinson Grimshaw, Moonlight On The Lake, Roundhay Park, Leeds, 1872",
  "edit_prompt": "make the lake full of lava",
  "target_prompt": "John Atkinson Grimshaw, Moonlight On The Lava Lake, Roundhay Park, Leeds, 1872",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_001_row_000209"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:25
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000209",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_001_row_000209\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_001_row_000209\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:25
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000228",
  "source_prompt": "painting of tree on river banks by Janine Robertson",
  "edit_prompt": "as a cubist painting",
  "target_prompt": "cubist painting of tree on river banks by Janine Robertson",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_002_row_000228"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:25
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000228",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_002_row_000228\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_002_row_000228\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:25
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000285",
  "source_prompt": "Central Park Winter - San Remo Through Trees - New York City",
  "edit_prompt": "have the trees be palm trees",
  "target_prompt": "Central Park Winter - San Remo Through Palm Trees - New York City",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_003_row_000285"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:25
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000285",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_003_row_000285\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_003_row_000285\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:25
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000457",
  "source_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting",
  "edit_prompt": "Make the sky purple",
  "target_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting, Purple Sky",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_004_row_000457"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:25
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000457",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_004_row_000457\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_004_row_000457\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:25
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000501",
  "source_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities",
  "edit_prompt": "add a tornado",
  "target_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities with Tornado",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_005_row_000501"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:25
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000501",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_005_row_000501\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_005_row_000501\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:25
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000563",
  "source_prompt": "\"\"\"Peach Packing, Spartanburg County\"\" by Wenonah Day Bell (1890–1981), 1938. Oil on canvas, 38-  by 48-  inches.\"",
  "edit_prompt": "make it a photo",
  "target_prompt": "\"\"Peach Packing, Spartanburg County\" by Wenonah Day Bell (1890–1981), 1938. Photographic print, 38-  by 48-  inches.\"",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_006_row_000563"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:25
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000563",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_006_row_000563\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_006_row_000563\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:25
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_001116",
  "source_prompt": "January 7, path in the snow at Saint Vincent",
  "edit_prompt": "make it a beach",
  "target_prompt": "January 7, path in the sand at Saint Vincent",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_007_row_001116"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:25
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_001116",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_007_row_001116\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1124\\samples\\sample_007_row_001116\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:25
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase1",
  "run_limit": 8,
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase1_20260328-1124\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase1_20260328-1124\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase1_20260328-1124\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 11:26
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000001F52232AF80>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 11:26
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "phase": "phase1",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase1_20260328-1126",
  "manifest_json": "runs\\dymask_v1\\phase1_20260328-1126\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase1_20260328-1126\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000051",
    "sample_001_row_000209",
    "sample_002_row_000228",
    "sample_003_row_000285",
    "sample_004_row_000457",
    "sample_005_row_000501",
    "sample_006_row_000563",
    "sample_007_row_001116"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 11:26
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "source_prompt": "Picture leaves, berries, table, kettle, window, the tea party, Cup, dishes, still life, blind, basket, jam",
  "edit_prompt": "Turn the leaves into pine needles",
  "target_prompt": "Picture pine needles, berries, table, kettle, window, the tea party, Cup, dishes, still life, blind, basket, jam",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_000_row_000051"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:26
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_000_row_000051\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_000_row_000051\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:26
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000209",
  "source_prompt": "John Atkinson Grimshaw, Moonlight On The Lake, Roundhay Park, Leeds, 1872",
  "edit_prompt": "make the lake full of lava",
  "target_prompt": "John Atkinson Grimshaw, Moonlight On The Lava Lake, Roundhay Park, Leeds, 1872",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_001_row_000209"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:26
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000209",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_001_row_000209\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_001_row_000209\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:26
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000228",
  "source_prompt": "painting of tree on river banks by Janine Robertson",
  "edit_prompt": "as a cubist painting",
  "target_prompt": "cubist painting of tree on river banks by Janine Robertson",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_002_row_000228"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:26
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000228",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_002_row_000228\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_002_row_000228\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:26
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000285",
  "source_prompt": "Central Park Winter - San Remo Through Trees - New York City",
  "edit_prompt": "have the trees be palm trees",
  "target_prompt": "Central Park Winter - San Remo Through Palm Trees - New York City",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_003_row_000285"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:27
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000285",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_003_row_000285\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_003_row_000285\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:27
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000457",
  "source_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting",
  "edit_prompt": "Make the sky purple",
  "target_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting, Purple Sky",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_004_row_000457"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:27
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000457",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_004_row_000457\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_004_row_000457\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:27
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000501",
  "source_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities",
  "edit_prompt": "add a tornado",
  "target_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities with Tornado",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_005_row_000501"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:27
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000501",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_005_row_000501\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_005_row_000501\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:27
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000563",
  "source_prompt": "\"\"\"Peach Packing, Spartanburg County\"\" by Wenonah Day Bell (1890–1981), 1938. Oil on canvas, 38-  by 48-  inches.\"",
  "edit_prompt": "make it a photo",
  "target_prompt": "\"\"Peach Packing, Spartanburg County\" by Wenonah Day Bell (1890–1981), 1938. Photographic print, 38-  by 48-  inches.\"",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_006_row_000563"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:27
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000563",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_006_row_000563\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_006_row_000563\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:27
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_001116",
  "source_prompt": "January 7, path in the snow at Saint Vincent",
  "edit_prompt": "make it a beach",
  "target_prompt": "January 7, path in the sand at Saint Vincent",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_007_row_001116"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:27
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_001116",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_007_row_001116\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1126\\samples\\sample_007_row_001116\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:27
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase1",
  "run_limit": 8,
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase1_20260328-1126\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase1_20260328-1126\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase1_20260328-1126\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 11:59
阶段：样本复跑
操作：从已有 sample.json 载入单样本并保留当前提示词
输入：
```json
{
  "sample_json": "runs\\dymask_v1\\phase1_20260328-1119\\samples\\sample_000_row_000051\\sample.json"
}
```
结果：
```json
{
  "sample_id": "sample_000_row_000051",
  "source_prompt": "pine leaves in a still life scene with berries, kettle, cups, and jam",
  "target_prompt": "pine needles in a still life scene with berries, kettle, cups, and jam",
  "run_dir": "runs\\dymask_v1\\phase1_20260328-1159"
}
```
结论：将按 sample.json 当前内容复跑该样本，不再回源 parquet 覆盖提示词。
下一步：进入对应 phase 的单样本验证。

## 2026-03-28 11:59
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "phase": "phase1",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase1_20260328-1159",
  "manifest_json": "runs\\dymask_v1\\phase1_20260328-1159\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase1_20260328-1159\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000051"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 11:59
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "source_prompt": "pine leaves in a still life scene with berries, kettle, cups, and jam",
  "edit_prompt": "Turn the leaves into pine needles",
  "target_prompt": "pine needles in a still life scene with berries, kettle, cups, and jam",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1159\\samples\\sample_000_row_000051"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 11:59
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1159\\samples\\sample_000_row_000051\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1159\\samples\\sample_000_row_000051\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 11:59
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase1",
  "run_limit": 1,
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase1_20260328-1159\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase1_20260328-1159\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase1_20260328-1159\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 15:57
阶段：样本复跑
操作：从已有 sample.json 载入单样本并保留当前提示词
输入：
```json
{
  "sample_json": "runs\\dymask_v1\\phase1_20260328-1159\\samples\\sample_000_row_000051\\sample.json"
}
```
结果：
```json
{
  "sample_id": "sample_000_row_000051",
  "source_prompt": "pine leaves in a still life scene with berries, kettle, cups, and jam",
  "target_prompt": "pine needles in a still life scene with berries, kettle, cups, and jam",
  "run_dir": "runs\\dymask_v1\\phase1_20260328-1557"
}
```
结论：将按 sample.json 当前内容复跑该样本，不再回源 parquet 覆盖提示词。
下一步：进入对应 phase 的单样本验证。

## 2026-03-28 15:57
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "phase": "phase1",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase1_20260328-1557",
  "manifest_json": "runs\\dymask_v1\\phase1_20260328-1557\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase1_20260328-1557\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000051"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 15:57
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "source_prompt": "pine leaves in a still life scene with berries, kettle, cups, and jam",
  "edit_prompt": "Turn the leaves into pine needles",
  "target_prompt": "pine needles in a still life scene with berries, kettle, cups, and jam",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1557\\samples\\sample_000_row_000051"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 15:57
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1557\\samples\\sample_000_row_000051\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1557\\samples\\sample_000_row_000051\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 15:57
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase1",
  "run_limit": 1,
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase1_20260328-1557\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase1_20260328-1557\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase1_20260328-1557\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 15:58
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000001C4FB81C840>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 15:58
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "phase": "phase1",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase1_20260328-1558",
  "manifest_json": "runs\\dymask_v1\\phase1_20260328-1558\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase1_20260328-1558\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000051",
    "sample_001_row_000209",
    "sample_002_row_000228",
    "sample_003_row_000285",
    "sample_004_row_000457",
    "sample_005_row_000501",
    "sample_006_row_000563",
    "sample_007_row_001116"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 15:58
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "source_prompt": "Picture leaves, berries, table, kettle, window, the tea party, Cup, dishes, still life, blind, basket, jam",
  "edit_prompt": "Turn the leaves into pine needles",
  "target_prompt": "Picture pine needles, berries, table, kettle, window, the tea party, Cup, dishes, still life, blind, basket, jam",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_000_row_000051"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 15:59
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_000_row_000051\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_000_row_000051\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 15:59
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000209",
  "source_prompt": "John Atkinson Grimshaw, Moonlight On The Lake, Roundhay Park, Leeds, 1872",
  "edit_prompt": "make the lake full of lava",
  "target_prompt": "John Atkinson Grimshaw, Moonlight On The Lava Lake, Roundhay Park, Leeds, 1872",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_001_row_000209"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 15:59
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000209",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_001_row_000209\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_001_row_000209\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 15:59
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000228",
  "source_prompt": "painting of tree on river banks by Janine Robertson",
  "edit_prompt": "as a cubist painting",
  "target_prompt": "cubist painting of tree on river banks by Janine Robertson",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_002_row_000228"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 15:59
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000228",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_002_row_000228\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_002_row_000228\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 15:59
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000285",
  "source_prompt": "Central Park Winter - San Remo Through Trees - New York City",
  "edit_prompt": "have the trees be palm trees",
  "target_prompt": "Central Park Winter - San Remo Through Palm Trees - New York City",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_003_row_000285"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 15:59
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000285",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_003_row_000285\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_003_row_000285\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 15:59
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000457",
  "source_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting",
  "edit_prompt": "Make the sky purple",
  "target_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting, Purple Sky",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_004_row_000457"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 15:59
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000457",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_004_row_000457\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_004_row_000457\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 15:59
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000501",
  "source_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities",
  "edit_prompt": "add a tornado",
  "target_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities with Tornado",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_005_row_000501"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 15:59
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000501",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_005_row_000501\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_005_row_000501\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 15:59
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000563",
  "source_prompt": "\"\"\"Peach Packing, Spartanburg County\"\" by Wenonah Day Bell (1890–1981), 1938. Oil on canvas, 38-  by 48-  inches.\"",
  "edit_prompt": "make it a photo",
  "target_prompt": "\"\"Peach Packing, Spartanburg County\" by Wenonah Day Bell (1890–1981), 1938. Photographic print, 38-  by 48-  inches.\"",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_006_row_000563"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 15:59
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000563",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_006_row_000563\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_006_row_000563\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 15:59
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_001116",
  "source_prompt": "January 7, path in the snow at Saint Vincent",
  "edit_prompt": "make it a beach",
  "target_prompt": "January 7, path in the sand at Saint Vincent",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_007_row_001116"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:00
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_001116",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_007_row_001116\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1558\\samples\\sample_007_row_001116\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:00
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase1",
  "run_limit": 8,
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase1_20260328-1558\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase1_20260328-1558\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase1_20260328-1558\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 16:00
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x0000020E4056BF80>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 16:00
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "phase": "phase1",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase1_20260328-1600",
  "manifest_json": "runs\\dymask_v1\\phase1_20260328-1600\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase1_20260328-1600\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000051",
    "sample_001_row_000209",
    "sample_002_row_000228",
    "sample_003_row_000285",
    "sample_004_row_000457",
    "sample_005_row_000501",
    "sample_006_row_000563",
    "sample_007_row_001116"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 16:00
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "source_prompt": "Picture leaves, berries, table, kettle, window, the tea party, Cup, dishes, still life, blind, basket, jam",
  "edit_prompt": "Turn the leaves into pine needles",
  "target_prompt": "Picture pine needles, berries, table, kettle, window, the tea party, Cup, dishes, still life, blind, basket, jam",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_000_row_000051"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:01
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_000_row_000051\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_000_row_000051\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:01
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000209",
  "source_prompt": "John Atkinson Grimshaw, Moonlight On The Lake, Roundhay Park, Leeds, 1872",
  "edit_prompt": "make the lake full of lava",
  "target_prompt": "John Atkinson Grimshaw, Moonlight On The Lava Lake, Roundhay Park, Leeds, 1872",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_001_row_000209"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:01
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000209",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_001_row_000209\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_001_row_000209\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:01
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000228",
  "source_prompt": "painting of tree on river banks by Janine Robertson",
  "edit_prompt": "as a cubist painting",
  "target_prompt": "cubist painting of tree on river banks by Janine Robertson",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_002_row_000228"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:01
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000228",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_002_row_000228\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_002_row_000228\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:01
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000285",
  "source_prompt": "Central Park Winter - San Remo Through Trees - New York City",
  "edit_prompt": "have the trees be palm trees",
  "target_prompt": "Central Park Winter - San Remo Through Palm Trees - New York City",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_003_row_000285"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:01
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000285",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_003_row_000285\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_003_row_000285\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:01
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000457",
  "source_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting",
  "edit_prompt": "Make the sky purple",
  "target_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting, Purple Sky",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_004_row_000457"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:01
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000457",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_004_row_000457\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_004_row_000457\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:01
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000501",
  "source_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities",
  "edit_prompt": "add a tornado",
  "target_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities with Tornado",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_005_row_000501"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:01
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000501",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_005_row_000501\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_005_row_000501\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:01
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000563",
  "source_prompt": "\"\"\"Peach Packing, Spartanburg County\"\" by Wenonah Day Bell (1890–1981), 1938. Oil on canvas, 38-  by 48-  inches.\"",
  "edit_prompt": "make it a photo",
  "target_prompt": "\"\"Peach Packing, Spartanburg County\" by Wenonah Day Bell (1890–1981), 1938. Photographic print, 38-  by 48-  inches.\"",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_006_row_000563"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:02
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000563",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_006_row_000563\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_006_row_000563\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:02
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_001116",
  "source_prompt": "January 7, path in the snow at Saint Vincent",
  "edit_prompt": "make it a beach",
  "target_prompt": "January 7, path in the sand at Saint Vincent",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_007_row_001116"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:02
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_001116",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_007_row_001116\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1600\\samples\\sample_007_row_001116\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:02
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase1",
  "run_limit": 8,
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase1_20260328-1600\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase1_20260328-1600\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase1_20260328-1600\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 16:02
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000002B45C8CC4C0>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 16:02
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "phase": "phase1",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase1_20260328-1602",
  "manifest_json": "runs\\dymask_v1\\phase1_20260328-1602\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase1_20260328-1602\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000051",
    "sample_001_row_000209",
    "sample_002_row_000228",
    "sample_003_row_000285",
    "sample_004_row_000457",
    "sample_005_row_000501",
    "sample_006_row_000563",
    "sample_007_row_001116"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 16:02
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "source_prompt": "Picture leaves, berries, table, kettle, window, the tea party, Cup, dishes, still life, blind, basket, jam",
  "edit_prompt": "Turn the leaves into pine needles",
  "target_prompt": "Picture pine needles, berries, table, kettle, window, the tea party, Cup, dishes, still life, blind, basket, jam",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_000_row_000051"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:03
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_000_row_000051\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_000_row_000051\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:03
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000209",
  "source_prompt": "John Atkinson Grimshaw, Moonlight On The Lake, Roundhay Park, Leeds, 1872",
  "edit_prompt": "make the lake full of lava",
  "target_prompt": "John Atkinson Grimshaw, Moonlight On The Lava Lake, Roundhay Park, Leeds, 1872",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_001_row_000209"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:03
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000209",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_001_row_000209\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_001_row_000209\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:03
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000228",
  "source_prompt": "painting of tree on river banks by Janine Robertson",
  "edit_prompt": "as a cubist painting",
  "target_prompt": "cubist painting of tree on river banks by Janine Robertson",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_002_row_000228"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:03
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000228",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_002_row_000228\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_002_row_000228\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:03
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000285",
  "source_prompt": "Central Park Winter - San Remo Through Trees - New York City",
  "edit_prompt": "have the trees be palm trees",
  "target_prompt": "Central Park Winter - San Remo Through Palm Trees - New York City",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_003_row_000285"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:03
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000285",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_003_row_000285\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_003_row_000285\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:03
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000457",
  "source_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting",
  "edit_prompt": "Make the sky purple",
  "target_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting, Purple Sky",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_004_row_000457"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:03
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000457",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_004_row_000457\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_004_row_000457\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:03
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000501",
  "source_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities",
  "edit_prompt": "add a tornado",
  "target_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities with Tornado",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_005_row_000501"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:04
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000501",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_005_row_000501\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_005_row_000501\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:04
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000563",
  "source_prompt": "\"\"\"Peach Packing, Spartanburg County\"\" by Wenonah Day Bell (1890–1981), 1938. Oil on canvas, 38-  by 48-  inches.\"",
  "edit_prompt": "make it a photo",
  "target_prompt": "\"\"Peach Packing, Spartanburg County\" by Wenonah Day Bell (1890–1981), 1938. Photographic print, 38-  by 48-  inches.\"",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_006_row_000563"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:04
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000563",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_006_row_000563\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_006_row_000563\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:04
阶段：Phase 1 target-only 编辑
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_001116",
  "source_prompt": "January 7, path in the snow at Saint Vincent",
  "edit_prompt": "make it a beach",
  "target_prompt": "January 7, path in the sand at Saint Vincent",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_007_row_001116"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:04
阶段：Phase 1 target-only 编辑
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_001116",
  "phase": "phase1"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_007_row_001116\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase1_20260328-1602\\samples\\sample_007_row_001116\\target_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:04
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase1",
  "run_limit": 8,
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase1_20260328-1602\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase1_20260328-1602\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase1_20260328-1602\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 16:25
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000002096D4DCB40>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 16:25
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "phase": "phase2",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase2_20260328-1625",
  "manifest_json": "runs\\dymask_v1\\phase2_20260328-1625\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase2_20260328-1625\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000051",
    "sample_001_row_000209",
    "sample_002_row_000228",
    "sample_003_row_000285",
    "sample_004_row_000457",
    "sample_005_row_000501",
    "sample_006_row_000563",
    "sample_007_row_001116"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 16:25
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "source_prompt": "Picture leaves, berries, table, kettle, window, the tea party, Cup, dishes, still life, blind, basket, jam",
  "edit_prompt": "Turn the leaves into pine needles",
  "target_prompt": "Picture pine needles, berries, table, kettle, window, the tea party, Cup, dishes, still life, blind, basket, jam",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_000_row_000051"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:25
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_000_row_000051\\source_reconstruction.png",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_000_row_000051\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_000_row_000051\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_000_row_000051\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:25
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000209",
  "source_prompt": "John Atkinson Grimshaw, Moonlight On The Lake, Roundhay Park, Leeds, 1872",
  "edit_prompt": "make the lake full of lava",
  "target_prompt": "John Atkinson Grimshaw, Moonlight On The Lava Lake, Roundhay Park, Leeds, 1872",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_001_row_000209"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:26
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000209",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_001_row_000209\\source_reconstruction.png",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_001_row_000209\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_001_row_000209\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_001_row_000209\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:26
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000228",
  "source_prompt": "painting of tree on river banks by Janine Robertson",
  "edit_prompt": "as a cubist painting",
  "target_prompt": "cubist painting of tree on river banks by Janine Robertson",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_002_row_000228"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:26
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000228",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_002_row_000228\\source_reconstruction.png",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_002_row_000228\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_002_row_000228\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_002_row_000228\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:26
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000285",
  "source_prompt": "Central Park Winter - San Remo Through Trees - New York City",
  "edit_prompt": "have the trees be palm trees",
  "target_prompt": "Central Park Winter - San Remo Through Palm Trees - New York City",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_003_row_000285"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:27
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000285",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_003_row_000285\\source_reconstruction.png",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_003_row_000285\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_003_row_000285\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_003_row_000285\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:27
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000457",
  "source_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting",
  "edit_prompt": "Make the sky purple",
  "target_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting, Purple Sky",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_004_row_000457"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:27
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000457",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_004_row_000457\\source_reconstruction.png",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_004_row_000457\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_004_row_000457\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_004_row_000457\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:27
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000501",
  "source_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities",
  "edit_prompt": "add a tornado",
  "target_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities with Tornado",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_005_row_000501"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:28
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000501",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_005_row_000501\\source_reconstruction.png",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_005_row_000501\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_005_row_000501\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_005_row_000501\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:28
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000563",
  "source_prompt": "\"\"\"Peach Packing, Spartanburg County\"\" by Wenonah Day Bell (1890–1981), 1938. Oil on canvas, 38-  by 48-  inches.\"",
  "edit_prompt": "make it a photo",
  "target_prompt": "\"\"Peach Packing, Spartanburg County\" by Wenonah Day Bell (1890–1981), 1938. Photographic print, 38-  by 48-  inches.\"",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_006_row_000563"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:28
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000563",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_006_row_000563\\source_reconstruction.png",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_006_row_000563\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_006_row_000563\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_006_row_000563\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:28
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_001116",
  "source_prompt": "January 7, path in the snow at Saint Vincent",
  "edit_prompt": "make it a beach",
  "target_prompt": "January 7, path in the sand at Saint Vincent",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_007_row_001116"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:28
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_001116",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_007_row_001116\\source_reconstruction.png",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_007_row_001116\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_007_row_001116\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1625\\samples\\sample_007_row_001116\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:28
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase2",
  "run_limit": 8,
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase2_20260328-1625\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase2_20260328-1625\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase2_20260328-1625\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 16:55
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x0000025EA258CF00>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 16:55
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": [
    7,
    11,
    48,
    113,
    209,
    285,
    428,
    501
  ],
  "phase": "phase2",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase2_20260328-1655",
  "manifest_json": "runs\\dymask_v1\\phase2_20260328-1655\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase2_20260328-1655\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000007",
    "sample_001_row_000011",
    "sample_002_row_000048",
    "sample_003_row_000113",
    "sample_004_row_000209",
    "sample_005_row_000285",
    "sample_006_row_000428",
    "sample_007_row_000501"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 16:55
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000007",
  "source_prompt": "The Great Outdoors-11.jpg",
  "edit_prompt": "Add a giant alien",
  "target_prompt": "The Great Outdoors with giant alien-11.jpg",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_000_row_000007"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:56
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000007",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_000_row_000007\\source_reconstruction.png",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_000_row_000007\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_000_row_000007\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_000_row_000007\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:56
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000011",
  "source_prompt": "Log cabin in the woods painting - Winter Scenes",
  "edit_prompt": "add a giant spider",
  "target_prompt": "Log cabin in the woods with giant spider painting - Winter Scenes",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_001_row_000011"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:56
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000011",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_001_row_000011\\source_reconstruction.png",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_001_row_000011\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_001_row_000011\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_001_row_000011\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:56
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000048",
  "source_prompt": "inle-lake-fishermen",
  "edit_prompt": "Add a herd of elephants",
  "target_prompt": "elephant herd mingling with fishermen at Lake Inle",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_002_row_000048"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:57
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000048",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_002_row_000048\\source_reconstruction.png",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_002_row_000048\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_002_row_000048\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_002_row_000048\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:57
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000113",
  "source_prompt": "The great elf city of Rivendell, sitting atop a waterfall as cascades of water spill around it",
  "edit_prompt": "Add a giant red dragon",
  "target_prompt": "The great elf city of Rivendell, sitting atop a waterfall as cascades of water spill around it with a giant red dragon flying overhead",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_003_row_000113"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:57
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000113",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_003_row_000113\\source_reconstruction.png",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_003_row_000113\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_003_row_000113\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_003_row_000113\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:57
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000209",
  "source_prompt": "John Atkinson Grimshaw, Moonlight On The Lake, Roundhay Park, Leeds, 1872",
  "edit_prompt": "make the lake full of lava",
  "target_prompt": "John Atkinson Grimshaw, Moonlight On The Lava Lake, Roundhay Park, Leeds, 1872",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_004_row_000209"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:58
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000209",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_004_row_000209\\source_reconstruction.png",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_004_row_000209\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_004_row_000209\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_004_row_000209\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:58
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000285",
  "source_prompt": "Central Park Winter - San Remo Through Trees - New York City",
  "edit_prompt": "have the trees be palm trees",
  "target_prompt": "Central Park Winter - San Remo Through Palm Trees - New York City",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_005_row_000285"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:58
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000285",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_005_row_000285\\source_reconstruction.png",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_005_row_000285\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_005_row_000285\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_005_row_000285\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:58
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000428",
  "source_prompt": "ACEO Limited Edition PRINT -  Landscape Print by Watercolor artist Jim Lagasse",
  "edit_prompt": "Replace the scenery with a Martian landscape",
  "target_prompt": "ACEO Limited Edition PRINT -  Martian Landscape Print by Watercolor artist Jim Lagasse",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_006_row_000428"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:58
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000428",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_006_row_000428\\source_reconstruction.png",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_006_row_000428\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_006_row_000428\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_006_row_000428\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:58
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_000501",
  "source_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities",
  "edit_prompt": "add a tornado",
  "target_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities with Tornado",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_007_row_000501"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 16:59
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_000501",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_007_row_000501\\source_reconstruction.png",
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_007_row_000501\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_007_row_000501\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1655\\samples\\sample_007_row_000501\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 16:59
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase2",
  "run_limit": 8,
  "methods": [
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase2_20260328-1655\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase2_20260328-1655\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase2_20260328-1655\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 17:00
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x0000025F79B4CF00>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 17:00
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": [
    7,
    11,
    48,
    113,
    209,
    285,
    428,
    501
  ],
  "phase": "phase2",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase2_20260328-1700",
  "manifest_json": "runs\\dymask_v1\\phase2_20260328-1700\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase2_20260328-1700\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000007",
    "sample_001_row_000011",
    "sample_002_row_000048",
    "sample_003_row_000113",
    "sample_004_row_000209",
    "sample_005_row_000285",
    "sample_006_row_000428",
    "sample_007_row_000501"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 17:00
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000007",
  "source_prompt": "The Great Outdoors-11.jpg",
  "edit_prompt": "Add a giant alien",
  "target_prompt": "The Great Outdoors with giant alien-11.jpg",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_000_row_000007"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:01
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000007",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_000_row_000007\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_000_row_000007\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_000_row_000007\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_000_row_000007\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_000_row_000007\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:01
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000011",
  "source_prompt": "Log cabin in the woods painting - Winter Scenes",
  "edit_prompt": "add a giant spider",
  "target_prompt": "Log cabin in the woods with giant spider painting - Winter Scenes",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_001_row_000011"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:01
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000011",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_001_row_000011\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_001_row_000011\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_001_row_000011\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_001_row_000011\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_001_row_000011\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:01
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000048",
  "source_prompt": "inle-lake-fishermen",
  "edit_prompt": "Add a herd of elephants",
  "target_prompt": "elephant herd mingling with fishermen at Lake Inle",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_002_row_000048"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:02
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000048",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_002_row_000048\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_002_row_000048\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_002_row_000048\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_002_row_000048\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_002_row_000048\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:02
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000113",
  "source_prompt": "The great elf city of Rivendell, sitting atop a waterfall as cascades of water spill around it",
  "edit_prompt": "Add a giant red dragon",
  "target_prompt": "The great elf city of Rivendell, sitting atop a waterfall as cascades of water spill around it with a giant red dragon flying overhead",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_003_row_000113"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:02
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000113",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_003_row_000113\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_003_row_000113\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_003_row_000113\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_003_row_000113\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_003_row_000113\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:02
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000209",
  "source_prompt": "John Atkinson Grimshaw, Moonlight On The Lake, Roundhay Park, Leeds, 1872",
  "edit_prompt": "make the lake full of lava",
  "target_prompt": "John Atkinson Grimshaw, Moonlight On The Lava Lake, Roundhay Park, Leeds, 1872",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_004_row_000209"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:03
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000209",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_004_row_000209\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_004_row_000209\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_004_row_000209\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_004_row_000209\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_004_row_000209\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:03
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000285",
  "source_prompt": "Central Park Winter - San Remo Through Trees - New York City",
  "edit_prompt": "have the trees be palm trees",
  "target_prompt": "Central Park Winter - San Remo Through Palm Trees - New York City",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_005_row_000285"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:03
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000285",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_005_row_000285\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_005_row_000285\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_005_row_000285\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_005_row_000285\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_005_row_000285\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:03
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000428",
  "source_prompt": "ACEO Limited Edition PRINT -  Landscape Print by Watercolor artist Jim Lagasse",
  "edit_prompt": "Replace the scenery with a Martian landscape",
  "target_prompt": "ACEO Limited Edition PRINT -  Martian Landscape Print by Watercolor artist Jim Lagasse",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_006_row_000428"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:04
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000428",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_006_row_000428\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_006_row_000428\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_006_row_000428\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_006_row_000428\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_006_row_000428\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:04
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_000501",
  "source_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities",
  "edit_prompt": "add a tornado",
  "target_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities with Tornado",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_007_row_000501"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:05
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_000501",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_007_row_000501\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_007_row_000501\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_007_row_000501\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_007_row_000501\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1700\\samples\\sample_007_row_000501\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:05
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase2",
  "run_limit": 8,
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase2_20260328-1700\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase2_20260328-1700\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase2_20260328-1700\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 17:15
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x00000141975FD4C0>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 17:15
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": [
    16,
    18,
    38,
    52,
    66,
    160,
    251,
    457
  ],
  "phase": "phase2",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase2_20260328-1715",
  "manifest_json": "runs\\dymask_v1\\phase2_20260328-1715\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase2_20260328-1715\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000016",
    "sample_001_row_000018",
    "sample_002_row_000038",
    "sample_003_row_000052",
    "sample_004_row_000066",
    "sample_005_row_000160",
    "sample_006_row_000251",
    "sample_007_row_000457"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 17:15
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000016",
  "source_prompt": "Asian woman playing piano in window background with light coming in (Vintage tone) Archivio Fotografico",
  "edit_prompt": "turn the background into a beach",
  "target_prompt": "Asian woman playing piano on beach background with light coming in (Vintage tone) Archivio Fotografico",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_000_row_000016"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:16
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000016",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_000_row_000016\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_000_row_000016\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_000_row_000016\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_000_row_000016\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_000_row_000016\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:16
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000018",
  "source_prompt": "rocky hill reflected in water under a starry night sky Stock fotó",
  "edit_prompt": "have the starry sky be full of purple rainbows",
  "target_prompt": "rocky hill reflected in water under a starry night sky full of purple rainbows Stock fotó",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_001_row_000018"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:16
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000018",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_001_row_000018\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_001_row_000018\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_001_row_000018\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_001_row_000018\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_001_row_000018\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:16
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000038",
  "source_prompt": "Fairy Glen by Tim McAndrew - Landscapes Waterscapes ( water, fairy glen, wales, green, conwy, long exposure, light, rays )",
  "edit_prompt": "Add a horse.",
  "target_prompt": "Fairy Glen with horse by Tim McAndrew - Landscapes Waterscapes ( water, fairy glen, horse, wales, green, conwy, long exposure, light, rays )",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_002_row_000038"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:17
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000038",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_002_row_000038\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_002_row_000038\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_002_row_000038\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_002_row_000038\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_002_row_000038\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:17
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000052",
  "source_prompt": "Original oil painting of a gorgeous forties style woman, by Linda Boucher from Brighton. Using strong reds and beautiful blue eyes, this painting has a vintage pinup feel to it.",
  "edit_prompt": "make her wearing a firefighter's outfit",
  "target_prompt": "Original oil painting of a gorgeous forties style firefighter wearing a firefighter's outfit, by Linda Boucher from Brighton. Using strong reds and beautiful blue eyes, this painting has a vintage pinup feel to it.",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_003_row_000052"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:18
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000052",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_003_row_000052\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_003_row_000052\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_003_row_000052\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_003_row_000052\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_003_row_000052\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:18
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000066",
  "source_prompt": "Live-Action de Lightning Returns: Final Fantasy XIII",
  "edit_prompt": "add a cat",
  "target_prompt": "Live-Action de Lightning Returns: Final Fantasy XIII with a cat",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_004_row_000066"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:18
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000066",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_004_row_000066\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_004_row_000066\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_004_row_000066\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_004_row_000066\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_004_row_000066\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:18
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000160",
  "source_prompt": "View of snow storm in Grand Teton National Park",
  "edit_prompt": "Add a tornado in the background",
  "target_prompt": "View of snow storm with tornado in Grand Teton National Park",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_005_row_000160"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:19
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000160",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_005_row_000160\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_005_row_000160\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_005_row_000160\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_005_row_000160\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_005_row_000160\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:19
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000251",
  "source_prompt": "Winter Sunrise Picture for Android, iPhone and iPad",
  "edit_prompt": "Replace the snow with rain",
  "target_prompt": "Winter Rain Picture for Android, iPhone and iPad",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_006_row_000251"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:19
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000251",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_006_row_000251\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_006_row_000251\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_006_row_000251\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_006_row_000251\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_006_row_000251\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:19
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_000457",
  "source_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting",
  "edit_prompt": "Make the sky purple",
  "target_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting, Purple Sky",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_007_row_000457"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:20
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_000457",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_007_row_000457\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_007_row_000457\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_007_row_000457\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_007_row_000457\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1715\\samples\\sample_007_row_000457\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:20
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase2",
  "run_limit": 8,
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase2_20260328-1715\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase2_20260328-1715\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase2_20260328-1715\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 17:32
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000002B4489ECDC0>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 17:32
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": [
    16,
    18,
    38,
    52,
    66,
    160,
    251,
    457
  ],
  "phase": "phase3",
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase3_20260328-1732",
  "manifest_json": "runs\\dymask_v1\\phase3_20260328-1732\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase3_20260328-1732\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000016",
    "sample_001_row_000018",
    "sample_002_row_000038",
    "sample_003_row_000052",
    "sample_004_row_000066",
    "sample_005_row_000160",
    "sample_006_row_000251",
    "sample_007_row_000457"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 17:32
阶段：Phase 3 仅 D_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000016",
  "source_prompt": "Asian woman playing piano in window background with light coming in (Vintage tone) Archivio Fotografico",
  "edit_prompt": "turn the background into a beach",
  "target_prompt": "Asian woman playing piano on beach background with light coming in (Vintage tone) Archivio Fotografico",
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_000_row_000016"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:32
阶段：Phase 3 仅 D_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000016",
  "phase": "phase3"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_000_row_000016\\source_reconstruction.png",
  "methods": [
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_000_row_000016\\discrepancy_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:32
阶段：Phase 3 仅 D_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000018",
  "source_prompt": "rocky hill reflected in water under a starry night sky Stock fotó",
  "edit_prompt": "have the starry sky be full of purple rainbows",
  "target_prompt": "rocky hill reflected in water under a starry night sky full of purple rainbows Stock fotó",
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_001_row_000018"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:32
阶段：Phase 3 仅 D_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000018",
  "phase": "phase3"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_001_row_000018\\source_reconstruction.png",
  "methods": [
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_001_row_000018\\discrepancy_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:32
阶段：Phase 3 仅 D_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000038",
  "source_prompt": "Fairy Glen by Tim McAndrew - Landscapes Waterscapes ( water, fairy glen, wales, green, conwy, long exposure, light, rays )",
  "edit_prompt": "Add a horse.",
  "target_prompt": "Fairy Glen with horse by Tim McAndrew - Landscapes Waterscapes ( water, fairy glen, horse, wales, green, conwy, long exposure, light, rays )",
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_002_row_000038"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:32
阶段：Phase 3 仅 D_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000038",
  "phase": "phase3"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_002_row_000038\\source_reconstruction.png",
  "methods": [
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_002_row_000038\\discrepancy_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:32
阶段：Phase 3 仅 D_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000052",
  "source_prompt": "Original oil painting of a gorgeous forties style woman, by Linda Boucher from Brighton. Using strong reds and beautiful blue eyes, this painting has a vintage pinup feel to it.",
  "edit_prompt": "make her wearing a firefighter's outfit",
  "target_prompt": "Original oil painting of a gorgeous forties style firefighter wearing a firefighter's outfit, by Linda Boucher from Brighton. Using strong reds and beautiful blue eyes, this painting has a vintage pinup feel to it.",
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_003_row_000052"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:32
阶段：Phase 3 仅 D_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000052",
  "phase": "phase3"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_003_row_000052\\source_reconstruction.png",
  "methods": [
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_003_row_000052\\discrepancy_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:32
阶段：Phase 3 仅 D_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000066",
  "source_prompt": "Live-Action de Lightning Returns: Final Fantasy XIII",
  "edit_prompt": "add a cat",
  "target_prompt": "Live-Action de Lightning Returns: Final Fantasy XIII with a cat",
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_004_row_000066"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:33
阶段：Phase 3 仅 D_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000066",
  "phase": "phase3"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_004_row_000066\\source_reconstruction.png",
  "methods": [
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_004_row_000066\\discrepancy_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:33
阶段：Phase 3 仅 D_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000160",
  "source_prompt": "View of snow storm in Grand Teton National Park",
  "edit_prompt": "Add a tornado in the background",
  "target_prompt": "View of snow storm with tornado in Grand Teton National Park",
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_005_row_000160"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:33
阶段：Phase 3 仅 D_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000160",
  "phase": "phase3"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_005_row_000160\\source_reconstruction.png",
  "methods": [
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_005_row_000160\\discrepancy_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:33
阶段：Phase 3 仅 D_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000251",
  "source_prompt": "Winter Sunrise Picture for Android, iPhone and iPad",
  "edit_prompt": "Replace the snow with rain",
  "target_prompt": "Winter Rain Picture for Android, iPhone and iPad",
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_006_row_000251"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:33
阶段：Phase 3 仅 D_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000251",
  "phase": "phase3"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_006_row_000251\\source_reconstruction.png",
  "methods": [
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_006_row_000251\\discrepancy_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:33
阶段：Phase 3 仅 D_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_000457",
  "source_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting",
  "edit_prompt": "Make the sky purple",
  "target_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting, Purple Sky",
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_007_row_000457"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:33
阶段：Phase 3 仅 D_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_000457",
  "phase": "phase3"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_007_row_000457\\source_reconstruction.png",
  "methods": [
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase3_20260328-1732\\samples\\sample_007_row_000457\\discrepancy_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:33
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase3",
  "run_limit": 8,
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase3_20260328-1732\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase3_20260328-1732\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase3_20260328-1732\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 17:42
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000002B7EC5ED1C0>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 17:42
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": [
    16,
    18,
    38,
    52,
    66,
    160,
    251,
    457
  ],
  "phase": "phase4",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase4_20260328-1742",
  "manifest_json": "runs\\dymask_v1\\phase4_20260328-1742\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase4_20260328-1742\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000016",
    "sample_001_row_000018",
    "sample_002_row_000038",
    "sample_003_row_000052",
    "sample_004_row_000066",
    "sample_005_row_000160",
    "sample_006_row_000251",
    "sample_007_row_000457"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 17:42
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000016",
  "source_prompt": "Asian woman playing piano in window background with light coming in (Vintage tone) Archivio Fotografico",
  "edit_prompt": "turn the background into a beach",
  "target_prompt": "Asian woman playing piano on beach background with light coming in (Vintage tone) Archivio Fotografico",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-1742\\samples\\sample_000_row_000016"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:43
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000001BCE84ACF00>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 17:43
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": [
    16,
    18,
    38,
    52,
    66,
    160,
    251,
    457
  ],
  "phase": "phase4",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase4_20260328-1743",
  "manifest_json": "runs\\dymask_v1\\phase4_20260328-1743\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase4_20260328-1743\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000016",
    "sample_001_row_000018",
    "sample_002_row_000038",
    "sample_003_row_000052",
    "sample_004_row_000066",
    "sample_005_row_000160",
    "sample_006_row_000251",
    "sample_007_row_000457"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 17:43
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000016",
  "source_prompt": "Asian woman playing piano in window background with light coming in (Vintage tone) Archivio Fotografico",
  "edit_prompt": "turn the background into a beach",
  "target_prompt": "Asian woman playing piano on beach background with light coming in (Vintage tone) Archivio Fotografico",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_000_row_000016"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:44
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000016",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_000_row_000016\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_000_row_000016\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:44
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000018",
  "source_prompt": "rocky hill reflected in water under a starry night sky Stock fotó",
  "edit_prompt": "have the starry sky be full of purple rainbows",
  "target_prompt": "rocky hill reflected in water under a starry night sky full of purple rainbows Stock fotó",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_001_row_000018"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:44
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000018",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_001_row_000018\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_001_row_000018\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:44
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000038",
  "source_prompt": "Fairy Glen by Tim McAndrew - Landscapes Waterscapes ( water, fairy glen, wales, green, conwy, long exposure, light, rays )",
  "edit_prompt": "Add a horse.",
  "target_prompt": "Fairy Glen with horse by Tim McAndrew - Landscapes Waterscapes ( water, fairy glen, horse, wales, green, conwy, long exposure, light, rays )",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_002_row_000038"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:44
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000038",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_002_row_000038\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_002_row_000038\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:44
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000052",
  "source_prompt": "Original oil painting of a gorgeous forties style woman, by Linda Boucher from Brighton. Using strong reds and beautiful blue eyes, this painting has a vintage pinup feel to it.",
  "edit_prompt": "make her wearing a firefighter's outfit",
  "target_prompt": "Original oil painting of a gorgeous forties style firefighter wearing a firefighter's outfit, by Linda Boucher from Brighton. Using strong reds and beautiful blue eyes, this painting has a vintage pinup feel to it.",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_003_row_000052"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:44
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000052",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_003_row_000052\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_003_row_000052\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:44
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000066",
  "source_prompt": "Live-Action de Lightning Returns: Final Fantasy XIII",
  "edit_prompt": "add a cat",
  "target_prompt": "Live-Action de Lightning Returns: Final Fantasy XIII with a cat",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_004_row_000066"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:44
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000066",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_004_row_000066\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_004_row_000066\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:44
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000160",
  "source_prompt": "View of snow storm in Grand Teton National Park",
  "edit_prompt": "Add a tornado in the background",
  "target_prompt": "View of snow storm with tornado in Grand Teton National Park",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_005_row_000160"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:44
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000160",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_005_row_000160\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_005_row_000160\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:44
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000251",
  "source_prompt": "Winter Sunrise Picture for Android, iPhone and iPad",
  "edit_prompt": "Replace the snow with rain",
  "target_prompt": "Winter Rain Picture for Android, iPhone and iPad",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_006_row_000251"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:45
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000251",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_006_row_000251\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_006_row_000251\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:45
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_000457",
  "source_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting",
  "edit_prompt": "Make the sky purple",
  "target_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting, Purple Sky",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_007_row_000457"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:45
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_000457",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_007_row_000457\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-1743\\samples\\sample_007_row_000457\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:45
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase4",
  "run_limit": 8,
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase4_20260328-1743\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase4_20260328-1743\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase4_20260328-1743\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 17:48
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000001E2E751D080>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 17:48
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": [
    16,
    18,
    38,
    52,
    66,
    160,
    251,
    457
  ],
  "phase": "phase5",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase5_20260328-1748",
  "manifest_json": "runs\\dymask_v1\\phase5_20260328-1748\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase5_20260328-1748\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000016",
    "sample_001_row_000018",
    "sample_002_row_000038",
    "sample_003_row_000052",
    "sample_004_row_000066",
    "sample_005_row_000160",
    "sample_006_row_000251",
    "sample_007_row_000457"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 17:48
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000016",
  "source_prompt": "Asian woman playing piano in window background with light coming in (Vintage tone) Archivio Fotografico",
  "edit_prompt": "turn the background into a beach",
  "target_prompt": "Asian woman playing piano on beach background with light coming in (Vintage tone) Archivio Fotografico",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_000_row_000016"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:48
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000016",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_000_row_000016\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_000_row_000016\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:48
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000018",
  "source_prompt": "rocky hill reflected in water under a starry night sky Stock fotó",
  "edit_prompt": "have the starry sky be full of purple rainbows",
  "target_prompt": "rocky hill reflected in water under a starry night sky full of purple rainbows Stock fotó",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_001_row_000018"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:48
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000018",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_001_row_000018\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_001_row_000018\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:48
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000038",
  "source_prompt": "Fairy Glen by Tim McAndrew - Landscapes Waterscapes ( water, fairy glen, wales, green, conwy, long exposure, light, rays )",
  "edit_prompt": "Add a horse.",
  "target_prompt": "Fairy Glen with horse by Tim McAndrew - Landscapes Waterscapes ( water, fairy glen, horse, wales, green, conwy, long exposure, light, rays )",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_002_row_000038"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:48
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000038",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_002_row_000038\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_002_row_000038\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:48
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000052",
  "source_prompt": "Original oil painting of a gorgeous forties style woman, by Linda Boucher from Brighton. Using strong reds and beautiful blue eyes, this painting has a vintage pinup feel to it.",
  "edit_prompt": "make her wearing a firefighter's outfit",
  "target_prompt": "Original oil painting of a gorgeous forties style firefighter wearing a firefighter's outfit, by Linda Boucher from Brighton. Using strong reds and beautiful blue eyes, this painting has a vintage pinup feel to it.",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_003_row_000052"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:49
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000052",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_003_row_000052\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_003_row_000052\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:49
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000066",
  "source_prompt": "Live-Action de Lightning Returns: Final Fantasy XIII",
  "edit_prompt": "add a cat",
  "target_prompt": "Live-Action de Lightning Returns: Final Fantasy XIII with a cat",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_004_row_000066"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:49
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000066",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_004_row_000066\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_004_row_000066\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:49
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000160",
  "source_prompt": "View of snow storm in Grand Teton National Park",
  "edit_prompt": "Add a tornado in the background",
  "target_prompt": "View of snow storm with tornado in Grand Teton National Park",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_005_row_000160"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:49
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000160",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_005_row_000160\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_005_row_000160\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:49
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000251",
  "source_prompt": "Winter Sunrise Picture for Android, iPhone and iPad",
  "edit_prompt": "Replace the snow with rain",
  "target_prompt": "Winter Rain Picture for Android, iPhone and iPad",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_006_row_000251"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:49
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000251",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_006_row_000251\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_006_row_000251\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:49
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_000457",
  "source_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting",
  "edit_prompt": "Make the sky purple",
  "target_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting, Purple Sky",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_007_row_000457"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 17:49
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_000457",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_007_row_000457\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-1748\\samples\\sample_007_row_000457\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 17:49
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase5",
  "run_limit": 8,
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase5_20260328-1748\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase5_20260328-1748\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase5_20260328-1748\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 19:12
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet",
  "num_rows": 140,
  "num_row_groups": 2,
  "column_names": "image, id, source_prompt, target_prompt, edit_action, aspect_mapping, blended_words, mask",
  "dataset_format": "single_image_prompt_edit",
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000001D8A713DC80>\nrequired group field_id=-1 schema {\n  optional group field_id=-1 image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 id (String);\n  optional binary field_id=-1 source_prompt (String);\n  optional binary field_id=-1 target_prompt (String);\n  optional binary field_id=-1 edit_action (String);\n  optional binary field_id=-1 aspect_mapping (String);\n  optional binary field_id=-1 blended_words (String);\n  optional binary field_id=-1 mask (String);\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 19:12
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": null,
  "phase": "phase2",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase2_20260328-1912",
  "manifest_json": "runs\\dymask_v1\\phase2_20260328-1912\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase2_20260328-1912\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000006",
    "sample_001_row_000026",
    "sample_002_row_000028",
    "sample_003_row_000035",
    "sample_004_row_000057",
    "sample_005_row_000062",
    "sample_006_row_000070",
    "sample_007_row_000139"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 19:12
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "source_prompt": "a cup of coffee with drawing of tulip putted on the wooden table",
  "edit_prompt": "{\"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"milk\": {\"position\": 3, \"edit_type\": 1, \"action\": \"coffee\"}, \"rose\": {\"position\": 7, \"edit_type\": 1, \"action\": \"tulip\"}}",
  "target_prompt": "a [yellow] cup of [milk] with drawing of [rose] putted on the wooden table",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_000_row_000006"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 19:13
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_000_row_000006\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_000_row_000006\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_000_row_000006\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_000_row_000006\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_000_row_000006\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 19:13
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "source_prompt": "a yellow bird with a red beak sitting on a branch",
  "edit_prompt": "{\"toy\": {\"position\": 1, \"edit_type\": 4, \"action\": \"+\"}, \"yellow\": {\"position\": 1, \"edit_type\": 3, \"action\": \"-\"}, \"cat\": {\"position\": 2, \"edit_type\": 1, \"action\": \"bird\"}, \"fur\": {\"position\": 6, \"edit_type\": 4, \"action\": \"beak\"}}",
  "target_prompt": "a [toy] [cat] with a red [fur] sitting on a branch",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_001_row_000026"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 19:13
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_001_row_000026\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_001_row_000026\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_001_row_000026\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_001_row_000026\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_001_row_000026\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 19:13
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000028",
  "source_prompt": "white flowers on a tree branch with blue sky background",
  "edit_prompt": "{\"Painting of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"red\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"white background\": {\"position\": 7, \"edit_type\": 8, \"action\": \"sky background\"}}",
  "target_prompt": "[Painting of] [red] flowers on a tree branch with [white background]",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_002_row_000028"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 19:14
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000028",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_002_row_000028\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_002_row_000028\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_002_row_000028\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_002_row_000028\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_002_row_000028\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 19:14
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000035",
  "source_prompt": "photograph, window of the world by jimmy kirk",
  "edit_prompt": "{\"painting\": {\"position\": 0, \"edit_type\": 9, \"action\": \"photograph\"}, \"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"ball\": {\"position\": 1, \"edit_type\": 1, \"action\": \"window\"}}",
  "target_prompt": "[painting], [yellow] [ball] of the world by jimmy kirk",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_003_row_000035"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 19:14
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000035",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_003_row_000035\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_003_row_000035\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_003_row_000035\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_003_row_000035\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_003_row_000035\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 19:14
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000057",
  "source_prompt": "an owl sitting on a branch",
  "edit_prompt": "{\"a photo of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"jumping\": {\"position\": 2, \"edit_type\": 5, \"action\": \"sitting\"}, \"rock\": {\"position\": 5, \"edit_type\": 1, \"action\": \"branch\"}}",
  "target_prompt": "[a photo of] an owl [jumping] on a [rock]",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_004_row_000057"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 19:15
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000057",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_004_row_000057\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_004_row_000057\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_004_row_000057\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_004_row_000057\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_004_row_000057\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 19:15
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000062",
  "source_prompt": "a rabbit is sitting in a pile of colorful eggs",
  "edit_prompt": "{\"cat\": {\"position\": 1, \"edit_type\": 1, \"action\": \"rabbit\"}, \"sleeping\": {\"position\": 3, \"edit_type\": 5, \"action\": \"sitting\"}, \"stones\": {\"position\": 9, \"edit_type\": 1, \"action\": \"eggs\"}}",
  "target_prompt": "a [cat] is [sleeping] in a pile of colorful [stones]",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_005_row_000062"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 19:15
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000062",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_005_row_000062\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_005_row_000062\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_005_row_000062\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_005_row_000062\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_005_row_000062\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 19:15
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000070",
  "source_prompt": "the city of dresden, germany, europe",
  "edit_prompt": "{\"a sunny day of\": {\"position\": 0, \"edit_type\": 4, \"action\": \"+\"}, \"park\": {\"position\": 1, \"edit_type\": 1, \"action\": \"city\"}}",
  "target_prompt": "[a sunny day of] the [park] of dresden, germany, europe",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_006_row_000070"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 19:16
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000070",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_006_row_000070\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_006_row_000070\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_006_row_000070\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_006_row_000070\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_006_row_000070\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 19:16
阶段：Phase 2 全局融合基线
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_000139",
  "source_prompt": "a duck standing on a rock near water",
  "edit_prompt": "{\"chicken\": {\"position\": 1, \"edit_type\": 1, \"action\": \"duck\"}, \"sitting\": {\"position\": 2, \"edit_type\": 5, \"action\": \"standing\"}, \"board\": {\"position\": 5, \"edit_type\": 1, \"action\": \"rock\"}}",
  "target_prompt": "a [chicken] [sitting] on a [board] near water",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_007_row_000139"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 19:17
阶段：Phase 2 全局融合基线
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_000139",
  "phase": "phase2"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_007_row_000139\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_007_row_000139\\target_only\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_007_row_000139\\global_blend_0.3\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_007_row_000139\\global_blend_0.5\\edited.png",
    "runs\\dymask_v1\\phase2_20260328-1912\\samples\\sample_007_row_000139\\global_blend_0.7\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 19:17
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase2",
  "run_limit": 8,
  "methods": [
    "target_only",
    "global_blend_0.3",
    "global_blend_0.5",
    "global_blend_0.7"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase2_20260328-1912\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase2_20260328-1912\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase2_20260328-1912\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 19:32
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet",
  "num_rows": 140,
  "num_row_groups": 2,
  "column_names": "image, id, source_prompt, target_prompt, edit_action, aspect_mapping, blended_words, mask",
  "dataset_format": "single_image_prompt_edit",
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000001995E95DFC0>\nrequired group field_id=-1 schema {\n  optional group field_id=-1 image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 id (String);\n  optional binary field_id=-1 source_prompt (String);\n  optional binary field_id=-1 target_prompt (String);\n  optional binary field_id=-1 edit_action (String);\n  optional binary field_id=-1 aspect_mapping (String);\n  optional binary field_id=-1 blended_words (String);\n  optional binary field_id=-1 mask (String);\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 19:32
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": [
    6,
    26,
    28,
    35,
    57,
    62,
    70,
    139
  ],
  "phase": "phase3",
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase3_20260328-1932",
  "manifest_json": "runs\\dymask_v1\\phase3_20260328-1932\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase3_20260328-1932\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000006",
    "sample_001_row_000026",
    "sample_002_row_000028",
    "sample_003_row_000035",
    "sample_004_row_000057",
    "sample_005_row_000062",
    "sample_006_row_000070",
    "sample_007_row_000139"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 19:33
阶段：Phase 3 仅 D_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "source_prompt": "a cup of coffee with drawing of tulip putted on the wooden table",
  "edit_prompt": "{\"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"milk\": {\"position\": 3, \"edit_type\": 1, \"action\": \"coffee\"}, \"rose\": {\"position\": 7, \"edit_type\": 1, \"action\": \"tulip\"}}",
  "target_prompt": "a [yellow] cup of [milk] with drawing of [rose] putted on the wooden table",
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_000_row_000006"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 19:33
阶段：Phase 3 仅 D_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "phase": "phase3"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_000_row_000006\\source_reconstruction.png",
  "methods": [
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_000_row_000006\\discrepancy_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 19:33
阶段：Phase 3 仅 D_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "source_prompt": "a yellow bird with a red beak sitting on a branch",
  "edit_prompt": "{\"toy\": {\"position\": 1, \"edit_type\": 4, \"action\": \"+\"}, \"yellow\": {\"position\": 1, \"edit_type\": 3, \"action\": \"-\"}, \"cat\": {\"position\": 2, \"edit_type\": 1, \"action\": \"bird\"}, \"fur\": {\"position\": 6, \"edit_type\": 4, \"action\": \"beak\"}}",
  "target_prompt": "a [toy] [cat] with a red [fur] sitting on a branch",
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_001_row_000026"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 19:33
阶段：Phase 3 仅 D_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "phase": "phase3"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_001_row_000026\\source_reconstruction.png",
  "methods": [
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_001_row_000026\\discrepancy_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 19:33
阶段：Phase 3 仅 D_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000028",
  "source_prompt": "white flowers on a tree branch with blue sky background",
  "edit_prompt": "{\"Painting of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"red\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"white background\": {\"position\": 7, \"edit_type\": 8, \"action\": \"sky background\"}}",
  "target_prompt": "[Painting of] [red] flowers on a tree branch with [white background]",
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_002_row_000028"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 19:33
阶段：Phase 3 仅 D_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000028",
  "phase": "phase3"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_002_row_000028\\source_reconstruction.png",
  "methods": [
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_002_row_000028\\discrepancy_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 19:33
阶段：Phase 3 仅 D_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000035",
  "source_prompt": "photograph, window of the world by jimmy kirk",
  "edit_prompt": "{\"painting\": {\"position\": 0, \"edit_type\": 9, \"action\": \"photograph\"}, \"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"ball\": {\"position\": 1, \"edit_type\": 1, \"action\": \"window\"}}",
  "target_prompt": "[painting], [yellow] [ball] of the world by jimmy kirk",
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_003_row_000035"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 19:33
阶段：Phase 3 仅 D_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000035",
  "phase": "phase3"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_003_row_000035\\source_reconstruction.png",
  "methods": [
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_003_row_000035\\discrepancy_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 19:33
阶段：Phase 3 仅 D_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000057",
  "source_prompt": "an owl sitting on a branch",
  "edit_prompt": "{\"a photo of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"jumping\": {\"position\": 2, \"edit_type\": 5, \"action\": \"sitting\"}, \"rock\": {\"position\": 5, \"edit_type\": 1, \"action\": \"branch\"}}",
  "target_prompt": "[a photo of] an owl [jumping] on a [rock]",
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_004_row_000057"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 19:33
阶段：Phase 3 仅 D_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000057",
  "phase": "phase3"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_004_row_000057\\source_reconstruction.png",
  "methods": [
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_004_row_000057\\discrepancy_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 19:33
阶段：Phase 3 仅 D_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000062",
  "source_prompt": "a rabbit is sitting in a pile of colorful eggs",
  "edit_prompt": "{\"cat\": {\"position\": 1, \"edit_type\": 1, \"action\": \"rabbit\"}, \"sleeping\": {\"position\": 3, \"edit_type\": 5, \"action\": \"sitting\"}, \"stones\": {\"position\": 9, \"edit_type\": 1, \"action\": \"eggs\"}}",
  "target_prompt": "a [cat] is [sleeping] in a pile of colorful [stones]",
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_005_row_000062"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 19:34
阶段：Phase 3 仅 D_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000062",
  "phase": "phase3"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_005_row_000062\\source_reconstruction.png",
  "methods": [
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_005_row_000062\\discrepancy_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 19:34
阶段：Phase 3 仅 D_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000070",
  "source_prompt": "the city of dresden, germany, europe",
  "edit_prompt": "{\"a sunny day of\": {\"position\": 0, \"edit_type\": 4, \"action\": \"+\"}, \"park\": {\"position\": 1, \"edit_type\": 1, \"action\": \"city\"}}",
  "target_prompt": "[a sunny day of] the [park] of dresden, germany, europe",
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_006_row_000070"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 19:34
阶段：Phase 3 仅 D_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000070",
  "phase": "phase3"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_006_row_000070\\source_reconstruction.png",
  "methods": [
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_006_row_000070\\discrepancy_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 19:34
阶段：Phase 3 仅 D_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_000139",
  "source_prompt": "a duck standing on a rock near water",
  "edit_prompt": "{\"chicken\": {\"position\": 1, \"edit_type\": 1, \"action\": \"duck\"}, \"sitting\": {\"position\": 2, \"edit_type\": 5, \"action\": \"standing\"}, \"board\": {\"position\": 5, \"edit_type\": 1, \"action\": \"rock\"}}",
  "target_prompt": "a [chicken] [sitting] on a [board] near water",
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_007_row_000139"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 19:34
阶段：Phase 3 仅 D_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_000139",
  "phase": "phase3"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_007_row_000139\\source_reconstruction.png",
  "methods": [
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase3_20260328-1932\\samples\\sample_007_row_000139\\discrepancy_only\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 19:34
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase3",
  "run_limit": 8,
  "methods": [
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase3_20260328-1932\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase3_20260328-1932\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase3_20260328-1932\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 19:35
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet",
  "num_rows": 140,
  "num_row_groups": 2,
  "column_names": "image, id, source_prompt, target_prompt, edit_action, aspect_mapping, blended_words, mask",
  "dataset_format": "single_image_prompt_edit",
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000002A29CF5A300>\nrequired group field_id=-1 schema {\n  optional group field_id=-1 image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 id (String);\n  optional binary field_id=-1 source_prompt (String);\n  optional binary field_id=-1 target_prompt (String);\n  optional binary field_id=-1 edit_action (String);\n  optional binary field_id=-1 aspect_mapping (String);\n  optional binary field_id=-1 blended_words (String);\n  optional binary field_id=-1 mask (String);\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 19:35
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet",
  "num_rows": 140,
  "num_row_groups": 2,
  "column_names": "image, id, source_prompt, target_prompt, edit_action, aspect_mapping, blended_words, mask",
  "dataset_format": "single_image_prompt_edit",
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x00000209D175A140>\nrequired group field_id=-1 schema {\n  optional group field_id=-1 image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 id (String);\n  optional binary field_id=-1 source_prompt (String);\n  optional binary field_id=-1 target_prompt (String);\n  optional binary field_id=-1 edit_action (String);\n  optional binary field_id=-1 aspect_mapping (String);\n  optional binary field_id=-1 blended_words (String);\n  optional binary field_id=-1 mask (String);\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 19:35
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": [
    6,
    26,
    28,
    35,
    57,
    62,
    70,
    139
  ],
  "phase": "phase4",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase4_20260328-1935",
  "manifest_json": "runs\\dymask_v1\\phase4_20260328-1935\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase4_20260328-1935\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000006",
    "sample_001_row_000026",
    "sample_002_row_000028",
    "sample_003_row_000035",
    "sample_004_row_000057",
    "sample_005_row_000062",
    "sample_006_row_000070",
    "sample_007_row_000139"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 19:35
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": [
    6,
    26,
    28,
    35,
    57,
    62,
    70,
    139
  ],
  "phase": "phase5",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase5_20260328-1935",
  "manifest_json": "runs\\dymask_v1\\phase5_20260328-1935\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase5_20260328-1935\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000006",
    "sample_001_row_000026",
    "sample_002_row_000028",
    "sample_003_row_000035",
    "sample_004_row_000057",
    "sample_005_row_000062",
    "sample_006_row_000070",
    "sample_007_row_000139"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 19:35
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "source_prompt": "a cup of coffee with drawing of tulip putted on the wooden table",
  "edit_prompt": "{\"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"milk\": {\"position\": 3, \"edit_type\": 1, \"action\": \"coffee\"}, \"rose\": {\"position\": 7, \"edit_type\": 1, \"action\": \"tulip\"}}",
  "target_prompt": "a [yellow] cup of [milk] with drawing of [rose] putted on the wooden table",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-1935\\samples\\sample_000_row_000006"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 19:35
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "source_prompt": "a cup of coffee with drawing of tulip putted on the wooden table",
  "edit_prompt": "{\"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"milk\": {\"position\": 3, \"edit_type\": 1, \"action\": \"coffee\"}, \"rose\": {\"position\": 7, \"edit_type\": 1, \"action\": \"tulip\"}}",
  "target_prompt": "a [yellow] cup of [milk] with drawing of [rose] putted on the wooden table",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-1935\\samples\\sample_000_row_000006"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 19:41
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-1935\\samples\\sample_000_row_000006\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-1935\\samples\\sample_000_row_000006\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 19:41
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "source_prompt": "a yellow bird with a red beak sitting on a branch",
  "edit_prompt": "{\"toy\": {\"position\": 1, \"edit_type\": 4, \"action\": \"+\"}, \"yellow\": {\"position\": 1, \"edit_type\": 3, \"action\": \"-\"}, \"cat\": {\"position\": 2, \"edit_type\": 1, \"action\": \"bird\"}, \"fur\": {\"position\": 6, \"edit_type\": 4, \"action\": \"beak\"}}",
  "target_prompt": "a [toy] [cat] with a red [fur] sitting on a branch",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-1935\\samples\\sample_001_row_000026"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 20:06
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet",
  "num_rows": 140,
  "num_row_groups": 2,
  "column_names": "image, id, source_prompt, target_prompt, edit_action, aspect_mapping, blended_words, mask",
  "dataset_format": "single_image_prompt_edit",
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000001652BCF1E40>\nrequired group field_id=-1 schema {\n  optional group field_id=-1 image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 id (String);\n  optional binary field_id=-1 source_prompt (String);\n  optional binary field_id=-1 target_prompt (String);\n  optional binary field_id=-1 edit_action (String);\n  optional binary field_id=-1 aspect_mapping (String);\n  optional binary field_id=-1 blended_words (String);\n  optional binary field_id=-1 mask (String);\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 20:06
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": [
    6,
    26,
    28,
    35,
    57,
    62,
    70,
    139
  ],
  "phase": "phase4",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase4_20260328-2006",
  "manifest_json": "runs\\dymask_v1\\phase4_20260328-2006\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase4_20260328-2006\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000006",
    "sample_001_row_000026",
    "sample_002_row_000028",
    "sample_003_row_000035",
    "sample_004_row_000057",
    "sample_005_row_000062",
    "sample_006_row_000070",
    "sample_007_row_000139"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 20:06
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "source_prompt": "a cup of coffee with drawing of tulip putted on the wooden table",
  "edit_prompt": "{\"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"milk\": {\"position\": 3, \"edit_type\": 1, \"action\": \"coffee\"}, \"rose\": {\"position\": 7, \"edit_type\": 1, \"action\": \"tulip\"}}",
  "target_prompt": "a [yellow] cup of [milk] with drawing of [rose] putted on the wooden table",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_000_row_000006"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 20:06
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_000_row_000006\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_000_row_000006\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 20:06
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "source_prompt": "a yellow bird with a red beak sitting on a branch",
  "edit_prompt": "{\"toy\": {\"position\": 1, \"edit_type\": 4, \"action\": \"+\"}, \"yellow\": {\"position\": 1, \"edit_type\": 3, \"action\": \"-\"}, \"cat\": {\"position\": 2, \"edit_type\": 1, \"action\": \"bird\"}, \"fur\": {\"position\": 6, \"edit_type\": 4, \"action\": \"beak\"}}",
  "target_prompt": "a [toy] [cat] with a red [fur] sitting on a branch",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_001_row_000026"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 20:07
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_001_row_000026\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_001_row_000026\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 20:07
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000028",
  "source_prompt": "white flowers on a tree branch with blue sky background",
  "edit_prompt": "{\"Painting of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"red\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"white background\": {\"position\": 7, \"edit_type\": 8, \"action\": \"sky background\"}}",
  "target_prompt": "[Painting of] [red] flowers on a tree branch with [white background]",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_002_row_000028"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 20:07
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000028",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_002_row_000028\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_002_row_000028\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 20:07
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000035",
  "source_prompt": "photograph, window of the world by jimmy kirk",
  "edit_prompt": "{\"painting\": {\"position\": 0, \"edit_type\": 9, \"action\": \"photograph\"}, \"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"ball\": {\"position\": 1, \"edit_type\": 1, \"action\": \"window\"}}",
  "target_prompt": "[painting], [yellow] [ball] of the world by jimmy kirk",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_003_row_000035"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 20:07
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000035",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_003_row_000035\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_003_row_000035\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 20:07
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000057",
  "source_prompt": "an owl sitting on a branch",
  "edit_prompt": "{\"a photo of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"jumping\": {\"position\": 2, \"edit_type\": 5, \"action\": \"sitting\"}, \"rock\": {\"position\": 5, \"edit_type\": 1, \"action\": \"branch\"}}",
  "target_prompt": "[a photo of] an owl [jumping] on a [rock]",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_004_row_000057"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 20:07
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000057",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_004_row_000057\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_004_row_000057\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 20:07
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000062",
  "source_prompt": "a rabbit is sitting in a pile of colorful eggs",
  "edit_prompt": "{\"cat\": {\"position\": 1, \"edit_type\": 1, \"action\": \"rabbit\"}, \"sleeping\": {\"position\": 3, \"edit_type\": 5, \"action\": \"sitting\"}, \"stones\": {\"position\": 9, \"edit_type\": 1, \"action\": \"eggs\"}}",
  "target_prompt": "a [cat] is [sleeping] in a pile of colorful [stones]",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_005_row_000062"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 20:07
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000062",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_005_row_000062\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_005_row_000062\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 20:07
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000070",
  "source_prompt": "the city of dresden, germany, europe",
  "edit_prompt": "{\"a sunny day of\": {\"position\": 0, \"edit_type\": 4, \"action\": \"+\"}, \"park\": {\"position\": 1, \"edit_type\": 1, \"action\": \"city\"}}",
  "target_prompt": "[a sunny day of] the [park] of dresden, germany, europe",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_006_row_000070"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 20:07
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000070",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_006_row_000070\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_006_row_000070\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 20:07
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_000139",
  "source_prompt": "a duck standing on a rock near water",
  "edit_prompt": "{\"chicken\": {\"position\": 1, \"edit_type\": 1, \"action\": \"duck\"}, \"sitting\": {\"position\": 2, \"edit_type\": 5, \"action\": \"standing\"}, \"board\": {\"position\": 5, \"edit_type\": 1, \"action\": \"rock\"}}",
  "target_prompt": "a [chicken] [sitting] on a [board] near water",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_007_row_000139"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 20:08
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_000139",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_007_row_000139\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-2006\\samples\\sample_007_row_000139\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 20:08
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase4",
  "run_limit": 8,
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase4_20260328-2006\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase4_20260328-2006\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase4_20260328-2006\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 20:09
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet",
  "num_rows": 140,
  "num_row_groups": 2,
  "column_names": "image, id, source_prompt, target_prompt, edit_action, aspect_mapping, blended_words, mask",
  "dataset_format": "single_image_prompt_edit",
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000001F3741CA2C0>\nrequired group field_id=-1 schema {\n  optional group field_id=-1 image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 id (String);\n  optional binary field_id=-1 source_prompt (String);\n  optional binary field_id=-1 target_prompt (String);\n  optional binary field_id=-1 edit_action (String);\n  optional binary field_id=-1 aspect_mapping (String);\n  optional binary field_id=-1 blended_words (String);\n  optional binary field_id=-1 mask (String);\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 20:09
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": [
    6,
    26,
    28,
    35,
    57,
    62,
    70,
    139
  ],
  "phase": "phase5",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase5_20260328-2009",
  "manifest_json": "runs\\dymask_v1\\phase5_20260328-2009\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase5_20260328-2009\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000006",
    "sample_001_row_000026",
    "sample_002_row_000028",
    "sample_003_row_000035",
    "sample_004_row_000057",
    "sample_005_row_000062",
    "sample_006_row_000070",
    "sample_007_row_000139"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 20:09
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "source_prompt": "a cup of coffee with drawing of tulip putted on the wooden table",
  "edit_prompt": "{\"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"milk\": {\"position\": 3, \"edit_type\": 1, \"action\": \"coffee\"}, \"rose\": {\"position\": 7, \"edit_type\": 1, \"action\": \"tulip\"}}",
  "target_prompt": "a [yellow] cup of [milk] with drawing of [rose] putted on the wooden table",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_000_row_000006"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 20:09
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_000_row_000006\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_000_row_000006\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 20:09
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "source_prompt": "a yellow bird with a red beak sitting on a branch",
  "edit_prompt": "{\"toy\": {\"position\": 1, \"edit_type\": 4, \"action\": \"+\"}, \"yellow\": {\"position\": 1, \"edit_type\": 3, \"action\": \"-\"}, \"cat\": {\"position\": 2, \"edit_type\": 1, \"action\": \"bird\"}, \"fur\": {\"position\": 6, \"edit_type\": 4, \"action\": \"beak\"}}",
  "target_prompt": "a [toy] [cat] with a red [fur] sitting on a branch",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_001_row_000026"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 20:09
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_001_row_000026\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_001_row_000026\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 20:09
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000028",
  "source_prompt": "white flowers on a tree branch with blue sky background",
  "edit_prompt": "{\"Painting of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"red\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"white background\": {\"position\": 7, \"edit_type\": 8, \"action\": \"sky background\"}}",
  "target_prompt": "[Painting of] [red] flowers on a tree branch with [white background]",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_002_row_000028"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 20:09
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000028",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_002_row_000028\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_002_row_000028\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 20:09
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000035",
  "source_prompt": "photograph, window of the world by jimmy kirk",
  "edit_prompt": "{\"painting\": {\"position\": 0, \"edit_type\": 9, \"action\": \"photograph\"}, \"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"ball\": {\"position\": 1, \"edit_type\": 1, \"action\": \"window\"}}",
  "target_prompt": "[painting], [yellow] [ball] of the world by jimmy kirk",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_003_row_000035"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 20:10
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000035",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_003_row_000035\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_003_row_000035\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 20:10
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000057",
  "source_prompt": "an owl sitting on a branch",
  "edit_prompt": "{\"a photo of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"jumping\": {\"position\": 2, \"edit_type\": 5, \"action\": \"sitting\"}, \"rock\": {\"position\": 5, \"edit_type\": 1, \"action\": \"branch\"}}",
  "target_prompt": "[a photo of] an owl [jumping] on a [rock]",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_004_row_000057"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 20:10
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000057",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_004_row_000057\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_004_row_000057\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 20:10
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000062",
  "source_prompt": "a rabbit is sitting in a pile of colorful eggs",
  "edit_prompt": "{\"cat\": {\"position\": 1, \"edit_type\": 1, \"action\": \"rabbit\"}, \"sleeping\": {\"position\": 3, \"edit_type\": 5, \"action\": \"sitting\"}, \"stones\": {\"position\": 9, \"edit_type\": 1, \"action\": \"eggs\"}}",
  "target_prompt": "a [cat] is [sleeping] in a pile of colorful [stones]",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_005_row_000062"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 20:10
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000062",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_005_row_000062\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_005_row_000062\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 20:10
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000070",
  "source_prompt": "the city of dresden, germany, europe",
  "edit_prompt": "{\"a sunny day of\": {\"position\": 0, \"edit_type\": 4, \"action\": \"+\"}, \"park\": {\"position\": 1, \"edit_type\": 1, \"action\": \"city\"}}",
  "target_prompt": "[a sunny day of] the [park] of dresden, germany, europe",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_006_row_000070"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 20:10
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000070",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_006_row_000070\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_006_row_000070\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 20:10
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_000139",
  "source_prompt": "a duck standing on a rock near water",
  "edit_prompt": "{\"chicken\": {\"position\": 1, \"edit_type\": 1, \"action\": \"duck\"}, \"sitting\": {\"position\": 2, \"edit_type\": 5, \"action\": \"standing\"}, \"board\": {\"position\": 5, \"edit_type\": 1, \"action\": \"rock\"}}",
  "target_prompt": "a [chicken] [sitting] on a [board] near water",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_007_row_000139"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 20:10
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_000139",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_007_row_000139\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-2009\\samples\\sample_007_row_000139\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 20:10
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase5",
  "run_limit": 8,
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase5_20260328-2009\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase5_20260328-2009\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase5_20260328-2009\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 21:13
阶段：A_t 单独可视化
操作：运行单样本 target prompt attention 探针
输入：
```json
{
  "sample_id": "sample_000_row_000026",
  "row_index": 26,
  "source_prompt": "a yellow bird with a red beak sitting on a branch",
  "target_prompt": "a [toy] [cat] with a red [fur] sitting on a branch"
}
```
结果：
```json
{
  "run_dir": "runs\\attention_probe\\attention_20260328-2113",
  "overview_path": "runs\\attention_probe\\attention_20260328-2113\\samples\\sample_000_row_000026\\attention_only\\attention_overview.png"
}
```
结论：已保存若干 timestep 的 A_t，用于检查 attention 是否落在语义对象附近。
下一步：人工查看 attention_overview.png 和 selected_steps/*.png。

## 2026-03-28 21:17
阶段：A_t 单独可视化
操作：运行单样本 target prompt attention 探针
输入：
```json
{
  "sample_id": "sample_000_row_000026",
  "row_index": 26,
  "source_prompt": "a yellow bird with a red beak sitting on a branch",
  "target_prompt": "a [toy] [cat] with a red [fur] sitting on a branch"
}
```
结果：
```json
{
  "run_dir": "runs\\attention_probe\\attention_20260328-2117",
  "overview_path": "runs\\attention_probe\\attention_20260328-2117\\samples\\sample_000_row_000026\\attention_only\\attention_overview.png"
}
```
结论：已保存若干 timestep 的 A_t，用于检查 attention 是否落在语义对象附近。
下一步：人工查看 attention_overview.png 和 selected_steps/*.png。

## 2026-03-28 21:19
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet",
  "num_rows": 140,
  "num_row_groups": 2,
  "column_names": "image, id, source_prompt, target_prompt, edit_action, aspect_mapping, blended_words, mask",
  "dataset_format": "single_image_prompt_edit",
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x00000210BB2AA2C0>\nrequired group field_id=-1 schema {\n  optional group field_id=-1 image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 id (String);\n  optional binary field_id=-1 source_prompt (String);\n  optional binary field_id=-1 target_prompt (String);\n  optional binary field_id=-1 edit_action (String);\n  optional binary field_id=-1 aspect_mapping (String);\n  optional binary field_id=-1 blended_words (String);\n  optional binary field_id=-1 mask (String);\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 21:19
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": [
    6,
    26,
    28,
    35,
    57,
    62,
    70,
    139
  ],
  "phase": "phase4",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase4_20260328-2119",
  "manifest_json": "runs\\dymask_v1\\phase4_20260328-2119\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase4_20260328-2119\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000006",
    "sample_001_row_000026",
    "sample_002_row_000028",
    "sample_003_row_000035",
    "sample_004_row_000057",
    "sample_005_row_000062",
    "sample_006_row_000070",
    "sample_007_row_000139"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 21:19
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "source_prompt": "a cup of coffee with drawing of tulip putted on the wooden table",
  "edit_prompt": "{\"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"milk\": {\"position\": 3, \"edit_type\": 1, \"action\": \"coffee\"}, \"rose\": {\"position\": 7, \"edit_type\": 1, \"action\": \"tulip\"}}",
  "target_prompt": "a [yellow] cup of [milk] with drawing of [rose] putted on the wooden table",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_000_row_000006"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 21:19
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_000_row_000006\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_000_row_000006\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 21:19
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "source_prompt": "a yellow bird with a red beak sitting on a branch",
  "edit_prompt": "{\"toy\": {\"position\": 1, \"edit_type\": 4, \"action\": \"+\"}, \"yellow\": {\"position\": 1, \"edit_type\": 3, \"action\": \"-\"}, \"cat\": {\"position\": 2, \"edit_type\": 1, \"action\": \"bird\"}, \"fur\": {\"position\": 6, \"edit_type\": 4, \"action\": \"beak\"}}",
  "target_prompt": "a [toy] [cat] with a red [fur] sitting on a branch",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_001_row_000026"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 21:19
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_001_row_000026\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_001_row_000026\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 21:19
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000028",
  "source_prompt": "white flowers on a tree branch with blue sky background",
  "edit_prompt": "{\"Painting of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"red\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"white background\": {\"position\": 7, \"edit_type\": 8, \"action\": \"sky background\"}}",
  "target_prompt": "[Painting of] [red] flowers on a tree branch with [white background]",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_002_row_000028"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 21:19
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000028",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_002_row_000028\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_002_row_000028\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 21:19
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000035",
  "source_prompt": "photograph, window of the world by jimmy kirk",
  "edit_prompt": "{\"painting\": {\"position\": 0, \"edit_type\": 9, \"action\": \"photograph\"}, \"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"ball\": {\"position\": 1, \"edit_type\": 1, \"action\": \"window\"}}",
  "target_prompt": "[painting], [yellow] [ball] of the world by jimmy kirk",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_003_row_000035"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 21:20
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000035",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_003_row_000035\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_003_row_000035\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 21:20
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000057",
  "source_prompt": "an owl sitting on a branch",
  "edit_prompt": "{\"a photo of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"jumping\": {\"position\": 2, \"edit_type\": 5, \"action\": \"sitting\"}, \"rock\": {\"position\": 5, \"edit_type\": 1, \"action\": \"branch\"}}",
  "target_prompt": "[a photo of] an owl [jumping] on a [rock]",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_004_row_000057"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 21:20
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000057",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_004_row_000057\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_004_row_000057\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 21:20
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000062",
  "source_prompt": "a rabbit is sitting in a pile of colorful eggs",
  "edit_prompt": "{\"cat\": {\"position\": 1, \"edit_type\": 1, \"action\": \"rabbit\"}, \"sleeping\": {\"position\": 3, \"edit_type\": 5, \"action\": \"sitting\"}, \"stones\": {\"position\": 9, \"edit_type\": 1, \"action\": \"eggs\"}}",
  "target_prompt": "a [cat] is [sleeping] in a pile of colorful [stones]",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_005_row_000062"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 21:20
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000062",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_005_row_000062\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_005_row_000062\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 21:20
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000070",
  "source_prompt": "the city of dresden, germany, europe",
  "edit_prompt": "{\"a sunny day of\": {\"position\": 0, \"edit_type\": 4, \"action\": \"+\"}, \"park\": {\"position\": 1, \"edit_type\": 1, \"action\": \"city\"}}",
  "target_prompt": "[a sunny day of] the [park] of dresden, germany, europe",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_006_row_000070"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 21:20
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000070",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_006_row_000070\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_006_row_000070\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 21:20
阶段：Phase 4 D_t + A_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_000139",
  "source_prompt": "a duck standing on a rock near water",
  "edit_prompt": "{\"chicken\": {\"position\": 1, \"edit_type\": 1, \"action\": \"duck\"}, \"sitting\": {\"position\": 2, \"edit_type\": 5, \"action\": \"standing\"}, \"board\": {\"position\": 5, \"edit_type\": 1, \"action\": \"rock\"}}",
  "target_prompt": "a [chicken] [sitting] on a [board] near water",
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_007_row_000139"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 21:20
阶段：Phase 4 D_t + A_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_000139",
  "phase": "phase4"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_007_row_000139\\source_reconstruction.png",
  "methods": [
    "discrepancy_attention"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase4_20260328-2119\\samples\\sample_007_row_000139\\discrepancy_attention\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 21:20
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase4",
  "run_limit": 8,
  "methods": [
    "discrepancy_attention"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase4_20260328-2119\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase4_20260328-2119\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase4_20260328-2119\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 21:23
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet",
  "num_rows": 140,
  "num_row_groups": 2,
  "column_names": "image, id, source_prompt, target_prompt, edit_action, aspect_mapping, blended_words, mask",
  "dataset_format": "single_image_prompt_edit",
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000002455132AB00>\nrequired group field_id=-1 schema {\n  optional group field_id=-1 image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 id (String);\n  optional binary field_id=-1 source_prompt (String);\n  optional binary field_id=-1 target_prompt (String);\n  optional binary field_id=-1 edit_action (String);\n  optional binary field_id=-1 aspect_mapping (String);\n  optional binary field_id=-1 blended_words (String);\n  optional binary field_id=-1 mask (String);\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 21:23
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": [
    6,
    26,
    28,
    35,
    57,
    62,
    70,
    139
  ],
  "phase": "phase5",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\phase5_20260328-2123",
  "manifest_json": "runs\\dymask_v1\\phase5_20260328-2123\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\phase5_20260328-2123\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000006",
    "sample_001_row_000026",
    "sample_002_row_000028",
    "sample_003_row_000035",
    "sample_004_row_000057",
    "sample_005_row_000062",
    "sample_006_row_000070",
    "sample_007_row_000139"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 21:23
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "source_prompt": "a cup of coffee with drawing of tulip putted on the wooden table",
  "edit_prompt": "{\"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"milk\": {\"position\": 3, \"edit_type\": 1, \"action\": \"coffee\"}, \"rose\": {\"position\": 7, \"edit_type\": 1, \"action\": \"tulip\"}}",
  "target_prompt": "a [yellow] cup of [milk] with drawing of [rose] putted on the wooden table",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_000_row_000006"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 21:23
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_000_row_000006\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_000_row_000006\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 21:23
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "source_prompt": "a yellow bird with a red beak sitting on a branch",
  "edit_prompt": "{\"toy\": {\"position\": 1, \"edit_type\": 4, \"action\": \"+\"}, \"yellow\": {\"position\": 1, \"edit_type\": 3, \"action\": \"-\"}, \"cat\": {\"position\": 2, \"edit_type\": 1, \"action\": \"bird\"}, \"fur\": {\"position\": 6, \"edit_type\": 4, \"action\": \"beak\"}}",
  "target_prompt": "a [toy] [cat] with a red [fur] sitting on a branch",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_001_row_000026"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 21:24
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_001_row_000026\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_001_row_000026\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 21:24
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000028",
  "source_prompt": "white flowers on a tree branch with blue sky background",
  "edit_prompt": "{\"Painting of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"red\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"white background\": {\"position\": 7, \"edit_type\": 8, \"action\": \"sky background\"}}",
  "target_prompt": "[Painting of] [red] flowers on a tree branch with [white background]",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_002_row_000028"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 21:24
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000028",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_002_row_000028\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_002_row_000028\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 21:24
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000035",
  "source_prompt": "photograph, window of the world by jimmy kirk",
  "edit_prompt": "{\"painting\": {\"position\": 0, \"edit_type\": 9, \"action\": \"photograph\"}, \"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"ball\": {\"position\": 1, \"edit_type\": 1, \"action\": \"window\"}}",
  "target_prompt": "[painting], [yellow] [ball] of the world by jimmy kirk",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_003_row_000035"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 21:24
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000035",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_003_row_000035\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_003_row_000035\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 21:24
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000057",
  "source_prompt": "an owl sitting on a branch",
  "edit_prompt": "{\"a photo of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"jumping\": {\"position\": 2, \"edit_type\": 5, \"action\": \"sitting\"}, \"rock\": {\"position\": 5, \"edit_type\": 1, \"action\": \"branch\"}}",
  "target_prompt": "[a photo of] an owl [jumping] on a [rock]",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_004_row_000057"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 21:24
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000057",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_004_row_000057\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_004_row_000057\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 21:24
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000062",
  "source_prompt": "a rabbit is sitting in a pile of colorful eggs",
  "edit_prompt": "{\"cat\": {\"position\": 1, \"edit_type\": 1, \"action\": \"rabbit\"}, \"sleeping\": {\"position\": 3, \"edit_type\": 5, \"action\": \"sitting\"}, \"stones\": {\"position\": 9, \"edit_type\": 1, \"action\": \"eggs\"}}",
  "target_prompt": "a [cat] is [sleeping] in a pile of colorful [stones]",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_005_row_000062"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 21:24
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000062",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_005_row_000062\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_005_row_000062\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 21:24
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000070",
  "source_prompt": "the city of dresden, germany, europe",
  "edit_prompt": "{\"a sunny day of\": {\"position\": 0, \"edit_type\": 4, \"action\": \"+\"}, \"park\": {\"position\": 1, \"edit_type\": 1, \"action\": \"city\"}}",
  "target_prompt": "[a sunny day of] the [park] of dresden, germany, europe",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_006_row_000070"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 21:24
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000070",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_006_row_000070\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_006_row_000070\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 21:24
阶段：Phase 5 D_t + A_t + C_t
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_000139",
  "source_prompt": "a duck standing on a rock near water",
  "edit_prompt": "{\"chicken\": {\"position\": 1, \"edit_type\": 1, \"action\": \"duck\"}, \"sitting\": {\"position\": 2, \"edit_type\": 5, \"action\": \"standing\"}, \"board\": {\"position\": 5, \"edit_type\": 1, \"action\": \"rock\"}}",
  "target_prompt": "a [chicken] [sitting] on a [board] near water",
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_007_row_000139"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 21:25
阶段：Phase 5 D_t + A_t + C_t
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_000139",
  "phase": "phase5"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_007_row_000139\\source_reconstruction.png",
  "methods": [
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\phase5_20260328-2123\\samples\\sample_007_row_000139\\full_dynamic_mask\\edited.png"
  ]
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 21:25
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "phase5",
  "run_limit": 8,
  "methods": [
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\phase5_20260328-2123\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\phase5_20260328-2123\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\phase5_20260328-2123\\metrics_summary.json"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 22:01
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\train-00000-of-00262-57cebf95b4a9170c.parquet",
  "num_rows": 1195,
  "num_row_groups": 2,
  "column_names": "original_prompt, original_image, edit_prompt, edited_prompt, edited_image",
  "dataset_format": "legacy_edit_pair",
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x0000020D6A2AC380>\nrequired group field_id=-1 schema {\n  optional binary field_id=-1 original_prompt (String);\n  optional group field_id=-1 original_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 edit_prompt (String);\n  optional binary field_id=-1 edited_prompt (String);\n  optional group field_id=-1 edited_image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 22:01
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": null,
  "phase": "custom",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260328-2201",
  "manifest_json": "runs\\dymask_v1\\v1_20260328-2201\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260328-2201\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000051",
    "sample_001_row_000209",
    "sample_002_row_000228",
    "sample_003_row_000285",
    "sample_004_row_000457",
    "sample_005_row_000501",
    "sample_006_row_000563",
    "sample_007_row_001116"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 22:01
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "source_prompt": "Picture leaves, berries, table, kettle, window, the tea party, Cup, dishes, still life, blind, basket, jam",
  "edit_prompt": "Turn the leaves into pine needles",
  "target_prompt": "Picture pine needles, berries, table, kettle, window, the tea party, Cup, dishes, still life, blind, basket, jam",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_000_row_000051"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 22:02
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000051",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_000_row_000051\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_000_row_000051\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_000_row_000051\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_000_row_000051\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_000_row_000051\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_000_row_000051\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_000_row_000051\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 22:02
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000209",
  "source_prompt": "John Atkinson Grimshaw, Moonlight On The Lake, Roundhay Park, Leeds, 1872",
  "edit_prompt": "make the lake full of lava",
  "target_prompt": "John Atkinson Grimshaw, Moonlight On The Lava Lake, Roundhay Park, Leeds, 1872",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_001_row_000209"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 22:02
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000209",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_001_row_000209\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_001_row_000209\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_001_row_000209\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_001_row_000209\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_001_row_000209\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_001_row_000209\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_001_row_000209\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 22:02
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000228",
  "source_prompt": "painting of tree on river banks by Janine Robertson",
  "edit_prompt": "as a cubist painting",
  "target_prompt": "cubist painting of tree on river banks by Janine Robertson",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_002_row_000228"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 22:02
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000228",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_002_row_000228\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_002_row_000228\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_002_row_000228\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_002_row_000228\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_002_row_000228\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_002_row_000228\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_002_row_000228\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 22:02
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000285",
  "source_prompt": "Central Park Winter - San Remo Through Trees - New York City",
  "edit_prompt": "have the trees be palm trees",
  "target_prompt": "Central Park Winter - San Remo Through Palm Trees - New York City",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_003_row_000285"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 22:03
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000285",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_003_row_000285\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_003_row_000285\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_003_row_000285\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_003_row_000285\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_003_row_000285\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_003_row_000285\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_003_row_000285\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 22:03
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000457",
  "source_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting",
  "edit_prompt": "Make the sky purple",
  "target_prompt": "Ronald Tinney Landscape Painting - 'Calm Before the Storm', Cape Cod Modern Impressionist Marine Oil Painting, Purple Sky",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_004_row_000457"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 22:03
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000457",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_004_row_000457\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_004_row_000457\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_004_row_000457\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_004_row_000457\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_004_row_000457\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_004_row_000457\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_004_row_000457\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 22:03
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000501",
  "source_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities",
  "edit_prompt": "add a tornado",
  "target_prompt": "Idyllic Landscape Paintings by Artist Tomás Sánchez Render Nature's Meditative Qualities with Tornado",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_005_row_000501"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 22:03
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000501",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_005_row_000501\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_005_row_000501\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_005_row_000501\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_005_row_000501\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_005_row_000501\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_005_row_000501\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_005_row_000501\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 22:03
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000563",
  "source_prompt": "\"\"\"Peach Packing, Spartanburg County\"\" by Wenonah Day Bell (1890–1981), 1938. Oil on canvas, 38-  by 48-  inches.\"",
  "edit_prompt": "make it a photo",
  "target_prompt": "\"\"Peach Packing, Spartanburg County\" by Wenonah Day Bell (1890–1981), 1938. Photographic print, 38-  by 48-  inches.\"",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_006_row_000563"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 22:04
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000563",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_006_row_000563\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_006_row_000563\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_006_row_000563\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_006_row_000563\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_006_row_000563\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_006_row_000563\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_006_row_000563\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 22:04
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_001116",
  "source_prompt": "January 7, path in the snow at Saint Vincent",
  "edit_prompt": "make it a beach",
  "target_prompt": "January 7, path in the sand at Saint Vincent",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_007_row_001116"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 22:04
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_001116",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_007_row_001116\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_007_row_001116\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_007_row_001116\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_007_row_001116\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_007_row_001116\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_007_row_001116\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2201\\samples\\sample_007_row_001116\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 22:04
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 8,
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260328-2201\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260328-2201\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260328-2201\\metrics_summary.json",
  "five_method_case_metrics_csv": "runs\\dymask_v1\\v1_20260328-2201\\metrics_five_methods_case_level.csv",
  "five_method_summary_metrics_csv": "runs\\dymask_v1\\v1_20260328-2201\\metrics_five_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 22:12
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "D:\\Program\\dymask\\assets\\data\\V1-00000-of-00001.parquet"
}
```
结果：
```json
{
  "parquet_path": "D:\\Program\\dymask\\assets\\data\\V1-00000-of-00001.parquet",
  "num_rows": 140,
  "num_row_groups": 2,
  "column_names": "image, id, source_prompt, target_prompt, edit_action, aspect_mapping, blended_words, mask",
  "dataset_format": "single_image_prompt_edit",
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000002834B4ECD40>\nrequired group field_id=-1 schema {\n  optional group field_id=-1 image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 id (String);\n  optional binary field_id=-1 source_prompt (String);\n  optional binary field_id=-1 target_prompt (String);\n  optional binary field_id=-1 edit_action (String);\n  optional binary field_id=-1 aspect_mapping (String);\n  optional binary field_id=-1 blended_words (String);\n  optional binary field_id=-1 mask (String);\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 22:12
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": null,
  "phase": "custom",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260328-2212",
  "manifest_json": "runs\\dymask_v1\\v1_20260328-2212\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260328-2212\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000006",
    "sample_001_row_000026",
    "sample_002_row_000028",
    "sample_003_row_000035",
    "sample_004_row_000057",
    "sample_005_row_000062",
    "sample_006_row_000070",
    "sample_007_row_000139"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 22:12
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "source_prompt": "a cup of coffee with drawing of tulip putted on the wooden table",
  "edit_prompt": "{\"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"milk\": {\"position\": 3, \"edit_type\": 1, \"action\": \"coffee\"}, \"rose\": {\"position\": 7, \"edit_type\": 1, \"action\": \"tulip\"}}",
  "target_prompt": "a [yellow] cup of [milk] with drawing of [rose] putted on the wooden table",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_000_row_000006"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 22:13
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_000_row_000006\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_000_row_000006\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_000_row_000006\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_000_row_000006\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_000_row_000006\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_000_row_000006\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_000_row_000006\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 22:13
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "source_prompt": "a yellow bird with a red beak sitting on a branch",
  "edit_prompt": "{\"toy\": {\"position\": 1, \"edit_type\": 4, \"action\": \"+\"}, \"yellow\": {\"position\": 1, \"edit_type\": 3, \"action\": \"-\"}, \"cat\": {\"position\": 2, \"edit_type\": 1, \"action\": \"bird\"}, \"fur\": {\"position\": 6, \"edit_type\": 4, \"action\": \"beak\"}}",
  "target_prompt": "a [toy] [cat] with a red [fur] sitting on a branch",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_001_row_000026"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 22:13
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_001_row_000026\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_001_row_000026\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_001_row_000026\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_001_row_000026\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_001_row_000026\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_001_row_000026\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_001_row_000026\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 22:13
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000028",
  "source_prompt": "white flowers on a tree branch with blue sky background",
  "edit_prompt": "{\"Painting of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"red\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"white background\": {\"position\": 7, \"edit_type\": 8, \"action\": \"sky background\"}}",
  "target_prompt": "[Painting of] [red] flowers on a tree branch with [white background]",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_002_row_000028"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 22:13
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000028",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_002_row_000028\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_002_row_000028\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_002_row_000028\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_002_row_000028\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_002_row_000028\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_002_row_000028\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_002_row_000028\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 22:13
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000035",
  "source_prompt": "photograph, window of the world by jimmy kirk",
  "edit_prompt": "{\"painting\": {\"position\": 0, \"edit_type\": 9, \"action\": \"photograph\"}, \"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"ball\": {\"position\": 1, \"edit_type\": 1, \"action\": \"window\"}}",
  "target_prompt": "[painting], [yellow] [ball] of the world by jimmy kirk",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_003_row_000035"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 22:14
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000035",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_003_row_000035\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_003_row_000035\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_003_row_000035\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_003_row_000035\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_003_row_000035\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_003_row_000035\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_003_row_000035\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 22:14
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000057",
  "source_prompt": "an owl sitting on a branch",
  "edit_prompt": "{\"a photo of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"jumping\": {\"position\": 2, \"edit_type\": 5, \"action\": \"sitting\"}, \"rock\": {\"position\": 5, \"edit_type\": 1, \"action\": \"branch\"}}",
  "target_prompt": "[a photo of] an owl [jumping] on a [rock]",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_004_row_000057"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 22:14
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000057",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_004_row_000057\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_004_row_000057\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_004_row_000057\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_004_row_000057\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_004_row_000057\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_004_row_000057\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_004_row_000057\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 22:14
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000062",
  "source_prompt": "a rabbit is sitting in a pile of colorful eggs",
  "edit_prompt": "{\"cat\": {\"position\": 1, \"edit_type\": 1, \"action\": \"rabbit\"}, \"sleeping\": {\"position\": 3, \"edit_type\": 5, \"action\": \"sitting\"}, \"stones\": {\"position\": 9, \"edit_type\": 1, \"action\": \"eggs\"}}",
  "target_prompt": "a [cat] is [sleeping] in a pile of colorful [stones]",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_005_row_000062"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 22:15
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000062",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_005_row_000062\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_005_row_000062\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_005_row_000062\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_005_row_000062\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_005_row_000062\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_005_row_000062\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_005_row_000062\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 22:15
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000070",
  "source_prompt": "the city of dresden, germany, europe",
  "edit_prompt": "{\"a sunny day of\": {\"position\": 0, \"edit_type\": 4, \"action\": \"+\"}, \"park\": {\"position\": 1, \"edit_type\": 1, \"action\": \"city\"}}",
  "target_prompt": "[a sunny day of] the [park] of dresden, germany, europe",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_006_row_000070"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 22:15
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000070",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_006_row_000070\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_006_row_000070\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_006_row_000070\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_006_row_000070\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_006_row_000070\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_006_row_000070\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_006_row_000070\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 22:15
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_000139",
  "source_prompt": "a duck standing on a rock near water",
  "edit_prompt": "{\"chicken\": {\"position\": 1, \"edit_type\": 1, \"action\": \"duck\"}, \"sitting\": {\"position\": 2, \"edit_type\": 5, \"action\": \"standing\"}, \"board\": {\"position\": 5, \"edit_type\": 1, \"action\": \"rock\"}}",
  "target_prompt": "a [chicken] [sitting] on a [board] near water",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_007_row_000139"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 22:15
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_000139",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_007_row_000139\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_007_row_000139\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_007_row_000139\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_007_row_000139\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_007_row_000139\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_007_row_000139\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2212\\samples\\sample_007_row_000139\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 22:15
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 8,
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260328-2212\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260328-2212\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260328-2212\\metrics_summary.json",
  "five_method_case_metrics_csv": "runs\\dymask_v1\\v1_20260328-2212\\metrics_five_methods_case_level.csv",
  "five_method_summary_metrics_csv": "runs\\dymask_v1\\v1_20260328-2212\\metrics_five_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-28 23:27
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "D:\\Program\\dymask\\assets\\data\\V1-00000-of-00001.parquet"
}
```
结果：
```json
{
  "parquet_path": "D:\\Program\\dymask\\assets\\data\\V1-00000-of-00001.parquet",
  "num_rows": 140,
  "num_row_groups": 2,
  "column_names": "image, id, source_prompt, target_prompt, edit_action, aspect_mapping, blended_words, mask",
  "dataset_format": "single_image_prompt_edit",
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x00000210DAF5DC00>\nrequired group field_id=-1 schema {\n  optional group field_id=-1 image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 id (String);\n  optional binary field_id=-1 source_prompt (String);\n  optional binary field_id=-1 target_prompt (String);\n  optional binary field_id=-1 edit_action (String);\n  optional binary field_id=-1 aspect_mapping (String);\n  optional binary field_id=-1 blended_words (String);\n  optional binary field_id=-1 mask (String);\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-28 23:27
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": null,
  "phase": "custom",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260328-2327",
  "manifest_json": "runs\\dymask_v1\\v1_20260328-2327\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260328-2327\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000006",
    "sample_001_row_000026",
    "sample_002_row_000028",
    "sample_003_row_000035",
    "sample_004_row_000057",
    "sample_005_row_000062",
    "sample_006_row_000070",
    "sample_007_row_000139"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-28 23:27
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "source_prompt": "a cup of coffee with drawing of tulip putted on the wooden table",
  "edit_prompt": "{\"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"milk\": {\"position\": 3, \"edit_type\": 1, \"action\": \"coffee\"}, \"rose\": {\"position\": 7, \"edit_type\": 1, \"action\": \"tulip\"}}",
  "target_prompt": "a [yellow] cup of [milk] with drawing of [rose] putted on the wooden table",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_000_row_000006"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 23:28
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_000_row_000006\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_000_row_000006\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_000_row_000006\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_000_row_000006\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_000_row_000006\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_000_row_000006\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_000_row_000006\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 23:28
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "source_prompt": "a yellow bird with a red beak sitting on a branch",
  "edit_prompt": "{\"toy\": {\"position\": 1, \"edit_type\": 4, \"action\": \"+\"}, \"yellow\": {\"position\": 1, \"edit_type\": 3, \"action\": \"-\"}, \"cat\": {\"position\": 2, \"edit_type\": 1, \"action\": \"bird\"}, \"fur\": {\"position\": 6, \"edit_type\": 4, \"action\": \"beak\"}}",
  "target_prompt": "a [toy] [cat] with a red [fur] sitting on a branch",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_001_row_000026"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 23:28
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_001_row_000026\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_001_row_000026\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_001_row_000026\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_001_row_000026\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_001_row_000026\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_001_row_000026\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_001_row_000026\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 23:28
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000028",
  "source_prompt": "white flowers on a tree branch with blue sky background",
  "edit_prompt": "{\"Painting of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"red\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"white background\": {\"position\": 7, \"edit_type\": 8, \"action\": \"sky background\"}}",
  "target_prompt": "[Painting of] [red] flowers on a tree branch with [white background]",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_002_row_000028"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 23:28
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000028",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_002_row_000028\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_002_row_000028\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_002_row_000028\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_002_row_000028\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_002_row_000028\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_002_row_000028\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_002_row_000028\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 23:28
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000035",
  "source_prompt": "photograph, window of the world by jimmy kirk",
  "edit_prompt": "{\"painting\": {\"position\": 0, \"edit_type\": 9, \"action\": \"photograph\"}, \"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"ball\": {\"position\": 1, \"edit_type\": 1, \"action\": \"window\"}}",
  "target_prompt": "[painting], [yellow] [ball] of the world by jimmy kirk",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_003_row_000035"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 23:29
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000035",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_003_row_000035\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_003_row_000035\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_003_row_000035\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_003_row_000035\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_003_row_000035\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_003_row_000035\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_003_row_000035\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 23:29
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000057",
  "source_prompt": "an owl sitting on a branch",
  "edit_prompt": "{\"a photo of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"jumping\": {\"position\": 2, \"edit_type\": 5, \"action\": \"sitting\"}, \"rock\": {\"position\": 5, \"edit_type\": 1, \"action\": \"branch\"}}",
  "target_prompt": "[a photo of] an owl [jumping] on a [rock]",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_004_row_000057"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 23:29
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000057",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_004_row_000057\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_004_row_000057\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_004_row_000057\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_004_row_000057\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_004_row_000057\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_004_row_000057\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_004_row_000057\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 23:29
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000062",
  "source_prompt": "a rabbit is sitting in a pile of colorful eggs",
  "edit_prompt": "{\"cat\": {\"position\": 1, \"edit_type\": 1, \"action\": \"rabbit\"}, \"sleeping\": {\"position\": 3, \"edit_type\": 5, \"action\": \"sitting\"}, \"stones\": {\"position\": 9, \"edit_type\": 1, \"action\": \"eggs\"}}",
  "target_prompt": "a [cat] is [sleeping] in a pile of colorful [stones]",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_005_row_000062"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 23:29
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000062",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_005_row_000062\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_005_row_000062\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_005_row_000062\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_005_row_000062\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_005_row_000062\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_005_row_000062\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_005_row_000062\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 23:29
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000070",
  "source_prompt": "the city of dresden, germany, europe",
  "edit_prompt": "{\"a sunny day of\": {\"position\": 0, \"edit_type\": 4, \"action\": \"+\"}, \"park\": {\"position\": 1, \"edit_type\": 1, \"action\": \"city\"}}",
  "target_prompt": "[a sunny day of] the [park] of dresden, germany, europe",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_006_row_000070"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 23:30
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000070",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_006_row_000070\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_006_row_000070\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_006_row_000070\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_006_row_000070\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_006_row_000070\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_006_row_000070\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_006_row_000070\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 23:30
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_000139",
  "source_prompt": "a duck standing on a rock near water",
  "edit_prompt": "{\"chicken\": {\"position\": 1, \"edit_type\": 1, \"action\": \"duck\"}, \"sitting\": {\"position\": 2, \"edit_type\": 5, \"action\": \"standing\"}, \"board\": {\"position\": 5, \"edit_type\": 1, \"action\": \"rock\"}}",
  "target_prompt": "a [chicken] [sitting] on a [board] near water",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_007_row_000139"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-28 23:30
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_000139",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_007_row_000139\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_007_row_000139\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_007_row_000139\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_007_row_000139\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_007_row_000139\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_007_row_000139\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260328-2327\\samples\\sample_007_row_000139\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-28 23:30
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 8,
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260328-2327\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260328-2327\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260328-2327\\metrics_summary.json",
  "five_method_case_metrics_csv": "runs\\dymask_v1\\v1_20260328-2327\\metrics_five_methods_case_level.csv",
  "five_method_summary_metrics_csv": "runs\\dymask_v1\\v1_20260328-2327\\metrics_five_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-29 00:32
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "D:\\Program\\dymask\\assets\\data\\V1-00000-of-00001.parquet"
}
```
结果：
```json
{
  "parquet_path": "D:\\Program\\dymask\\assets\\data\\V1-00000-of-00001.parquet",
  "num_rows": 140,
  "num_row_groups": 2,
  "column_names": "image, id, source_prompt, target_prompt, edit_action, aspect_mapping, blended_words, mask",
  "dataset_format": "single_image_prompt_edit",
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x0000016799F0E600>\nrequired group field_id=-1 schema {\n  optional group field_id=-1 image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 id (String);\n  optional binary field_id=-1 source_prompt (String);\n  optional binary field_id=-1 target_prompt (String);\n  optional binary field_id=-1 edit_action (String);\n  optional binary field_id=-1 aspect_mapping (String);\n  optional binary field_id=-1 blended_words (String);\n  optional binary field_id=-1 mask (String);\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-29 00:32
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 1,
  "sample_seed": 42,
  "row_indices": [
    6
  ],
  "phase": "custom",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260329-0032",
  "manifest_json": "runs\\dymask_v1\\v1_20260329-0032\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260329-0032\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000006"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-29 00:32
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "source_prompt": "a cup of coffee with drawing of tulip putted on the wooden table",
  "edit_prompt": "{\"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"milk\": {\"position\": 3, \"edit_type\": 1, \"action\": \"coffee\"}, \"rose\": {\"position\": 7, \"edit_type\": 1, \"action\": \"tulip\"}}",
  "target_prompt": "a [yellow] cup of [milk] with drawing of [rose] putted on the wooden table",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-0032\\samples\\sample_000_row_000006"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 00:32
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-0032\\samples\\sample_000_row_000006\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-0032\\samples\\sample_000_row_000006\\target_only\\edited.png"
  ],
  "overview_path": null
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 00:32
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 1,
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260329-0032\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260329-0032\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260329-0032\\metrics_summary.json",
  "five_method_case_metrics_csv": "runs\\dymask_v1\\v1_20260329-0032\\metrics_five_methods_case_level.csv",
  "five_method_summary_metrics_csv": "runs\\dymask_v1\\v1_20260329-0032\\metrics_five_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-29 14:45
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet",
  "num_rows": 140,
  "num_row_groups": 2,
  "column_names": "image, id, source_prompt, target_prompt, edit_action, aspect_mapping, blended_words, mask",
  "dataset_format": "single_image_prompt_edit",
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x00000157BF1E2D80>\nrequired group field_id=-1 schema {\n  optional group field_id=-1 image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 id (String);\n  optional binary field_id=-1 source_prompt (String);\n  optional binary field_id=-1 target_prompt (String);\n  optional binary field_id=-1 edit_action (String);\n  optional binary field_id=-1 aspect_mapping (String);\n  optional binary field_id=-1 blended_words (String);\n  optional binary field_id=-1 mask (String);\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-29 14:45
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": null,
  "phase": "custom",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260329-1445",
  "manifest_json": "runs\\dymask_v1\\v1_20260329-1445\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260329-1445\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000006",
    "sample_001_row_000026",
    "sample_002_row_000028",
    "sample_003_row_000035",
    "sample_004_row_000057",
    "sample_005_row_000062",
    "sample_006_row_000070",
    "sample_007_row_000139"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-29 14:46
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet",
  "num_rows": 140,
  "num_row_groups": 2,
  "column_names": "image, id, source_prompt, target_prompt, edit_action, aspect_mapping, blended_words, mask",
  "dataset_format": "single_image_prompt_edit",
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000001BE9633ED00>\nrequired group field_id=-1 schema {\n  optional group field_id=-1 image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 id (String);\n  optional binary field_id=-1 source_prompt (String);\n  optional binary field_id=-1 target_prompt (String);\n  optional binary field_id=-1 edit_action (String);\n  optional binary field_id=-1 aspect_mapping (String);\n  optional binary field_id=-1 blended_words (String);\n  optional binary field_id=-1 mask (String);\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-29 14:46
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 1,
  "sample_seed": 42,
  "row_indices": null,
  "phase": "custom",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260329-1446",
  "manifest_json": "runs\\dymask_v1\\v1_20260329-1446\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260329-1446\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000028"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-29 14:46
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000028",
  "source_prompt": "white flowers on a tree branch with blue sky background",
  "edit_prompt": "{\"Painting of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"red\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"white background\": {\"position\": 7, \"edit_type\": 8, \"action\": \"sky background\"}}",
  "target_prompt": "[Painting of] [red] flowers on a tree branch with [white background]",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1446\\samples\\sample_000_row_000028"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 14:46
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000028",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1446\\samples\\sample_000_row_000028\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1446\\samples\\sample_000_row_000028\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1446\\samples\\sample_000_row_000028\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1446\\samples\\sample_000_row_000028\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1446\\samples\\sample_000_row_000028\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1446\\samples\\sample_000_row_000028\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1446\\samples\\sample_000_row_000028\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1446\\samples\\sample_000_row_000028\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 14:46
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 1,
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260329-1446\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260329-1446\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260329-1446\\metrics_summary.json",
  "five_method_case_metrics_csv": "runs\\dymask_v1\\v1_20260329-1446\\metrics_five_methods_case_level.csv",
  "five_method_summary_metrics_csv": "runs\\dymask_v1\\v1_20260329-1446\\metrics_five_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-29 14:47
阶段：数据准备
操作：探测 parquet schema
输入：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet"
}
```
结果：
```json
{
  "parquet_path": "assets\\data\\V1-00000-of-00001.parquet",
  "num_rows": 140,
  "num_row_groups": 2,
  "column_names": "image, id, source_prompt, target_prompt, edit_action, aspect_mapping, blended_words, mask",
  "dataset_format": "single_image_prompt_edit",
  "schema": "<pyarrow._parquet.ParquetSchema object at 0x000001BFB9A8F000>\nrequired group field_id=-1 schema {\n  optional group field_id=-1 image {\n    optional binary field_id=-1 bytes;\n    optional binary field_id=-1 path (String);\n  }\n  optional binary field_id=-1 id (String);\n  optional binary field_id=-1 source_prompt (String);\n  optional binary field_id=-1 target_prompt (String);\n  optional binary field_id=-1 edit_action (String);\n  optional binary field_id=-1 aspect_mapping (String);\n  optional binary field_id=-1 blended_words (String);\n  optional binary field_id=-1 mask (String);\n}\n"
}
```
结论：已确认数据集字段结构，可用于 source/target 成对抽样。
下一步：抽样并固化 sample manifest。

## 2026-03-29 14:47
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": null,
  "phase": "custom",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260329-1447",
  "manifest_json": "runs\\dymask_v1\\v1_20260329-1447\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260329-1447\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_row_000006",
    "sample_001_row_000026",
    "sample_002_row_000028",
    "sample_003_row_000035",
    "sample_004_row_000057",
    "sample_005_row_000062",
    "sample_006_row_000070",
    "sample_007_row_000139"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-29 14:47
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "source_prompt": "a cup of coffee with drawing of tulip putted on the wooden table",
  "edit_prompt": "{\"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"milk\": {\"position\": 3, \"edit_type\": 1, \"action\": \"coffee\"}, \"rose\": {\"position\": 7, \"edit_type\": 1, \"action\": \"tulip\"}}",
  "target_prompt": "a [yellow] cup of [milk] with drawing of [rose] putted on the wooden table",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_000_row_000006"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 14:48
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_row_000006",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_000_row_000006\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_000_row_000006\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_000_row_000006\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_000_row_000006\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_000_row_000006\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_000_row_000006\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_000_row_000006\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_000_row_000006\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 14:48
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "source_prompt": "a yellow bird with a red beak sitting on a branch",
  "edit_prompt": "{\"toy\": {\"position\": 1, \"edit_type\": 4, \"action\": \"+\"}, \"yellow\": {\"position\": 1, \"edit_type\": 3, \"action\": \"-\"}, \"cat\": {\"position\": 2, \"edit_type\": 1, \"action\": \"bird\"}, \"fur\": {\"position\": 6, \"edit_type\": 4, \"action\": \"beak\"}}",
  "target_prompt": "a [toy] [cat] with a red [fur] sitting on a branch",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_001_row_000026"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 14:49
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_row_000026",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_001_row_000026\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_001_row_000026\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_001_row_000026\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_001_row_000026\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_001_row_000026\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_001_row_000026\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_001_row_000026\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_001_row_000026\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 14:49
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_row_000028",
  "source_prompt": "white flowers on a tree branch with blue sky background",
  "edit_prompt": "{\"Painting of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"red\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"white background\": {\"position\": 7, \"edit_type\": 8, \"action\": \"sky background\"}}",
  "target_prompt": "[Painting of] [red] flowers on a tree branch with [white background]",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_002_row_000028"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 14:49
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_row_000028",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_002_row_000028\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_002_row_000028\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_002_row_000028\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_002_row_000028\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_002_row_000028\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_002_row_000028\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_002_row_000028\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_002_row_000028\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 14:49
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_row_000035",
  "source_prompt": "photograph, window of the world by jimmy kirk",
  "edit_prompt": "{\"painting\": {\"position\": 0, \"edit_type\": 9, \"action\": \"photograph\"}, \"yellow\": {\"position\": 1, \"edit_type\": 6, \"action\": \"+\"}, \"ball\": {\"position\": 1, \"edit_type\": 1, \"action\": \"window\"}}",
  "target_prompt": "[painting], [yellow] [ball] of the world by jimmy kirk",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_003_row_000035"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 14:50
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_row_000035",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_003_row_000035\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_003_row_000035\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_003_row_000035\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_003_row_000035\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_003_row_000035\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_003_row_000035\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_003_row_000035\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_003_row_000035\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 14:50
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_row_000057",
  "source_prompt": "an owl sitting on a branch",
  "edit_prompt": "{\"a photo of\": {\"position\": 0, \"edit_type\": 9, \"action\": \"+\"}, \"jumping\": {\"position\": 2, \"edit_type\": 5, \"action\": \"sitting\"}, \"rock\": {\"position\": 5, \"edit_type\": 1, \"action\": \"branch\"}}",
  "target_prompt": "[a photo of] an owl [jumping] on a [rock]",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_004_row_000057"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 14:51
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_row_000057",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_004_row_000057\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_004_row_000057\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_004_row_000057\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_004_row_000057\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_004_row_000057\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_004_row_000057\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_004_row_000057\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_004_row_000057\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 14:51
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_row_000062",
  "source_prompt": "a rabbit is sitting in a pile of colorful eggs",
  "edit_prompt": "{\"cat\": {\"position\": 1, \"edit_type\": 1, \"action\": \"rabbit\"}, \"sleeping\": {\"position\": 3, \"edit_type\": 5, \"action\": \"sitting\"}, \"stones\": {\"position\": 9, \"edit_type\": 1, \"action\": \"eggs\"}}",
  "target_prompt": "a [cat] is [sleeping] in a pile of colorful [stones]",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_005_row_000062"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 14:52
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_row_000062",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_005_row_000062\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_005_row_000062\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_005_row_000062\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_005_row_000062\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_005_row_000062\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_005_row_000062\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_005_row_000062\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_005_row_000062\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 14:52
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_row_000070",
  "source_prompt": "the city of dresden, germany, europe",
  "edit_prompt": "{\"a sunny day of\": {\"position\": 0, \"edit_type\": 4, \"action\": \"+\"}, \"park\": {\"position\": 1, \"edit_type\": 1, \"action\": \"city\"}}",
  "target_prompt": "[a sunny day of] the [park] of dresden, germany, europe",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_006_row_000070"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 14:53
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_row_000070",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_006_row_000070\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_006_row_000070\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_006_row_000070\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_006_row_000070\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_006_row_000070\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_006_row_000070\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_006_row_000070\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_006_row_000070\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 14:53
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_row_000139",
  "source_prompt": "a duck standing on a rock near water",
  "edit_prompt": "{\"chicken\": {\"position\": 1, \"edit_type\": 1, \"action\": \"duck\"}, \"sitting\": {\"position\": 2, \"edit_type\": 5, \"action\": \"standing\"}, \"board\": {\"position\": 5, \"edit_type\": 1, \"action\": \"rock\"}}",
  "target_prompt": "a [chicken] [sitting] on a [board] near water",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_007_row_000139"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 14:54
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_row_000139",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_007_row_000139\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_007_row_000139\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_007_row_000139\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_007_row_000139\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_007_row_000139\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_007_row_000139\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_007_row_000139\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1447\\samples\\sample_007_row_000139\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 14:54
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 8,
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260329-1447\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260329-1447\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260329-1447\\metrics_summary.json",
  "five_method_case_metrics_csv": "runs\\dymask_v1\\v1_20260329-1447\\metrics_five_methods_case_level.csv",
  "five_method_summary_metrics_csv": "runs\\dymask_v1\\v1_20260329-1447\\metrics_five_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-29 16:38
阶段：数据准备
操作：加载 PIE-Bench 数据集
输入：
```json
{
  "piebench_path": "assets\\PIE-Bench"
}
```
结果：
```json
{
  "dataset": "PIE-Bench",
  "path": "assets\\PIE-Bench"
}
```
结论：已确认 PIE-Bench 数据集，将使用 GT mask 计算 masked 指标。
下一步：抽样并固化 sample manifest。

## 2026-03-29 16:38
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 2,
  "sample_seed": 42,
  "row_indices": null,
  "phase": "custom",
  "methods": [
    "target_only",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260329-1638",
  "manifest_json": "runs\\dymask_v1\\v1_20260329-1638\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260329-1638\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_pie_424000000000",
    "sample_001_pie_712000000003"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-29 16:38
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_pie_424000000000",
  "source_prompt": "the [dimly] illuminated earth",
  "edit_prompt": "Change dimly illuminated to sunlit illuminated",
  "target_prompt": "the sunlit illuminated earth",
  "methods": [
    "target_only",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1638\\samples\\sample_000_pie_424000000000"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 16:39
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_pie_424000000000",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1638\\samples\\sample_000_pie_424000000000\\source_reconstruction.png",
  "methods": [
    "target_only",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1638\\samples\\sample_000_pie_424000000000\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1638\\samples\\sample_000_pie_424000000000\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": null
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 16:39
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_pie_712000000003",
  "source_prompt": "two boys in the water with sticks and buckets",
  "edit_prompt": "Add wooden puppet characteristics to the boys",
  "target_prompt": "two wooden boys puppet in the water with sticks and buckets",
  "methods": [
    "target_only",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1638\\samples\\sample_001_pie_712000000003"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 16:39
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_pie_712000000003",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1638\\samples\\sample_001_pie_712000000003\\source_reconstruction.png",
  "methods": [
    "target_only",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1638\\samples\\sample_001_pie_712000000003\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1638\\samples\\sample_001_pie_712000000003\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": null
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 16:39
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 2,
  "methods": [
    "target_only",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260329-1638\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260329-1638\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260329-1638\\metrics_summary.json",
  "five_method_case_metrics_csv": "runs\\dymask_v1\\v1_20260329-1638\\metrics_five_methods_case_level.csv",
  "five_method_summary_metrics_csv": "runs\\dymask_v1\\v1_20260329-1638\\metrics_five_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-29 16:40
阶段：数据准备
操作：加载 PIE-Bench 数据集
输入：
```json
{
  "piebench_path": "assets\\PIE-Bench"
}
```
结果：
```json
{
  "dataset": "PIE-Bench",
  "path": "assets\\PIE-Bench"
}
```
结论：已确认 PIE-Bench 数据集，将使用 GT mask 计算 masked 指标。
下一步：抽样并固化 sample manifest。

## 2026-03-29 16:40
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": null,
  "phase": "custom",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260329-1640",
  "manifest_json": "runs\\dymask_v1\\v1_20260329-1640\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260329-1640\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_pie_424000000000",
    "sample_001_pie_712000000003",
    "sample_002_pie_213000000003",
    "sample_003_pie_121000000005",
    "sample_004_pie_913000000002",
    "sample_005_pie_321000000007",
    "sample_006_pie_314000000005",
    "sample_007_pie_911000000000"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-29 16:40
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_pie_424000000000",
  "source_prompt": "the [dimly] illuminated earth",
  "edit_prompt": "Change dimly illuminated to sunlit illuminated",
  "target_prompt": "the sunlit illuminated earth",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_000_pie_424000000000"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 16:40
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_pie_424000000000",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_000_pie_424000000000\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_000_pie_424000000000\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_000_pie_424000000000\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_000_pie_424000000000\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_000_pie_424000000000\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_000_pie_424000000000\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_000_pie_424000000000\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_000_pie_424000000000\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 16:40
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_pie_712000000003",
  "source_prompt": "two boys in the water with sticks and buckets",
  "edit_prompt": "Add wooden puppet characteristics to the boys",
  "target_prompt": "two wooden boys puppet in the water with sticks and buckets",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_001_pie_712000000003"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 16:41
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_pie_712000000003",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_001_pie_712000000003\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_001_pie_712000000003\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_001_pie_712000000003\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_001_pie_712000000003\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_001_pie_712000000003\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_001_pie_712000000003\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_001_pie_712000000003\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_001_pie_712000000003\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 16:41
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_pie_213000000003",
  "source_prompt": "notebook, pencil, glasses, camera on a map",
  "edit_prompt": "Add a cup of coffee on the map",
  "target_prompt": "notebook, pencil, glasses, camera and coffee on a map",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_002_pie_213000000003"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 16:42
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_pie_213000000003",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_002_pie_213000000003\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_002_pie_213000000003\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_002_pie_213000000003\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_002_pie_213000000003\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_002_pie_213000000003\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_002_pie_213000000003\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_002_pie_213000000003\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_002_pie_213000000003\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 16:42
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_pie_121000000005",
  "source_prompt": "a [squirrel] is sitting on top of a wooden fence",
  "edit_prompt": "Change the animal from squirrel to rabbit",
  "target_prompt": "a rabbit is sitting on top of a wooden fence",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_003_pie_121000000005"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 16:43
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_pie_121000000005",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_003_pie_121000000005\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_003_pie_121000000005\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_003_pie_121000000005\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_003_pie_121000000005\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_003_pie_121000000005\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_003_pie_121000000005\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_003_pie_121000000005\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_003_pie_121000000005\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 16:43
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_pie_913000000002",
  "source_prompt": "christmas living room with fireplace, chair, wreath and tree",
  "edit_prompt": "Add a pixel art style to the Christmas living room",
  "target_prompt": "a pixel art of christmas living room with fireplace, chair, wreath and tree",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_004_pie_913000000002"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 16:43
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_pie_913000000002",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_004_pie_913000000002\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_004_pie_913000000002\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_004_pie_913000000002\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_004_pie_913000000002\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_004_pie_913000000002\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_004_pie_913000000002\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_004_pie_913000000002\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_004_pie_913000000002\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 16:43
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_pie_321000000007",
  "source_prompt": "[a husky dog running on] a path in the woods",
  "edit_prompt": "Remove the husky dog",
  "target_prompt": "a path in the woods",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_005_pie_321000000007"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 16:44
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_pie_321000000007",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_005_pie_321000000007\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_005_pie_321000000007\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_005_pie_321000000007\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_005_pie_321000000007\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_005_pie_321000000007\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_005_pie_321000000007\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_005_pie_321000000007\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_005_pie_321000000007\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 16:44
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_pie_314000000005",
  "source_prompt": "a painting of a house [by the water]",
  "edit_prompt": "Remove the water",
  "target_prompt": "a painting of a house",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_006_pie_314000000005"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 16:45
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_pie_314000000005",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_006_pie_314000000005\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_006_pie_314000000005\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_006_pie_314000000005\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_006_pie_314000000005\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_006_pie_314000000005\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_006_pie_314000000005\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_006_pie_314000000005\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_006_pie_314000000005\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 16:45
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_pie_911000000000",
  "source_prompt": "a cat and a bunny",
  "edit_prompt": "change the style of the image to photo",
  "target_prompt": "a photo of a cat and a bunny",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_007_pie_911000000000"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 16:46
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_pie_911000000000",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_007_pie_911000000000\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_007_pie_911000000000\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_007_pie_911000000000\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_007_pie_911000000000\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_007_pie_911000000000\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_007_pie_911000000000\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_007_pie_911000000000\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1640\\samples\\sample_007_pie_911000000000\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 16:46
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 8,
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260329-1640\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260329-1640\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260329-1640\\metrics_summary.json",
  "five_method_case_metrics_csv": "runs\\dymask_v1\\v1_20260329-1640\\metrics_five_methods_case_level.csv",
  "five_method_summary_metrics_csv": "runs\\dymask_v1\\v1_20260329-1640\\metrics_five_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-29 17:51
阶段：数据准备
操作：加载 PIE-Bench 数据集
输入：
```json
{
  "piebench_path": "assets\\PIE-Bench"
}
```
结果：
```json
{
  "dataset": "PIE-Bench",
  "path": "assets\\PIE-Bench"
}
```
结论：已确认 PIE-Bench 数据集，将使用 GT mask 计算 masked 指标。
下一步：抽样并固化 sample manifest。

## 2026-03-29 17:51
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": null,
  "phase": "custom",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260329-1751",
  "manifest_json": "runs\\dymask_v1\\v1_20260329-1751\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260329-1751\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_pie_424000000000",
    "sample_001_pie_712000000003",
    "sample_002_pie_213000000003",
    "sample_003_pie_121000000005",
    "sample_004_pie_913000000002",
    "sample_005_pie_321000000007",
    "sample_006_pie_314000000005",
    "sample_007_pie_911000000000"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-29 17:52
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_pie_424000000000",
  "source_prompt": "the [dimly] illuminated earth",
  "edit_prompt": "Change dimly illuminated to sunlit illuminated",
  "target_prompt": "the sunlit illuminated earth",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_000_pie_424000000000"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 17:53
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_pie_424000000000",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_000_pie_424000000000\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_000_pie_424000000000\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_000_pie_424000000000\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_000_pie_424000000000\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_000_pie_424000000000\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_000_pie_424000000000\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_000_pie_424000000000\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_000_pie_424000000000\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 17:53
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_pie_712000000003",
  "source_prompt": "two boys in the water with sticks and buckets",
  "edit_prompt": "Add wooden puppet characteristics to the boys",
  "target_prompt": "two wooden boys puppet in the water with sticks and buckets",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_001_pie_712000000003"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 17:55
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_pie_712000000003",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_001_pie_712000000003\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_001_pie_712000000003\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_001_pie_712000000003\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_001_pie_712000000003\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_001_pie_712000000003\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_001_pie_712000000003\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_001_pie_712000000003\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_001_pie_712000000003\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 17:55
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_pie_213000000003",
  "source_prompt": "notebook, pencil, glasses, camera on a map",
  "edit_prompt": "Add a cup of coffee on the map",
  "target_prompt": "notebook, pencil, glasses, camera and coffee on a map",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_002_pie_213000000003"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 17:56
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_pie_213000000003",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_002_pie_213000000003\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_002_pie_213000000003\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_002_pie_213000000003\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_002_pie_213000000003\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_002_pie_213000000003\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_002_pie_213000000003\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_002_pie_213000000003\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_002_pie_213000000003\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 17:56
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_pie_121000000005",
  "source_prompt": "a [squirrel] is sitting on top of a wooden fence",
  "edit_prompt": "Change the animal from squirrel to rabbit",
  "target_prompt": "a rabbit is sitting on top of a wooden fence",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_003_pie_121000000005"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 17:58
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_pie_121000000005",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_003_pie_121000000005\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_003_pie_121000000005\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_003_pie_121000000005\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_003_pie_121000000005\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_003_pie_121000000005\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_003_pie_121000000005\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_003_pie_121000000005\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_003_pie_121000000005\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 17:58
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_pie_913000000002",
  "source_prompt": "christmas living room with fireplace, chair, wreath and tree",
  "edit_prompt": "Add a pixel art style to the Christmas living room",
  "target_prompt": "a pixel art of christmas living room with fireplace, chair, wreath and tree",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_004_pie_913000000002"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 17:59
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_pie_913000000002",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_004_pie_913000000002\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_004_pie_913000000002\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_004_pie_913000000002\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_004_pie_913000000002\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_004_pie_913000000002\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_004_pie_913000000002\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_004_pie_913000000002\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_004_pie_913000000002\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 17:59
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_pie_321000000007",
  "source_prompt": "[a husky dog running on] a path in the woods",
  "edit_prompt": "Remove the husky dog",
  "target_prompt": "a path in the woods",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_005_pie_321000000007"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 18:01
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_pie_321000000007",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_005_pie_321000000007\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_005_pie_321000000007\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_005_pie_321000000007\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_005_pie_321000000007\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_005_pie_321000000007\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_005_pie_321000000007\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_005_pie_321000000007\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_005_pie_321000000007\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 18:01
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_pie_314000000005",
  "source_prompt": "a painting of a house [by the water]",
  "edit_prompt": "Remove the water",
  "target_prompt": "a painting of a house",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_006_pie_314000000005"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 18:02
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_pie_314000000005",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_006_pie_314000000005\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_006_pie_314000000005\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_006_pie_314000000005\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_006_pie_314000000005\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_006_pie_314000000005\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_006_pie_314000000005\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_006_pie_314000000005\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_006_pie_314000000005\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 18:02
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_pie_911000000000",
  "source_prompt": "a cat and a bunny",
  "edit_prompt": "change the style of the image to photo",
  "target_prompt": "a photo of a cat and a bunny",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_007_pie_911000000000"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 18:04
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_pie_911000000000",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_007_pie_911000000000\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_007_pie_911000000000\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_007_pie_911000000000\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_007_pie_911000000000\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_007_pie_911000000000\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_007_pie_911000000000\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_007_pie_911000000000\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1751\\samples\\sample_007_pie_911000000000\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 18:04
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 8,
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260329-1751\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260329-1751\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260329-1751\\metrics_summary.json",
  "five_method_case_metrics_csv": "runs\\dymask_v1\\v1_20260329-1751\\metrics_five_methods_case_level.csv",
  "five_method_summary_metrics_csv": "runs\\dymask_v1\\v1_20260329-1751\\metrics_five_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-29 18:06
阶段：数据准备
操作：加载 PIE-Bench 数据集
输入：
```json
{
  "piebench_path": "assets\\PIE-Bench"
}
```
结果：
```json
{
  "dataset": "PIE-Bench",
  "path": "assets\\PIE-Bench"
}
```
结论：已确认 PIE-Bench 数据集，将使用 GT mask 计算 masked 指标。
下一步：抽样并固化 sample manifest。

## 2026-03-29 18:06
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": null,
  "phase": "custom",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260329-1806",
  "manifest_json": "runs\\dymask_v1\\v1_20260329-1806\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260329-1806\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_pie_424000000000",
    "sample_001_pie_712000000003",
    "sample_002_pie_213000000003",
    "sample_003_pie_121000000005",
    "sample_004_pie_913000000002",
    "sample_005_pie_321000000007",
    "sample_006_pie_314000000005",
    "sample_007_pie_911000000000"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-29 18:06
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_pie_424000000000",
  "source_prompt": "the [dimly] illuminated earth",
  "edit_prompt": "Change dimly illuminated to sunlit illuminated",
  "target_prompt": "the sunlit illuminated earth",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_000_pie_424000000000"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 18:07
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_pie_424000000000",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_000_pie_424000000000\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_000_pie_424000000000\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_000_pie_424000000000\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_000_pie_424000000000\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_000_pie_424000000000\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_000_pie_424000000000\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_000_pie_424000000000\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_000_pie_424000000000\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 18:07
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_pie_712000000003",
  "source_prompt": "two boys in the water with sticks and buckets",
  "edit_prompt": "Add wooden puppet characteristics to the boys",
  "target_prompt": "two wooden boys puppet in the water with sticks and buckets",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_001_pie_712000000003"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 18:08
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_pie_712000000003",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_001_pie_712000000003\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_001_pie_712000000003\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_001_pie_712000000003\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_001_pie_712000000003\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_001_pie_712000000003\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_001_pie_712000000003\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_001_pie_712000000003\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_001_pie_712000000003\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 18:08
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_pie_213000000003",
  "source_prompt": "notebook, pencil, glasses, camera on a map",
  "edit_prompt": "Add a cup of coffee on the map",
  "target_prompt": "notebook, pencil, glasses, camera and coffee on a map",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_002_pie_213000000003"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 18:09
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_pie_213000000003",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_002_pie_213000000003\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_002_pie_213000000003\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_002_pie_213000000003\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_002_pie_213000000003\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_002_pie_213000000003\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_002_pie_213000000003\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_002_pie_213000000003\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_002_pie_213000000003\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 18:09
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_pie_121000000005",
  "source_prompt": "a [squirrel] is sitting on top of a wooden fence",
  "edit_prompt": "Change the animal from squirrel to rabbit",
  "target_prompt": "a rabbit is sitting on top of a wooden fence",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_003_pie_121000000005"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 18:10
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_pie_121000000005",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_003_pie_121000000005\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_003_pie_121000000005\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_003_pie_121000000005\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_003_pie_121000000005\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_003_pie_121000000005\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_003_pie_121000000005\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_003_pie_121000000005\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_003_pie_121000000005\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 18:10
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_pie_913000000002",
  "source_prompt": "christmas living room with fireplace, chair, wreath and tree",
  "edit_prompt": "Add a pixel art style to the Christmas living room",
  "target_prompt": "a pixel art of christmas living room with fireplace, chair, wreath and tree",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_004_pie_913000000002"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 18:11
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_pie_913000000002",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_004_pie_913000000002\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_004_pie_913000000002\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_004_pie_913000000002\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_004_pie_913000000002\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_004_pie_913000000002\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_004_pie_913000000002\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_004_pie_913000000002\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_004_pie_913000000002\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 18:11
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_pie_321000000007",
  "source_prompt": "[a husky dog running on] a path in the woods",
  "edit_prompt": "Remove the husky dog",
  "target_prompt": "a path in the woods",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_005_pie_321000000007"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 18:12
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_pie_321000000007",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_005_pie_321000000007\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_005_pie_321000000007\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_005_pie_321000000007\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_005_pie_321000000007\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_005_pie_321000000007\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_005_pie_321000000007\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_005_pie_321000000007\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_005_pie_321000000007\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 18:12
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_pie_314000000005",
  "source_prompt": "a painting of a house [by the water]",
  "edit_prompt": "Remove the water",
  "target_prompt": "a painting of a house",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_006_pie_314000000005"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 18:13
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_pie_314000000005",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_006_pie_314000000005\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_006_pie_314000000005\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_006_pie_314000000005\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_006_pie_314000000005\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_006_pie_314000000005\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_006_pie_314000000005\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_006_pie_314000000005\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_006_pie_314000000005\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 18:13
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_pie_911000000000",
  "source_prompt": "a cat and a bunny",
  "edit_prompt": "change the style of the image to photo",
  "target_prompt": "a photo of a cat and a bunny",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_007_pie_911000000000"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-29 18:13
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_pie_911000000000",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_007_pie_911000000000\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_007_pie_911000000000\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_007_pie_911000000000\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_007_pie_911000000000\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_007_pie_911000000000\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_007_pie_911000000000\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_007_pie_911000000000\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260329-1806\\samples\\sample_007_pie_911000000000\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-29 18:13
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 8,
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260329-1806\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260329-1806\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260329-1806\\metrics_summary.json",
  "five_method_case_metrics_csv": "runs\\dymask_v1\\v1_20260329-1806\\metrics_five_methods_case_level.csv",
  "five_method_summary_metrics_csv": "runs\\dymask_v1\\v1_20260329-1806\\metrics_five_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-30 17:00
阶段：样本复跑
操作：从已有 sample.json 载入单样本并保留当前提示词
输入：
```json
{
  "sample_json": "runs\\dymask_v1\\v1_20260330-1644\\samples\\sample_000_pie_424000000000\\sample.json"
}
```
结果：
```json
{
  "sample_id": "sample_000_pie_424000000000",
  "source_prompt": "the [dimly] illuminated earth",
  "target_prompt": "the sunlit illuminated earth",
  "run_dir": "runs\\dymask_v1\\v1_20260330-1700"
}
```
结论：将按 sample.json 当前内容复跑该样本，不再回源 parquet 覆盖提示词。
下一步：进入对应 phase 的单样本验证。

## 2026-03-30 17:00
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": null,
  "phase": "custom",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260330-1700",
  "manifest_json": "runs\\dymask_v1\\v1_20260330-1700\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260330-1700\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_pie_424000000000"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-30 17:00
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_pie_424000000000",
  "source_prompt": "the [dimly] illuminated earth",
  "edit_prompt": "Change dimly illuminated to sunlit illuminated",
  "target_prompt": "the sunlit illuminated earth",
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1700\\samples\\sample_000_pie_424000000000"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 17:00
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_pie_424000000000",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1700\\samples\\sample_000_pie_424000000000\\source_reconstruction.png",
  "methods": [
    "target_only"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1700\\samples\\sample_000_pie_424000000000\\target_only\\edited.png"
  ],
  "overview_path": null
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 17:00
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 1,
  "methods": [
    "target_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260330-1700\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260330-1700\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260330-1700\\metrics_summary.json",
  "overview_method_case_metrics_csv": "runs\\dymask_v1\\v1_20260330-1700\\metrics_overview_methods_case_level.csv",
  "overview_method_summary_metrics_csv": "runs\\dymask_v1\\v1_20260330-1700\\metrics_overview_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-30 17:21
阶段：数据准备
操作：加载 PIE-Bench 数据集
输入：
```json
{
  "piebench_path": "assets\\PIE-Bench"
}
```
结果：
```json
{
  "dataset": "PIE-Bench",
  "path": "assets\\PIE-Bench"
}
```
结论：已确认 PIE-Bench 数据集，将使用 GT mask 计算 masked 指标。
下一步：抽样并固化 sample manifest。

## 2026-03-30 17:21
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": [
    461,
    465,
    466,
    467,
    468,
    474,
    475,
    477
  ],
  "phase": "custom",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260330-1721",
  "manifest_json": "runs\\dymask_v1\\v1_20260330-1721\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260330-1721\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_pie_611000000001",
    "sample_001_pie_612000000000",
    "sample_002_pie_612000000001",
    "sample_003_pie_612000000002",
    "sample_004_pie_612000000003",
    "sample_005_pie_613000000004",
    "sample_006_pie_614000000000",
    "sample_007_pie_614000000002"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-30 17:21
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_pie_611000000001",
  "source_prompt": "otter in the water with [pink] hearts",
  "edit_prompt": "Change the raven from pink to green",
  "target_prompt": "otter in the water with green hearts",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1721\\samples\\sample_000_pie_611000000001"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 17:23
阶段：数据准备
操作：加载 PIE-Bench 数据集
输入：
```json
{
  "piebench_path": "assets\\PIE-Bench"
}
```
结果：
```json
{
  "dataset": "PIE-Bench",
  "path": "assets\\PIE-Bench"
}
```
结论：已确认 PIE-Bench 数据集，将使用 GT mask 计算 masked 指标。
下一步：抽样并固化 sample manifest。

## 2026-03-30 17:23
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 8,
  "sample_seed": 42,
  "row_indices": [
    461,
    465,
    466,
    467,
    468,
    474,
    475,
    477
  ],
  "phase": "custom",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260330-1723",
  "manifest_json": "runs\\dymask_v1\\v1_20260330-1723\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260330-1723\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_pie_611000000001",
    "sample_001_pie_612000000000",
    "sample_002_pie_612000000001",
    "sample_003_pie_612000000002",
    "sample_004_pie_612000000003",
    "sample_005_pie_613000000004",
    "sample_006_pie_614000000000",
    "sample_007_pie_614000000002"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-30 17:23
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_pie_611000000001",
  "source_prompt": "otter in the water with [pink] hearts",
  "edit_prompt": "Change the raven from pink to green",
  "target_prompt": "otter in the water with green hearts",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_000_pie_611000000001"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 17:23
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_pie_611000000001",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_000_pie_611000000001\\source_reconstruction.png",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_000_pie_611000000001\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_000_pie_611000000001\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_000_pie_611000000001\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_000_pie_611000000001\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_000_pie_611000000001\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_000_pie_611000000001\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 17:23
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_pie_612000000000",
  "source_prompt": "a [black and white] drawing of a woman with long hair",
  "edit_prompt": "make the drawing of the woman colorful",
  "target_prompt": "a colorful and detailed drawing of a woman with long hair",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_001_pie_612000000000"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 17:24
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_pie_612000000000",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_001_pie_612000000000\\source_reconstruction.png",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_001_pie_612000000000\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_001_pie_612000000000\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_001_pie_612000000000\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_001_pie_612000000000\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_001_pie_612000000000\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_001_pie_612000000000\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 17:24
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_pie_612000000001",
  "source_prompt": "a woman wearing a [red] hat and a red dress",
  "edit_prompt": "Change the woman's hat to green",
  "target_prompt": "a woman wearing a green hat and a red dress",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_002_pie_612000000001"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 17:25
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_pie_612000000001",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_002_pie_612000000001\\source_reconstruction.png",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_002_pie_612000000001\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_002_pie_612000000001\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_002_pie_612000000001\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_002_pie_612000000001\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_002_pie_612000000001\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_002_pie_612000000001\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 17:25
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_pie_612000000002",
  "source_prompt": "a woman in a hat and black dress is standing in front of an [orange] circle",
  "edit_prompt": "make the circle cyan",
  "target_prompt": "a woman in a hat and black dress is standing in front of an cyan circle",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_003_pie_612000000002"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 17:26
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_pie_612000000002",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_003_pie_612000000002\\source_reconstruction.png",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_003_pie_612000000002\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_003_pie_612000000002\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_003_pie_612000000002\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_003_pie_612000000002\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_003_pie_612000000002\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_003_pie_612000000002\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 17:26
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_004_pie_612000000003",
  "source_prompt": "a girl with a [pink] umbrella in the rain",
  "edit_prompt": "Change the color of the umbrella from pink to yellow",
  "target_prompt": "a girl with a yellow umbrella in the rain",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_004_pie_612000000003"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 17:26
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_004_pie_612000000003",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_004_pie_612000000003\\source_reconstruction.png",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_004_pie_612000000003\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_004_pie_612000000003\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_004_pie_612000000003\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_004_pie_612000000003\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_004_pie_612000000003\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_004_pie_612000000003\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 17:26
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_005_pie_613000000004",
  "source_prompt": "a painting of [purple] lilas in a vase",
  "edit_prompt": "Change the color of the lilas to orange",
  "target_prompt": "a painting of orange lilas in a vase",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_005_pie_613000000004"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 17:27
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_005_pie_613000000004",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_005_pie_613000000004\\source_reconstruction.png",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_005_pie_613000000004\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_005_pie_613000000004\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_005_pie_613000000004\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_005_pie_613000000004\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_005_pie_613000000004\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_005_pie_613000000004\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 17:27
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_006_pie_614000000000",
  "source_prompt": "a [white] seagull flying over the ocean waves",
  "edit_prompt": "Change the color of the seagull from white to red",
  "target_prompt": "a red seagull flying over the ocean waves",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_006_pie_614000000000"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 17:28
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_006_pie_614000000000",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_006_pie_614000000000\\source_reconstruction.png",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_006_pie_614000000000\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_006_pie_614000000000\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_006_pie_614000000000\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_006_pie_614000000000\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_006_pie_614000000000\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_006_pie_614000000000\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 17:28
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_007_pie_614000000002",
  "source_prompt": "a stack of [black] rocks and a ball in the water",
  "edit_prompt": "Change the color of the rocks to white",
  "target_prompt": "a stack of white rocks and a ball in the water",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_007_pie_614000000002"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 17:29
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_007_pie_614000000002",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_007_pie_614000000002\\source_reconstruction.png",
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_007_pie_614000000002\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_007_pie_614000000002\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_007_pie_614000000002\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_007_pie_614000000002\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_007_pie_614000000002\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1723\\samples\\sample_007_pie_614000000002\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 17:29
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 8,
  "methods": [
    "target_only",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260330-1723\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260330-1723\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260330-1723\\metrics_summary.json",
  "overview_method_case_metrics_csv": "runs\\dymask_v1\\v1_20260330-1723\\metrics_overview_methods_case_level.csv",
  "overview_method_summary_metrics_csv": "runs\\dymask_v1\\v1_20260330-1723\\metrics_overview_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-30 17:58
阶段：数据准备
操作：加载 PIE-Bench 数据集
输入：
```json
{
  "piebench_path": "assets\\PIE-Bench"
}
```
结果：
```json
{
  "dataset": "PIE-Bench",
  "path": "assets\\PIE-Bench"
}
```
结论：已确认 PIE-Bench 数据集，将使用 GT mask 计算 masked 指标。
下一步：抽样并固化 sample manifest。

## 2026-03-30 17:58
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 2,
  "sample_seed": 42,
  "row_indices": [
    461,
    465
  ],
  "phase": "custom",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260330-1758",
  "manifest_json": "runs\\dymask_v1\\v1_20260330-1758\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260330-1758\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_pie_611000000001",
    "sample_001_pie_612000000000"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-30 17:58
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_pie_611000000001",
  "source_prompt": "otter in the water with [pink] hearts",
  "edit_prompt": "Change the raven from pink to green",
  "target_prompt": "otter in the water with green hearts",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1758\\samples\\sample_000_pie_611000000001"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 17:59
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_pie_611000000001",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1758\\samples\\sample_000_pie_611000000001\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1758\\samples\\sample_000_pie_611000000001\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1758\\samples\\sample_000_pie_611000000001\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1758\\samples\\sample_000_pie_611000000001\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1758\\samples\\sample_000_pie_611000000001\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1758\\samples\\sample_000_pie_611000000001\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1758\\samples\\sample_000_pie_611000000001\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1758\\samples\\sample_000_pie_611000000001\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 17:59
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_pie_612000000000",
  "source_prompt": "a [black and white] drawing of a woman with long hair",
  "edit_prompt": "make the drawing of the woman colorful",
  "target_prompt": "a colorful and detailed drawing of a woman with long hair",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1758\\samples\\sample_001_pie_612000000000"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 18:00
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_pie_612000000000",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1758\\samples\\sample_001_pie_612000000000\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1758\\samples\\sample_001_pie_612000000000\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1758\\samples\\sample_001_pie_612000000000\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1758\\samples\\sample_001_pie_612000000000\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1758\\samples\\sample_001_pie_612000000000\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1758\\samples\\sample_001_pie_612000000000\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1758\\samples\\sample_001_pie_612000000000\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1758\\samples\\sample_001_pie_612000000000\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 18:00
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 2,
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260330-1758\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260330-1758\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260330-1758\\metrics_summary.json",
  "overview_method_case_metrics_csv": "runs\\dymask_v1\\v1_20260330-1758\\metrics_overview_methods_case_level.csv",
  "overview_method_summary_metrics_csv": "runs\\dymask_v1\\v1_20260330-1758\\metrics_overview_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-30 18:03
阶段：数据准备
操作：加载 PIE-Bench 数据集
输入：
```json
{
  "piebench_path": "assets\\PIE-Bench"
}
```
结果：
```json
{
  "dataset": "PIE-Bench",
  "path": "assets\\PIE-Bench"
}
```
结论：已确认 PIE-Bench 数据集，将使用 GT mask 计算 masked 指标。
下一步：抽样并固化 sample manifest。

## 2026-03-30 18:03
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 2,
  "sample_seed": 42,
  "row_indices": [
    461,
    465
  ],
  "phase": "custom",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260330-1803",
  "manifest_json": "runs\\dymask_v1\\v1_20260330-1803\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260330-1803\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_pie_611000000001",
    "sample_001_pie_612000000000"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-30 18:03
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_pie_611000000001",
  "source_prompt": "otter in the water with [pink] hearts",
  "edit_prompt": "Change the raven from pink to green",
  "target_prompt": "otter in the water with green hearts",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1803\\samples\\sample_000_pie_611000000001"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 18:04
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_pie_611000000001",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1803\\samples\\sample_000_pie_611000000001\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1803\\samples\\sample_000_pie_611000000001\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1803\\samples\\sample_000_pie_611000000001\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1803\\samples\\sample_000_pie_611000000001\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1803\\samples\\sample_000_pie_611000000001\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1803\\samples\\sample_000_pie_611000000001\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1803\\samples\\sample_000_pie_611000000001\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1803\\samples\\sample_000_pie_611000000001\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 18:04
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_pie_612000000000",
  "source_prompt": "a [black and white] drawing of a woman with long hair",
  "edit_prompt": "make the drawing of the woman colorful",
  "target_prompt": "a colorful and detailed drawing of a woman with long hair",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1803\\samples\\sample_001_pie_612000000000"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 18:05
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_pie_612000000000",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1803\\samples\\sample_001_pie_612000000000\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1803\\samples\\sample_001_pie_612000000000\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1803\\samples\\sample_001_pie_612000000000\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1803\\samples\\sample_001_pie_612000000000\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1803\\samples\\sample_001_pie_612000000000\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1803\\samples\\sample_001_pie_612000000000\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1803\\samples\\sample_001_pie_612000000000\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1803\\samples\\sample_001_pie_612000000000\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 18:05
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 2,
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260330-1803\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260330-1803\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260330-1803\\metrics_summary.json",
  "overview_method_case_metrics_csv": "runs\\dymask_v1\\v1_20260330-1803\\metrics_overview_methods_case_level.csv",
  "overview_method_summary_metrics_csv": "runs\\dymask_v1\\v1_20260330-1803\\metrics_overview_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-30 18:08
阶段：数据准备
操作：加载 PIE-Bench 数据集
输入：
```json
{
  "piebench_path": "assets\\PIE-Bench"
}
```
结果：
```json
{
  "dataset": "PIE-Bench",
  "path": "assets\\PIE-Bench"
}
```
结论：已确认 PIE-Bench 数据集，将使用 GT mask 计算 masked 指标。
下一步：抽样并固化 sample manifest。

## 2026-03-30 18:08
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 2,
  "sample_seed": 42,
  "row_indices": [
    143,
    154
  ],
  "phase": "custom",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260330-1808",
  "manifest_json": "runs\\dymask_v1\\v1_20260330-1808\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260330-1808\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_pie_111000000003",
    "sample_001_pie_112000000004"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-30 18:08
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_pie_111000000003",
  "source_prompt": "a cute little [bunny] with big eyes",
  "edit_prompt": "Change the bunny to a pig",
  "target_prompt": "a cute little pig with big eyes",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1808\\samples\\sample_000_pie_111000000003"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 18:09
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_pie_111000000003",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1808\\samples\\sample_000_pie_111000000003\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1808\\samples\\sample_000_pie_111000000003\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1808\\samples\\sample_000_pie_111000000003\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1808\\samples\\sample_000_pie_111000000003\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1808\\samples\\sample_000_pie_111000000003\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1808\\samples\\sample_000_pie_111000000003\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1808\\samples\\sample_000_pie_111000000003\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1808\\samples\\sample_000_pie_111000000003\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 18:09
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_pie_112000000004",
  "source_prompt": "a cartoon girl sitting on a [backpack]",
  "edit_prompt": "Add a rock for the cartoon girl",
  "target_prompt": "a cartoon girl sitting on a rock",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1808\\samples\\sample_001_pie_112000000004"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 18:10
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_pie_112000000004",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1808\\samples\\sample_001_pie_112000000004\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1808\\samples\\sample_001_pie_112000000004\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1808\\samples\\sample_001_pie_112000000004\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1808\\samples\\sample_001_pie_112000000004\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1808\\samples\\sample_001_pie_112000000004\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1808\\samples\\sample_001_pie_112000000004\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1808\\samples\\sample_001_pie_112000000004\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1808\\samples\\sample_001_pie_112000000004\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 18:10
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 2,
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260330-1808\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260330-1808\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260330-1808\\metrics_summary.json",
  "overview_method_case_metrics_csv": "runs\\dymask_v1\\v1_20260330-1808\\metrics_overview_methods_case_level.csv",
  "overview_method_summary_metrics_csv": "runs\\dymask_v1\\v1_20260330-1808\\metrics_overview_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-30 18:26
阶段：数据准备
操作：加载 PIE-Bench 数据集
输入：
```json
{
  "piebench_path": "assets\\PIE-Bench"
}
```
结果：
```json
{
  "dataset": "PIE-Bench",
  "path": "assets\\PIE-Bench"
}
```
结论：已确认 PIE-Bench 数据集，将使用 GT mask 计算 masked 指标。
下一步：抽样并固化 sample manifest。

## 2026-03-30 18:26
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 4,
  "sample_seed": 42,
  "row_indices": [
    223,
    234,
    251,
    255
  ],
  "phase": "custom",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260330-1826",
  "manifest_json": "runs\\dymask_v1\\v1_20260330-1826\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260330-1826\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_pie_211000000003",
    "sample_001_pie_212000000004",
    "sample_002_pie_214000000001",
    "sample_003_pie_214000000005"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-30 18:26
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_pie_211000000003",
  "source_prompt": "a small dog dressed in armor",
  "edit_prompt": "Add a hurbat to the small dog's armor",
  "target_prompt": "a small dog dressed in armor with a hurbat",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_000_pie_211000000003"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 18:27
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_pie_211000000003",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_000_pie_211000000003\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_000_pie_211000000003\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_000_pie_211000000003\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_000_pie_211000000003\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_000_pie_211000000003\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_000_pie_211000000003\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_000_pie_211000000003\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_000_pie_211000000003\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 18:27
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_pie_212000000004",
  "source_prompt": "a female character in a blue outfit",
  "edit_prompt": "Add a tiger to the female character's outfit",
  "target_prompt": "a female character in a blue outfit with a tiger",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_001_pie_212000000004"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 18:28
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_pie_212000000004",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_001_pie_212000000004\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_001_pie_212000000004\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_001_pie_212000000004\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_001_pie_212000000004\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_001_pie_212000000004\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_001_pie_212000000004\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_001_pie_212000000004\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_001_pie_212000000004\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 18:28
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_pie_214000000001",
  "source_prompt": "a round painting of a forest with flowers, trees",
  "edit_prompt": "Add deer in the forest",
  "target_prompt": "a round painting of a forest with deer, flowers, trees",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_002_pie_214000000001"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 18:29
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_pie_214000000001",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_002_pie_214000000001\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_002_pie_214000000001\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_002_pie_214000000001\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_002_pie_214000000001\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_002_pie_214000000001\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_002_pie_214000000001\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_002_pie_214000000001\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_002_pie_214000000001\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 18:29
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_pie_214000000005",
  "source_prompt": "the witcher 3, fantasy art",
  "edit_prompt": "Add a wizard to the witcher",
  "target_prompt": "the witcher 3 with a small wizard, fantasy art",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_003_pie_214000000005"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 18:30
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_pie_214000000005",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_003_pie_214000000005\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_003_pie_214000000005\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_003_pie_214000000005\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_003_pie_214000000005\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_003_pie_214000000005\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_003_pie_214000000005\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_003_pie_214000000005\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1826\\samples\\sample_003_pie_214000000005\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 18:30
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 4,
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260330-1826\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260330-1826\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260330-1826\\metrics_summary.json",
  "overview_method_case_metrics_csv": "runs\\dymask_v1\\v1_20260330-1826\\metrics_overview_methods_case_level.csv",
  "overview_method_summary_metrics_csv": "runs\\dymask_v1\\v1_20260330-1826\\metrics_overview_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-30 18:31
阶段：数据准备
操作：加载 PIE-Bench 数据集
输入：
```json
{
  "piebench_path": "assets\\PIE-Bench"
}
```
结果：
```json
{
  "dataset": "PIE-Bench",
  "path": "assets\\PIE-Bench"
}
```
结论：已确认 PIE-Bench 数据集，将使用 GT mask 计算 masked 指标。
下一步：抽样并固化 sample manifest。

## 2026-03-30 18:31
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 4,
  "sample_seed": 42,
  "row_indices": [
    303,
    314,
    331,
    335
  ],
  "phase": "custom",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1\\v1_20260330-1831",
  "manifest_json": "runs\\dymask_v1\\v1_20260330-1831\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1\\v1_20260330-1831\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_pie_311000000003",
    "sample_001_pie_312000000004",
    "sample_002_pie_314000000001",
    "sample_003_pie_314000000005"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-30 18:31
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_pie_311000000003",
  "source_prompt": "a brownish grey knitted bunny [with three painted eggs]",
  "edit_prompt": "Remove the three painted eggs",
  "target_prompt": "a brownish grey knitted bunny",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_000_pie_311000000003"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 18:32
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_pie_311000000003",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_000_pie_311000000003\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_000_pie_311000000003\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_000_pie_311000000003\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_000_pie_311000000003\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_000_pie_311000000003\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_000_pie_311000000003\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_000_pie_311000000003\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_000_pie_311000000003\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 18:32
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_pie_312000000004",
  "source_prompt": "a cartoon girl sitting [by a campfire]",
  "edit_prompt": "remove the campfire",
  "target_prompt": "a cartoon girl sitting",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_001_pie_312000000004"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 18:33
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_pie_312000000004",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_001_pie_312000000004\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_001_pie_312000000004\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_001_pie_312000000004\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_001_pie_312000000004\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_001_pie_312000000004\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_001_pie_312000000004\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_001_pie_312000000004\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_001_pie_312000000004\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 18:33
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_002_pie_314000000001",
  "source_prompt": "a girl standing on the withered grass [with a red tree]",
  "edit_prompt": "Remove the red tree",
  "target_prompt": "a girl standing on the withered grass",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_002_pie_314000000001"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 18:34
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_002_pie_314000000001",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_002_pie_314000000001\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_002_pie_314000000001\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_002_pie_314000000001\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_002_pie_314000000001\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_002_pie_314000000001\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_002_pie_314000000001\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_002_pie_314000000001\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_002_pie_314000000001\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 18:34
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_003_pie_314000000005",
  "source_prompt": "a painting of a house [by the water]",
  "edit_prompt": "Remove the water",
  "target_prompt": "a painting of a house",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_003_pie_314000000005"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 18:35
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_003_pie_314000000005",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_003_pie_314000000005\\source_reconstruction.png",
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_003_pie_314000000005\\target_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_003_pie_314000000005\\global_blend\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_003_pie_314000000005\\discrepancy_only\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_003_pie_314000000005\\discrepancy_attention\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_003_pie_314000000005\\discrepancy_latent\\edited.png",
    "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_003_pie_314000000005\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1\\v1_20260330-1831\\samples\\sample_003_pie_314000000005\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 18:35
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 4,
  "methods": [
    "target_only",
    "global_blend",
    "discrepancy_only",
    "discrepancy_attention",
    "discrepancy_latent",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1\\v1_20260330-1831\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1\\v1_20260330-1831\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1\\v1_20260330-1831\\metrics_summary.json",
  "overview_method_case_metrics_csv": "runs\\dymask_v1\\v1_20260330-1831\\metrics_overview_methods_case_level.csv",
  "overview_method_summary_metrics_csv": "runs\\dymask_v1\\v1_20260330-1831\\metrics_overview_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-30 19:07
阶段：数据准备
操作：加载 PIE-Bench 数据集
输入：
```json
{
  "piebench_path": "D:\\Program\\dymask\\assets\\PIE-Bench"
}
```
结果：
```json
{
  "dataset": "PIE-Bench",
  "path": "D:\\Program\\dymask\\assets\\PIE-Bench"
}
```
结论：已确认 PIE-Bench 数据集，将使用 GT mask 计算 masked 指标。
下一步：抽样并固化 sample manifest。

## 2026-03-30 19:07
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 2,
  "sample_seed": 0,
  "row_indices": null,
  "phase": "custom",
  "methods": [
    "target_only",
    "discrepancy_only",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1_batch_smoke\\v1_20260330-1907",
  "manifest_json": "runs\\dymask_v1_batch_smoke\\v1_20260330-1907\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1_batch_smoke\\v1_20260330-1907\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_pie_113000000000",
    "sample_001_pie_313000000000"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-30 19:08
阶段：数据准备
操作：加载 PIE-Bench 数据集
输入：
```json
{
  "piebench_path": "D:\\Program\\dymask\\assets\\PIE-Bench"
}
```
结果：
```json
{
  "dataset": "PIE-Bench",
  "path": "D:\\Program\\dymask\\assets\\PIE-Bench"
}
```
结论：已确认 PIE-Bench 数据集，将使用 GT mask 计算 masked 指标。
下一步：抽样并固化 sample manifest。

## 2026-03-30 19:08
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 2,
  "sample_seed": 0,
  "row_indices": null,
  "phase": "custom",
  "methods": [
    "target_only",
    "discrepancy_only",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1_batch_smoke\\v1_20260330-1908",
  "manifest_json": "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_pie_113000000000",
    "sample_001_pie_313000000000"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-30 19:08
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_pie_113000000000",
  "source_prompt": "a gold plated bowl filled with [fruit]",
  "edit_prompt": "change the fruit to candy",
  "target_prompt": "a gold plated bowl filled with candy",
  "methods": [
    "target_only",
    "discrepancy_only",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\samples\\sample_000_pie_113000000000"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 19:08
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_pie_113000000000",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\samples\\sample_000_pie_113000000000\\source_reconstruction.png",
  "methods": [
    "target_only",
    "discrepancy_only",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\samples\\sample_000_pie_113000000000\\target_only\\edited.png",
    "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\samples\\sample_000_pie_113000000000\\discrepancy_only\\edited.png",
    "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\samples\\sample_000_pie_113000000000\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\samples\\sample_000_pie_113000000000\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 19:08
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_pie_313000000000",
  "source_prompt": "a cartoon illustration of two plants [with faces]",
  "edit_prompt": "Remove the faces from the plants",
  "target_prompt": "a cartoon illustration of two plants",
  "methods": [
    "target_only",
    "discrepancy_only",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\samples\\sample_001_pie_313000000000"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 19:08
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_pie_313000000000",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\samples\\sample_001_pie_313000000000\\source_reconstruction.png",
  "methods": [
    "target_only",
    "discrepancy_only",
    "full_dynamic_mask"
  ],
  "artifacts": [
    "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\samples\\sample_001_pie_313000000000\\target_only\\edited.png",
    "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\samples\\sample_001_pie_313000000000\\discrepancy_only\\edited.png",
    "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\samples\\sample_001_pie_313000000000\\full_dynamic_mask\\edited.png"
  ],
  "overview_path": "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\samples\\sample_001_pie_313000000000\\overview.png"
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 19:08
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 2,
  "methods": [
    "target_only",
    "discrepancy_only",
    "full_dynamic_mask"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\metrics_summary.json",
  "overview_method_case_metrics_csv": "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\metrics_overview_methods_case_level.csv",
  "overview_method_summary_metrics_csv": "runs\\dymask_v1_batch_smoke\\v1_20260330-1908\\metrics_overview_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-30 19:21
阶段：数据准备
操作：加载 PIE-Bench 数据集
输入：
```json
{
  "piebench_path": "D:\\Program\\dymask\\assets\\PIE-Bench"
}
```
结果：
```json
{
  "dataset": "PIE-Bench",
  "path": "D:\\Program\\dymask\\assets\\PIE-Bench"
}
```
结论：已确认 PIE-Bench 数据集，将使用 GT mask 计算 masked 指标。
下一步：抽样并固化 sample manifest。

## 2026-03-30 19:21
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 2,
  "sample_seed": 0,
  "row_indices": null,
  "phase": "custom",
  "methods": [
    "target_only",
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1_batch_smoke_auto\\v1_20260330-1921",
  "manifest_json": "runs\\dymask_v1_batch_smoke_auto\\v1_20260330-1921\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1_batch_smoke_auto\\v1_20260330-1921\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_pie_113000000000",
    "sample_001_pie_313000000000"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-30 19:22
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_pie_113000000000",
  "source_prompt": "a gold plated bowl filled with [fruit]",
  "edit_prompt": "change the fruit to candy",
  "target_prompt": "a gold plated bowl filled with candy",
  "methods": [
    "target_only",
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1_batch_smoke_auto\\v1_20260330-1921\\samples\\sample_000_pie_113000000000"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 19:22
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_pie_113000000000",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1_batch_smoke_auto\\v1_20260330-1921\\samples\\sample_000_pie_113000000000\\source_reconstruction.png",
  "methods": [
    "target_only",
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1_batch_smoke_auto\\v1_20260330-1921\\samples\\sample_000_pie_113000000000\\target_only\\edited.png",
    "runs\\dymask_v1_batch_smoke_auto\\v1_20260330-1921\\samples\\sample_000_pie_113000000000\\discrepancy_only\\edited.png"
  ],
  "overview_path": null
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 19:22
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_pie_313000000000",
  "source_prompt": "a cartoon illustration of two plants [with faces]",
  "edit_prompt": "Remove the faces from the plants",
  "target_prompt": "a cartoon illustration of two plants",
  "methods": [
    "target_only",
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1_batch_smoke_auto\\v1_20260330-1921\\samples\\sample_001_pie_313000000000"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 19:22
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_pie_313000000000",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1_batch_smoke_auto\\v1_20260330-1921\\samples\\sample_001_pie_313000000000\\source_reconstruction.png",
  "methods": [
    "target_only",
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1_batch_smoke_auto\\v1_20260330-1921\\samples\\sample_001_pie_313000000000\\target_only\\edited.png",
    "runs\\dymask_v1_batch_smoke_auto\\v1_20260330-1921\\samples\\sample_001_pie_313000000000\\discrepancy_only\\edited.png"
  ],
  "overview_path": null
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 19:22
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 2,
  "methods": [
    "target_only",
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1_batch_smoke_auto\\v1_20260330-1921\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1_batch_smoke_auto\\v1_20260330-1921\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1_batch_smoke_auto\\v1_20260330-1921\\metrics_summary.json",
  "overview_method_case_metrics_csv": "runs\\dymask_v1_batch_smoke_auto\\v1_20260330-1921\\metrics_overview_methods_case_level.csv",
  "overview_method_summary_metrics_csv": "runs\\dymask_v1_batch_smoke_auto\\v1_20260330-1921\\metrics_overview_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。

## 2026-03-30 19:28
阶段：数据准备
操作：加载 PIE-Bench 数据集
输入：
```json
{
  "piebench_path": "D:\\Program\\dymask\\assets\\PIE-Bench"
}
```
结果：
```json
{
  "dataset": "PIE-Bench",
  "path": "D:\\Program\\dymask\\assets\\PIE-Bench"
}
```
结论：已确认 PIE-Bench 数据集，将使用 GT mask 计算 masked 指标。
下一步：抽样并固化 sample manifest。

## 2026-03-30 19:28
阶段：样本抽样
操作：生成样本清单并导出缓存图片
输入：
```json
{
  "sample_count": 2,
  "sample_seed": 0,
  "row_indices": null,
  "phase": "custom",
  "methods": [
    "target_only",
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "run_dir": "runs\\dymask_v1_batch_probe_smoke\\v1_20260330-1928",
  "manifest_json": "runs\\dymask_v1_batch_probe_smoke\\v1_20260330-1928\\sample_manifest.json",
  "manifest_csv": "runs\\dymask_v1_batch_probe_smoke\\v1_20260330-1928\\sample_manifest.csv",
  "sample_ids": [
    "sample_000_pie_113000000000",
    "sample_001_pie_313000000000"
  ]
}
```
结论：样本清单已冻结，后续所有阶段应复用同一批样本。
下一步：根据 phase 进入分阶段验证。

## 2026-03-30 19:29
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_000_pie_113000000000",
  "source_prompt": "a gold plated bowl filled with [fruit]",
  "edit_prompt": "change the fruit to candy",
  "target_prompt": "a gold plated bowl filled with candy",
  "methods": [
    "target_only",
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1_batch_probe_smoke\\v1_20260330-1928\\samples\\sample_000_pie_113000000000"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 19:29
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_000_pie_113000000000",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1_batch_probe_smoke\\v1_20260330-1928\\samples\\sample_000_pie_113000000000\\source_reconstruction.png",
  "methods": [
    "target_only",
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1_batch_probe_smoke\\v1_20260330-1928\\samples\\sample_000_pie_113000000000\\target_only\\edited.png",
    "runs\\dymask_v1_batch_probe_smoke\\v1_20260330-1928\\samples\\sample_000_pie_113000000000\\discrepancy_only\\edited.png"
  ],
  "overview_path": null
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 19:29
阶段：Custom 多方法运行
操作：开始执行单样本阶段验证
输入：
```json
{
  "sample_id": "sample_001_pie_313000000000",
  "source_prompt": "a cartoon illustration of two plants [with faces]",
  "edit_prompt": "Remove the faces from the plants",
  "target_prompt": "a cartoon illustration of two plants",
  "methods": [
    "target_only",
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "sample_dir": "runs\\dymask_v1_batch_probe_smoke\\v1_20260330-1928\\samples\\sample_001_pie_313000000000"
}
```
结论：进入反演与阶段方法运行。
下一步：保存 reconstruction、方法结果和指标。

## 2026-03-30 19:29
阶段：Custom 多方法运行
操作：单样本阶段验证完成
输入：
```json
{
  "sample_id": "sample_001_pie_313000000000",
  "phase": "custom"
}
```
结果：
```json
{
  "reconstruction_path": "runs\\dymask_v1_batch_probe_smoke\\v1_20260330-1928\\samples\\sample_001_pie_313000000000\\source_reconstruction.png",
  "methods": [
    "target_only",
    "discrepancy_only"
  ],
  "artifacts": [
    "runs\\dymask_v1_batch_probe_smoke\\v1_20260330-1928\\samples\\sample_001_pie_313000000000\\target_only\\edited.png",
    "runs\\dymask_v1_batch_probe_smoke\\v1_20260330-1928\\samples\\sample_001_pie_313000000000\\discrepancy_only\\edited.png"
  ],
  "overview_path": null
}
```
结论：该样本已保存固定产物和阶段产物，可进入下一样本或汇总。
下一步：继续剩余样本，或检查 summary 指标和中间图。

## 2026-03-30 19:29
阶段：实验汇总
操作：落盘阶段 case-level 与 summary 指标
输入：
```json
{
  "phase": "custom",
  "run_limit": 2,
  "methods": [
    "target_only",
    "discrepancy_only"
  ]
}
```
结果：
```json
{
  "case_metrics_csv": "runs\\dymask_v1_batch_probe_smoke\\v1_20260330-1928\\metrics_case_level.csv",
  "summary_metrics_csv": "runs\\dymask_v1_batch_probe_smoke\\v1_20260330-1928\\metrics_summary.csv",
  "summary_metrics_json": "runs\\dymask_v1_batch_probe_smoke\\v1_20260330-1928\\metrics_summary.json",
  "overview_method_case_metrics_csv": "runs\\dymask_v1_batch_probe_smoke\\v1_20260330-1928\\metrics_overview_methods_case_level.csv",
  "overview_method_summary_metrics_csv": "runs\\dymask_v1_batch_probe_smoke\\v1_20260330-1928\\metrics_overview_methods_summary.csv"
}
```
结论：当前阶段的可视化、指标、日志和样本留存已齐备。
下一步：按顺序进入下一阶段，而不是一次性堆叠所有模块。
