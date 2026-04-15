# Orange Agent (Hermes) Scripts 目录说明

本目录包含了项目安装、部署、调试与日常运维所需的各种辅助脚本。

其中最核心的脚本是 `install.sh`（适用于 Linux/macOS）和 `install.ps1`（适用于 Windows），它们负责实现项目的“一键全自动部署”。

---

## `install.sh` 执行流程深度解析

`install.sh` 脚本长达 1400 多行，它不仅负责下载代码，更是一个**“全自动化环境保姆”**。当你执行该脚本时，它在后台严格按照以下 6 个阶段（Phase）运行：

### 阶段 1：环境嗅探 (Environment Detection)
脚本一启动，首先摸清目标系统的底细。
*   执行 `uname -s` 判断是 Linux 还是 macOS。
*   对于 Linux，读取 `/etc/os-release` 识别具体的发行版（如 Ubuntu 对应 `apt`，CentOS 对应 `dnf`，Arch 对应 `pacman`）。
*   对于 Windows (如 Cygwin/MSYS 环境)，直接报错并提示用户改用同目录下的 `install.ps1` PowerShell 脚本。

### 阶段 2：基建工具与系统包安装 (Dependencies)
强制将目标系统补齐到满足 Agent 运行的标准：
*   **安装 `uv`**：下载极速的 Rust 版 Python 包管理器 `uv`（替代缓慢的 `pip`）。
*   **准备 Python 3.11**：若系统无合适版本，脚本使用 `uv` 在沙盒内自动下载部署 Python 3.11，不污染系统全局环境。
*   **准备 Node.js 22**：若系统未安装 Node，脚本会直接从官网拉取 Node 22 二进制压缩包并解压，专供 Browser 自动化工具使用。
*   **系统增强包**：静默调用系统的 `apt` 或 `brew` 等包管理器，自动安装 `ripgrep`（极速搜代码）和 `ffmpeg`（处理语音消息）。

### 阶段 3：代码拉取与更新 (Clone & Update)
管理源码仓库，实现代码的无缝下载或更新：
*   默认将代码 `git clone` 到隔离目录 `~/.hermes/hermes-agent`。
*   如果检测到目标目录已存在，脚本会执行 `git stash` 暂存用户的本地修改，然后执行 `git pull --ff-only` 更新代码，最后询问是否恢复暂存。

### 阶段 4：虚拟环境与依赖隔离 (Virtual Environment)
构建绝对隔离的运行环境，避免版本冲突：
*   在源码目录下执行 `uv venv` 创建 Python 虚拟环境。
*   执行 `uv pip install -e ".[all]"`，极速安装诸如 `playwright`、`pyvmomi`、`openai` 等几百个第三方 Python 库。
*   执行 `npm install` 下载前端依赖，并静默下载上百兆的无头浏览器（Chromium）内核以支持 Web 操作。

### 阶段 5：环境变量与目录初始化 (Setup PATH)
完成代码逻辑与运行时状态的物理隔离架构：
*   **创建运行时目录**：在用户主目录 `~/.hermes/` 下建立 `logs/`, `memories/`, `skills/`, `sessions/` 等一系列干净的数据文件夹。
*   **拷贝配置模板**：将源码中的 `.env.example` 和 `cli-config.yaml.example` 复制一份作为用户的专属配置。
*   **注入全局命令**：将 `hermes` 启动脚本软链接到 `~/.local/bin`，并自动向用户的 `~/.bashrc` 或 `~/.zshrc` 中注入 `export PATH` 环境变量。确保用户在任何路径下敲击 `hermes` 均可唤醒 Agent。

### 阶段 6：交互向导与服务注册 (Setup Wizard)
环境搭建完毕后，将控制权交还给用户进行个性化配置：
*   弹出交互式向导（Setup Wizard），引导用户输入大语言模型（如 OpenAI, Anthropic）的 API Key。
*   若检测到配置了 Telegram 或 Discord 机器人的 Token，脚本会询问是否需要将其注册为 Linux 的 **Systemd 后台守护服务**，从而实现 Agent 的开机自启和 24 小时无人值守运行。

---

## 目录架构设计理念（代码与状态分离）

理解本脚本的安装行为，需要明白 Hermes 架构中的“读写分离”设计：

*   **`~/.hermes/hermes-agent/`（源代码目录）**
    这是“执行者”（类似游戏引擎）。它包含了所有 `.py` 脚本、工具逻辑（如 vCenter 插件）和系统提示词。用户通常不需要修改这里的代码，只需通过 `git pull` 升级即可。
*   **`~/.hermes/` 根目录（运行时数据目录）**
    这是“被读写对象”（类似游戏存档）。它包含了用户的 API 配置（`.env`）、对话数据库（`state.db`）、长期记忆（`memories/`）和运行日志（`logs/`）。

这种设计确保了在执行代码升级（阶段 3）时，绝不会覆盖或污染用户私有的对话记录和配置文件，同时极大方便了 Docker 容器化挂载和数据迁移。