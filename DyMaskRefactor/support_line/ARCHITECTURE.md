# support_line Architecture

这个目录只负责 `source_anchored_support` 这条主线的实验组织层。目标不是重写全部编辑逻辑，而是把最常改的那一层拆干净。

## 模块职责

- `parser.py`
  负责命令行参数定义，只做参数声明。
- `configuration.py`
  负责把 argparse 参数转成 `ExperimentConfig` 和 `DiffEditConfig`。
- `execution.py`
  负责 prepare / execute 两阶段编排：建 run 目录、写 config、装配 pipeline、调用 editor、汇总指标。
- `base.py`
  放 baseline editor 壳，保留所有 support 变体共享的初始化约束。
- `masking.py` / `roi.py`
  放 support 系列真正共用的机制钩子。
- `variants_progressive.py`
  放 C1-C4 这种“沿着 support / anchor schedule 逐步加机制”的版本。
- `variants_confidence.py`
  放 C5-C6d 这种“围绕 confidence / local anchor / recovery 做深化”的版本。
- `mainline_hardcore.py`
  放 C5H0-C5H1：hard-core support、confidence anchor、thin soft boundary。
- `mainline_roi.py`
  放 C5H2：deterministic DiffEdit ROI cache 与 core/boundary 分解。
- `mainline_underedit.py`
  放 C5H3-C5H4：under-edit rescue 与 temporal guard。
- `variants_mainline.py`
  只做最新主线兼容层 re-export，保留 registry / notebook 旧导入路径。
- `specs.py`
  定义 `SupportVariantSpec`，并把 editor 类解析做成惰性加载。
- `registry.py`
  维护 variant key 到 spec 的映射。这里只存 `editor_ref` 字符串，不在 import 时加载 editor 实现。
- `__init__.py`
  只做惰性 re-export，避免简单导入时拉起整套 DyMask 运行依赖。

## 运行流

```text
CLI
  -> parser.build_parser()
  -> configuration.build_config() / build_diffedit_config()
  -> execution.prepare_support_run()
      -> registry.get_support_variant()
      -> datasets.load_materialized_samples()
      -> write config / manifest / variant payload
  -> execution.execute_support_run()
      -> runtime.build_pipeline()
      -> inversion.build_inversion_backend()
      -> spec.editor_cls(...)
      -> editor.run_samples(...)
      -> reporting.collect_case_rows()
      -> reporting.write_run_reports()
```

## 为什么要做惰性解析

以前 `support_line/__init__.py` 和 `registry.py` 会在 import 时直接把 editor 类和下游依赖全部拉进来。这样即便只是想：

- 看 parser 参数
- 列一下有哪些 variant
- 在 notebook 里 inspect 一下 registry

也会立刻碰到完整运行时依赖。现在改成惰性后，只有真正执行到 `spec.editor_cls` 时，才会去加载对应 editor 实现。

## 新增一个变体怎么做

1. 先决定它属于哪一类。
   - 如果是在 C1-C4 这种 schedule / support memory / anchor gate 上递进，就放到 `variants_progressive.py`。
   - 如果是在 C5-C6d 这种 confidence / local anchor / recovery 上深化，就放到 `variants_confidence.py`。
   - 如果是在当前最新主线 C5H0-C5H4 上继续深化，就按机制放到 `mainline_hardcore.py`、`mainline_roi.py` 或 `mainline_underedit.py`；`variants_mainline.py` 只保留兼容导出。
2. 在对应文件里新增 editor 类。
   - 尽量继承最接近的上一个版本，而不是直接从 baseline 复制一大段。
   - 新逻辑优先落到可覆写钩子，不要把整段 step loop 再抄一遍。
3. 在 `registry.py` 里新增一个 `SupportVariantSpec`。
   - `editor_ref` 写成 `模块路径:类名`。
   - `extra_arg_names` 只列这个变体新增的参数。
4. 如果引入了新参数，再更新 `parser.py`。
   - 同时确认 `configuration.py` 是否需要把它们写入 config。
5. 更新 `README.md`。
   - 让当前主线和保留分支列表保持一致。

## 当前边界

这套 refactor 目前仍然复用旧 `DyMask/` 的底层能力，包括：

- inversion backend
- DiffEdit ROI 生成
- attention store
- case-level 指标实现
- batch fallback / OOM 处理

所以这里的重点是“把实验主线组织清楚”，不是马上把整个底座重写一遍。


## Standalone Runtime

当前 `support_line/` 依赖的底层运行时已经内置到 `DyMaskRefactor` 根目录，不再要求旁边存在旧 `DyMask/` 包。权重路径与 NTIP2P 路径通过 `RuntimeConfig` 和 CLI/JSON 配置指定。
