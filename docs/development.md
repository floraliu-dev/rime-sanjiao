# 開發說明

給要修改這個專案的人。假設你會用 Git，但沒有開發過輸入法。

## 需要的工具

| 工具 | 用途 | 為什麼需要 |
|---|---|---|
| 終端機（macOS 內建「終端機」App） | 輸入指令 | 建置和測試都是用指令執行 |
| Git | 版本控制 | 記錄每次修改，並推上 GitHub |
| Python 3.10 以上 | 執行 `build.py` 和測試 | 產生碼表與鍵盤設定、跑自動測試。macOS 內建的 python3 是 3.9，太舊，要另外從 [python.org](https://www.python.org/downloads/) 安裝 |
| 文字編輯器（推薦 VS Code） | 修改檔案 | YAML 對縮排很敏感，要用能顯示空白的編輯器 |
| 倉輸入法（iPhone） | 實機測試 | 鍵盤外觀只能在手機上確認 |

不需要 Xcode、Apple 開發者帳號，也不需要伺服器。

## 第一次設定（每台電腦做一次）

```bash
git clone https://github.com/floraliu-dev/rime-sanjiao.git
cd rime-sanjiao

python3 -m venv .venv                  # 建立這個專案專用的 Python 環境
source .venv/bin/activate              # 啟用它（Windows：.venv\Scripts\activate）
pip install -r requirements-dev.txt    # 安裝測試用的套件
python -m tools.fetch_librime          # 下載官方 RIME 引擎（只放在 .cache/，不會安裝到系統）
```

為什麼要用 venv：讓這個專案用的套件和電腦上其他專案分開，彼此不會互相影響。之後每次打開新的終端機視窗，都要先 `source .venv/bin/activate`。

## 日常修改流程

```bash
# 1. 修改檔案（見下方「檔案地圖」）
# 2. 重新產生檔案
python build.py
# 3. 跑全部測試
python -m unittest discover -s tests -t . -v
# 4. 都通過了再提交
git add -A
git commit -m "說明這次改了什麼"
git push
```

推上 GitHub 後，GitHub Actions 會在 Linux、Windows、macOS 上再跑一次全部測試，結果在 repo 的「Actions」分頁。

## 檔案地圖

| 想改什麼 | 改哪裡 | 改完要做 |
|---|---|---|
| 輸入規則（連打、標點、空白鍵的行為） | `rime/sanjiao.schema.yaml` | 跑測試；如果行為變了，同時更新 `tests/test_rime.py` 和 `docs/design.md` |
| 候選排序規則 | `tools/ranking.py` | `python build.py`，跑測試 |
| 鍵盤配置 | `tools/keyboard.py` 的 `LAYOUT` | `python build.py`，跑測試，更新教學裡的鍵盤圖 |
| 碼表 | 照 `data/SOURCE.md` 的步驟 | |
| 安裝包內容 | `build.py` 的 `package()` | |

**不要手動修改**：`rime/sanjiao.dict.yaml`、`hamster/` 裡的檔案。它們是 `build.py` 產生的，下次建置會被覆蓋，測試也會檢查它們跟產生器的輸出是否一致。

## 在 Mac 上直接試打（選用）

自動測試已經用真正的 RIME 引擎驗證過輸入行為。如果想在 Mac 上親手試打：

1. 安裝 [鼠鬚管](https://rime.im/download/)（RIME 的 macOS 版，免費）。
2. 把 `rime/sanjiao.schema.yaml`、`rime/sanjiao.dict.yaml` 複製到 `~/Library/Rime/`。
3. 在 `~/Library/Rime/default.custom.yaml` 加上 `schema_list/@before 0`（見 `install-iphone.md`「已經有自訂設定的人」）。
4. 選單列的鼠鬚管圖示 →「重新部署」。

實體鍵盤上數字不能用來選字，請用空白鍵或方向鍵，原因見 `design.md`。

## 發布新版本

1. 決定版本號（[語意化版本](https://semver.org/lang/zh-TW/)）：修正錯誤 → 0.1.**1**；新增功能 → 0.**2**.0。
2. 更新三個地方的版本號，必須一致（測試會檢查）：
   - `VERSION`
   - `rime/sanjiao.schema.yaml` 的 `schema/version`
   - `CHANGELOG.md` 新增一段 `## 版本號`
3. `python build.py --package`，跑測試。
4. 在 iPhone 上照 `docs/device-test.md` 驗收。
5. 提交、打標籤、發布：

```bash
git commit -am "Release 0.1.0"
git tag v0.1.0
git push --follow-tags
gh release create v0.1.0 dist/rime-sanjiao-0.1.0-hamster.zip dist/rime-sanjiao-0.1.0-schema-only.zip \
  --title "0.1.0" --notes-file <(awk '/^## 0.1.0/{f=1; next} /^## /{f=0} f' CHANGELOG.md)
```

GitHub Releases 頁面上的下載次數，就是「有多少人下載」的數據來源。
