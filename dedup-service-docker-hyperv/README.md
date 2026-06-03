# dedup-service Docker Desktop Hyper-V 运行层

这个目录是原 `dedup-service` 的 Windows Docker Desktop Hyper-V backend 运行层。它不替代原版本，也不会复制完整服务代码；Docker build 会以父目录 `file-agent/` 作为 build context，把 `dedup-service/` 中的应用代码复制进 Linux container 镜像。

适用目标：Windows 上不使用 WSL，使用 Docker Desktop Hyper-V backend 运行 Linux containers。

## 前置条件

- Windows 10/11 Pro、Enterprise 或 Education。
- Docker Desktop 使用 all-users installation。
- Docker Desktop 使用 Hyper-V backend。
- Docker Desktop 切换为 Linux containers。
- Windows Features 已启用 Hyper-V 和 Containers。
- BIOS/UEFI 已开启硬件虚拟化。
- 不使用 WSL，不使用 Windows containers。

可以先运行检查脚本：

```powershell
.\scripts\install-docker-hyperv.ps1
```

该脚本只做检查和提示，不会自动下载或安装 Docker Desktop。启用 Windows Features 时，脚本会先询问确认。

## 为什么不使用 Windows containers

当前服务依赖 Python、Docling、PDF 解析、OpenCV 相关包和若干 Linux 系统库。Linux container 更接近后续服务器部署环境，也更容易复现生产依赖。

Windows containers 在 Python 文档解析、PDF 工具链和图像处理依赖上调试成本较高，不作为第一阶段推荐路线。

## 安装 Docker Desktop Hyper-V 后端

交互安装时，请选择 all-users installation，并在 Docker Desktop 设置中使用 Hyper-V backend。安装后确认 Docker Desktop 正在使用 Linux containers。

命令行安装示例：

```powershell
Start-Process 'Docker Desktop Installer.exe' -Wait -ArgumentList 'install', '--backend=hyper-v', '--accept-license'
```

如果你之前安装的是 per-user 模式，切换到 all-users / Hyper-V backend 时可能需要卸载并重新安装 Docker Desktop。

## 启动服务

从 `file-agent` 父目录进入本目录：

```powershell
cd file-agent\dedup-service-docker-hyperv
.\scripts\run.ps1
```

也可以直接运行：

```powershell
docker compose up --build
```

服务启动后会监听宿主机端口 `8000`。SQLite 数据库持久化在本目录的 `data/dedup.db`，容器内路径是 `/app/data/dedup.db`。

## 健康检查

另开一个 PowerShell：

```powershell
curl.exe http://localhost:8000/health
```

预期返回：

```json
{"status":"ok"}
```

## 扫描默认 sample_docs

默认 `docker-compose.yml` 会把本目录下的 `sample_docs` 只读挂载到容器内 `/data/docs`。

```powershell
.\scripts\scan.ps1
```

或者直接调用：

```powershell
curl.exe -X POST http://localhost:8000/scan `
  -H "Content-Type: application/json" `
  -d "{\"source_path\":\"/data/docs\"}"
```

注意：请求里必须传容器内路径 `/data/docs`，不是 Windows 路径。

## 扫描真实 Windows 文件夹

例如真实目录是：

```text
D:\company_docs
```

请修改 `docker-compose.yml`：

```yaml
volumes:
  - ./data:/app/data
  - D:/company_docs:/data/docs:ro
```

然后请求仍然传：

```json
{"source_path":"/data/docs"}
```

不要传：

```json
{"source_path":"D:\\company_docs"}
```

也可以参考 `docker-compose.override.example.yml`，把真实目录挂载到容器内 `/data/docs`。

## 查看结果

```powershell
curl.exe http://localhost:8000/documents
curl.exe http://localhost:8000/clusters
curl.exe http://localhost:8000/report.md
```

`sample_docs/a.md` 和 `sample_docs/a_copy.md` 内容完全相同，用于测试 exact duplicate；`sample_docs/b.md` 与它们高度相似，用于测试 MinHash near duplicate。

## 常见问题

### Docker 无法选择 Hyper-V backend

确认 Docker Desktop 是 all-users installation。per-user 安装模式下可能无法选择 Hyper-V backend，通常需要卸载后重新安装。

### Windows Home 不适合该方案

Hyper-V backend 推荐 Windows 10/11 Pro、Enterprise 或 Education。Windows Home 通常更适合 WSL2 backend，但本目录明确不走 WSL 路线。

### 忘记使用 Linux containers

请在 Docker Desktop 中切换到 Linux containers。当前镜像基于 `python:3.11-slim`，不是 Windows container 镜像。

### 端口 8000 被占用

修改 `docker-compose.yml` 的端口映射，例如：

```yaml
ports:
  - "8001:8000"
```

之后访问：

```powershell
curl.exe http://localhost:8001/health
```

### Docling 首次解析 PDF 慢

Docling 和相关模型、PDF/OCR 依赖首次运行可能较慢。`sample_docs` 使用 Markdown 文件，适合先验证服务链路。

### 容器内路径和 Windows 路径混淆

`/scan` 接口只能看到容器内路径。Windows 目录必须先通过 `volumes` 挂载进容器，再传容器内路径，例如 `/data/docs`。

### SQLite 数据库持久化位置

宿主机位置是：

```text
dedup-service-docker-hyperv\data\dedup.db
```

容器内位置是：

```text
/app/data/dedup.db
```

不要提交 `data/dedup.db` 或真实业务文档。

### PowerShell 中使用 curl.exe

PowerShell 中的 `curl` 可能是别名。请使用 `curl.exe`，避免参数解析行为不同。

## .dockerignore 说明

当前 compose 使用父目录 `file-agent/` 作为 build context，因此真正生效的 `.dockerignore` 应放在父目录 `file-agent/.dockerignore`。本目录不强制修改父目录；如果后续 build context 变大，可以在父目录添加忽略规则，例如 `.venv/`、`data/`、`*.db`、`__pycache__/`。
