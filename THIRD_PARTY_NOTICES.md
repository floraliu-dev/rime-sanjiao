# 第三方資料與致謝

## 隨本專案發布的資料

### 三角編號碼表（`data/3corner.cin`，以及由它產生的 `rime/sanjiao.dict.yaml`）

- 來源：[chinese-opendesktop/cin-tables](https://github.com/chinese-opendesktop/cin-tables) 的 `3corner.cin`
- 授權：Public Domain（檔頭註明「授權方式: Public Domain」；上游專案整體標示 CC0-1.0）
- 編碼規則：胡立人、張源渭、黃克東（美國王安電腦公司）
- 資料依據：中國文字資料庫（CCDB），行政院文化建設委員會資訊應用國字整理小組；國家圖書館 UNICODE 工作小組 CI_UNI_V2.txt
- 格式整理：趙惟倫，2006

本專案沒有修改碼表內容，只轉換格式並加上排序權重。詳細版本見 `data/SOURCE.md`。

## 參考但沒有複製程式碼

- [SanJiaoIM](https://github.com/AllencxWang/SanJiaoIM)（MIT）：macOS 版三角編號輸入法。本專案參考了它的設計文件，包含輸入行為與「依 Big5 常用程度分層排序」的做法。
- [android-three-corner-ime](https://github.com/itemx/android-three-corner-ime)（MIT）：Android 版三角編號輸入法。
- [倉輸入法 Hamster](https://github.com/imfuxiao/Hamster)：自訂鍵盤的 YAML 格式依照其官方 wiki 與開源版本的原始碼。

## 只在測試時使用，不隨本專案發布

- [librime](https://github.com/rime/librime)（BSD-3-Clause）：RIME 輸入法引擎。自動測試會從官方 GitHub Releases 下載 1.17.0 版，用來驗證實際的輸入行為。
- [PyYAML](https://pyyaml.org/)（MIT）：測試時用來檢查 YAML 格式。
