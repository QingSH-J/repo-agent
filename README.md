# Repo Agent

一個運行在終端中的互動式程式碼倉庫助手。Repo Agent 既是一個 REPL 風格的 Git 工作流工具，也是一個由 LLM 驅動的編碼代理：你可以用斜線指令直接操作倉庫，也可以用自然語言讓代理替你閱讀、搜尋、修改檔案，並提交變更。

底層使用 [LangChain](https://www.langchain.com/) 的 `create_agent` + [DeepSeek](https://www.deepseek.com/) (`deepseek-chat`) 作為推理模型，使用 [`prompt-toolkit`](https://python-prompt-toolkit.readthedocs.io/) 提供帶歷史記錄的輸入體驗，並透過 [`rich`](https://rich.readthedocs.io/) 渲染彩色面板、語法高亮、表格與檔案樹。

---

## 功能特色

- **互動式 REPL**：帶歷史記錄與行編輯，啟動後可在同一個會話中切換多個倉庫。
- **倉庫上下文索引**：基於 `git ls-files` 建立檔案清單（自動跳過 `.git`、`.venv`、`__pycache__`、`*.egg-info`、`.env` 等）。
- **Git 工作流斜線指令**：`/diff`、`/git-status`、`/stage`、`/unstage`、`/commit-preview`、`/commit` 等。
- **自然語言代理**：未以 `/` 開頭的輸入會交由 LLM 處理，可自動呼叫工具完成多步驟任務。
- **安全的檔案寫入**：`/write` 與 `write_file` 工具均會先顯示語法高亮預覽，並要求使用者確認後才會落盤；寫入路徑會被限制在倉庫根目錄之內。
- **提交訊息建議**：`/commit-message` 會讓 LLM 讀取已暫存的 diff，並產出符合 Conventional Commit 風格的訊息。
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
| `REPO_AGENT_HOME` | `~/.repo_agent` | 存放 REPL 歷史與專案資料的目錄 |

---

## 快速開始

```bash
repo-agent
```

啟動後輸入 `/open <repo_path>` 載入一個 Git 倉庫，之後就可以使用所有指令或直接用自然語言提問：

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

---

## 斜線指令

| 指令 | 說明 |
| --- | --- |
| `/open <repo_path>` | 載入一個倉庫；會自動向上尋找 `.git` 根目錄 |
| `/status` | 顯示目前載入的倉庫、分支、檔案數、訊息數 |
| `/files` | 列出已索引的檔案（最多 40 個） |
| `/tree` | 以樹狀方式顯示倉庫檔案結構 |
| `/read <file_path>` | 讀取並語法高亮一個檔案；支援唯一檔名簡寫 |
| `/search <query>` | 在已索引檔案中做大小寫不敏感的子字串搜尋 |
| `/diff` | 顯示未暫存的 `git diff` |
| `/git-status` | 顯示 `git status --short` |
| `/stage <path>` | 暫存單一檔案（`git add`） |
| `/unstage <path>` | 取消暫存（`git restore --staged`） |
| `/commit-preview` | 顯示已暫存的 name-status 與 cached diff |
| `/commit-message` | 讓 LLM 根據已暫存 diff 產生 commit message |
| `/commit <message>` | 提交已暫存的變更 |
| `/write <path>` | 進入多行輸入模式寫入檔案（以 `---END---` 結束），會先預覽並要求確認 |
| `/run <command>` | 在倉庫根目錄執行一個 shell 指令並顯示結果 |
| `/refresh` | 重新建立倉庫的分支與檔案索引 |
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

代理的系統提示詞（[repo_agent/agent.py:9](repo_agent/agent.py#L9)）會引導模型先搜尋再讀檔、寫入時必須寫入完整內容、並在寫入成功後提醒使用者用 `/stage` 與 `/commit` 完成提交。

---

## 專案結構

```
repo-agent/
├── pyproject.toml              # 套件中繼資料與相依
├── repo_agent/
│   ├── __init__.py             # 早期 prototype CLI（已被 cli.py 取代）
│   ├── cli.py                  # REPL 主迴圈與所有斜線指令處理
│   ├── agent.py                # LangChain agent：handle_user_task / suggest_commit_message
│   ├── lc_tools.py             # 暴露給 LLM 的工具：read/search/list/diff/write
│   ├── llm.py                  # DeepSeek LLM 工廠
│   ├── tools.py                # 底層檔案 I/O 與 shell 執行
│   ├── repo_context.py         # 對 git 的所有薄包裝
│   ├── session.py              # RepoSession：保存 repo_path、branch、files、messages
│   ├── display.py              # 所有 rich 終端輸出
│   └── path.py                 # REPO_AGENT_HOME / history / project dir 計算
└── .env                        # DEEPSEEK_API_KEY
```

各檔案的職責：

- [repo_agent/cli.py](repo_agent/cli.py)：定義 `main()` 與 `handle_command()` / `handle_natural_language()`，是程式入口。
- [repo_agent/repo_context.py](repo_agent/repo_context.py)：所有 `git` 子程序的薄包裝，並提供 `is_indexable_file` 過濾規則。
- [repo_agent/tools.py](repo_agent/tools.py)：與 git 無關的 IO：解析使用者輸入的路徑、讀檔、搜尋、寫檔、執行 shell 指令。
- [repo_agent/agent.py](repo_agent/agent.py)：建立 LangChain agent，定義 `SYSTEM_PROMPT` 與 `COMMIT_AGENT_PROMPT`。
- [repo_agent/path.py](repo_agent/path.py)：集中管理 `~/.repo_agent` 下的 history 與 project 目錄。

---

## 安全性

- **寫入需確認**：`/write` 與 LLM 工具 `write_file` 都會先以語法高亮顯示預覽，並要求 `y/N` 確認後才會落盤。
- **路徑沙箱**：`write_repo_file` 與 `write_file` 工具會把目標路徑 `resolve()` 後檢查是否仍在倉庫根目錄之內，逃逸的路徑會被拒絕。
- **不會自動提交**：所有的 `git add` / `git commit` 都由使用者明確觸發；LLM 代理本身沒有提交工具。

---

## 開發

```bash
pip install -e .
repo-agent
```

歷史檔案位於 `~/.repo_agent/history`（或 `$REPO_AGENT_HOME/history`）。

如果要更換 LLM，可修改 [repo_agent/llm.py](repo_agent/llm.py) 中的 `build_llm()`，回傳任何相容於 LangChain `BaseChatModel` 的物件即可。

---

## 路線圖 / TODO

下列項目仍可進一步加強：

- 把訊息歷史持久化到 `RepoSession.message`，並餵給 agent，讓多輪自然語言對話可以維持上下文。
- 移除 [repo_agent/__init__.py](repo_agent/__init__.py) 中與 [repo_agent/cli.py](repo_agent/cli.py) 重複的 prototype 程式碼。
- 支援更多檔案類型的索引與二進位檔案的偵測。
- 為 agent 增加 `git status` / `stage` / `commit` 等工具，使其能端到端完成提交流程（同時保留使用者確認）。
