# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

This is a group project for the course "Data Science for Environment and Energy" at National Taiwan University. The role is an energy data consulting firm pitching energy-saving / net-zero proposals to NTU. The core analysis is quantifying excess AC electricity caused by operating below the 26°C government standard, and proposing a governance framework for AC usage — a gap NTU has confirmed it currently lacks.

**Key finding from school consultation:** NTU has no AC *usage* guidelines (no rules on setpoint or operating hours). There are procurement rules (size limits per room area), but nothing governing how AC is actually operated. The government standard is 26°C but NTU has no enforcement mechanism. This policy gap is the central framing of our pitch.

**Control room interview findings (added 2026-05-16):**
- The school does have energy-saving measures, but they are informal and ad hoc — teachers can request adjustments (warmer or cooler), so there is no consistent enforced setpoint.
- **Seasonal operation:** Winter = ventilation only (no cooling). AC cooling is only active during warm months. For AC analysis, filter to months where cooling is likely (roughly April–October, or where T_outdoor > 24°C).
- **博雅大階梯教室:** Small classrooms have sealed windows (cannot open) → AC must run regardless. Large lecture halls also require AC. This explains 博雅's relatively high and inelastic AC load.
- Key qualitative finding: "規範不能預測實際" (rules cannot predict actual behavior) — even informal guidelines are not reliably followed, reinforcing the governance gap argument.

**Methodology anchor:** NTU's 永續辦公室 has already decomposed total electricity into AC and non-AC components for all 145 campus buildings using a temperature-stratified, day-type-aware approach. Their output (`館舍用電基礎值.xlsx`) gives us a defensible, school-endorsed AC load estimate for every building — including all four of our target lecture halls. We use this as the foundation and add a 26°C counterfactual on top.

## Data

### Smart meter data (`data/`)

All meters are NTU lecture hall buildings — 普通, 共同, 博雅, and 新生 are all lecture hall complexes on campus.

| Meter | Description | Files |
|---|---|---|
| 普通高壓空調 | One AC sub-circuit in 普通 lecture hall — used **only for setpoint inference (inflection point)**; do not use to validate whole-building AC magnitude | 2016–2020 individual + one combined 2021–2025 file |
| 博雅館一 / 博雅館二 | 博雅 lecture hall sub-meters 1 & 2 (total electricity) | 2016–2025 |
| 博雅三 / 博雅四 | 博雅 lecture hall sub-meters 3 & 4 (total electricity) | 2016–2025 |
| 共同教室 | 共同 lecture hall total electricity | 2016–2025 |
| 新生大樓 | 新生 lecture hall total electricity | 2016–2025 |

Note: The 普通高壓空調 meter reads 10–70 kW in practice, while the sustainability office estimates the whole 普通教學館 AC load at 117 kW. The gap confirms this meter covers only one sub-circuit out of multiple AC circuits in the building. Downstream panels are also not managed by the Facilities Office, so the meter may include some non-AC loads. **Do not use this meter to validate the 117 kW magnitude — they measure different scopes.** The meter is still useful for setpoint inference: its temperature-response inflection point reflects the building’s thermostat setpoint even if it only captures a fraction of total AC load.

**All files share 13 columns:** `日期時間` (hourly timestamp), `功率 kW`, `電表數值` (cumulative meter), `用電度數` (kWh per interval), `功因 %`, `I_r/s/t`, `V_rs/st/tr`, `總視在功率 kVa`, `總無效功率 kVar`.

### Reading the files

The `.xls` files come in **two different formats** — check by file size:

- **Most files (~7.5 MB): HTML-disguised-as-XLS** — use `pd.read_html(path, encoding='big5')`. Returns 2 tables; use `tables[1]` (table[0] is a header block). Row 0 is the column name row, data starts at row 1.

```python
tables = pd.read_html(filepath, encoding='big5')
df = tables[1].iloc[1:].copy()
df.columns = ['datetime','kw','meter','kwh','pf','Ir','Is','It','Vrs','Vst','Vtr','kva','kvar']
```

- **新生大樓 files (~1.2 MB): True binary XLS** — use `engine='calamine'` (requires `pip install python-calamine`). Row 0 is the column name row.

```python
df = pd.read_excel(filepath, engine='calamine', header=0)
```

After loading, always cast `datetime` to `pd.to_datetime` and `kw`/`kwh` to `float`.

### 永續辦公室 data (`永續辦公室/`)

| File | Description |
|---|---|
| `館舍用電基礎值.xlsx` | Pre-computed electricity decomposition for all 145 NTU buildings. Key column: `人員空調使用用電` (kW) — the AC component extracted by the sustainability office's method. Also contains floor area and per-area density columns. |
| `08_計算館舍不同日子用電值.py` | The decomposition script. Uses `Dayoff` (0=上課日, 1=上班日, 2=週末, 3=假日), hourly temperature, and 75th-percentile cold/hot stratification to separate AC from base load. |

Key figures for the four target lecture halls from `館舍用電基礎值.xlsx`:

| 館舍 | 面積 (m²) | 人員空調用電 (kW) | 空調用電密度 (kW/m²) |
|---|---|---|---|
| 普通教學館 | 8,791 | 119 (df_basic 實際值；04 notebook 硬編碼為 117) | 0.01331 |
| 博雅教學館 | 10,743 | 94 | 0.00875 |
| 新生教學館 | 5,201 | 113 | 0.02173 |
| 共同教學館 | 5,461 | 118 | 0.02161 |

