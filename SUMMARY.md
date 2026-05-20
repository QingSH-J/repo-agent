# Repo Agent — 專案總結報告

> 生成日期：2025-01-XX  
> 版本：0.1.0  
> 語言：Python >= 3.10

---

## 專案概述

**Repo Agent** 是一個運行在終端中的互動式程式碼倉庫助手，兼具 REPL 風格的 Git 工作流工具與 LLM 驅動的多代理（Multi-Agent）編碼助手。使用者可以透過斜線指令直接操作倉庫，也可以讓代理自動規劃、思考並執行複雜的多步驟任務。

底層技術棧：

- **LangChain** + **LangGraph** — 多代理圖執行管線
- **DeepSeek** (`deepseek-chat`) — 推理模型
- **prompt-toolkit** — 帶歷史記錄的輸入體驗
- **rich** — 彩色面板、語法高亮、表格與檔案樹渲染

---

## 專案結構

```
repo-agent/
├── pyproject.toml                  # 套件中繼資料與相依
├── repo_agent/
│   ├── __init__.py                 # 套件初始化（早期原型版本）
│   ├── cli.py                      # REPL 主迴圈與所有斜線指令處理
│   ├── agent.py                    # LangChain agents：對話 / 提交訊息 / Session 摘要
│   ├── graph.py                    # LangGraph 多代理管線（build_context → plan → act）
│   ├── graph_state.py              # AgentGraphState TypedDict
│   ├── plan.py                     # 規劃代理（Planner Agent），唯讀工具
│   ├── context_engine.py           # 倉庫上下文構建（git status / diff / files）
│   ├── session_store.py            # Session JSONL 事件記錄與 Markdown 摘要
│   ├── session.py                  # RepoSession：repo_path、branch、files、messages、session_id
│   ├── lc_tools.py                 # 暴露給 LLM 的工具：read / search / list / diff / write
│   ├── llm.py                      # DeepSeek LLM 工廠
│   ├── tools.py                    # 底層檔案 I/O 與 shell 執行
│   ├── repo_context.py             # 對 git 的所有薄包裝
│   ├── display.py                  # 所有 rich 終端輸出
│   └── path.py                     # REPO_AGENT_HOME / history / project dir 計算
├── .env                            # DEEPSEEK_API_KEY（使用者自行建立）
└── SUMMARY.md                      # 本文件
```

---

## 模組職責

| 模組 | 職責 |
| --- | --- |
| `cli.py` | 程式入口，定義 `main()` 與所有指令處理器；負責 Session 事件記錄 |
| `agent.py` | 三個 agent 函式：`handle_user_task`（對話）、`suggest_commit_message`（提交訊息）、`summarize_current_session`（Session 摘要） |
| `graph.py` | LangGraph DAG 的定義與編譯，`run_graph_agent()` 是外部呼叫入口 |
| `graph_state.py` | 定義 `AgentGraphState` TypedDict，包含 task、context、plan、result 等欄位 |
| `plan.py` | 規劃代理，只使用唯讀工具，輸出 3–6 步執行計劃 |
| `context_engine.py` | `build_basic_context()` 將倉庫狀態格式化為 LLM 友好的上下文字串 |
| `session_store.py` | Session JSONL 的讀寫、摘要 Markdown 的儲存 |
| `session.py` | `RepoSession` 資料類別，保存 repo_path、branch、files、messages、session_id |
| `lc_tools.py` | 建構提供給 LangChain agent 的工具清單（read_file、search_code、git_diff、list_files、write_file） |
| `llm.py` | `build_llm()` 工廠，回傳 DeepSeek ChatDeepSeek 實例 |
| `tools.py` | 與 git 無關的 IO：解析路徑、讀檔、搜尋、寫檔、執行 shell 指令 |
| `repo_context.py` | 所有 `git` 子程序的薄包裝，並提供 `is_indexable_file` 過濾規則 |
| `display.py` | 所有 rich 終端輸出函式（面板、語法高亮、表格、檔案樹等） |
| `path.py` | 集中管理 `~/.repo_agent` 下的 history 與 project 目錄 |

---

## 核心流程

### 1. REPL 主迴圈

`cli.py` 中的 `main()` 使用 `prompt-toolkit` 啟動一個帶歷史記錄的 REPL：

- 輸入以 `/` 開頭 → 由 `handle_command()` 處理斜線指令
- 其他輸入 → 由 `handle_natural_language()` 送往 LLM agent 處理

