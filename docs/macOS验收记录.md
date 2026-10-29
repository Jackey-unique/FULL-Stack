# macOS 验收记录（2026-10-28）

本次在 macOS Apple Silicon 上使用 Python 3.13、项目固定版本依赖和 MongoDB Community 8.0.25，使用全新的临时虚拟环境及临时数据库目录。没有加载或改写 Windows 环境的真实研究数据库。

- 工作目录源码：pytest 51 项通过。
- 将 `submission/BrainAgeConnect_Code.zip` 解压到独立临时目录，并使用上述环境：pytest 51 项通过。
- 从解压的代码包运行 Newman：48 个请求、63 条断言全部通过；测试使用独立生成的合成数据和临时数据库。Node 与 Newman 由本机提供，未从代码 ZIP 安装。
- 代码 ZIP 中与工作目录同名的 47 个文件逐字节一致。

这些结果是补充验证，不是完全干净电脑的安装验收：MongoDB、Node/Newman 和 Python 依赖先行准备；当时尚未从数据库 ZIP 恢复；后续补充验证见下文。未检查真实数据和影像。最初的沙箱内测试无法连接 MongoDB，之后在允许本地连接的环境中重跑通过。Postman 原生 Runner 截图和 Postman 原生打印文档尚未生成，已有 Newman 证据不能冒充它们。视频仍未制作。

macOS 系统自带 `unzip` 在本机因 ZIP 内中文文件名编码报错；Python `zipfile` 可成功解压。这提示跨平台解压兼容性仍需处理或向接收方说明。

2026-10-28 补充：从合成数据库 ZIP 解压后，使用 MongoDB Database Tools 100.13.0 的 mongoimport 和提交包的恢复脚本导入空临时数据库，得到 150 条样本、2 个用户、两个空支持集合；登录、列表和统计接口均返回 200，列表和统计总数均为 150。依赖需事先安装，不能称为无依赖的一键安装。
