# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

This is a group project for the course "Data Science for Environment and Energy" at National Taiwan University. The role is an energy data consulting firm pitching energy-saving / net-zero proposals to NTU. The core analysis is quantifying excess AC electricity caused by operating below the 26°C government standard, and proposing a governance framework for AC usage — a gap NTU has confirmed it currently lacks.

**Key finding from school consultation:** NTU has no AC *usage* guidelines (no rules on setpoint or operating hours). There are procurement rules (size limits per room area), but nothing governing how AC is actually operated. The government standard is 26°C but NTU has no enforcement mechanism. This policy gap is the central framing of our pitch.

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
| 普通教學館 | 8,791 | 117 | 0.01331 |
| 博雅教學館 | 10,743 | 94 | 0.00875 |
| 新生教學館 | 5,201 | 113 | 0.02173 |
| 共同教學館 | 5,461 | 118 | 0.02161 |

## Analysis Pipeline

1. **Data loading & cleaning** — load all files per meter, concatenate, parse datetimes, remove anomalies (negative kW, meter resets); output `cleaned/*.parquet`
2. **Weather data integration** — join with CWA hourly temperature data for Taipei station; compute `CDH_actual = max(0, T_outdoor − T_setpoint)` and `CDH_26 = max(0, T_outdoor − 26)`
3. **EDA + setpoint inference** — seasonal heatmaps, load curves by occupancy; scatter of 普通 AC kW vs outdoor temperature to find the inflection point → estimated current effective setpoint (this is the key input for the counterfactual)
4. **Adopt sustainability office decomposition** — load `館舍用電基礎值.xlsx`; extract `人員空調使用用電` for the four target halls; reproduce the decomposition logic for transparency
5. **Setpoint verification** — if actual setpoint data is obtained from 教務處課務組, confirm the 普通 meter's inflection point aligns with it; if not available, use the inflection point as the setpoint estimate with ±1–2°C uncertainty; note that kW magnitude comparison between the meter and the sustainability office figure is not meaningful (sub-circuit vs whole building)
6. **26°C counterfactual** — estimate AC savings if setpoint raised to 26°C using CDH ratio scaling: `savings_fraction ≈ 1 − CDH_26 / CDH_actual`; apply to each building's `人員空調使用用電`; report range using low/high setpoint estimates
7. **Campus-wide scaling** — apply the 26°C correction to all 145 buildings in `館舍用電基礎值.xlsx`; sum to get campus-wide annual excess consumption
8. **Results & policy recommendations** — kWh/yr saved, cost/yr (台電高壓電價), CO₂/yr (能源局排放係數); propose three policy levers: (a) formal 26°C setpoint standard, (b) time-of-day shutoff rules, (c) sub-metering requirement for buildings without AC meters

## Key Assumptions to Document

- Effective AC setpoint is inferred from the inflection point of the 普通 AC kW vs T_outdoor scatter, not from thermostat logs; uncertainty ±1–2°C
- `人員空調使用用電` from 永續辦公室 represents a typical peak-occupancy hour under hot-weather conditions (75th percentile of hot-afternoon readings); it is a demand figure, not an annual energy total — annualisation requires multiplying by estimated operating hours
- CDH ratio scaling assumes linear relationship between setpoint and AC energy, which is an approximation; run sensitivity with ±1°C on setpoint
- Taiwan grid emission factor: use the year-matched annual figure published by the Bureau of Energy (電力排放係數, kg CO₂e/kWh)
- The 普通高壓空調 meter reads 10–70 kW (one sub-circuit); the sustainability office's 117 kW figure is the whole building’s AC load — these cannot be directly compared; the meter is used only for inflection-point-based setpoint inference, not magnitude validation

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