### 2. 自然語言對話模式

任何不以 `/` 開頭的輸入，會被送往 `agent.py` 中的 `handle_user_task()`，由 LangChain agent 處理。代理可使用的工具包括：

- `read_file(path)` — 讀取檔案（支援唯一檔名解析）
- `search_code(query)` — 子字串搜尋
- `git_diff()` — 未暫存 diff
- `list_files()` — 列出所有已索引檔案
- `write_file(path, content)` — 寫入檔案（需使用者確認）

### 3. LangGraph 多代理管線（`/agent`）

`/agent <task>` 指令觸發一個三節點的 LangGraph DAG：

```
build_context  →  plan  →  act
```

- **build_context**：收集倉庫路徑、分支、檔案清單、git status 與 git diff
- **plan**：規劃代理使用唯讀工具產出 3–6 步執行計劃
- **act**：執行代理使用完整工具集完成實際操作

### 4. Session 管理

每次 `/open` 載入倉庫時自動建立 Session，事件以 JSONL 格式記錄在 `~/.repo_agent/<repo_hash>/sessions/` 下。支援 `/session-summary` 讓 LLM 生成結構化 Markdown 摘要。

---

## 目前變更摘要（Git Diff）

以下為目前未暫存的變更，涉及三個檔案：

### `repo_agent/lc_tools.py`

- `build_langchain_tools()` 新增 `include_write: bool = True` 參數
- 當 `include_write=False` 時，`write_file` 工具不會被加入工具清單
- 此變更讓呼叫端可以選擇是否暴露寫入能力

### `repo_agent/plan.py`

- 呼叫 `build_langchain_tools(repo_session, include_write=False)`
- 確保規劃代理（Planner Agent）只能使用唯讀工具，無法修改任何檔案
- 符合安全性原則：規劃階段不應寫入檔案

### `repo_agent/agent.py`

- `summarize_current_session()` 中呼叫 `build_langchain_tools(repo_session, include_write=False)`
- Session 摘要代理只需要讀取權限來檢查檔案，不應寫入
- 結尾新增換行符（EOF 修正）

**變更總結**：引入 `include_write` 參數，讓不同用途的 agent 可以精細控制是否暴露寫入工具，增強系統安全性。

---

## 安全性設計

- **寫入需確認**：`/write` 與 LLM 工具 `write_file` 都會先以語法高亮顯示預覽，並要求 `y/N` 確認後才會落盤
- **路徑沙箱**：寫入工具會檢查目標路徑是否仍在倉庫根目錄之內，逃逸路徑會被拒絕
- **不會自動提交**：所有 `git add` / `git commit` 都由使用者明確觸發
- **規劃代理唯讀**：`/agent` 管線中的 Plan 節點只能使用唯讀工具

---

## 開發狀態與下一步

### 已完成

- [x] REPL 主迴圈與所有斜線指令
- [x] 自然語言對話模式（LangChain agent）
- [x] LangGraph 多代理管線（build_context → plan → act）
- [x] Session 事件記錄與 Markdown 摘要
- [x] 提交訊息建議
- [x] 安全的檔案寫入（預覽 + 確認 + 路徑沙箱）
- [x] 規劃代理唯讀限制（`include_write=False`）

### 規劃中 / TODO

- [ ] 將 Session 歷史訊息餵給對話代理，支援跨 Session 上下文
- [ ] 在 LangGraph 管線中加入條件邊（Conditional Edge），支援動態調整步驟
- [ ] 為執行代理加入 `git status` / `stage` / `commit` 等工具，實現端到端提交流程
- [ ] 支援更多檔案類型的索引與二進位檔案偵測
- [ ] 加入向量嵌入式語意搜尋，取代純子字串搜尋

---

## 相依套件

| 套件 | 用途 |
| --- | --- |
| `prompt-toolkit >= 3.0.0` | REPL 輸入與歷史記錄 |
| `langchain >= 1.0.0` | Agent 框架 |
| `langchain-deepseek >= 1.0.0` | DeepSeek LLM 整合 |
| `langgraph` | 多代理圖執行管線 |
| `python-dotenv >= 1.0.0` | `.env` 環境變數載入 |
| `rich >= 13.0.0` | 終端富文本輸出 |

---

## 設定方式

1. 安裝依賴：`pip install -e .`
2. 在根目錄建立 `.env`：`DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx`
3. 啟動：`repo-agent`
4. 在 REPL 中使用 `/open <repo_path>` 載入倉庫
