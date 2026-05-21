# Repo Agent

一個運行在終端中的互動式程式碼倉庫助手。Repo Agent 既是一個 REPL 風格的 Git 工作流工具，也是一個由 LLM 驅動的本地 coding agent runtime：你可以用斜線指令直接操作倉庫，也可以進入 Agent Mode，讓代理根據任務自動路由、規劃、逐步執行、驗證並總結。

底層使用 [LangChain](https://www.langchain.com/) + [LangGraph](https://langchain-ai.github.io/langgraph/) 構建代理圖執行管線，以 [DeepSeek](https://www.deepseek.com/) 的 `deepseek-chat` 作為工具呼叫模型、`deepseek-reasoner` 作為無工具推理模型，使用 [`prompt-toolkit`](https://python-prompt-toolkit.readthedocs.io/) 提供帶歷史記錄的輸入體驗，並透過 [`rich`](https://rich.readthedocs.io/) 渲染彩色面板、語法高亮、表格、檔案樹、計劃 checklist、驗證報告與 token usage。

---

## 功能特色

- **互動式 REPL**：帶歷史記錄與行編輯，啟動後可在同一個會話中載入倉庫並執行斜線指令。
- **Agent Mode**：輸入 `/agent` 後進入 `Agent>` 子模式，後續自然語言輸入會先經過 intent router，再分流到聊天、Session 回憶、唯讀分析或可寫 coding graph。
- **LLM Router + 權限分層**：使用 no-tool LLM router 將輸入分類為 `chat`、`memory_query`、`read_only_repo_task`、`code_change`、`command_task`，並用 `write_allowed` 控制 executor 是否能拿到 `write_file` 工具。
- **倉庫上下文索引**：基於 `git ls-files --cached --others --exclude-standard` 建立檔案清單（自動跳過 `.git`、`.venv`、`__pycache__`、`*.egg-info`、`.env` 等）。
- **Git 工作流斜線指令**：`/diff`、`/git-status`、`/stage`、`/unstage`、`/commit-preview`、`/commit-message`、`/commit` 等。
- **LangGraph agent pipeline**：目前管線為 `build_context → plan → act → verify → summarize`，支援結構化計劃、逐步 executor、Git verification、final run summary。
- **Plan Checklist UI**：planner 輸出 JSON steps，終端顯示 `[ ]` / `[>]` / `[x]` 狀態，step executor 逐步更新進度。
- **Verify 節點**：執行後收集 `git status --short`、unstaged diff、staged diff、staged / unstaged / untracked files。
- **Token usage 顯示**：executor 會嘗試從 LangChain message metadata 中提取 token usage，並在 graph run 末尾顯示 token 統計。
- **持久化 Session 記錄**：每次開啟倉庫時自動建立 Session，使用者輸入、agent task、路由結果與回應會以 JSONL 格式記錄在本地。
- **Session 摘要**（`/session-summary`）：讓 LLM 讀取 Session 事件紀錄，生成結構化 Markdown 摘要，方便下次繼續。
- **安全的檔案寫入**：`/write` 與 `write_file` 工具均會先顯示語法高亮預覽，並要求使用者確認後才會落盤；寫入路徑被限制在倉庫根目錄之內。
- **富文本輸出**：差異、檔案內容、搜尋結果、檔案樹、Git 狀態、agent trace 等皆透過 `rich` 渲染。

---

## 安裝

需求：Python `>= 3.10`，並已安裝 `git`。

```bash
# 建議使用虛擬環境
python -m venv .venv
source .venv/bin/activate

# 以可編輯模式安裝
pip install -e .
```

安裝後即可在 PATH 中使用 `repo-agent` 指令（由 [pyproject.toml](pyproject.toml) 中的 `[project.scripts]` 定義）。

### 依賴

主要相依套件：

- `prompt-toolkit >= 3.0.0`
- `langchain >= 1.0.0`
- `langchain-deepseek >= 1.0.0`
- `langgraph`
- `python-dotenv >= 1.0.0`
- `rich >= 13.0.0`

---

## 設定

Repo Agent 使用 DeepSeek 作為 LLM 後端，需要設定 API 金鑰。在專案根目錄（或工作目錄）建立 `.env`：

```env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

`.env` 會由 [repo_agent/llm.py](repo_agent/llm.py) 中的模型 builder 透過 `python-dotenv` 載入。

### 可選環境變數

| 變數 | 預設值 | 用途 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | _(無)_ | DeepSeek API 金鑰，必填 |
| `REPO_AGENT_HOME` | `~/.repo-agent` | 存放 REPL 歷史、Session 記錄與專案資料的目錄 |

---

## 快速開始

```bash
repo-agent
```

啟動後輸入 `/open <repo_path>` 載入一個 Git 倉庫：

```text
> /open ~/code/my-project
OK Repository loaded: /Users/me/code/my-project
> /tree
> 幫我看一下 src/utils.py 裡的 parse_args 是做什麼的
> /diff
> /stage src/utils.py
> /commit-message
> /commit "refactor: simplify parse_args"
```

進入 Agent Mode：

```text
> /agent
OK Agent mode enabled. Enter a task for the agent to perform.
Agent> 總結 repo_agent/llm.py，不要修改文件
> Route: read_only_repo_task (write_allowed=False, run_command_allowed=False)
...
Agent> 幫我修 token usage 顯示 bug
> Route: code_change (write_allowed=True, run_command_allowed=False)
...
Agent> /back
OK Exited agent mode.
>
```

也可以保留一次性用法：

```text
> /agent 總結 repo_agent/lc_tools.py，不要修改文件
```

---

## 斜線指令

### 倉庫操作

| 指令 | 說明 |
| --- | --- |
| `/open <repo_path>` | 載入一個倉庫；會使用 `git rev-parse --show-toplevel` 解析 Git 根目錄，並建立新 Session |
| `/status` | 顯示目前載入的倉庫、分支、檔案數、訊息數 |
| `/refresh` | 重新建立倉庫的分支與檔案索引 |
| `/files` | 列出已索引的檔案（最多 40 個） |
| `/tree` | 以樹狀方式顯示倉庫檔案結構 |
| `/read <file_path>` | 讀取並語法高亮一個檔案；支援唯一檔名簡寫 |
| `/search <query>` | 在已索引檔案中做大小寫不敏感的子字串搜尋 |
| `/run <command>` | 在倉庫根目錄執行一個 shell 指令並顯示結果 |
| `/write <path>` | 進入多行輸入模式寫入檔案（以 `---END---` 結束），會先預覽並要求確認 |

### Git 操作

| 指令 | 說明 |
| --- | --- |
| `/diff` | 顯示未暫存的 `git diff` |
| `/git-status` | 顯示 `git status --short` |
| `/git-tree` | 顯示近期 Git 提交歷史樹 |
| `/stage <path>` | 暫存單一檔案（`git add`） |
| `/unstage <path>` | 取消暫存（`git restore --staged`） |
| `/commit-preview` | 顯示已暫存的 name-status 與 cached diff |
| `/commit-message` | 讓 LLM 根據已暫存 diff 生成 Conventional Commit 風格的訊息 |
| `/commit <message>` | 提交已暫存的變更 |

### Agent 操作

| 指令 | 說明 |
| --- | --- |
| `/agent` | 進入 Agent Mode，後續自然語言輸入會經過 router 分流 |
| `/agent <task>` | 執行一次 routed agent task |
| `/back` | 退出 Agent Mode，回到普通 REPL |

### Session 操作

| 指令 | 說明 |
| --- | --- |
| `/session` | 顯示目前 Session ID 與記錄檔路徑 |
| `/sessions` | 列出目前倉庫的所有歷史 Session |
| `/session-summary` | 讓 LLM 摘要本次 Session 並儲存為 Markdown 檔案 |

### 其他

| 指令 | 說明 |
| --- | --- |
| `/help` | 列出所有指令 |
| `/quit` | 退出 |

> 路徑解析支援「唯一檔名簡寫」：例如倉庫中只有一個 `utils.py`，可直接寫 `/read utils.py`；若同名檔案不只一個，會列出所有匹配以供消歧。

---

## 自然語言模式

在普通 REPL 中，任何不以 `/` 開頭的輸入，會被送往 [repo_agent/agent.py](repo_agent/agent.py) 中的 `handle_user_task()`，由 LangChain agent 處理。代理在每次呼叫時會獲得以下工具（見 [repo_agent/lc_tools.py](repo_agent/lc_tools.py)）：

| 工具 | 行為 |
| --- | --- |
| `read_file(path)` | 讀取倉庫中的檔案；支援唯一檔名解析 |
| `search_code(query)` | 在已索引檔案中以子字串搜尋（最多回傳 30 條） |
| `git_diff()` | 回傳目前未暫存的 diff |
| `list_files()` | 列出所有已索引的檔案 |
| `write_file(path, content)` | 寫入檔案，會先在終端顯示預覽並要求使用者確認 |

在 Agent Mode 中，普通文字不會直接進入可寫 agent，而是先經過 [repo_agent/router.py](repo_agent/router.py) 的 `route_agent_input()`：

| Intent | 行為 |
| --- | --- |
| `chat` | 一般聊天，不進入 coding graph |
| `memory_query` | 讀取目前 Session 的近期事件並回答 |
| `read_only_repo_task` | 進入 graph，但 executor 不會拿到 `write_file` |
| `code_change` | 進入 graph，允許 executor 使用 `write_file` |
| `command_task` | 標記為命令類任務；目前會以受限權限進入 graph |

---

## LangGraph Agent 管線

Repo Agent 的 graph 入口是 [repo_agent/graph.py](repo_agent/graph.py) 中的 `run_graph_agent()`。目前管線為：

```text
build_context  →  plan  →  act  →  verify  →  summarize
```

1. **`build_context`**：收集倉庫路徑、當前分支、檔案清單、`git status` 與 `git diff`，建立上下文字串。
2. **`plan`**：先用 `deepseek-chat` + 唯讀工具做 scout，再用 `deepseek-reasoner` 生成 JSON 結構化 plan。`parse_plan_steps()` 會優先解析 JSON，並過濾 markdown heading、note、final-output 等非執行步驟。
3. **`act`**：逐個執行 plan steps。每一步開始時標記 `[>]`，完成後標記 `[x]`，並把 step result 傳給下一步。executor 使用 `deepseek-chat` + tools；是否暴露 `write_file` 由 router 的 `write_allowed` 決定。
4. **`verify`**：使用 Git 收集 working tree facts，包括 dirty/clean、staged files、unstaged files、untracked files、unstaged diff、staged diff。
5. **`summarize`**：使用 `deepseek-reasoner` 根據 task、plan、step results 與 verification report 生成 final run summary，並顯示 token usage panel。

Graph state 定義在 [repo_agent/graph_state.py](repo_agent/graph_state.py)，目前包含：

- `plan_steps`：checklist 狀態（`pending` / `in_progress` / `completed` / `failed` / `skipped`）
- `step_results`：每一步 executor 的結果
- `verification`：Git verification report
- `summary`：本次 agent run 的最終摘要
- `token_usage`：目前收集到的 token usage 統計

---

## Session 管理

每次透過 `/open` 載入倉庫時，系統會自動建立一個新 Session，並在 `~/.repo-agent/projects/<project_id>/sessions/` 目錄下建立一個 JSONL 事件日誌。

**記錄的事件類型：**

| 事件類型 | 觸發時機 |
| --- | --- |
| `session_start` | `/open` 成功後 |
| `repo_opened` | 倉庫載入完成，含分支與檔案列表 |
| `user_input` | 每次普通自然語言輸入 |
| `assistant_response` | 普通自然語言模式的 LLM 回應 |
| `agent_task` | `/agent <task>` 或 Agent Mode 輸入觸發，包含 route |
| `agent_result` | Agent graph 執行完成的結果 |
| `agent_chat_response` | Agent Mode 中的一般聊天回應 |
| `agent_memory_response` | Agent Mode 中的 Session 回憶回應 |

**`/session-summary`** 指令會讓 LLM 讀取整個 Session 的事件紀錄，生成包含以下章節的 Markdown 摘要：

- **User Goals** — 使用者本次的主要目標
- **Work Completed** — 已完成的工作
- **Important Files** — 涉及的重要檔案
- **Decisions** — 關鍵設計決策
- **Errors And Fixes** — 遇到的問題與解決方法
- **Next Steps** — 建議的後續步驟

摘要同時儲存為 `.md` 檔案，位於對應 Session 的 JSONL 旁邊。

---

## 專案結構

```text
repo-agent/
├── pyproject.toml              # 套件中繼資料與相依
├── README.md
├── repo_agent/
│   ├── __init__.py
│   ├── cli.py                  # REPL 主迴圈、斜線指令、Agent Mode 路由入口
│   ├── agent.py                # LangChain agents：handle_user_task / suggest_commit_message / summarize_current_session
│   ├── router.py               # LLM intent router + policy fallback
│   ├── graph.py                # LangGraph 管線（build_context → plan → act → verify → summarize）
│   ├── graph_state.py          # AgentGraphState / PlanStep / StepResult / TokenUsage
│   ├── plan.py                 # Scout + reasoning planner，輸出結構化 JSON plan
│   ├── executor.py             # 單步 step executor，根據 include_write 控制工具權限
│   ├── verifier.py             # Git working tree verification
│   ├── summarizer.py           # Agent run final summary
│   ├── token_usage.py          # LangChain message token usage 提取與累加
│   ├── context_engine.py       # 倉庫上下文構建（git status/diff/files）
│   ├── session_store.py        # Session JSONL 事件記錄與 Markdown 摘要
│   ├── session.py              # RepoSession：保存 repo_path、branch、files、messages、session_id、agent_mode
│   ├── lc_tools.py             # 暴露給 LLM 的工具：read/search/list/diff/write
│   ├── llm.py                  # DeepSeek chat/reasoning model builders
│   ├── tools.py                # 底層檔案 I/O 與 shell 執行
│   ├── repo_context.py         # 對 git 的所有薄包裝
│   ├── display.py              # 所有 rich 終端輸出
│   └── path.py                 # REPO_AGENT_HOME / history / project dir 計算
└── .env                        # DEEPSEEK_API_KEY
```

各檔案的職責：

- [repo_agent/cli.py](repo_agent/cli.py)：定義 `main()`、所有斜線指令與 Agent Mode；負責 Session 事件記錄。
- [repo_agent/router.py](repo_agent/router.py)：使用 no-tool LLM 產生 route，並用規則 fallback 強制 read-only / write policy。
- [repo_agent/graph.py](repo_agent/graph.py)：LangGraph DAG 的定義與編譯，`run_graph_agent()` 是外部呼叫入口。
- [repo_agent/plan.py](repo_agent/plan.py)：兩階段 planner：chat scout 使用唯讀工具，reasoning planner 輸出 JSON steps。
- [repo_agent/executor.py](repo_agent/executor.py)：逐步執行 plan steps，透過 `include_write` 控制是否暴露寫入工具。
- [repo_agent/verifier.py](repo_agent/verifier.py)：收集 Git working tree facts，包含 staged / unstaged / untracked 狀態。
- [repo_agent/summarizer.py](repo_agent/summarizer.py)：使用 reasoning model 生成單次 agent run summary。
- [repo_agent/context_engine.py](repo_agent/context_engine.py)：`build_basic_context()` 將倉庫狀態格式化為 LLM 上下文字串。
- [repo_agent/session_store.py](repo_agent/session_store.py)：Session JSONL 的讀寫、摘要 Markdown 的儲存。
- [repo_agent/agent.py](repo_agent/agent.py)：三個 agent 函式：`handle_user_task`（對話）、`suggest_commit_message`（提交訊息）、`summarize_current_session`（Session 摘要）。
- [repo_agent/repo_context.py](repo_agent/repo_context.py)：所有 `git` 子程序的薄包裝，並提供 `is_indexable_file` 過濾規則。
- [repo_agent/tools.py](repo_agent/tools.py)：與 git 無關的 IO：解析路徑、讀檔、搜尋、寫檔、執行 shell 指令。
- [repo_agent/path.py](repo_agent/path.py)：集中管理 `~/.repo-agent` 下的 history 與 project 目錄。

---

## 安全性

- **Router 權限分層**：Agent Mode 會先分類 intent；`read_only_repo_task`、`chat`、`memory_query` 不會取得 `write_file` 工具。
- **寫入需確認**：`/write` 與 LLM 工具 `write_file` 都會先以語法高亮顯示預覽，並要求 `y/N` 確認後才會落盤。
- **路徑沙箱**：`write_repo_file` 與 `write_file` 工具會把目標路徑 `resolve()` 後檢查是否仍在倉庫根目錄之內，逃逸的路徑會被拒絕。
- **不會自動提交**：所有的 `git add` / `git commit` 都由使用者明確觸發；LLM 代理本身沒有提交工具。
- **規劃階段唯讀**：Plan 節點使用唯讀工具，不會修改任何檔案。
- **reasoning model 不接 tools**：`deepseek-reasoner` 只用於 planner / summarizer 這類無工具節點；tool-calling executor 使用 `deepseek-chat`。

---

## 開發

```bash
pip install -e .
repo-agent
```

歷史檔案位於 `~/.repo-agent/history`（或 `$REPO_AGENT_HOME/history`）。

Session 記錄位於 `~/.repo-agent/projects/<project_id>/sessions/`，包含：

- `<session_id>.jsonl` — 事件日誌
- `<session_id>.md` — LLM 生成的摘要（執行 `/session-summary` 後產生）

如果要更換 LLM，可修改 [repo_agent/llm.py](repo_agent/llm.py) 中的 `build_chat_model()` / `build_reasoning_model()`，回傳任何相容於 LangChain `BaseChatModel` 的物件即可。

---

## 路線圖 / TODO

- 將 context engine 重構為帶 budget 的 context packer，避免把完整檔案列表與大型 diff 直接塞進每次 LLM call。
- 將 `plan_steps` 升級為 first-class task state（含 `id`、`subject`、`active_form`、可動態新增/更新/刪除）。
- 加入 judge node：`verify → judge → summarize`，讓 verification 進一步影響控制流。
- 加入 validation runner：例如 `python -m compileall repo_agent`、`pytest`、`ruff` 等。
- 完整統計 planner / executor / summarizer 的 token usage，並按 graph node 拆分成本。
- 將 Session event logging 深度接入 graph nodes，為 memory writer 提供穩定資料來源。
- 加入向量嵌入式語意搜尋與 code retrieval，取代目前的純子字串搜尋。