## Analysis Pipeline & Notebook Status

### `01_data_loading_cleaning.ipynb` ✅ Complete
- Loads all meter files (HTML-disguised XLS + binary XLS formats), concatenates, parses datetimes
- Removes anomalies (negative kW, extreme spikes, meter resets); fills gaps ≤3 hours by interpolation, longer gaps left as NaN
- Outputs `cleaned_data/*.parquet` for all meters
- Appended exploratory sections: inter-building kWh correlation (Section 9) and 普通AC share of total 普通 load (Section 10)

### `02_eda.ipynb` ✅ Complete
- Merges 普通 meters with CWA hourly weather data (Taipei station)
- Classifies hours into 16 usage-type × day-type categories (4 usage types × 4 day types); computes electricity decomposition into 8 components (館舍基礎/設備待機/人員設備/人員空調)
- **Setpoint inference (Section 三):** scatter of 普通 AC kW vs outdoor temperature, filtered to weekday class-hours; finds inflection point visually → estimated setpoint ~24°C (full-year aggregate)
- Additional EDA: heatmaps (month × hour), weekday vs holiday load curves, annual consumption trend 2016–2025

### `03_sustainability_method.ipynb` 🔴 Stub
- Currently only loads `館舍用電基礎值.xlsx` and prints `df_basic.head()`. No substantive analysis or markdown.
- Intended purpose (unexplained decomposition logic, cross-validation with smart meter data) is not yet written.

### `04_counterfactual.ipynb` ✅ Complete (single-setpoint baseline)
- Single annual setpoint T_set = 24°C (from 02 inflection point)
- Defines AC operating hours: weekdays × 08–22h × April–October × T_outdoor > 24°C → avg **1,222 hr/yr**
- CDH ratio: `savings_fraction = 1 − CDH_26 / CDH_24 = 36.0%` over 2016–2025
- Applies to four target halls via sustainability office figures → annualised savings per hall
- Scales to all 145 buildings: **3.58 GWh/yr saved, 1,252 萬元/yr, 1,767 公噸 CO₂/yr**
- Sensitivity: T_set 23°C → 47% savings; T_set 25°C → 21% savings
- **Note:** Section 九 result summary table contains placeholder `—` values not yet filled in.

### `05_seasonal_ac_temperature_savings.ipynb` ✅ Complete (seasonal, preferred method)
- Extends 04 by inferring a **separate setpoint per semester** using two-segment piecewise linear regression (minimises RSS over candidate breakpoints):
  - 下學期 (Feb–Jun): **T_set = 24.0°C** — meaningful savings vs 26°C
  - 上學期 (Sep–Dec): **T_set = 26.1°C** — already at/above standard, near-zero savings
  - 暑假 (Jul–Aug):   **T_set = 29.6°C** — almost no cooling demand, negligible savings
- Quantifies two policy interventions separately:
  1. **Raise setpoint to 26°C** (temperature policy)
  2. **Delay AC start to 09:00** (operating-hours policy, currently assumed 08:00)
- Four-hall annual results: **~152,000 kWh/yr** from 26°C measure
- Campus-wide (145 buildings): **2.48 GWh/yr** (26°C) + **0.58 GWh/yr** (delay) = **3.06 GWh/yr combined**; 8.7 百萬元/yr from 26°C alone
- Exports `cleaned_data/seasonal_ac_savings.xlsx`
- **Known issue:** campus CO₂ output in Section 七 prints "1 公噸" — unit conversion bug, needs fix.

### Relationship between 04 and 05
04 uses a single annual setpoint (24°C) and overestimates savings for the upper semester (where T_set ≈ 26°C already). 05 is more accurate because it accounts for seasonal variation. **Use 05 as the primary result for the pitch; 04 is a useful sensitivity benchmark.**

## Key Assumptions to Document

- Effective AC setpoint is inferred from piecewise linear regression of 普通 AC kW vs T_outdoor (weekdays, class hours only), not from thermostat logs; uncertainty ±1–2°C. Seasonal decomposition in 05 reveals the full-year aggregate (24°C) masks near-26°C behaviour in the fall semester.
- `人員空調使用用電` from 永續辦公室 is a demand figure (kW at hot-afternoon peak), not an annual total — annualisation multiplies by estimated AC operating hours per year
- CDH ratio scaling assumes linear AC energy response to setpoint; validated with ±1°C sensitivity
- Taiwan grid emission factor: 0.494 kg CO₂e/kWh (Bureau of Energy 2023); use year-matched figure for final reporting
- The 普通高壓空調 meter (10–70 kW) is one sub-circuit; the sustainability office’s figure for 普通教學館 (119 kW per df_basic, 117 kW as hard-coded in 04) covers the whole building — not comparable in magnitude; meter used only for setpoint inference

## Dependencies

```
pandas
numpy
matplotlib / seaborn
scikit-learn
python-calamine   # for 新生大樓 binary XLS files
beautifulsoup4    # for pd.read_html on HTML-disguised XLS
html5lib
openpyxl          # for reading 館舍用電基礎值.xlsx
```
