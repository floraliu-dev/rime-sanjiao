# 自訂設定

RIME 用「補丁檔」修改方案：在使用者資料夾放一個 `sanjiao.custom.yaml`，裡面寫要改的設定，重新部署後生效。不需要修改原本的方案檔，之後更新三角編號時，你的設定也不會被蓋掉。

在倉輸入法裡，可以用「Wi-Fi 上传方案」或 iCloud 同步把檔案放進 `Rime` 資料夾，再點「RIME」→「重新部署」。

## 開啟字頻學習

讓選過的字下次排在前面。範例檔：[`examples/sanjiao.custom.yaml`](examples/sanjiao.custom.yaml)

```yaml
patch:
  translator/enable_user_dict: true
```

缺點：只要選過一次某個字，它就會排到最前面。之後按空格或連打時，送出的字可能和你習慣的不一樣。

## 唯一候選自動送出

打滿 6 碼而且只有一個候選字時，直接送出，不必按空格。大約 88% 的編碼只對應一個字。

```yaml
patch:
  speller/auto_select: true
```

缺點：打錯碼時，如果剛好也對應到某個字，會直接送出錯字。

## 兩個設定都要

同一個檔案裡只能有一個 `patch:`，把兩行放在一起：

```yaml
patch:
  translator/enable_user_dict: true
  speller/auto_select: true
```
