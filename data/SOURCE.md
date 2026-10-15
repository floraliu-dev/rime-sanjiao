# 碼表來源

`3corner.cin` 是從上游原封不動複製過來的，沒有做任何修改。

| 項目 | 內容 |
|---|---|
| 上游專案 | https://github.com/chinese-opendesktop/cin-tables |
| 檔案 | `3corner.cin` |
| 固定版本（commit） | `c19338255f2aac07b3e5eca4f4a8e8df30c2586b`（2020-07-24，這個檔案最後一次修改） |
| SHA-256 | `d5fa9e4f9cc21ed82020aec6dbba5f20a9629d5bc88f36d6bbfff1752581e019` |
| 授權 | Public Domain（檔頭註明）；上游專案整體標示 CC0-1.0 |
| 編碼規則 | 胡立人、張源渭、黃克東（美國王安電腦公司） |
| 資料依據 | 中國文字資料庫（CCDB），行政院文化建設委員會資訊應用國字整理小組；國家圖書館 UNICODE 工作小組 CI_UNI_V2.txt |

`build.py` 每次建置都會檢查 SHA-256。檔案內容只要被改動過，建置就會停下來，避免不小心用到不同版本的碼表。

## 更新碼表的步驟

1. 從上游下載新版 `3corner.cin`，覆蓋 `data/3corner.cin`。
2. 更新本檔的 commit 與 SHA-256，以及 `build.py` 裡的 `EXPECTED_SHA256`。
3. 執行 `python build.py`，再執行測試（見 `docs/development.md`）。
4. 在 `CHANGELOG.md` 記錄差異（新增或移除了多少字）。
