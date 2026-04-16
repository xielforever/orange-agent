<p align="center">
  <img src="assets/banner.png" alt="Hermes Agent" width="100%">
</p>

# Hermes Agent ☤

<p align="center">
  <a href="https://github.com/xielforever/orange-agent/tree/main/docs"><img src="https://img.shields.io/badge/Docs-orange--agent-FFD700?style=for-the-badge" alt="Documentation"></a>
  <a href="https://discord.gg/your-discord-invite"><img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://github.com/xielforever/orange-agent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://github.com/xielforever"><img src="https://img.shields.io/badge/Built%20by-Your%20Name-blueviolet?style=for-the-badge" alt="Built by xielforever"></a>
</p>

**基于 Hermes 核心构建的具备自我进化能力的 AI 智能体。** 

这是唯一一个内置“学习循环”的智能体 —— 它能够从经验中创建技能、在使用中自我完善、主动将知识持久化、搜索过往对话，并在跨会话交互中建立对您的深度认知模型。您可以将其部署在 5 美元的 VPS、GPU 集群，或者是闲置时几乎零成本的 Serverless 基础设施上。它不仅局限于您的笔记本电脑 —— 您可以在它运行于云端虚拟机时，通过 Telegram、微信等方式与它对话。

支持使用任何您偏好的模型 —— [Nous Portal](https://portal.nousresearch.com), [OpenRouter](https://openrouter.ai) (200+ 模型), [Xiaomi MiMo](https://platform.xiaomimimo.com), [z.ai/GLM](https://z.ai), [Kimi/Moonshot](https://platform.moonshot.ai), [MiniMax](https://www.minimax.io), [Hugging Face](https://huggingface.co), OpenAI, 或者是您本地私有部署的模型端点。只需使用 `hermes model` 即可一键切换 —— 无需修改代码，拒绝平台绑定。

---

## ✨ 核心特性

<table>
<tr><td><b>💻 真正的终端界面 (TUI)</b></td><td>提供全功能的 TUI 界面，支持多行编辑、斜杠命令自动补全、对话历史记录、随时中断与重定向，以及工具输出的实时流式显示。</td></tr>
<tr><td><b>📱 无处不在的接入点</b></td><td>支持 Telegram, Discord, Slack, WhatsApp, Signal 以及 CLI —— 全部由单一网关进程统一管理。支持语音备忘录转录，实现跨平台的对话连续性。</td></tr>
<tr><td><b>🔄 闭环学习系统</b></td><td>由智能体自行管理的记忆库，定期进行提醒。在完成复杂任务后自主创建技能。技能在使用过程中自我进化。支持 FTS5 会话搜索与 LLM 摘要，实现跨会话的记忆唤醒。结合 <a href="https://github.com/plastic-labs/honcho">Honcho</a> 进行辩证的用户建模。兼容 <a href="https://agentskills.io">agentskills.io</a> 开放标准。</td></tr>
<tr><td><b>⏱️ 计划任务与自动化</b></td><td>内置 Cron 调度器，支持向任何平台投递消息。无论是每日巡检报告、夜间备份，还是每周审计 —— 全部通过自然语言配置，并在后台无人值守运行。</td></tr>
<tr><td><b>🔀 任务委派与并发</b></td><td>能够生成隔离的子智能体以处理并行的工作流。编写通过 RPC 调用工具的 Python 脚本，将多步骤的流水线压缩为零上下文成本的单次交互。</td></tr>
<tr><td><b>☁️ 随处运行</b></td><td>支持六种终端后端 —— 本地、Docker、SSH、Daytona、Singularity 以及 Modal。其中 Daytona 和 Modal 提供 Serverless 持久化 —— 您的智能体环境在闲置时休眠，在需要时唤醒。</td></tr>
</table>

---

## 🚀 快速安装

最推荐的一键极速安装方式（支持 Linux & macOS）：

```bash
curl -fsSL https://raw.githubusercontent.com/xielforever/orange-agent/main/scripts/install.sh | bash
```

*(如果你需要本地修改代码或二次开发，也可以手动 `git clone` 仓库后运行 `./scripts/install.sh`)*

支持 Linux, macOS, WSL2 以及通过 Termux 运行在 Android 上。安装脚本将为您处理特定平台的依赖设置。

安装完成后：

```bash
source ~/.bashrc    # 重新加载 shell 配置
hermes              # 开始对话！
```

---

## 💡 快速入门指令

```bash
hermes              # 交互式 CLI — 开始对话
hermes model        # 选择您的 LLM 提供商和模型
hermes tools        # 配置启用哪些工具
hermes config set   # 设置独立的配置项
hermes gateway      # 启动消息网关 (Telegram, Discord 等)
hermes setup        # 运行完整的设置向导
hermes doctor       # 诊断并修复任何问题
```

📖 **[查看完整官方英文文档 →](https://github.com/xielforever/orange-agent/tree/main/docs)**

## CLI 与消息平台对照表

Hermes 提供两种入口：通过 `hermes` 启动终端 UI，或运行网关并通过 Telegram、Discord 等与其对话。一旦进入对话，许多斜杠命令在两个界面中都是通用的。

| 动作 | CLI 终端 | 消息平台 (Telegram/Discord等) |
|---------|-----|---------------------|
| 开始聊天 | `hermes` | 运行 `hermes gateway setup` + `hermes gateway start`，然后给机器人发消息 |
| 开启新对话 | `/new` 或 `/reset` | `/new` 或 `/reset` |
| 切换模型 | `/model [provider:model]` | `/model [provider:model]` |
| 设置人格 | `/personality [name]` | `/personality [name]` |
| 重试或撤销 | `/retry`, `/undo` | `/retry`, `/undo` |
| 压缩上下文 / 检查用量 | `/compress`, `/usage`, `/insights [--days N]` | `/compress`, `/usage`, `/insights [days]` |
| 浏览技能 | `/skills` 或 `/<skill-name>` | `/skills` 或 `/<skill-name>` |
| 中断当前工作 | `Ctrl+C` 或发送新消息 | `/stop` 或发送新消息 |

---

## 🤝 参与贡献

我们非常欢迎您的贡献！开发环境快速启动：

```bash
git clone https://github.com/xielforever/orange-agent.git
cd orange-agent
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv venv --python 3.11
source venv/bin/activate
uv pip install -e ".[all,dev]"
# 运行测试
python -m pytest tests/ -q
```

---

## 🌐 社区资源

- 💬 [Discord](https://discord.gg/your-discord-invite)
- 📚 [Skills Hub 技能中心](https://agentskills.io)
- 🔌 [HermesClaw](https://github.com/AaronWong1999/hermesclaw) — 社区微信桥接方案：在同一个微信号上运行 Hermes Agent 和 OpenClaw。

---

## 📄 开源许可

MIT 协议 — 详见 [LICENSE](LICENSE)。

由您的团队或 [xielforever](https://github.com/xielforever) 构建 (Based on Hermes Agent).
