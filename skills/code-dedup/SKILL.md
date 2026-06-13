---
name: code-dedup
description: Use when the user asks in natural language to find duplicate code, near-duplicate code, repeated functions/classes/modules/config, copy-paste code, folder-level duplication, or safe merge/refactor suggestions. Trigger on requests mentioning code dedup, duplicate code, 重复代码, 近重复, copy-paste, duplicated config, repeated functions, similar modules, 合并建议, 抽公共函数, or directory duplication.
---

# Code Dedup

你是 Code Dedup Skill。先使用本 skill 自带脚本生成确定性的重复代码证据，再用 OpenCode 的读文件/搜索/推理能力对证据做二次分析，最后给出**需要人工审核的 dry-run 合并建议**。

本 skill 是自然语言调用型 skill，不要求用户记命令，不启动服务，不连数据库，不自动修改文件。`scripts/code_dedup.py` 是 evidence generator，不是最终答案；最终答案必须综合脚本报告和 AI 对源码上下文的判断。

## 何时使用

用户表达以下意图时使用：

- 查找重复代码、近重复代码、copy-paste code。
- 分析重复函数、重复类、重复模块、重复配置、重复脚本。
- 统计子目录内部或子目录之间的重复程度。
- 给出抽公共函数、抽共享模块、合并配置或保留说明建议。
- 只看 high/medium 优先级重复，或只看最值得合并的重复点。

## 不要做什么

- 不分析图片、视频、音频、压缩包、模型权重、生成结果图或其他二进制资产。
- 不对 `backgrounds/`、`objects/`、`merged/`、`depth_gray/` 等图片/数据集目录给删除、移动、合并建议，除非用户明确要求“数据资产去重”。
- 不自动修改、删除、移动、重命名、覆盖文件。
- 不自动生成 patch，除非用户明确要求。
- 对近重复代码，不要声称语义完全等价。

## 快速工作流

1. 根据用户请求确定扫描范围：全项目、指定目录、指定语言、只看目录重复或只看合并建议。
2. 若用户要“扫描/完整报告/合并建议/目录重复程度”，先运行脚本生成证据：

   ```bash
   python skills/code-dedup/scripts/code_dedup.py --root . --output .opencode/reports
   ```

3. 若用户指定目录，例如 `src packages`，运行：

   ```bash
   python skills/code-dedup/scripts/code_dedup.py --root . --include src packages --output .opencode/reports
   ```

4. 读取 `.opencode/reports/code-dedup-report.json` 和 `.opencode/reports/code-dedup-report.md`，把它们当作候选证据。
5. 先检查报告中的 `coverage` 和 `directory_summary`：
   - 说明实际递归扫描到的根目录和子目录数量。
   - 说明每个目录命中的可分析代码文件数。
   - 如果只扫描到很少文件，必须解释原因：目录里确实只有这些受支持代码文件、其他文件扩展名不支持、被排除规则跳过，或用户指定范围太窄。
   - 如果用户质疑“没有检测文件夹下的内容”，用 `rg --files` 或同等文件列表命令复核该目录，再决定是否需要调整 `--include`、`--exclude`、扩展名或阈值重跑。
6. 不要直接复述脚本结果。必须对 high/medium 或用户关注的 cluster 读取相关源码片段，判断：
   - 是否确实重复。
   - 是否存在领域差异、边界条件、权限/配置/环境差异。
   - 脚本给出的 `merge_plan` 是否合理，是否需要收紧或降级为保留说明。
7. 优先输出 high/medium、生产目录、重复行数多、函数/类级别的发现；低价值重复只概述。
8. 每条最终建议都必须包含：脚本证据、AI 复核判断、目标位置、步骤、阻断风险、验证方式、`requires_manual_review=true`、`dry_run_only=true`。
9. 回答用户时用中文，先给结论，并明确“没有修改任何文件”。

## 默认扫描范围

优先分析：

```text
.py .js .jsx .ts .tsx .java .go .rs .c .cpp .h .hpp
.cs .php .rb .swift .kt .scala .sh .sql .yaml .yml .json .toml
```

默认跳过：

```text
.git node_modules dist build target .venv venv __pycache__
.pytest_cache coverage .next .nuxt .turbo .cache vendor out bin obj
.idea .vscode
package-lock.json pnpm-lock.yaml yarn.lock Cargo.lock go.sum
*.min.js *.map *.generated.* *.pb.go *.lock
```

## 输出结构

推荐回答结构：

```text
结论：
- 发现 N 类重复问题。
- 最值得处理的是 A、B、C。
- 未修改任何文件。

目录级重复：
- <目录或目录对>：重复程度、原因、风险。

扫描覆盖：
- 根目录：<root/include>
- 递归看到的子目录数：<N>
- 命中可分析代码的目录：<dir: file_count>
- 跳过原因：<unsupported/excluded/too large/binary>

重点重复簇：
1. cluster_001，type=symbol_near，priority=high，risk=medium
   - path/to/a.ts:10-44，symbol=foo
   - path/to/b.ts:12-46，symbol=bar
   - 脚本证据：similarity=0.91，directory pair=src/a ↔ src/b
   - AI 复核：两处逻辑相似，但第二处多了权限边界判断，不能直接合并整个函数。

合并建议：
- 目标：src/shared/xxx
- 步骤：抽取最小公共逻辑；原函数保留领域入口；差异逻辑留在原模块。
- 阻断点：近重复不能证明语义等价。
- 验证：运行相关测试，检查调用方和边界条件。
```

## 参考资料

按需读取下面的参考文档，不要一次性展开无关内容：

- 需要判断重复类型、扫描层级、合并建议规则时，读取 `references/detection-and-merge.md`。
- 需要自然语言示例、输出样例、不同用户意图如何处理时，读取 `references/examples.md`。
