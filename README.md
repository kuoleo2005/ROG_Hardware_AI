# 電腦硬體 AI 顧問 

Windows 桌面硬體檢測、跑分估算、升級建議與 Gemini AI 顧問工具。

## 主要功能

- CPU / RAM / GPU / VRAM / 磁碟偵測
- 遊戲、生產力、AI、綜合評級
- 硬體能力雷達圖與瓶頸分析圖
- Gemini AI 顧問
- 黑色 / 白色主題
- 字體縮放與字重切換

## 安裝

```powershell
python -m pip install -U pip
pip install -r requirements.txt
```

## 執行

```powershell
python main.py
```

## Gemini API Key

建議不要把 API Key 寫入程式碼或上傳到 GitHub。

方式一：使用環境變數：

```powershell
setx GEMINI_API_KEY "你的_Gemini_API_Key"
```

設定後請重新開啟 PyCharm 或 Terminal。

方式二：建立檔案：

```powershell
New-Item -ItemType Directory -Force "$env:APPDATA\ROGHardwareAI"
Set-Content "$env:APPDATA\ROGHardwareAI\gemini_api_key.txt" "你的_Gemini_API_Key"
```

## 注意事項

- 查價功能目前暫停顯示。
- 硬體評分是估算，不等同實際跑分。
- PSU 瓦數一般無法由 Windows 可靠讀取，需查看電源本體標籤或購買紀錄。
