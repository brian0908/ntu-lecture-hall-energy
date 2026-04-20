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

## 分析規劃

### 核心問題

台大各講堂冷氣設定溫度普遍低於政府規定的 26°C，造成超額耗電。我們的目標是量化這個超額耗電量，並推估全校節能潛力。

### 分析架構

```
資料前處理
    ↓
探索性分析（EDA）
    ↓
普通講堂 AC 模型（直接量測，作為基準）
    ↓
分解其他講堂的冷氣用電（從總用電中拆解）
    ↓
推廣至全校
    ↓
節能建議與成本效益估算
```

### 各階段說明

**Stage 1｜資料前處理** `01_data_loading_cleaning.ipynb` ✅
- 載入所有電表資料（HTML-XLS 與 binary XLS 兩種格式）
- 清除異常值（負功率、極端峰值、電表重置）
- 補插短暫缺值（≤3小時），長缺值保留為 NaN
- 加入時間特徵（季節、學期、週末）
- 匯出 `cleaned/*.parquet` 供後續使用

**Stage 2｜探索性分析（EDA）** `02_eda.ipynb`
- 各講堂年度、月度用電趨勢（2016–2025）
- 用電熱力圖（月份 × 時段）
- 學期 vs 寒暑假、平日 vs 假日負載曲線比較
- **關鍵圖表：** 普通冷氣 kW vs 室外溫度散佈圖，找出實際設定溫度的拐點

**Stage 3｜普通講堂冷氣模型** `03_ac_model.ipynb`
- 資料：普通高壓空調電表（唯一有冷氣直接量測的建築）
- 訓練期：2016–2021；測試期：2022–2024
- 特徵：冷卻度時數（CDH）、相對濕度、時段、是否學期
- 模型：線性回歸（可解釋性）＋ XGBoost（預測精度）
- 估算實際設定溫度（從拐點推算）
- 計算 26°C 反事實情境下的超額耗電量

**Stage 4｜其他講堂冷氣用電分解** `04_decomposition.ipynb`
- 對共同、博雅一/二/三/四、新生各別處理
- 以冬季資料（12–2月，T < 18°C）擬合基礎負載模型
- 推算冷氣用電：`AC推算 = 總用電 − 基礎負載預測`
- 交叉驗證：各講堂溫度敏感係數（β）應與普通講堂相近

**Stage 5｜全校推廣估算** `05_extrapolation.ipynb`
- 依建築面積（參考台大永續報告書）或建築類型進行縮放
- 三層次結果：
  - 普通講堂（電表直接驗證）
  - 六棟講堂（分解推算）
  - 全校估算（附不確定範圍）

**Stage 6｜節能建議** `06_results.ipynb`
- 超額耗電量（kWh/年）
- 節省電費（元/年，使用台電高壓電價）
- 減碳量（公噸 CO₂/年，使用能源局年度排放係數）
- 政策建議：調高冷氣設定溫度至 26°C、搭配時段管理

### 重要假設

| 假設 | 說明 |
|---|---|
| 實際設定溫度 | 從冷氣用電 vs 室外溫度的拐點推算，非直接量測 |
| 冷氣 COP | 假設 3–4（典型冰水主機），進行敏感度分析 |
| 基礎負載 | 以 12–2月、T < 18°C 的資料擬合 |
| 訓練/測試分割 | 2016–2021 訓練，2022–2024 測試 |
| 碳排放係數 | 使用能源局每年公布的電力排放係數（kg CO₂e/kWh）|

### 筆記本對照表

| 筆記本 | 階段 | 狀態 |
|---|---|---|
| `01_data_loading_cleaning.ipynb` | 資料前處理 | ✅ 完成 |
| `02_eda.ipynb` | 探索性分析 | 🔲 待開始 |
| `03_ac_model.ipynb` | 普通講堂 AC 模型 | 🔲 待開始 |
| `04_decomposition.ipynb` | 其他講堂分解 | 🔲 待開始 |
| `05_extrapolation.ipynb` | 全校推廣 | 🔲 待開始 |
| `06_results.ipynb` | 節能建議與成果 | 🔲 待開始 |

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
