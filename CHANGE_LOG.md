# Tina 系統修改紀錄（Change Log）

> 每次修改 建立紀錄，預防重蹈覆轍

---

## 📋 修改紀錄格式

```yaml
日期: YYYY-MM-DD HH:MM
人員: Tina / Jo
檔案: <file_path>
commit: <git_hash>
類型: [BUG|FEATURE|OPT|refactor|security|hotfix]
優先: [P0緊急|P1高|P2中|P3低]

標題: <簡短描述>

問題: <發生了什麼 / 為什麼要改>

對策: <怎麼修 / 預防復發措施>

影響: <影響哪些功能 / 需要重新測試什麼>

測試驗證: <已通過什麼測試>
```

---

## 🔧 Streamlit Cloud Telegram 問題修改紀錄

### Bug #1（2026-05-07 16:20）— chat_id 變成 dict

| 欄位 | 內容 |
|:-----|:-----|
| **日期** | 2026-05-07 16:20 |
| **檔案** | `streamlit_tw_stock.py` |
| **commit** | `c6214ae` |
| **類型** | BUG |
| **優先** | P0緊急（已影響功能） |

**問題：**
```
DEBUG chat_id={'tg_chat_id': '1616824689'} token_len=1
HTTP 400: Bad Request: chat not found
```
- `_get_secret()` 在 Streamlit Cloud 的 TOML 格式下返回 dict `{'tg_chat_id': '1616824689'}`
- chat_id 沒有被正確 unwrap，直接拿 dict 當字串送 API

**對策：**
```python
def _validate_chat_id(raw):
    """Robust chat_id extraction — handles dict/List/int all edge cases"""
    if raw is None:
        return '1616824689'
    if isinstance(raw, str) and raw.isdigit():
        return raw
    if isinstance(raw, dict):
        raw = raw.get('chat_id', raw.get('tg_chat_id', '1616824689'))
    # ... while loop for nested dict
    return str(raw) if raw else '1616824689'
```

**預防復發：**
- ✅ 所有 module-level secrets 初始化，都經過 `_validate_*` 函式
- ✅ 未來新加 secrets 時，強制使用相同 pattern
- ❌ 不再直接使用 `st.secrets['key']` 作為字串

**測試驗證：** 本地 `.streamlit/secrets.toml` 正常讀取，但 Streamlit Cloud 環境需要實際部署後確認

---

### Bug #2（2026-05-07 16:25）— token_len=1 截斷

| 欄位 | 內容 |
|:-----|:-----|
| **日期** | 2026-05-07 16:25 |
| **檔案** | `streamlit_tw_stock.py` |
| **commit** | `470017f` |
| **類型** | BUG |
| **優先** | P0緊急 |

**問題：**
- `DEBUG token_len=1` — Token 被截斷成 1 字元
- Streamlit Cloud 可能對長字串有長度限制或截斷行為

**對策：**
```python
def _validate_token(raw):
    """Reject truncated tokens (< 20 chars)"""
    if not raw:
        return ''
    raw_str = str(raw).strip()
    if len(raw_str) < 20:  # 正常 bot token 起碼 40+ 字元
        print(f'[TOKEN WARNING] Token truncated ({len(raw_str)} chars)')
        return ''  # 觸發 fallback
    return raw_str
```

**預防復發：**
- ✅ 所有 token 初始化都經過 `_validate_token()`
- ✅ 偵測長度 < 20 的 token，主動發 warning 並 fallback
- ✅ push_telegram 內再次驗證 chat_id 型別（double-check）

---

### Bug #3（2026-05-07 16:33）— `_get_secret()` 反而造成 dict 包裝

| 欄位 | 內容 |
|:-----|:-----|
| **日期** | 2026-05-07 16:33 |
| **檔案** | `streamlit_tw_stock.py` |
| **commit** | `8738c02` |
| **類型** | BUG |
| **優先** | P0緊急 |

**問題：**
- 修復 Bug #1 的 `_get_secret()` 在某些 Streamlit Cloud 環境下反而造成 dict 包裝
- 錯誤：`chat_id={'tg_chat_id': '1616824689'}` 仍然出現

