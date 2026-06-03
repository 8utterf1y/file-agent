# dedup-service

`dedup-service` 是一个企业文档去重与重组织建议的第一阶段 MVP。它读取本地文件夹，递归扫描 `.pdf`、`.docx`、`.pptx`、`.html`、`.htm`、`.md`、`.txt` 文档，解析正文后进行文件级、正文级、段落级精确重复检测，并使用 MinHash + LSH 发现 chunk 近重复。

服务只读取原始文件并生成数据库记录和报告，不会删除、移动、覆盖或修改原始文件。

## 安装方式

```bash
cd dedup-service
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

可复制 `.env.example` 为 `.env` 修改配置。默认数据库是当前目录下的 SQLite 文件：

```bash
DATABASE_URL=sqlite:///./dedup.db
MINHASH_NUM_PERM=128
LSH_THRESHOLD=0.82
```

## 启动方式

```bash
uvicorn app.main:app --reload --port 8000
```

启动后访问：

```bash
curl http://localhost:8000/health
```

返回：

```json
{"status":"ok"}
```

## 扫描示例

准备一个 `sample_docs` 目录，例如放入：

- 两个内容完全相同的 Markdown 文件
- 两个大部分内容相似但略有修改的 Markdown 文件
- 一个普通 `.txt` 文件

调用扫描：

```bash
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -d '{"source_path": "./sample_docs"}'
```

示例响应：

```json
{
  "source_path": "./sample_docs",
  "total_files": 5,
  "processed": 5,
  "skipped": 0,
  "failed": [],
  "cluster_count": 2
}
```

## API 示例

查看文档：

```bash
curl http://localhost:8000/documents
```

查看 chunk：

```bash
curl http://localhost:8000/chunks
curl "http://localhost:8000/chunks?doc_id=doc_xxx"
```

查看重复簇：

```bash
curl http://localhost:8000/clusters
```

导出 Markdown 报告：

```bash
curl http://localhost:8000/report.md
```

## 当前限制

- 第一版没有前端，也不会自动改写、移动或删除文件。
- Docling 用于 `.pdf`、`.docx`、`.pptx`，如果解析失败会在 `/scan` 的 `failed` 字段中返回错误。
- 近重复基于字符级 5-gram MinHash，适合初筛，不等价于语义重复检测。
- 文件级和正文级重复会映射到文档的首个 chunk 进入重复簇；极短文档如果没有产生 chunk，暂不会出现在 cluster 中。
- SQLite 是默认数据库，适合 MVP 和本地验证；生产环境建议切换 PostgreSQL。

## 后续路线

- 接入 PostgreSQL 和迁移工具。
- 增加后台任务队列和扫描任务状态。
- 为极短文档建立 doc-level cluster 成员模型。
- 增加 embedding 或 RAG 系统集成，用于语义级重复检测。
- 接入 Dify、FastGPT、RAGFlow、Onyx 等上层知识库平台。
- 增加导入上传接口、权限控制和审计日志。

## 测试

```bash
pytest
```
