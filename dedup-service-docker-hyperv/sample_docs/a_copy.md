# JDK 安装说明

本文档用于说明在开发环境中安装 JDK 的基础流程。建议优先安装当前项目统一要求的 LTS 版本，并在安装完成后检查 `JAVA_HOME`、`PATH` 和命令行输出，确保构建工具可以找到正确的 Java 运行时。

安装完成后，可以在终端执行以下命令确认版本信息。如果输出的版本号符合团队标准，就可以继续配置 Maven、Gradle 或其他构建工具。

```bash
java -version
javac -version
echo "$JAVA_HOME"
```

如果系统中存在多个 JDK 版本，请在 shell 配置文件中显式设置 `JAVA_HOME`，避免构建脚本读取到旧版本。
