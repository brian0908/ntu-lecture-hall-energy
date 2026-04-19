# 臺大教學館節能規劃 — 冷氣過冷耗電量估算

**課程：** 環境與能源的資料科學  
**角色扮演：** 能源數據顧問公司，向台大校方提案  
**核心分析：** 估算台大各講堂因冷氣設定溫度低於標準（26°C）所造成的超額耗電量，並推估節能潛力

---

## 資料說明

`data/` 資料夾包含台大各講堂的每小時用電數據（2016–2025）：

| 資料夾名稱 | 說明 |
|---|---|
| `普通高壓空調` | 普通講堂**冷氣專用電表**（唯一的冷氣直接量測數據）|
| `共同教室` | 共同講堂總用電 |
| `博雅館一 / 二 / 三 / 四` | 博雅講堂四個子電表總用電 |
| `新生大樓` | 新生講堂總用電 |

每個檔案包含 13 個欄位：日期時間、功率 kW、電表數值、用電度數、功因 %、三相電流（I_r/s/t）、三相電壓（V_rs/st/tr）、總視在功率 kVa、總無效功率 kVar。

---

## 分析流程

| 筆記本 | 內容 |
|---|---|
| `01_data_loading_cleaning.ipynb` | 資料載入、清理、缺值補插、匯出 parquet |
| （後續） | EDA、溫度模型、超額耗電估算、推廣至其他講堂 |

---

## 本機環境設定

### 1. 安裝必要工具（只做一次）

- [Git](https://git-scm.com/downloads)
- [VS Code](https://code.visualstudio.com/)
- [Python 3.10+](https://www.python.org/downloads/)

### 2. 安裝 VS Code 擴充套件（只做一次）

打開 VS Code，點左側 Extensions 圖示（四個方塊），搜尋並安裝：
- **Python**（Microsoft 出品）
- **Jupyter**（Microsoft 出品）

### 3. Clone 專案（只做一次）

1. 打開 VS Code
2. 按 `Ctrl+Shift+P`（Mac 用 `Command+Shift+P`），搜尋 `Git: Clone`，按 Enter
3. 貼上 `https://github.com/brian0908/ntu-lecture-hall-energy.git`，按 Enter
4. 選擇一個想存放的資料夾 → 點「Open」開啟專案

### 4. 安裝套件（只做一次）

在 VS Code 裡按 `` Ctrl+` ``（Mac 用 `` Control+` ``）開啟內建終端機，輸入：

```bash
pip install pandas numpy matplotlib seaborn scikit-learn xgboost shap \
            python-calamine beautifulsoup4 html5lib pyarrow jupyter
```

### 5. 設定 Git 身份（只做一次）

同樣在 VS Code 的終端機裡輸入：

```bash
git config --global user.name "你的名字"
git config --global user.email "你的GitHub信箱"
```

---

## 每次工作的流程

### 第一步：開啟專案

打開 VS Code → File → Open Folder → 選擇 `ntu-lecture-hall-energy` 資料夾

### 第二步：拉取最新版本（Pull）

點左側**原始檔控制**圖示（三個圓圈連線的圖示，或按 `Ctrl+Shift+G`）

點上方的 **⋯ → Pull**，取得最新版本

或在內建終端機（`` Ctrl+` ``）輸入：
```bash
git pull
```

### 第三步：開啟筆記本開始工作

在左側檔案列表點擊 `.ipynb` 檔案，VS Code 會直接開啟 Jupyter 筆記本介面，不需要另開瀏覽器。

### 第四步：完成後上傳（Push）

先清除筆記本輸出：點筆記本上方工具列的 **⋯ → Restart Kernel and Clear All Outputs → 存檔（Ctrl+S）**

然後點左側**原始檔控制**圖示：

1. 在「Changes」區塊，點 **＋** 號將檔案加入暫存（等同 `git add`）
2. 在上方輸入框填寫說明，例如：`新增溫度與用電散佈圖`
3. 點 **✓ Commit** 按鈕
4. 點 **Sync Changes**（或 **Push**）上傳

第一次 push 會跳出 GitHub 登入視窗，登入自己的帳號即可。

---

## 協作注意事項

- **開始前一定要先 `git pull`**，避免版本衝突
- 不要兩個人同時編輯同一個筆記本

---

## 使用 Google Colab（不想在本機安裝的組員）

在筆記本最上方加入以下程式碼，之後其餘程式碼不需要修改：

```python
!git clone https://github.com/brian0908/ntu-lecture-hall-energy.git
import os
os.chdir('ntu-lecture-hall-energy')
```

> 注意：Colab 每次重新開啟 session 都需要重新執行上面的指令。如需 push，請聯絡 Brian 協助合併。
