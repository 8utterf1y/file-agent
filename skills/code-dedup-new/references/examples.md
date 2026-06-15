# Natural Language Examples

## 例子 1：全项目扫描

用户：

```text
帮我扫描当前项目的重复代码，忽略图片和二进制资产，给出合并建议，不要修改文件。
```

应该流程：

1. 运行 `scripts/code_dedup.py` 生成 JSON/Markdown。
2. 读取 `quality_warnings`、`coverage`、`directory_summary`、`clusters`。
3. 对 high/medium cluster 继续读取源码，检查 import/reference/caller。
4. 最终中文回答，不直接照抄脚本报告。

应该回答：

```text
结论：本次扫描发现 4 个重复簇，其中 1 个 high、2 个 medium。当前未修改任何文件。

重复项汇总：
| 簇ID | 类型 | 优先级 | 风险 | 证据强度 | 建议动作 |
|---|---|---|---|---|---|
| cluster_001 | symbol_exact | high | medium | strong | extract_shared_function |

cluster_001 证据：
| 文件 | 符号/代码块 | 行号 | 角色 | 预览 |
|---|---|---:|---|---|
| src/common/a.py | normalize_record | 1-32 | production | ... |
| src/common/b.py | normalize_record | 1-32 | production | ... |

AI 复核：两处输入输出基本一致，但还需确认调用方和异常处理。
建议：dry-run 建议抽到 src/shared/normalize_record.py；requires_manual_review=true。
```

## 例子 2：指定目录扫描

用户：

```text
只检查 src 和 packages，跳过 tests，只给 high/medium 的重复和合并建议。
```

应该流程：

1. 运行脚本时传入 `--include src packages --exclude tests`。
2. 只展开 high/medium。
3. 对 near duplicate 默认标记人工复核。

应该回答：

```text
已按要求只检查 src 和 packages，并跳过 tests。当前未修改任何文件。

| 簇ID | 类型 | 优先级 | 风险 | 证据强度 | 建议动作 |
|---|---|---|---|---|---|
| cluster_002 | symbol_near | medium | medium | moderate | manual_review_required |

相似点：两个函数都执行格式化和默认值处理。
差异点：billing 版本多了金额舍入规则，shared 版本没有。
调用关系检查：脚本未完成；需要 Agent 搜索 import/reference/caller。
建议：不要直接合并整个函数，只能人工确认后抽取最小公共 helper。
```

## 例子 2.1：自然语言范围映射

用户：

```text
检查 dedup-agent/app 目录下的重复项。
```

应该运行：

```bash
python skills/code-dedup/scripts/code_dedup.py --root . --include dedup-agent/app --output .opencode/reports
```

用户：

```text
检查 dedup-agent/app 和 dedup-service/app 两个目录下的重复项。
```

应该运行：

```bash
python skills/code-dedup/scripts/code_dedup.py --root . --include dedup-agent/app dedup-service/app --output .opencode/reports
```

用户：

```text
检查此目录下的重复项。
```

应该流程：

1. 如果当前工作目录就是目标目录，运行 `--root .`。
2. 如果“此目录”指当前打开文件所在目录，先推断或确认该目录，再运行 `--root <该目录>`。
3. 回答里说明实际扫描的 `run.root` 和 `run.include`，避免范围误解。

## 例子 3：只看目录重复程度

用户：

```text
哪些子文件夹之间重复最明显？不要展开每个低优先级文件。
```

应该回答：

```text
目录级结论：

| 目录 | 重复簇 | 受影响文件 | 重复行数 | 风险 |
|---|---:|---:|---:|---|
| src/common | 3 | 5 | 180 | medium |
| src/user ↔ src/admin | 2 | 4 | 96 | high |

src/user ↔ src/admin 属于跨模块近重复，需要先确认业务边界、权限差异和调用方，再考虑抽公共逻辑。
当前未修改任何文件。
```

## 例子 4：零结果但覆盖不足

用户：

```text
为什么只说没有重复，感觉没有检查子文件夹？
```

应该回答：

```text
你这个判断是对的，不能只用“0 个重复簇”当最终结论。

质量预警：
| 预警码 | 说明 | 建议 |
|---|---|---|
| LOW_SUPPORTED_FILE_COUNT | 本次只扫描到 3 个受支持文件 | 先检查 coverage，再考虑调整 include 或扩展名 |

本次脚本递归看到了 6 个子目录，但只有 2 个目录包含当前支持的代码文件。其他目录主要是图片或生成资产，因此被默认跳过。

结论应写成：本次扫描范围内未发现重复代码；但覆盖不足，不能代表整个目录没有重复。
```

## 例子 5：后续批准重构

用户：

```text
我批准 cluster_001，帮我进入重构计划。
```

应该流程：

1. 不直接用旧报告改代码。
2. 重新读取 cluster_001 涉及源文件。
3. 搜索 import/reference/caller。
4. medium/high 风险先给最小 patch 计划并等待确认。
5. 用户确认后再进入单独 patch/refactor 工作流。
