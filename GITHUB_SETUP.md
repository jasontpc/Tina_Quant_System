# GitHub 初始化指南

## 快速開始

### 1. 安裝 Git (如尚未安裝)

前往 https://git-scm.com/download/win 下載並安裝。

### 2. 執行初始化腳本

```bash
cd Tina_Quant_System
.\setup_git.bat
```

### 3. 在 GitHub 建立 Repo

1. 前往 https://github.com/new
2. Repository name: `Tina_Quant_System`
3. 選擇 **Private** (私人)
4. 點擊 Create repository

### 4. 連接本地與 GitHub

```bash
cd Tina_Quant_System
git remote add origin https://github.com/YOUR_USERNAME/Tina_Quant_System.git
git push -u origin main
```

## 未來提交更新

```bash
git add .
git commit -m "描述你的更改"
git push
```

## 分支開發 (建議)

```bash
# 創建新分支
git checkout -b feature/v3_13

# 在新分支開發
git add .
git commit -m "v3.13 新策略"

# 合併回主分支
git checkout main
git merge feature/v3_13
git push
```

## Gitignore 已經設定

以下檔案不會被提交：
- `*.db` (資料庫)
- `__pycache__/` (Python 緩存)
- `venv/` (虛擬環境)

## 團隊協作

| 角色 | Git 操作 |
|:-----|:---------|
| Architect | `git merge` 審核 |
| Quant | `git checkout -b` 開發新功能 |
| SRE | `git push` 維護版本 |
