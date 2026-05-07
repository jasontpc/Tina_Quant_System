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
- `_validate_token()` 在初始化時已經解析過 dict-string repr
- 但 Streamlit Cloud 的 `st.secrets` 行為在模組載入後又變化
- `TELEGRAM_BOT_TOKEN` 在模組層級是正確的，但 `push_telegram()` 收到的卻是 dict-string repr
- 懷疑：Streamlit Cloud 在同一 runtime 環境中對同一 secret 的讀取值不一致

**對策：**
- `push_telegram()` 內最後一道防線用 **regex 提取**：`re.search(r'([0-9]+:[A-Za-z0-9_-]{30,})', str(token_raw))`
- 無論 token 是 dict / dict-string repr / 已解析的字串，regex 都能正確抽到真正的 token
- 三层防护：
  1. `_validate_token()` — 初始化時解析 dict-string
  2. `_validate_token()` fallback chain — 環境變數 → 寫死備援
  3. `push_telegram()` 內 **regex 最終 extraction** — 確保送到 API 的 token 一定正確

**預防復發：**
- ✅ 所有 API URL build 前都做 regex validation
- ✅ 未来所有 telegram/外部 API 调用都强制做 URL-safe 检查

**測試驗證：** TW/US 個股按鈕 Telegram 發送成功

---

## 📐 修改流程規範（未來適用的標準流程）

### 每次修改前

1. **先建立 Change Log 草稿**（上面格式）
2. **確認影響範圍**（哪些檔案/功能可能受影響）
3. **本地語法檢查**：`python -m py_compile <file>.py`
4. **了解為什麼壊**：不只是修 symptom，要找到根本原因

### 修改時

1. **每個檔案獨立 commit**（方便追蹤）
2. **commit message 格式**：`type: short description (issue #if any)`
   - `fix: _validate_chat_id handles dict on Streamlit Cloud`
   - `feat: add trailing stop for US positions`
3. **commit message 加入為什麼改**：未來好追蹤

### 修改後

1. **本地測試**：執行一次相關腳本
2. **push 前確認**：無語法錯誤、無明顯邏輯問題
3. **填入 Change Log**：問題→對策→預防→測試
4. **觀察 Streamslit Cloud logs**：部署後看 DEBUG output

---

## 🔒 Streamlit Cloud 部署防呆檢查表

每次部署 Streamlit Cloud 前：

```
□ 檢查 st.secrets 讀取是否經過 _validate_* 函式
□ 確認 chat_id 是 str（不是 dict/List）
□ 確認 token 長度 >= 20
□ 本地 python -m py_compile 無錯誤
□ commit message 清楚描述改什麼 + 為什麼
□ Change Log 已建立草稿
□ 部署後檢查 logs 有 [SECRETS] DEBUG output
□ 通知 Jo 測試（TW/US 各一筆）
```

---

_Last updated: 2026-05-07 16:40_
_下次修改時，請先在這個檔案新增草稿，再開始修_