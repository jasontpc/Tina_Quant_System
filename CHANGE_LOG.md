# Tina 系統修改紀錄（Change Log）

> 每次修改建立紀錄，預防重蹈覆轍

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

## 🔧 Streamlit Cloud 開發標準（2026-05-07 實戰經驗）

> 從 Bug #1~#6 整理出的 Streamlit Cloud 開發規範，
> 所有 Tina 系統成員務必遵守。

---

### ⚠️ Streamlit Cloud 專屬警告

**Streamlit Cloud 的 `st.secrets` 行為與本地完全不同：**

| 現象 | 本地 | Streamlit Cloud |
|:-----|:-----|:---------------|
| TOML `[tg_chat_id]` 區段 | `dict` 直接取值 | `AttrDict`（Streamlit 自定義 dict 子類）|
| `isinstance(x, dict)` | ✅ | ✅ 回 `True`（繼承關係）|
| `list(dict.values())[0]` | value | **完整 dict**（行為不同！）|
| `.get('key')` | ✅ | ✅ 可用 |
| `hasattr(x, 'attr')` | ✅ | ✅ **最可靠的訪問方式** |
| dict-string repr | 無 | 可能出現 `"{'key': 'value'}"` |

**核心原則：不要只靠 `isinstance()` + `.get()`，一定要加上 `hasattr()` 屬性訪問。**

---

### 🔒 Streamlit Cloud 部署防呆檢查表

每次部署 Streamlit Cloud 前，確認以下 9 點：

```
□ 1. st.secrets 讀取是否果斷用已知值 fallback（不要只靠 parsing）
□ 2. 是否用 hasattr(raw, 'get') 檢測 AttrDict
□ 3. chat_id 確認是純數字字串（isdigit() == True）
□ 4. token 長度確認 >= 20 且包含 ':'
□ 5. 所有 API URL build 前是否做 URL-safe check
□ 6. 本地 python -m py_compile 無錯誤
□ 7. commit message 清楚描述改什麼 + 為什麼
□ 8. Change Log 已建立草稿（即使是 hotfix）
□ 9. 部署後通知 Jo 測試（TW/US 各一筆）
```

---

### 📐 修改流程規範（強制執行）

**每次修改 → 必定建立 Change Log 條目**（不管大小）

#### Standard Flow（非緊急）

```
收到問題 / 功能需求
    ↓
Step 1：建立 Change Log 草稿（ copy 格式）
    ├─ 填入「問題」和「初步假說」
    └─ commit: 留空，修完再填
    ↓
Step 2：本地語法檢查 → python -m py_compile <file>.py
    ↓
Step 3：找到根本原因（問：為什麼壊？哪一層壊的？）
    ↓
Step 4：實作修復 + 預防復發措施
    ↓
Step 5：本地驗證 → 執行相關腳本確認不報錯
    ↓
Step 6：commit + 填 Change Log
    ↓
Step 7：git push
    ↓
Step 8：通知 Jo 測試（明確說「測試範圍」+「預期結果」）
    ↓
Step 9：觀察 → Jo 回報正常 → 關閉 🔜→✅
         └─ Jo 回報新問題 → 回到 Step 1
```

#### Emergency Flow（P0 功能完全壊掉）

```
Step 1：直接修補（不用先寫草稿）
Step 2：修完馬上 commit + push
Step 3：事後補寫 Change Log（最慢 24h 內補完）
Step 4：加入「預防復發」措施
```

---

### st.secrets 讀取標準（Bug #1~#6 血淚經驗）

**所有 `st.secrets` 讀取都必須遵守以下 pattern：**

```python
# 已知正確值，直接寫死當最終 fallback
_KNOWN_CHAT_ID = '1616824689'
_KNOWN_BOT_TOKEN = '8614615741:AAHEMV6daIzF6J_MFUAm8KkhJYtOGVOM14Q'

def _try_get_chat_id():
    try:
        raw = st.secrets.get('tg_chat_id', st.secrets.get('chat_id', None))
        if raw is None:
            return _KNOWN_CHAT_ID
        # AttrDict/dict → 用 hasattr 檢測
        if hasattr(raw, 'get'):
            v = raw.get('chat_id') or raw.get('tg_chat_id') or raw.get('value')
            if isinstance(v, str) and v.isdigit():
                return v
            # 屬性訪問（AttrDict 特有）
            if hasattr(raw, 'tg_chat_id') and str(raw.tg_chat_id).isdigit():
                return str(raw.tg_chat_id)
        # 字串 → 檢查是否為 dict-string repr
        if isinstance(raw, str) and raw.startswith('{'):
            import json
            try:
                parsed = json.loads(raw.replace("'", '"'))
                v = parsed.get('chat_id') or parsed.get('tg_chat_id')
                if isinstance(v, str) and v.isdigit():
                    return v
            except:
                pass
        # 都失敗 → regex 最後萃取
        import re
        m = re.search(r'(\d{7,15})', str(raw))
        if m:
            return m.group(1)
        return _KNOWN_CHAT_ID
    except:
        return _KNOWN_CHAT_ID  # 任何失敗果斷用已知值
```