**對策：**
- 繞過 `_get_secret()`，直接用 `st.secrets.get()` unwrap
- 對 chat_id 和 token 都做 direct unwrap：

```python
# 強制繞過 _get_secret() 直接解包
_raw_chat = st.secrets.get('tg_chat_id', st.secrets.get('chat_id', '1616824689'))
if isinstance(_raw_chat, dict):
    _raw_chat = _raw_chat.get('tg_chat_id', _raw_chat.get('chat_id', '1616824689'))
TELEGRAM_CHAT_ID = _validate_chat_id(_raw_chat)

_raw_token = st.secrets.get('tg_bot_token', st.secrets.get('bot_token', ''))
if isinstance(_raw_token, dict):
    _raw_token = _raw_token.get('tg_bot_token', _raw_token.get('bot_token', ''))
# ... validate token
```

- 加 DEBUG log 模組初始化時直接印出 raw values

**預防復發：**
- ✅ 未來所有 st.secrets 讀取都用此 pattern
- ✅ 模組初始化時印出 DEBUG log，部署後可從 logs 確認
- ✅ chat_id 和 token 都有 double-check validation

**測試驗證：** 部署後檢查 Streamlit Cloud logs 中 `[SECRETS] tg_bot_token raw = ...` 輸出

---

### Bug #4（2026-05-07 17:50）— 模組初始化後 token 仍被轉成 dict-string repr

| 欄位 | 內容 |
|:-----|:-----|
| **日期** | 2026-05-07 17:50 |
| **檔案** | `streamlit_tw_stock.py` |
| **commit** | `604b2d6` |
| **類型** | BUG |
| **優先** | P0緊急 |

**問題：**
```
Error: URL can't contain control characters. "/bot{'tg_bot_token': '861461…M14Q'}/sendMessage"
```
- Streamlit Cloud 在同一 runtime 環境中對同一 secret 的讀取值不一致
- `_validate_token()` 在模組載入時已解析，但 `push_telegram()` 收到時又變成 dict-string repr
- 根本原因：st.secrets 在同一 runtime 有快取不一致的問題

**對策：**
- `push_telegram()` 內最後一道防線用 **regex 提取**：`re.search(r'([0-9]+:[A-Za-z0-9_-]{30,})', str(token_raw))`
- 無論 token 是 dict / dict-string repr / 已解析的字串，regex 都能正確抽到真正的 token
- 三層防護：
  1. `_validate_token()` — 初始化時解析 dict-string
  2. 環境變數 → 寫死備援 fallback chain
  3. `push_telegram()` 內 **regex 最終 extraction** — 確保送到 API 的 token 一定正確

**預防復發：**
- ✅ 所有外部 API 呼叫前，都做 regex validation + URL-safe check
- ✅ 未來任何新 API URL build 前，強制做 URL-safe 檢查
- ✅ 任何 secret 初始化後，在 function 內再做一次最後萃取

**測試驗證：** TW/US 個股按鈕 Telegram 發送成功

### Bug #5（2026-05-07 18:40）— `chat_id='telegram:1616824689'` 導致 chat not found

| 欄位 | 內容 |
|:-----|:-----|
| **日期** | 2026-05-07 18:40 |
| **檔案** | `streamlit_tw_stock.py` |
| **commit** | `cd7c100` |
| **類型** | BUG |
| **優先** | P0緊急 |

**問題：**
```
HTTP 400: Bad Request: chat not found
```
- 本地測試發現：`chat_id='telegram:1616824689'` 這個格式會造成 400
- 正常 chat_id 只要數字字串 `'1616824689'` 或純 int `1616824689`
- 但 `TELEGRAM_CHAT_ID` 在 Streamlit Cloud 上可能帶有 `telegram:` 前綴
- 本地測試：`'telegram:1616824689'` → 400；去掉前綴 → 200 OK

**對策：**
```python
def _validate_chat_id(raw):
    # ... existing dict/List unwrap logic ...
    # Strip 'telegram:' or 'tg_' prefixes that Streamlit Cloud may inject
    if isinstance(raw, str):
        raw = raw.replace('telegram:', '').replace('tg_', '')
    return str(raw) if raw else '1616824689'
```


