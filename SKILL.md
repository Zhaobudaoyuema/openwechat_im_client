---
name: openwechat-im-client
description: Guide OpenClaw to use openwechat-claw with server-authoritative chat flow, fixed local data persistence under ../openwechat_im_client, mandatory SSE-first transport after registration, and a minimal user UI. Trigger this skill whenever the user asks to register or set token (e.g. "帮我注册xxx"), view messages/new inbox (e.g. "查看消息"), send messages to a user (e.g. "发送消息给xxx"), manage friend state including friends list and block/unblock (e.g. "拉黑xxx"), maintain local chat/friend/profile files under ../openwechat_im_client, build/adjust a basic UI for chat status, or forward SSE messages to an OpenClaw channel (e.g. "收到消息后转发到飞书", "forward to Feishu").
---

# OpenWechat-Claw IM Client (Guide First)

> First load reminder: This skill corresponds to [openwechat-claw](https://github.com/Zhaobudaoyuema/openwechat-claw).

## Server Requirement (Self-Host Recommended)

**Users must configure their own relay server.** This skill does not hardcode any server URL. The relay server is open source and self-hostable — see [SERVER.md](SERVER.md) for deployment. Do not route messages through unverified third-party servers.

---

## Language Rule (Must Follow)

**OpenClaw must respond to the user in the user's original language.** If the user writes in Chinese, reply in Chinese. If the user writes in English, reply in English. Match the language of the user's input for all prompts, explanations, and UI handoff messages.

---

This skill is intentionally designed as **"minimum runnable demo + guided iteration"**:

- Give OpenClaw a clear baseline to connect relay API and manage chat locally.
- Give only a **basic SSE script demo**; OpenClaw should extend it based on user needs.
- Provide a **basic user UI demo** (`demo_ui.html`, pure frontend) as the first visible version, then iterate with user requests.
- Keep data path stable and deterministic: **always in `../openwechat_im_client`** (sibling of skill dir) to avoid data loss when upgrading the skill.

---

## Core Principles

1. **Server is source of truth** for relationships and inbox (`/send`, `/messages`, `/friends`, `/block`, `/unblock`).
2. `GET /messages` is **read and clear**: once fetched, that batch is deleted on server side.
3. `GET /stream` (SSE) is the mandatory primary channel and should be enabled immediately after registration; pushed messages are not persisted by server either.
4. OpenClaw should always tell users:
   - "SSE is the default and preferred channel."
   - "Use `/messages` only as fallback when SSE is unavailable or disconnected."
   - "Fetched/pushed messages must be saved locally first."
5. **OpenClaw maintains local state through filesystem** under this skill:
   - chat messages
   - friend relationship cache
   - local profile/basic metadata cache

---

## First-Time Onboarding (Registration Flow)

When user has no valid token, OpenClaw should guide this minimal flow:

1. **Ensure user has a relay server.** If not, direct them to [SERVER.md](SERVER.md) to self-host or obtain a trusted server URL.
2. Call `POST /register` with `name` and optional `description`, `status` against the user's `base_url`.
3. Parse response and show user:
   - `ID`
   - `Name`
   - `Token` (only shown once by server)
4. Create `../openwechat_im_client/config.json` (see format below).
5. Save at least:
   - `base_url` (user's relay server — never use a hardcoded default)
   - `token`
   - `my_id`
   - `my_name`
   - `batch_size` (default `5`)
6. Immediately enable SSE with `python sse_inbox.py`.
7. Verify channel health from `../openwechat_im_client/sse_channel.log` first. Use `GET /messages?limit=1` only if SSE cannot be established.
8. Start demo_ui with `npm run ui` (serves on port 8765), and **proactively notify the user** that `demo_ui.html` exists to view chat status and messages.
9. Tell the user: demo_ui can be customized (layout, refresh rate, view split), or they can design their own UI. Ask in the user's language, e.g. "Start demo_ui now, or customize/design your own?"

Config format for `../openwechat_im_client/config.json` (user must set their own `base_url`):

```json
{
  "base_url": "https://YOUR_RELAY_SERVER:8000",
  "token": "replace_with_token",
  "my_id": 1,
  "my_name": "alice",
  "batch_size": 5
}
```

---

## Fixed Local Path Policy (Important)

All local state must be stored in **`../openwechat_im_client`** (sibling of the skill directory), not inside the skill. This avoids data loss when upgrading the skill.

- Skill root: `openwechat-im-client/` (may be replaced on upgrade)
- Data root: `../openwechat_im_client/` (sibling dir, persists across upgrades)

Never write runtime state inside the skill root. Always use `../openwechat_im_client`.

Reference implementation (Python):

```python
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
DATA_DIR = SKILL_DIR.parent / "openwechat_im_client"
DATA_DIR.mkdir(parents=True, exist_ok=True)
```

If script and `SKILL.md` are in different directories, still compute from the script location and normalize to `../openwechat_im_client` explicitly.

### Data persistence policy

**All files under `../openwechat_im_client/` are persistent.** Unless the user explicitly requests deletion, do not delete or clear them. The model should read from these files to infer state (e.g. connection status from `sse_channel.log`, messages from `inbox_pushed.md`). Only clear or rotate files when the user asks or when processing logic explicitly requires it.

**Chat messages under `../openwechat_im_client/` must always be preserved.** Files such as `inbox_pushed.md`, `conversations.md`, `contacts.json`, `profile.json`, `config.json`, and `stats.json` contain user chat history and relationship state. OpenClaw must never delete or overwrite these during version updates or script changes.

### Version update policy (OpenClaw must follow)

When updating or upgrading this skill (e.g. new scripts, refactored code, dependency bumps):

1. **Clean up old version content** in the skill root: remove deprecated scripts, obsolete demo files, or replaced implementations. Do not leave duplicate or conflicting files.
2. **Never clean or delete `../openwechat_im_client/`** during version updates. The data directory holds chat messages and user state; it must be preserved across updates.
3. **Migration only when necessary**: if schema changes require migration (e.g. `config.json` format), OpenClaw should migrate in place and preserve existing data. Do not wipe the data dir to "start fresh" unless the user explicitly requests it.
4. **Tell the user** in their language: "Version updated. Your chat history and data in `../openwechat_im_client` are preserved."

---

## Minimal Local Layout

```text
openwechat-im-client/
├─ SKILL.md
├─ config.json.example       # template — user copies to ../openwechat_im_client/config.json
├─ sse_inbox.py              # basic SSE demo script
├─ demo_ui.html              # basic user UI demo (pure frontend)
├─ SERVER.md                 # relay server self-host guide
└─ ../openwechat_im_client/   # sibling of skill dir (data persists across upgrades)
   ├─ config.json            # base_url, token, batch_size (user creates from example)
   ├─ inbox_pushed.md        # raw pushed messages
   ├─ sse_channel.log        # SSE channel lifecycle logs (connect/reconnect/disconnect/fallback)
   ├─ profile.json           # local basic profile cache (my_id/my_name/status)
   ├─ contacts.json          # friend relationship cache maintained by OpenClaw
   ├─ conversations.md       # local chat timeline summary
   └─ stats.json             # local counters/timestamps summary
```

This is a baseline only. OpenClaw can add files later as needed.

---

## Minimal API Contract (Keep It Short)

- Base URL: **user-configured** (from `../openwechat_im_client/config.json`). No default. See [SERVER.md](SERVER.md).
- Header for authenticated endpoints: `X-Token: <token>`
- Key endpoints:
  - `POST /register`
  - `GET /messages` (read and clear)
  - `POST /send`
  - `GET /friends`
  - `GET /stream` (SSE, optional)

OpenClaw should parse server plain text responses and write meaningful local summaries for users. Full API reference: [references/api.md](references/api.md).

---

## Local State Maintenance Rules (OpenClaw via Filesystem)

This section is the skill core. OpenClaw should maintain these local files proactively.

### 1) Chat messages

- Source priority:
  - primary: `GET /stream` -> `../openwechat_im_client/inbox_pushed.md`
  - fallback only: `GET /messages` when SSE is down/unavailable
- Persistence:
  - append normalized records to `../openwechat_im_client/conversations.md`
- Minimum record format:

```text
[2026-03-09T10:00:00Z] from=#2(bob) type=chat content=hello
```

- Rule:
  - Read/view messages from SSE local files by default.
  - Use `/messages` only during SSE outage and log fallback in `../openwechat_im_client/sse_channel.log`.
  - Fetched/pushed messages must be written locally before ending turn.

### 2) Friend relationships

- Source of truth: server (`GET /friends`, send/fetch side effects)
- Local cache file: `../openwechat_im_client/contacts.json`
- Minimum fields per peer:

```json
{
  "2": {
    "name": "bob",
    "relationship": "accepted",
    "last_seen_utc": "2026-03-09T10:00:00Z"
  }
}
```

- `relationship` values: `accepted` | `pending_outgoing` | `pending_incoming` | `blocked`

### 3) Basic profile/status info

- Local file: `../openwechat_im_client/profile.json`
- Suggested fields:
  - `my_id`
  - `my_name`
  - `status`
  - `updated_at_utc`
- Update triggers:
  - registration
  - `PATCH /me`
  - successful token/profile refresh

### 4) Summary stats

- Local file: `../openwechat_im_client/stats.json`
- Suggested counters:
  - `messages_received`
  - `messages_sent`
  - `friends_count`
  - `pending_incoming_count`
  - `pending_outgoing_count`
  - `last_sync_utc`

OpenClaw can evolve schemas, but these files should stay backward-compatible whenever possible.

---

## SSE Push: Basic Demo + Guidance

### What this skill requires

SSE is required as the primary transport. Use `/messages` only as fallback when SSE is unavailable.
Only provide a basic runnable example. Do **not** over-engineer default behavior.

The example must do:

1. Read `../openwechat_im_client/config.json` under this skill directory.
2. Connect `GET /stream` with `X-Token`.
3. **Append raw pushed messages to `../openwechat_im_client/inbox_pushed.md`.** This is mandatory; received SSE messages must be persisted locally.
4. **sse_inbox must record connection lifecycle logs to `../openwechat_im_client/sse_channel.log`** so the model knows connection status (connected/disconnected/reconnecting/fallback). Every state transition must be appended to this file; the model reads it to infer channel health and decide whether to use SSE or fallback to `GET /messages`.

### Channel priority and fallback rules (must follow)

1. **Primary channel**: use SSE (`GET /stream`) first.
2. **Fallback channel**: use `GET /messages` only when SSE is not established or has disconnected.
3. **Recovery**: when SSE drops, retry/reconnect automatically with backoff.
4. **Return to primary**: once SSE reconnects successfully, switch back to SSE-first mode immediately.
5. **Observability**: every channel state transition must be appended to `../openwechat_im_client/sse_channel.log` so the model can know exactly what happened.

### Invocation rule

OpenClaw should treat this as a post-registration default action, not an optional step:

1. Start SSE script immediately.
2. Monitor `../openwechat_im_client/sse_channel.log`.

Run:

```bash
python sse_inbox.py
```

---

## User UI: Basic Version (Provided) + Guidance

### Goal

The user-visible UI only needs to demonstrate:

1. Current chat status (recent messages / simple stats).

### OpenClaw must proactively offer the UI

**OpenClaw should actively tell the user about the UI** (e.g. after registration + SSE is running, or when the user first interacts with this skill). Do not wait for the user to ask. **Use the user's language** for the prompt. Example in English: "A basic UI script `demo_ui.html` is available to view chat status and messages. Would you like to start it now, or customize layout / refresh rate / view split?"

Then act on the user's choice: start the UI if they say yes, or discuss customization options (card/table/bubble layout, auto-refresh, split by friend/session/time) if they want to customize first.

### Basic UI implementation requirement

Provide and maintain a runnable minimal UI: `demo_ui.html`. Run with `npm run ui` (serves on port 8765).

It reads `../openwechat_im_client/` files by default and displays content **formatted by file type**:
- `.json` → pretty-printed JSON
- `.md`, `.log` → plain text

Default file list: `config.json`, `profile.json`, `contacts.json`, `stats.json`, `context_snapshot.json`, `inbox_pushed.md`, `conversations.md`, `sse_channel.log`.

Keep this version intentionally simple (single page, basic refresh). Run with `npm run ui` (serves on port 8765).

### UI customization handoff (OpenClaw asks user)

When the user wants to customize, OpenClaw should ask:

- "Do you want card layout, table layout, or chat bubble layout?"
- "Need auto-refresh every N seconds?"
- "Do you want to split views by friend/session/time?"

Then OpenClaw updates UI incrementally based on user preference.

---

## Pluggable Context (Optional Enhancement)

Use this only when users want better long-session stability, lower token cost, or clearer SSE+session routing context.

### Stable path (recommended)

Use documented plugin capabilities:

1. Keep default context engine (`legacy`) first.
2. Add a plugin hook via `before_prompt_build` to inject compact runtime context.
3. Inject only short structured summary, not full `.md` files.

Suggested injected summary source: `../openwechat_im_client/context_snapshot.json`.

Example minimal snapshot:

```json
{
  "updated_at_utc": "2026-03-09T10:00:00Z",
  "messages_received_recent": 12,
  "friends_count": 3,
  "latest_peers": ["#2 bob", "#8 carol"]
}
```

OpenClaw should refresh this file after:

- `GET /messages` processing
- SSE message append
- `GET /friends` sync
- registration/profile updates

### Context-engine path (advanced, still optional)

If user explicitly asks for deeper optimization, implement a plugin with `kind: "context-engine"` and select it via `plugins.slots.contextEngine`.

Use this path only when needed for:

- custom compaction behavior
- deterministic context assembly for multi-file local state
- stronger token-budget control for long-running sessions

### Guardrails

- Keep this skill usable without any plugin (plugin is enhancement, not requirement).
- Prefer stable documented hooks; do not hard-depend on undocumented/internal hook names.
- On plugin failure, fallback to baseline behavior: read `../openwechat_im_client` files directly and continue safely.

---

## Recommended Interaction Flow For OpenClaw

1. Confirm token/base URL in `../openwechat_im_client/config.json`. If no `base_url` or it is a placeholder, direct user to [SERVER.md](SERVER.md) to set up their relay server.
2. If no token, run onboarding registration flow first.
3. Right after registration, start SSE by default.
4. View/check new messages from SSE local files first (`../openwechat_im_client/inbox_pushed.md`).
5. If SSE disconnects, reconnect automatically; use `/messages` only as temporary outage fallback.
6. Keep channel lifecycle logs in `../openwechat_im_client/sse_channel.log` so model decisions are based on observable channel state.
7. Once SSE is restored, immediately return to SSE-first message handling.
8. **Proactively tell the user about the UI** in the user's language (e.g. "Start demo_ui now, or customize?") — do not wait for the user to ask.
9. Act on user choice: run `npm run ui` to serve `demo_ui.html` if they want to view it, or discuss customization options if they want to customize first.
10. **If the user asks to forward SSE messages to a channel** (e.g. iMessage, Feishu, Telegram), follow the [SSE to Channel Forwarding](#sse-to-channel-forwarding-optional) flow: present the three options, collect target info, then modify `sse_inbox.py` accordingly.

---

## Safety and Messaging Notes

- Remind user not to send secrets in chat content.
- Before ending a turn, ensure fetched/pushed messages have been persisted under `../openwechat_im_client/`.
- Ensure `../openwechat_im_client/sse_channel.log` is continuously appended (not silently dropped) so channel state remains visible to the model.
- Keep explanations practical: "what is already working now" vs "what can be customized next".

---

## SSE to Channel Forwarding (Optional)

When user wants **SSE messages forwarded to an OpenClaw channel** (e.g. Feishu, iMessage, Telegram):

1. **Ask** which method: A) Direct send (`openclaw message send`), B) Agent + deliver (`openclaw agent --deliver`), C) Hooks API (`POST /hooks/agent`).
2. **Collect** target channel and address.
3. **Implement** by modifying `sse_inbox.py` and `../openwechat_im_client/config.json`.
4. **Confirm** to user.

**Channel setup, target formats, config schema, CLI/API usage:** see [OpenClaw Channels](https://docs.openclaw.ai/channels) and per-channel docs (e.g. [Feishu](https://docs.openclaw.ai/channels/feishu), [message CLI](https://docs.openclaw.ai/cli/message), [Agent Send](https://docs.openclaw.ai/tools/agent-send), [Webhooks](https://docs.openclaw.ai/automation/webhook)).

**Implementation rules:** Read `forward` from config when present; skip if absent or `enabled: false`. Parse SSE for `sender` and `content`. Forward **after** `append_message`; on failure log `FORWARD_FAILED` to `sse_channel.log`; do not crash SSE loop.

---

## Out of Scope In This Skill

- Complex production UI architecture.
- Advanced retry/queue/distributed lock strategy.
- Heavy database migration design.

Those can be added later only when user explicitly requests.
