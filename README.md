# openwechat-im-client

OpenClaw skill for WeChat-style IM: register, send/receive messages, friend list, discover users, block/unblock.

## Server Requirement

**You must configure your own relay server.** This skill does not include or hardcode any server URL. The relay server is open source and self-hostable — see [SERVER.md](SERVER.md).

## Quick Start

1. Clone or install this skill.
2. Set up a relay server (see [SERVER.md](SERVER.md)).
3. Copy `config.json.example` to `.data/config.json` and set your `base_url` and `token`.
4. Use OpenClaw with natural language: "帮我注册xxx", "发送消息给xxx", etc.

## Files

| File | Description |
|------|-------------|
| [SKILL.md](SKILL.md) | Skill definition and OpenClaw guidance |
| [SERVER.md](SERVER.md) | Relay server self-host guide |
| [config.json.example](config.json.example) | Config template — copy to `.data/config.json` |
| `sse_inbox.py` | SSE push script |
| `demo_ui.html` | Basic chat UI (run with `npm run ui`) |
| [references/api.md](references/api.md) | API reference |

## License

MIT
