# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

This is a group project for the course "Data Science for Environment and Energy" at National Taiwan University. The role is an energy data consulting firm pitching energy-saving / net-zero proposals to NTU. The core analysis is quantifying excess AC electricity caused by indoor setpoints below the 26°C government standard, then generalizing from the one metered AC system to the other lecture halls and campus-wide.

## Data

All data lives in `data/`. All meters are **NTU lecture hall buildings** — 普通, 共同, 博雅, and 新生 are all lecture hall complexes on campus.

| Meter | Description | Files |
|---|---|---|
| 普通高壓空調 | AC-only sub-meter for the 普通 lecture hall — **the only direct AC ground truth** | 2016–2020 individual + one combined 2021–2025 file |
| 博雅館一 / 博雅館二 | 博雅 lecture hall sub-meters 1 & 2 (total electricity) | 2016–2025 |
| 博雅三 / 博雅四 | 博雅 lecture hall sub-meters 3 & 4 (total electricity) | 2016–2025 |
| 共同教室 | 共同 lecture hall total electricity | 2016–2025 |
| 新生大樓 | 新生 lecture hall total electricity | 2016–2025 |

**Important:** There is no total electricity meter for 普通 — only its AC sub-meter. There is no AC sub-meter for any of the other lecture halls — only their total electricity. This asymmetry shapes the entire analysis strategy.

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

## Analysis Pipeline

The notebook follows this sequence:

1. **Data loading & cleaning** — load all files per meter, concatenate, parse datetimes, remove anomalies (negative kW, meter resets)
2. **Weather data integration** — join with CWA hourly temperature data for Taipei station; compute `CDH = max(0, T_outdoor − 26)` as the primary cooling-load feature
3. **EDA** — seasonal heatmaps, load curves by occupancy (semester vs. vacation, weekday vs. weekend), scatter of AC kW vs. outdoor temperature to identify the effective indoor setpoint (inflection point)
4. **普通 AC model** — train `AC_kWh = f(CDH_actual, CDH_26, humidity, hour, occupancy)` on 普通高壓空調 data; estimate actual setpoint from inflection point (temperature at which AC power starts rising above base); compute 26°C counterfactual excess for 普通
5. **Decomposition for other halls** — for 共同, 博雅一/二/三/四, 新生: fit base-load model from each building's own winter data (Dec–Feb, T < 18°C), then `AC_inferred = Total − Base_load` for warm months; all are lecture halls so occupancy patterns are comparable
6. **Cross-validation of decomposition** — verify that the AC_inferred series for the other halls has similar temperature-sensitivity shape (β coefficient) to 普通's actual AC meter; large outliers suggest a building has non-AC sources of temperature-sensitive load
7. **University-wide extrapolation** — scale by building floor area (from NTU 永續報告書 or facilities data) or by building type; report as a range with explicit uncertainty
8. **Results** — three-tier table: reference building (meter-validated) → 6 buildings → campus-wide

## Key Assumptions to Document

- Actual AC setpoint is inferred from the temperature inflection point in the AC-vs-T scatter, not from thermostat logs
- COP assumption for the chiller system (typical range 3–4) affects the physics-based model; run sensitivity analysis
- Base load is fitted from Dec–Feb data where T < 18°C
- Train/test split: 2016–2021 train, 2022–2024 test (held out for all models)
- Taiwan grid emission factor: published annually by the Bureau of Energy (電力排放係數, kg CO₂e/kWh); use the year-matched factor for each row

## Dependencies

```
pandas
numpy
matplotlib / seaborn
scikit-learn
xgboost or lightgbm
shap
python-calamine   # for 新生大樓 binary XLS files
beautifulsoup4    # for pd.read_html on HTML-disguised XLS
html5lib
```
