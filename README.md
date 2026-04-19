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

### 2. Clone 專案（只做一次）

```bash
git clone https://github.com/brian0908/ntu-lecture-hall-energy.git
cd ntu-lecture-hall-energy
```

### 3. 安裝套件（只做一次）

```bash
pip install pandas numpy matplotlib seaborn scikit-learn xgboost shap \
            python-calamine beautifulsoup4 html5lib pyarrow jupyter
```

### 4. 設定 Git 身份（只做一次）

```bash
git config --global user.name "你的名字"
git config --global user.email "你的GitHub信箱"
```

### 5. 開啟筆記本

```bash
jupyter notebook
```

---

## 每次工作的流程

### 開始前：拉取最新版本

```bash
git pull
```

### 結束後：上傳修改

commit 前請先清除筆記本輸出：**Kernel → Restart & Clear Output → 存檔**

```bash
git add .
git commit -m "簡短說明修改內容，例如：新增溫度與用電散佈圖"
git push
```

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
