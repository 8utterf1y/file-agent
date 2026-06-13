# Natural Language Examples

## 例子 1：全项目扫描

用户：

```text
帮我扫描当前项目的重复代码，忽略图片和二进制资产，给出合并建议，不要修改文件。
```

应该流程：

1. 先运行 `scripts/code_dedup.py` 生成报告。
2. 再读取 high/medium cluster 对应源码片段。
3. 最终回答综合脚本证据和 AI 复核，不要直接照抄报告。

应该回答：

```text
结论：发现 4 个值得关注的重复点，其中 1 个 high、2 个 medium。
我没有修改任何文件。

目录级重复：
- src/common：内部重复较多，主要是工具函数重复。
- src/user ↔ src/admin：存在跨目录近重复，需要人工确认领域差异。

重点建议：
1. cluster_001，type=symbol_exact，risk=low
   - src/common/a.py:1-32，symbol=normalize_record
   - src/common/b.py:1-32，symbol=normalize_record
   脚本证据：两个符号 normalized hash 相同。
   AI 复核：两个函数输入输出和副作用一致，适合抽公共实现。
   合并目标：src/shared/normalize_record.py
   步骤：抽公共函数；原模块保留入口；补测试。
   阻断点：确认调用方和副作用。
```

## 例子 2：指定目录扫描

用户：

```text
只检查 src 和 packages，跳过 tests，只给 high/medium 的重复和合并建议。
```

应该流程：

1. 运行脚本时传入 include/exclude。
2. 读取脚本报告中的 medium/high cluster。
3. 对每个候选读取源码，判断是否能合并。

应该回答：

```text
已按要求只检查 src 和 packages，跳过 tests。
发现 2 个 medium 重复点，没有 high。

1. cluster_002，type=symbol_near，risk=medium
   - src/billing/format.ts:10-48
   - packages/shared/format.ts:8-45
   脚本证据：两个函数结构近似，similarity=0.88。
   AI 复核：billing 版本多了金额舍入规则，shared 版本没有，不能整体合并。
   建议：先人工确认格式化规则是否一致，只抽取最小公共 helper。
   不建议直接合并整个函数。
```

## 例子 3：只看合并建议

用户：

```text
只告诉我最值得合并的 5 个重复点，不要展开低优先级问题。
```

应该流程：

1. 先根据脚本报告按 priority_score 排序。
2. 读取前 5 个候选的源码上下文。
3. 只输出 AI 复核后仍值得合并的点；如果脚本候选不可靠，要降级或排除。

应该回答：

```text
最值得合并的 5 个点如下，均为 dry-run 建议：

1. cluster_004，type=symbol_exact，score=91
   目标：src/shared/date_utils
   步骤：抽公共日期解析函数；原模块保留业务入口；补充两侧测试。
   风险：low，但仍需人工确认调用方。
```

## 例子 4：只看目录重复程度

用户：

```text
哪些子文件夹之间重复最明显？不要展开每个低优先级文件。
```

应该回答：

```text
目录级结论：
- src/common 内部重复最多，主要是工具函数。
- src/user ↔ src/admin 存在跨目录近重复，建议人工确认领域边界后再抽公共逻辑。
- tests 内部重复较多但优先级低，暂不建议优先处理。

我没有修改任何文件。
```

## 例子 5：结果为 0 但用户怀疑没扫到子文件夹

用户：

```text
为什么只说没有重复，感觉没有检查子文件夹？
```

应该流程：

1. 先读取报告里的 `coverage`、`directory_summary` 和 `ignored`。
2. 优先检查 `quality_warnings`，尤其是 `LOW_SUPPORTED_FILE_COUNT`、`NO_SUPPORTED_FILES`、`NO_DUPLICATES_WITH_MANY_UNSUPPORTED_FILES`。
3. 如果覆盖信息不足，用 `rg --files <用户关注目录>` 复核目录下实际文件。
4. 说明“递归看到了哪些目录”和“哪些目录没有可分析代码文件”，必要时调整参数重跑。

应该回答：

```text
你这个判断是对的，不能只用“0 个重复簇”当结论。

质量提醒：
- LOW_SUPPORTED_FILE_COUNT：本次只扫描到 3 个受支持代码/配置文件。

本次脚本递归看到了 6 个子目录，但只有 2 个目录包含当前支持的代码文件：
- .：README.md、requirements.txt
- tools：synthesize_by_gt.py

其他目录主要是 .png/.jpg 输出资产，所以被默认跳过；这代表“图片资产未分析”，不代表“文件夹内容不存在”。

如果你要分析某个源码子目录，我会用 --include 指向它重跑；如果那些文件是自定义后缀，也需要把后缀加入支持列表。
```

## 例子 6：报告 schema 被 Agent 消费

用户：

```text
给我一份机器可读的重复代码扫描结果，并说明哪些结论需要谨慎。
```

应该流程：

1. 运行脚本生成 JSON。
2. 读取顶层 `schema_version`、`tool`、`run`、`summary`、`quality_warnings`、`clusters`。
3. 只把 JSON 当证据，最终仍需用源码上下文复核重要 cluster。

应该回答：

```text
报告格式：schema_version=1.1，tool=code-dedup 0.2.0，mode=read_only_analysis。

本次扫描参数：
- root=.
- include=all
- threshold=0.86
- min_lines=12

质量提醒：
- MAX_COMPARISONS_REACHED：近重复比较达到上限，因此 medium/low 候选可能不完整。

结论：high 级别发现仍可优先复核；目录级统计可参考，但不应把 low 级候选视为完整列表。
```
