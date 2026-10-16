# 更新紀錄

格式參考 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)，版本號採用 [語意化版本](https://semver.org/lang/zh-TW/)。

## 0.1.1（2026-10-16）

輸入行為和 0.1.0 相同，不需要急著更新。

### 變更
- 安裝包檔名不再包含版本號：`rime-sanjiao-hamster.zip`、`rime-sanjiao-schema-only.zip`。下載連結 `releases/latest/download/rime-sanjiao-hamster.zip` 永遠指向最新版，存成書籤就能更新。
- 安裝教學新增「更新到新版」與新版通知的說明。

## 0.1.0（2026-10-16）

第一個版本。

### 新增
- 三角編號 RIME 方案 `sanjiao`：6 位數字編碼、打字時即時顯示候選、可省略結尾的 0、打滿 6 碼後直接連打。
- 碼表：chinese-opendesktop/cin-tables 的 `3corner.cin`，共 32,889 字（Public Domain）。
- 候選排序：Big5 常用字 → 次常用字 → 其他 → Unicode 擴充 B 區以後的罕用字；同一層維持原碼表順序。共 1,027 個編碼因此改由常用字排第一（例如 018660 的「高」）。
- 固定字序（預設不學習字頻），可另外開啟學習。
- 倉輸入法（Hamster）專用的三角數字鍵盤，含標點、符號鍵盤、英文鍵盤與切換輸入法鍵。
- 兩種安裝包：倉輸入法完整包、只有方案的通用包。
- 匯入後三角編號自動排在方案清單第一個（倉輸入法每次叫出鍵盤都用第一個方案）。
- 自動測試：碼表解析、碼表產生、鍵盤設定、安裝包，以及在 librime 1.17.0 上的實際輸入行為。
