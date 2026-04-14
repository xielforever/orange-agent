# Hermes Agent 核心代码百科 (Code Wiki)

Hermes Agent 是由 Nous Research 开发的一个自我进化的 AI 智能体系统。它具有独立的本地终端（CLI）、多平台网关（Gateway，支持 Telegram/Discord/Slack 等）以及可插拔的运行环境（Docker, Daytona, Modal 等），支持自主学习技能（Skills）和长程记忆。

---

## 1. 项目整体架构

项目整体采用分层架构，将核心智能体逻辑与外部通信接口、工具执行沙箱进行了解耦：

- **Agent 核心层 (`agent/`, `run_agent.py`)**：整个系统的“大脑”。负责与大模型（LLM）的通信、工具调用循环（Agent Loop）、提示词构建（Prompt Builder）、上下文压缩（Context Compressor）以及记忆管理（Memory Manager）。
- **工具与技能层 (`tools/`, `skills/`)**：提供代理可以执行的实际操作（如文件读写、终端命令执行、浏览器控制、MCP 等）。技能（Skills）可以由智能体在运行中自主学习并持久化到本地。
- **网关与通信层 (`gateway/`)**：处理与外部通讯平台（Discord, Telegram, Mattermost, Feishu 等）的集成，通过事件驱动和会话隔离来响应多用户并发请求。
- **CLI 与交互层 (`hermes_cli/`, `cli.py`)**：提供全功能的终端用户界面（TUI），支持多行输入、快捷斜杠命令（Slash Commands）、流式输出和配置管理。
- **运行环境层 (`environments/`)**：管理智能体执行工具（如 Terminal 工具）时的底层沙箱，支持多种环境如本地、Docker、Daytona、Singularity 等。
- **IDE 协议适配 (`acp_adapter/`)**：实现了 Agent Client Protocol (ACP)，允许将 Hermes Agent 作为辅助编程插件无缝集成到 Cursor、JetBrains 等 IDE 中。

---

## 2. 主要模块职责

- **根目录核心脚本**：
  - [`run_agent.py`](file:///workspace/run_agent.py)：定义了核心的 `AIAgent` 类和 Agent Loop。
  - [`cli.py`](file:///workspace/cli.py)：CLI 的核心入口。
- **`agent/` 目录**：
  - [`prompt_builder.py`](file:///workspace/agent/prompt_builder.py)：负责组装系统提示词（System Prompt），整合身份设定、工具 Schema、动态 Context 文件（如 `AGENTS.md`）和提取的记忆。
  - [`memory_manager.py`](file:///workspace/agent/memory_manager.py) & [`memory_provider.py`](file:///workspace/agent/memory_provider.py)：管理内置及外部的记忆插件，通过预加载机制将用户的历史信息注入当前对话，支持长期记忆。
  - [`context_compressor.py`](file:///workspace/agent/context_compressor.py)：防止 Token 溢出的核心机制。当对话达到长度上限时，对历史消息进行摘要并进行有损压缩。
  - [`smart_model_routing.py`](file:///workspace/agent/smart_model_routing.py)：处理不同模型提供商（Provider）的路由、重试与故障转移。
- **`gateway/` 目录**：
  - [`run.py`](file:///workspace/gateway/run.py)：网关服务的启动入口，加载配置并拉起所有启用的通信平台适配器。
  - `platforms/`：存放各通信平台的具体实现（例如 Telegram、Discord、Slack 等）。
  - [`session.py`](file:///workspace/gateway/session.py)：管理独立的会话状态，防止多用户高并发操作导致状态冲突。
- **`hermes_cli/` 目录**：
  - 包含了 CLI 的业务逻辑，如配置文件加载、交互式 Setup 向导、状态管理等。
- **`tools/` 目录**：
  - 实现具体的工具能力：如终端控制 ([`terminal_tool.py`](file:///workspace/tools/terminal_tool.py))、文件操作 ([`file_tools.py`](file:///workspace/tools/file_tools.py))、浏览器控制 ([`browser_tool.py`](file:///workspace/tools/browser_tool.py)) 和 MCP 支持 ([`mcp_tool.py`](file:///workspace/tools/mcp_tool.py))。

---

## 3. 关键类与函数说明

### `AIAgent` (位于 `run_agent.py`)
- **职责**：智能体执行引擎。
- **机制**：维护对话历史，处理 API 的不同调用模式（`chat_completions`, `codex_responses`, `anthropic_messages`），并在单次回合中自动循环执行模型的工具调用，直到任务完成。同时负责调用 `MemoryManager` 进行会话记忆的 Flush 和拉取。

### `MemoryManager` (位于 `agent/memory_manager.py`)
- **职责**：统一的记忆调度中心。
- **机制**：通过 `prefetch_all()` 在每次模型交互前拉取相关记忆；通过 `sync_all()` 在回合结束后同步新记忆。支持一个内置记忆库和一个可选的外部插件记忆库。

### `ContextCompressor` (位于 `agent/context_compressor.py`)
- **职责**：对话上下文的动态裁剪器。
- **机制**：当系统追踪到会话长度超过阈值时，自动调用辅模型（或主模型）对历史对话进行摘要，丢弃中间内容而保留最前与最后的关键信息，以保证持续稳定运行。

### `GatewayRunner` (位于 `gateway/run.py`)
- **职责**：网关的生命周期管理器。
- **机制**：负责初始化 SSL 证书环境，桥接 `config.yaml` 到环境变量，拉起异步的 `asyncio` 事件循环，并同时启动多个平台（如 Telegram、Discord）的客户端。

---

## 4. 依赖关系

- **Python 版本**：项目基于 Python 3.11+。
- **依赖管理工具**：通过 `pyproject.toml` 和 `requirements.txt` 管理依赖。推荐使用 `uv` 极速安装环境。
- **大模型 SDK**：主要依赖 `openai` 和 `anthropic` 的 Python 库。
- **异步与网络**：使用 `aiohttp` 和 `asyncio` 进行高并发的网络通讯（特别是 `gateway/` 层）。
- **浏览器控制**：集成了 Node.js 和 `playwright`，用于实现复杂的网页自动化操作。
- **数据库/状态存储**：使用本地文件系统和 SQLite (`state.db`) 来维护状态与持久化数据。

---

## 5. 项目运行方式

### 5.1 快速安装与配置
官方推荐使用自动化安装脚本：
```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
```

首次运行可以通过向导配置 API Key 等：
```bash
hermes setup
```

### 5.2 启动 CLI 交互模式 (TUI)
在终端直接启动进入智能体对话：
```bash
hermes
```
在 CLI 模式下可以使用斜杠命令，如：
- `/model` 切换大模型
- `/new` 开启新对话
- `/skills` 查看和管理学习到的技能

### 5.3 启动消息网关模式 (Gateway)
将 Hermes Agent 接入到 Discord、Telegram 或 Slack 等平台：
1. 运行网关配置向导：
   ```bash
   hermes gateway setup
   ```
2. 启动网关服务（保持后台运行）：
   ```bash
   hermes gateway run
   ```

### 5.4 Docker 运行方式
如果希望完全容器化运行：
```bash
# 创建数据卷目录
mkdir -p ~/.hermes

# 运行初始化 Setup 向导
docker run -it --rm -v ~/.hermes:/opt/data nousresearch/hermes-agent setup

# 后台持续运行网关
docker run -d --name hermes --restart unless-stopped -v ~/.hermes:/opt/data nousresearch/hermes-agent gateway run
```