# Repo Agent

一個運行在終端中的互動式程式碼倉庫助手。Repo Agent 既是一個 REPL 風格的 Git 工作流工具，也是一個由 LLM 驅動的多代理（Multi-Agent）編碼助手：你可以用斜線指令直接操作倉庫，也可以讓代理自動規劃、思考並執行複雜的多步驟任務。

底層使用 [LangChain](https://www.langchain.com/) + [LangGraph](https://langchain-ai.github.io/langgraph/) 構建多代理圖執行管線，以 [DeepSeek](https://www.deepseek.com/) (`deepseek-chat`) 作為推理模型，使用 [`prompt-toolkit`](https://python-prompt-toolkit.readthedocs.io/) 提供帶歷史記錄的輸入體驗，並透過 [`rich`](https://rich.readthedocs.io/) 渲染彩色面板、語法高亮、表格與檔案樹。

---

## 功能特色

- **互動式 REPL**：帶歷史記錄與行編輯，啟動後可在同一個會話中切換多個倉庫。
- **倉庫上下文索引**：基於 `git ls-files` 建立檔案清單（自動跳過 `.git`、`.venv`、`__pycache__`、`*.egg-info`、`.env` 等）。
- **Git 工作流斜線指令**：`/diff`、`/git-status`、`/stage`、`/unstage`、`/commit-preview`、`/commit` 等。
- **自然語言對話**：未以 `/` 開頭的輸入會交由 LLM 處理，可自動呼叫工具完成多步驟任務。
- **LangGraph 多代理管線**（`/agent`）：三階段自動執行流程：上下文收集 → 規劃 → 行動，在執行中即時顯示每個步驟。
- **持久化 Session 記錄**：每次開啟倉庫時自動建立 Session，所有使用者輸入、代理行動與回應以 JSONL 格式記錄在本地。
- **Session 摘要**（`/session-summary`）：讓 LLM 讀取 Session 事件紀錄，生成結構化的 Markdown 摘要，方便下次繼續。
- **安全的檔案寫入**：`/write` 與 `write_file` 工具均會先顯示語法高亮預覽，並要求使用者確認後才會落盤；寫入路徑被限制在倉庫根目錄之內。
- **提交訊息建議**：`/commit-message` 會讓 LLM 讀取已暫存的 diff，產出符合 Conventional Commit 風格的訊息。
- **富文本輸出**：所有結果（差異、檔案內容、搜尋結果、檔案樹、Git 狀態等）皆透過 `rich` 渲染。

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

主要相依套件（見 [pyproject.toml](pyproject.toml)）：

- `prompt-toolkit >= 3.0.0`
- `langchain >= 1.0.0`
- `langchain-deepseek >= 1.0.0`
- `langgraph`
- `python-dotenv >= 1.0.0`
- `rich >= 13.0.0`

---

## 設定

Repo Agent 使用 DeepSeek 作為 LLM 後端，需要設定 API 金鑰。在專案根目錄（或工作目錄）建立 `.env`：

```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

`.env` 會由 [repo_agent/llm.py](repo_agent/llm.py) 中的 `build_llm()` 透過 `python-dotenv` 載入。

### 可選環境變數

| 變數 | 預設值 | 用途 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | _(無)_ | DeepSeek API 金鑰，必填 |
| `REPO_AGENT_HOME` | `~/.repo_agent` | 存放 REPL 歷史、Session 記錄與專案資料的目錄 |

---

## 快速開始

```bash
repo-agent
```

啟動後輸入 `/open <repo_path>` 載入一個 Git 倉庫：

```
> /open ~/code/my-project
OK Repository loaded: /Users/me/code/my-project
> /tree
> 幫我看一下 src/utils.py 裡的 parse_args 是做什麼的
> /diff
> /stage src/utils.py
> /commit-message
> /commit "refactor: simplify parse_args"
```

使用 LangGraph 多代理模式執行複雜任務：

```
> /agent 找出所有沒有加型別標注的函式，並修改 utils.py 補上型別
  > build_context  - collecting repo files, git status, diff
  > plan           - creating execution plan
  > act            - calling tools to complete the task
OK Agent task complete.
```

---

## 斜線指令

### 倉庫操作

| 指令 | 說明 |
| --- | --- |
| `/open <repo_path>` | 載入一個倉庫；會自動向上尋找 `.git` 根目錄，並建立新 Session |
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
| `/agent <task>` | 以 LangGraph 多代理管線執行任務（上下文 → 規劃 → 行動） |

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

任何不以 `/` 開頭的輸入，會被送往 [repo_agent/agent.py](repo_agent/agent.py) 中的 `handle_user_task()`，由 LangChain agent 處理。代理在每次呼叫時會獲得以下工具（見 [repo_agent/lc_tools.py](repo_agent/lc_tools.py)）：

| 工具 | 行為 |
| --- | --- |
| `read_file(path)` | 讀取倉庫中的檔案；支援唯一檔名解析 |
| `search_code(query)` | 在已索引檔案中以子字串搜尋（最多回傳 30 條） |
| `git_diff()` | 回傳目前未暫存的 diff |
| `list_files()` | 列出所有已索引的檔案 |
| `write_file(path, content)` | 寫入檔案，會先在終端顯示預覽並要求使用者確認 |

每次對話都會被記錄到 Session 事件紀錄中，方便後續透過 `/session-summary` 回顧。

---

## LangGraph 多代理管線（`/agent`）

`/agent <task>` 指令會觸發一個三節點的 LangGraph 有向無環圖（DAG）：

```
build_context  →  plan  →  act
```

1. **`build_context`**：收集倉庫路徑、當前分支、完整檔案清單、`git status` 與 `git diff`，建立結構化的上下文字串。
2. **`plan`**：將任務描述與上下文交給**規劃代理**（Planner Agent），生成 3–6 個具體執行步驟。規劃代理只能使用唯讀工具，不會修改任何檔案。
3. **`act`**：將上下文、執行計劃與原始任務一同交給**執行代理**（Act Agent），由其呼叫工具完成實際操作（讀取、搜尋、寫入等）。

每個節點執行時都會在終端輸出當前步驟，方便追蹤進度。

---

## Session 管理

每次透過 `/open` 載入倉庫時，系統會自動建立一個新 Session，並在 `~/.repo_agent/<repo_hash>/sessions/` 目錄下建立一個 JSONL 事件日誌。

**記錄的事件類型：**

| 事件類型 | 觸發時機 |
| --- | --- |
| `session_start` | `/open` 成功後 |
| `repo_opened` | 倉庫載入完成，含分支與檔案列表 |
| `user_input` | 每次自然語言輸入 |
| `assistant_response` | 每次 LLM 回應 |
| `agent_task` | `/agent` 指令觸發 |
| `agent_result` | Agent 執行完成的結果 |

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

```
repo-agent/
├── pyproject.toml              # 套件中繼資料與相依
├── repo_agent/
│   ├── __init__.py
│   ├── cli.py                  # REPL 主迴圈與所有斜線指令處理
│   ├── agent.py                # LangChain agents：handle_user_task / suggest_commit_message / summarize_current_session
│   ├── graph.py                # LangGraph 多代理管線（build_context → plan → act）
│   ├── graph_state.py          # AgentGraphState TypedDict
│   ├── plan.py                 # 規劃代理（Planner Agent）
│   ├── context_engine.py       # 倉庫上下文構建（git status/diff/files）
│   ├── session_store.py        # Session JSONL 事件記錄與 Markdown 摘要
│   ├── session.py              # RepoSession：保存 repo_path、branch、files、messages、session_id
│   ├── lc_tools.py             # 暴露給 LLM 的工具：read/search/list/diff/write
│   ├── llm.py                  # DeepSeek LLM 工廠
│   ├── tools.py                # 底層檔案 I/O 與 shell 執行
│   ├── repo_context.py         # 對 git 的所有薄包裝
│   ├── display.py              # 所有 rich 終端輸出
│   └── path.py                 # REPO_AGENT_HOME / history / project dir 計算
└── .env                        # DEEPSEEK_API_KEY
```

各檔案的職責：

- [repo_agent/cli.py](repo_agent/cli.py)：定義 `main()` 與所有指令處理器，是程式入口；負責 Session 事件記錄。
- [repo_agent/graph.py](repo_agent/graph.py)：LangGraph DAG 的定義與編譯，`run_graph_agent()` 是外部呼叫入口。
- [repo_agent/plan.py](repo_agent/plan.py)：規劃代理，只使用唯讀工具，輸出 3–6 步執行計劃。
- [repo_agent/context_engine.py](repo_agent/context_engine.py)：`build_basic_context()` 將倉庫狀態格式化為 LLM 友好的上下文字串。
- [repo_agent/session_store.py](repo_agent/session_store.py)：Session JSONL 的讀寫、摘要 Markdown 的儲存。
- [repo_agent/agent.py](repo_agent/agent.py)：三個 agent 函式：`handle_user_task`（對話）、`suggest_commit_message`（提交訊息）、`summarize_current_session`（Session 摘要）。
- [repo_agent/repo_context.py](repo_agent/repo_context.py)：所有 `git` 子程序的薄包裝，並提供 `is_indexable_file` 過濾規則。
- [repo_agent/tools.py](repo_agent/tools.py)：與 git 無關的 IO：解析路徑、讀檔、搜尋、寫檔、執行 shell 指令。
- [repo_agent/path.py](repo_agent/path.py)：集中管理 `~/.repo_agent` 下的 history 與 project 目錄。

---

## 安全性

- **寫入需確認**：`/write` 與 LLM 工具 `write_file` 都會先以語法高亮顯示預覽，並要求 `y/N` 確認後才會落盤。
- **路徑沙箱**：`write_repo_file` 與 `write_file` 工具會把目標路徑 `resolve()` 後檢查是否仍在倉庫根目錄之內，逃逸的路徑會被拒絕。
- **不會自動提交**：所有的 `git add` / `git commit` 都由使用者明確觸發；LLM 代理本身沒有提交工具。
- **規劃代理唯讀**：`/agent` 管線中的 Plan 節點只能使用唯讀工具，不能修改任何檔案。

---

## 開發

```bash
pip install -e .
repo-agent
```

歷史檔案位於 `~/.repo_agent/history`（或 `$REPO_AGENT_HOME/history`）。

Session 記錄位於 `~/.repo_agent/<repo>/sessions/`，包含：
- `<session_id>.jsonl` — 事件日誌
- `<session_id>.md` — LLM 生成的摘要（執行 `/session-summary` 後產生）

如果要更換 LLM，可修改 [repo_agent/llm.py](repo_agent/llm.py) 中的 `build_llm()`，回傳任何相容於 LangChain `BaseChatModel` 的物件即可。

---

## 路線圖 / TODO

- 將 Session 歷史訊息餵給對話代理，讓多輪自然語言對話可以跨 Session 維持上下文。
- 在 LangGraph 管線中加入條件邊（Conditional Edge），支援根據規劃結果動態調整步驟。
- 為執行代理加入 `git status` / `stage` / `commit` 等工具，使其能端到端完成提交流程（同時保留使用者確認）。
- 支援更多檔案類型的索引與二進位檔案的偵測。
- 加入向量嵌入式語意搜尋，取代目前的純子字串搜尋。
