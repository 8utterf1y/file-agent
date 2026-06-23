# 自然语言调用示例

## 目录

- 例子 0：三层模式选择
- 例子 1：全项目扫描
- 例子 2：指定目录扫描
- 例子 2.1：自然语言范围映射
- 例子 3：只看目录重复程度
- 例子 4：零结果但覆盖不足
- 例子 4.1：解释已有报告不重跑脚本
- 例子 5：后续批准重构
- 例子 6：只分析已有重复簇

## 例子 0：三层模式选择

用户：

```text
先快速看一下有没有完全重复文件，不要做近重复分析。
```

应该运行：

```bash
python skills/code-dedup-new/scripts/code_dedup.py --root . --mode exact --output .opencode/reports
```

回答要点：

```text
当前为 exact 快速模式，只检测完全重复和规范化完全重复，未检测近重复。
```

用户：

```text
帮我扫描当前项目的重复代码。
```

应该运行：

```bash
python skills/code-dedup-new/scripts/code_dedup.py --root . --mode standard --output .opencode/reports
```

回答要点：

```text
当前使用 standard 模式，包含完全重复和常规近重复证据生成。
```

用户：

```text
做一次深度分析，可以跑久一点，尽量不要漏掉近重复。
```

应该运行：

```bash
python skills/code-dedup-new/scripts/code_dedup.py --root . --mode deep --output .opencode/reports
```

回答要点：

```text
当前使用 deep 模式，成本较高，会生成更多近重复候选。如果达到比较上限，结论仍可能不完整。
```

## 例子 1：全项目扫描

用户：

```text
帮我扫描当前项目的重复代码，忽略图片和二进制资产，给出后续分析建议，不要修改文件。
```

应该流程：

1. 运行 `scripts/code_dedup.py --mode standard` 生成 JSON/Markdown 证据报告。
2. 读取 `quality_warnings`、`coverage`、`directory_summary`、`clusters`。
3. 对高/中优先级重复簇继续读取源码，检查导入、引用和调用方。
4. 最终中文回答，不直接照抄脚本报告，也不把脚本证据当成最终合并结论。

应该回答：

```text
结论：本次扫描发现 4 个重复簇，其中 1 个 high、2 个 medium。当前未修改任何文件。

重复证据汇总：
| 簇ID | 类型 | 优先级 | 证据强度 | 相似度 | 需要 AI 复核 |
|---|---|---|---|---:|---|
| cluster_001 | symbol_exact | high | strong | 1.0 | 是 |

cluster_001 证据：
| 文件 | 符号/代码块 | 行号 | 角色 | 预览 |
|---|---|---:|---|---|
| src/common/a.py | normalize_record | 1-32 | production | ... |
| src/common/b.py | normalize_record | 1-32 | production | ... |

复核提示：脚本只证明文本或结构重复，尚未检查调用方、业务语义、测试覆盖和公共 API 影响。
下一步：我会读取这两个函数源码并搜索引用后，再判断是否适合合并或应保留。
```

## 例子 2：指定目录扫描

用户：

```text
只检查 src 和 packages，跳过 tests，只给高/中优先级的重复证据。
```

应该流程：

1. 运行脚本时传入 `--include src packages --exclude tests`。
2. 只展开高/中优先级重复项。
3. 对近重复默认标记为需要 AI 复核。

应该回答：

```text
已按要求只检查 src 和 packages，并跳过 tests。当前未修改任何文件。

| 簇ID | 类型 | 优先级 | 证据强度 | 相似度 | 需要 AI 复核 |
|---|---|---|---|---:|---|
| cluster_002 | symbol_near | medium | moderate | 0.91 | 是 |

脚本证据：两个函数的文本结构相似，达到 near duplicate 阈值。
脚本未检查：调用方、业务语义、测试覆盖、公共 API 影响。
下一步：需要读取源码并搜索引用后，才能判断合并、保留或暂不处理。
```

## 例子 2.1：自然语言范围映射

用户：

```text
检查 dedup-agent/app 目录下的重复项。
```

应该运行：

```bash
python skills/code-dedup-new/scripts/code_dedup.py --root . --mode standard --include dedup-agent/app --output .opencode/reports
```

用户：

```text
检查 dedup-agent/app 和 dedup-service/app 两个目录下的重复项。
```

应该运行：

```bash
python skills/code-dedup-new/scripts/code_dedup.py --root . --mode standard --include dedup-agent/app dedup-service/app --output .opencode/reports
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
目录级证据：

| 目录 | 重复簇 | 受影响文件 | 重复行数 |
|---|---:|---:|---:|
| src/common | 3 | 5 | 180 |
| src/user ↔ src/admin | 2 | 4 | 96 |

src/user ↔ src/admin 有跨目录重复证据。脚本尚未判断业务边界、权限差异和调用方影响。
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

## 例子 4.1：解释已有报告不重跑脚本

用户：

```text
帮我解释一下这份 code-dedup-report.json 里为什么没有发现重复。
```

应该流程：

1. 读取已有 `code-dedup-report.json`。
2. 检查 `run`、`quality_warnings`、`coverage`、`summary`。
3. 解释扫描范围、运行模式、覆盖面和预警。
4. 不重新运行脚本，除非用户明确要求重新扫描。

应该回答要点：

```text
我先基于已有报告解释，不重新扫描。当前结论只适用于 run.root 和 run.include 指定的范围。
```

## 例子 5：后续批准重构

用户：

```text
我批准 cluster_001，帮我进入重构计划。
```

应该流程：

1. 不直接用旧报告改代码。
2. 重新读取 cluster_001 涉及源文件。
3. 搜索导入、引用和调用方。
4. 中/高风险先给最小补丁计划并等待确认。
5. 用户确认后再进入单独补丁/重构工作流。

## 例子 6：只分析已有重复簇

用户：

```text
cluster_003 能不能合并？
```

应该流程：

1. 读取已有 `code-dedup-report.json`。
2. 定位 `cluster_003`。
3. 读取该重复簇涉及源码。
4. 搜索导入、引用和调用方。
5. 基于源码和调用关系给出中文分析。
6. 不重新跑全量扫描，除非用户要求重新扫描。

应该回答要点：

```text
我会只复核 cluster_003 涉及的文件和引用，不重新跑全量扫描。当前仍不会修改文件。
```