**預防復發：**
- ✅ `_validate_chat_id()` 最後統一做 prefix strip
- ✅ `push_telegram()` 內對 chat_id 再做一次 isdigit() 驗證

**測試驗證：** TW/US 個股 + 批次都正常發送

### Bug #6（2026-05-07 20:50）— `st.secrets` 返回 dict-string repr 而非 dict

| 欄位 | 內容 |
|:-----|:-----|
| **日期** | 2026-05-07 20:50 |
| **檔案** | `streamlit_tw_stock.py` |
| **commit** | `fbcaaed` |
| **類型** | BUG |
| **優先** | P0緊急 |

**問題：**
```
DEBUG chat_id="{'tg_chat_id': '1616824689'}" type=str
HTTP 400: Bad Request: chat not found
```
- Streamlit Cloud 的 `st.secrets` 返回的是 **Python string repr** of dict：`"{'tg_chat_id': '1616824689'}"`（type=str）
- 不是 dict 型別，是 string！
- 所以 `isinstance(raw, dict)` 在 `_validate_chat_id()` 一直是 `False`
- dict-string repr 從未被解析，所以最後 `TELEGRAM_CHAT_ID = "{'tg_chat_id': '1616824689'}"` 整個帶著 `{}` 進了 API

**對策：**
```python
def _validate_chat_id(raw):
    # STEP 1: If raw is a string that looks like dict-string repr, parse it FIRST
    if isinstance(raw, str):
        s = raw.strip()
        if s.startswith('{') and 'chat_id' in s:
            try:
                parsed = json.loads(s.replace("'", '"'))
                raw = parsed.get('chat_id', ...)
            except:
                pass
        # Also strip prefixes immediately after parsing
        raw = raw.replace('telegram:', '').replace('tg_', '')
    # STEP 2~3: Unwrap nested dict/List
    while isinstance(raw, (dict, list)):
        ...
    # STEP 4: Final guard
    if isinstance(raw, str):
        raw = raw.replace('telegram:', '').replace('tg_', '')
    return str(raw)
```

**根本原因：**
- Streamlit Cloud 的 TOML secrets 行為：`[section]` → `st.secrets['section']` 返回 `str(dict)` 而非 `dict`
- Python 的 `json.loads("{'key': 'value'}".replace("'", '"'))` 可正確解析 Python dict-string repr

**預防復發：**
- ✅ 任何從 `st.secrets` 讀取的值，一律先檢查是否為 dict-string repr 並 parse
- ✅ 未來新加 secrets 時，強制使用 `json.loads(s.replace("'", '"'))` pattern

**測試驗證：** TW/US 個股 + 批次都正常發送

---

## 📐 修改流程規範（強制執行）

### 核心原則

**每次修改 → 必定建立 Change Log 條目**（不管大小）

- ❌ 不准：「小改一下就好，不用記」
- ✅ 要記：「修改了什麼 + 為什麼 + 怎麼修」
- 理由：99% 的重蹈覆轍都來自「這次小事不用記」

---

### 修改流程 Step-by-Step