**預防復發要點：**
- ✅ 任何 `st.secrets` 回傳值，最後都要經過 `isdigit()` 驗證
- ✅ 都失敗果斷用 `_KNOWN_*` 寫死值，不要留空
- ✅ 每年更新一次 `_KNOWN_*` 值（更換密鑰時）

---

### commit message 格式標準

```
[type]: [short description] (#[issue])
[type]：fix / feat / opt / refactor / security / docs / chore
```

**好範例：**
```
fix: _try_get_chat_id handles AttrDict on Streamlit Cloud (Bug #6)
feat: add sandbox phase to Full Think mode
refactor: archive nana_v2~v67 to archive/old/
```

**壞範例：**
```
fix bug / update file / small fix
```

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
| 測試驗證 | 🔜 | Jo 確認正常後標 ✅ |

### Change Log 追蹤狀態標記

| 標記 | 意思 |
|:----:|:-----|
| 🔜 | 待 Jo 確認 / 待測試 |
| ✅ | 已驗證正常 |
| ❌ | 驗證失敗，需重新修 |
| 📌 | 長期追蹤觀察 |

---

## 📂 Bug / Feature 修改紀錄

### Bug #1（2026-05-07 16:20）— chat_id 變成 dict

| 欄位 | 內容 |
|:-----|:-----|
| **日期** | 2026-05-07 16:20 |
| **檔案** | `streamlit_tw_stock.py` |
| **commit** | `c6214ae` |
| **類型** | BUG |
| **優先** | P0緊急 |
| **狀態** | ✅ 已修復 |

**問題：**
```
DEBUG chat_id={'tg_chat_id': '1616824689'} token_len=1
HTTP 400: Bad Request: chat not found
```

**對策：** `_validate_chat_id()` unwrap dict

**預防復發：** ✅ 所有 module-level secrets 都經過 `_validate_*` 函式

---

### Bug #2（2026-05-07 16:25）— token_len=1 截斷

| 欄位 | 內容 |
|:-----|:-----|
| **日期** | 2026-05-07 16:25 |
| **commit** | `470017f` |
| **狀態** | ✅ 已修復 |

**問題：** Token 被截斷成 1 字元

**對策：** `_validate_token()` 長度檢查（< 20 字元 → fallback）

---

### Bug #3（2026-05-07 16:33）— `_get_secret()` 反而造成 dict 包裝

| 欄位 | 內容 |
|:-----|:-----|
| **commit** | `8738c02` |
| **狀態** | ✅ 已修復 |

**對策：** 繞過 `_get_secret()`，直接用 `st.secrets.get()` unwrap

---

### Bug #4（2026-05-07 17:50）— Token 變成 dict-string repr

| 欄位 | 內容 |
|:-----|:-----|
| **commit** | `604b2d6` |
| **狀態** | ✅ 已修復 |

**問題：** `"/bot{'tg_bot_token': '...'}/sendMessage"`

**對策：** `push_telegram()` 內 regex extraction `([0-9]+:[A-Za-z0-9_-]{30,})`

---

### Bug #5（2026-05-07 18:40）— `telegram:` 前綴造成 chat not found

| 欄位 | 內容 |
|:-----|:-----|
| **commit** | `cd7c100` |
| **狀態** | ✅ 已修復 |

**問題：** `chat_id='telegram:1616824689'` → HTTP 400

**對策：** prefix strip `raw.replace('telegram:', '').replace('tg_', '')`

---

### Bug #6（2026-05-07 20:50—21:02）— Streamlit Cloud AttrDict ✅ 已修復

| 欄位 | 內容 |
|:-----|:-----|
| **commit** | `e32eb80` |
| **狀態** | ✅ 已修復並驗證（Jo 確認成功）|

**問題：**
```
MODULE DEBUG _raw_chat={'tg_chat_id': '1616824689'} type=AttrDict
HTTP 400: Bad Request: chat not found
```

**根本原因：** Streamlit Cloud 的 `st.secrets` 返回 `AttrDict`（dict 子類），`list(AttrDict.values())[0]` 取出的是完整 dict，不是 value。

**最終修復架構：**
```python
if hasattr(raw, 'get'):       # ← AttrDict 檢測（不是只靠 isinstance(dict)）
    v = raw.get('tg_chat_id')
    if isinstance(v, str) and v.isdigit(): return v
    if hasattr(raw, 'tg_chat_id') and str(raw.tg_chat_id).isdigit(): return str(raw.tg_chat_id)
```

---

_Last updated: 2026-05-07 21:06_
