# Detection And Merge Rules

## 检测层级

按这些层级组织发现：

1. `file_exact`：文件内容完全相同。
2. `file_normalized_exact`：格式、空白、换行规范化后相同。
3. `symbol_exact`：函数、类、方法、结构体等符号级重复。
4. `symbol_near`：函数、类、方法等近重复。
5. `window_near`：文件片段或连续逻辑块近重复。
6. `config_duplicate`：配置或脚本块重复。

不要只停留在文件层面。必须尽量检查：

- 子目录内部重复。
- 子目录之间重复。
- 函数、类、方法重复。
- 配置片段重复。
- 近重复逻辑块。

## 零结果或少结果处理

当报告显示 `duplicate_clusters=0` 或只扫描到很少文件时，不要直接说“整个文件夹没有问题”。必须先区分：

- `coverage.directories_seen`：脚本是否递归看到了子目录。
- `coverage.supported_files_by_directory`：哪些子目录里有可分析代码文件。
- `coverage.unsupported_files_by_extension`：是否大量文件因为扩展名不在支持列表而被跳过。
- `ignored`：是否因为排除规则、文件过大、二进制或缺失路径被跳过。

如果用户要求检查某个文件夹，而 `supported_files_by_directory` 没有该文件夹，先用 `rg --files <folder>` 复核实际文件列表，再判断是否需要：

- 扩展支持的代码后缀。
- 调整 `--include` 指向真正的源码目录。
- 放宽 `--min-lines` 或 `--threshold`。
- 说明该文件夹主要是图片、模型、数据、锁文件或生成产物，当前 skill 默认不分析。

## 合并建议规则

脚本报告只提供候选证据。最终合并建议必须经过 AI 复核：

- 读取候选 cluster 的源码上下文。
- 检查脚本相似度是否被样板代码、命名、配置格式或测试重复误导。
- 检查差异是否来自业务域、权限、环境、异常处理、输入校验或边界条件。
- 如有不确定性，把建议降级为 `manual_review_required` 或 `keep_separate_with_note`。

- `file_exact`：可以建议选择 canonical 文件，但必须人工确认引用关系、发布路径和所有权，不自动删除。
- `file_normalized_exact`：建议人工审核格式、注释、生成方式差异，不直接合并。
- `symbol_exact`：优先建议抽公共函数、公共类或共享模块。
- `symbol_near`：只建议人工审核后抽取确认等价的最小公共逻辑。
- `window_near`：建议抽 helper，或保留并添加说明。
- `config_duplicate`：建议抽公共配置模板，环境差异保留为 override。

每条合并建议必须包含：

- `candidate_target`：建议合并目标位置。
- `steps`：合并步骤。
- `blockers`：不能直接合并的风险。
- `validation`：验证方式。
- `requires_manual_review=true`。
- `dry_run_only=true`。

## 风险判断

提高风险：

- 跨业务目录或跨模块重复。
- 公共 API、权限、安全、生产路径相关代码。
- 近重复而非精确重复。
- 配置文件、部署脚本、环境差异。

降低优先级：

- tests、fixtures、examples 中的重复。
- 很短的重复片段。
- 仅命名或样板代码相似。

## 性能策略

保持轻量，不做全量无脑比较：

- 先按目录和扩展名分组。
- 优先看同语言、同类型、同目录或相邻模块。
- 大仓库先抽 high/medium 候选，不展开所有低价值重复。
- 对超大文件先只看函数/类入口和明显重复片段。
- 用户只指定目录时，不扫描无关目录。
