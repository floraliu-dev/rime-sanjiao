# 三角編號輸入法 for iPhone（RIME 方案）

在 iPhone 上用**三角編號**打中文。免費、開源，裝在免費的「倉輸入法」App 裡使用。

> **狀態：0.1.0**。輸入行為已經用官方 RIME 引擎自動測試過，並通過 iPhone 實機驗收。

## 為什麼做這個

三角編號是由王安電腦的胡立人、張源渭、黃克東提出的數字輸入法，每個字用 6 位數字表示。電腦上有現成的三角編號輸入法，但 iPhone 上一直沒有。

這個專案把三角編號做成 [RIME](https://rime.im/) 輸入法方案。RIME 是一套開源的輸入法引擎，iPhone 上的「倉輸入法」就是用它做的。所以不需要另外上架 App，就能在 iPhone 上使用。

## 安裝

👉 **[iPhone 安裝教學](docs/install-iphone.md)**（約 5 分鐘）

也可以用在其他 RIME 輸入法上：Mac 的鼠鬚管、Windows 的小狼毫。下載 `schema-only` 安裝包即可。

## 怎麼打

```
符號   1   2   3   ⌫
ABC    4   5   6   ，
🌐     7   8   9   。
？     、  0   空格 換行
```

- 每個字 6 位數字，例如「三」是 `101010`、「我」是 `305354`。
- 打字時就會顯示候選字，點一下就能輸入；或按「空格」選第一個。
- 編碼結尾的 0 可以省略：「二」`101000` 只要打 `101`。
- 打滿 6 碼後直接打下一個字，前一個字會自動送出。
- 候選順序固定，常用字在前。

完整的規則和設計理由見 [設計說明](docs/design.md)。

## 文件

| 文件 | 內容 |
|---|---|
| [iPhone 安裝教學](docs/install-iphone.md) | 一般使用者看這份就好 |
| [自訂設定](docs/customize.md) | 開啟字頻學習、唯一候選自動送出 |
| [設計說明](docs/design.md) | 每個設計決定和理由 |
| [開發說明](docs/development.md) | 要修改專案的人：工具、流程、發布 |
| [實機驗收清單](docs/device-test.md) | 發布前在 iPhone 上逐項檢查 |
| [更新紀錄](CHANGELOG.md) | 每個版本改了什麼 |

## 授權與致謝

- 方案設定與程式：[MIT](LICENSE)
- 碼表：Public Domain，來自 [chinese-opendesktop/cin-tables](https://github.com/chinese-opendesktop/cin-tables)
- 編碼規則：胡立人、張源渭、黃克東（美國王安電腦公司）
- 參考：[SanJiaoIM](https://github.com/AllencxWang/SanJiaoIM)（macOS 版）、[倉輸入法](https://github.com/imfuxiao/Hamster)

詳見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

---

## English

**Three-Corner Code (三角編號) input method for iPhone**, packaged as a [RIME](https://rime.im/) schema that runs inside the free [Hamster (倉輸入法)](https://apps.apple.com/app/id6446617683) keyboard app. Each character is a 6-digit code. Includes a custom numeric touch keyboard, frequency-layered candidate ranking (common Big5 characters first), and an automated test suite that drives the official librime 1.17.0 engine key by key. Schema and tooling are MIT; the code table is public domain.