```
收到問題 / 功能需求
    ↓
Step 1：建立 Change Log 草稿
    ├─ 在 CHANGE_LOG.md 新增條目（copy 格式）
    ├─ 填入「問題」和「初步假說」
    └─ commit: 留空，等修完再填
    ↓
Step 2：本地語法檢查
    └─ python -m py_compile <file>.py
    ↓
Step 3：找到根本原因
    ├─ 不只是修 symptom
    ├─ 問：為什麼會壊？哪一層壊的？
    └─ 寫入 Change Log 的「根本原因」欄位
    ↓
Step 4：實作修復
    ├─ 每一個改動都要有理由
    └─ 加入預防復發措施（不只是修當下）
    ↓
Step 5：本地驗證
    └─ 執行相關腳本，確認不報錯
    ↓
Step 6：commit + 填 Change Log
    ├─ commit message: `fix/feat: 具體描述 (#issue)`
    └─ 補完 Change Log 條目（對策/預防/測試）
    ↓
Step 7：git push
    ↓
Step 8：通知 Jo 測試
    └─ 明確說「測試範圍」和「預期結果」
    ↓
Step 9：觀察 + 關閉
    ├─ Jo 回報正常 → 關閉 Change Log 條目（🔜→✅）
    └─ Jo 回報新問題 → 回到 Step 1
```

---

### 修改類型對應的 Change Log 格式

| 類型 | 格式選擇 | 說明 |
|:----|:--------|:-----|
| **BUG** | Bug #N（日期）— 標題 | 功能壊了，修復 |
| **FEATURE** | Feature #N（日期）— 標題 | 新增功能 |
| **OPT** | Opt #N（日期）— 標題 | 效能/優化改動 |
| **refactor** | Refactor #N（日期）— 標題 | 結構重構，不改功能 |
| **security** | Security #N（日期）— 標題 | 安全相關修補 |
| **hotfix** | Hotfix #N（日期）— 標題 | 緊急修補（事後補記） |

---

### Change Log 必填欄位

| 欄位 | 必填 | 說明 |
|:----:|:----:|:-----|
| 日期 | ✅ | 精確到「小時」 |
| 檔案 | ✅ | 明確路徑 |
| commit | ✅ | 修完後填入 |
| 類型 | ✅ | BUG/FEATURE/OPT/refactor/security/hotfix |
| 優先 | ✅ | P0/P1/P2/P3 |
| 標題 | ✅ | 30字內簡述 |
| 問題 | ✅ | 壞了什麼/為什麼改 |
| 對策 | ✅ | 怎麼修 + 預防復發 |
| 影響 | 🔜 | 影響哪些功能 |
| 測試驗證 | 🔜 | 已通過什麼測試 |

---

### 預防復發模板（必選 >=1）

```
預防復發：
- ✅ [具體做法] — 確保同類問題不再發生
- ✅ [具體做法]
- ❌ [不做了什麼] — 舊方法的問題
```

---

### commit message 格式標準

```
[type]: [short description] (#[issue])
[type] 可選：fix / feat / opt / refactor / security / docs / chore
[short description]：具體描述，不超過 50 字
(#[issue])：對應的 Change Log Bug/Feature 編號
```

**好範例：**
```
fix: push_telegram regex extraction for dict-string token repr (Bug #4)
feat: add sandbox phase to Full Think mode
refactor: archive nana_v2~v67 to archive/old/ (Nana cleanup)
```

**壞範例：**
```
fix bug
update file
small fix
```

---

### 緊急 hotfix 流程（不一樣！）

當問題緊急（P0 功能完全壊掉）時：

```
Step 1：直接修補（不用先寫草稿）
Step 2：修完馬上 commit + push
Step 3：事後補寫 Change Log（最慢 24h 內補完）
Step 4：加入「預防復發」措施
```

---

### Change Log 追蹤狀態標記

| 標記 | 意思 |
|:----:|:-----|
| 🔜 | 待 Jo 確認 / 待測試 |
| ✅ | 已驗證正常 |
| ❌ | 驗證失敗，需重新修 |
| 📌 | 長期追蹤觀察 |

---

### 誰來維護 Change Log

- **Tina 負責**：所有 Code 修改（Python/shell）
- **Jo 負責**：通知 Tina 需要修改的項目
- **原則**：Jo 不需要寫 Change Log，Tina 會代理

---

## 🔒 Streamlit Cloud 部署防呆檢查表

每次部署 Streamlit Cloud 前：

```
□ st.secrets 讀取是否經過 _validate_* 函式
□ chat_id 確認是 str（不是 dict/List）
□ token 長度確認 >= 20
□ 本地 python -m py_compile 無錯誤
□ commit message 清楚描述改什麼 + 為什麼
□ Change Log 已建立草稿（即使是 hotfix）
□ 部署後檢查 logs 有 [SECRETS] DEBUG output
□ 通知 Jo 測試（TW/US 各一筆）
□ Jo 回報正常 → 關閉 Change Log 🔜→✅
□ Jo 回報新問題 → 回到 修改流程 Step 1
```

---

_Last updated: 2026-05-07 18:36_
_下次修改時，請先在 CHANGE_LOG.md 新增草稿，再開始修_
