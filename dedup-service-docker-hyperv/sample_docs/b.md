# JDK 环境安装指南

这份文档介绍如何在开发机器上配置 JDK。推荐安装团队约定的长期支持版本，并在安装结束后检查 `JAVA_HOME`、系统 `PATH` 以及命令行中的 Java 版本，确认编译工具能访问正确的运行环境。

完成安装以后，可以通过下面的命令验证当前 Java 和编译器版本。如果版本号满足项目要求，就可以继续配置 Maven、Gradle 等常用构建工具。

```bash
java -version
javac -version
echo "$JAVA_HOME"
```

当一台机器上同时保留多个 JDK 时，请在 shell 配置文件里明确指定 `JAVA_HOME`，避免构建流程误用历史版本。
