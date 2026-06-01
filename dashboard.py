"""
NTU Lecture Hall Energy Dashboard
Interactive dashboard for AC electricity savings analysis.
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from scipy.optimize import minimize_scalar
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc

warnings.filterwarnings("ignore")

CLEANED = Path("cleaned_data")
SUS = Path("永續辦公室")
TARIFF = 3.5      # NTD/kWh
EMISSION = 0.494  # kg CO2e/kWh (Bureau of Energy 2023)

BLDG_COLORS = {
    "普通教學館": "#2196F3",
    "博雅教學館": "#E91E63",
    "共同教學館": "#FF9800",
    "新生教學館": "#4CAF50",
    "禮賢樓":    "#9C27B0",
    "行政大樓":  "#795548",
}
BLDG_LIST = list(BLDG_COLORS.keys())

# ── Holiday sets (mirrors notebook) ─────────────────────────────────
_NATIONAL = set([
    "2016-01-01","2016-02-28","2016-02-29","2016-04-04","2016-04-05","2016-06-09","2016-09-15","2016-10-10",
    "2017-01-01","2017-01-02","2017-02-28","2017-04-04","2017-05-30","2017-10-04","2017-10-10",
    "2018-01-01","2018-02-28","2018-04-04","2018-04-05","2018-06-18","2018-09-24","2018-10-10",
    "2019-01-01","2019-02-28","2019-04-04","2019-04-05","2019-06-07","2019-09-13","2019-10-10",
    "2020-01-01","2020-02-28","2020-04-02","2020-04-03","2020-04-04","2020-04-05","2020-06-25",
    "2020-10-01","2020-10-09","2020-10-10","2020-10-11",
    "2021-01-01","2021-02-28","2021-03-01","2021-04-02","2021-04-03","2021-04-04","2021-04-05",
    "2021-06-14","2021-09-21","2021-10-10","2021-10-11",
    "2022-01-01","2022-02-28","2022-04-02","2022-04-03","2022-04-04","2022-04-05","2022-06-03",
    "2022-09-10","2022-10-10",
    "2023-01-01","2023-01-02","2023-02-28","2023-04-01","2023-04-02","2023-04-03","2023-04-04",
    "2023-04-05","2023-06-22","2023-09-29","2023-10-10",
    "2024-01-01","2024-02-28","2024-04-04","2024-04-05","2024-04-06","2024-04-07","2024-06-10",
    "2024-09-17","2024-10-10",
    "2025-01-01","2025-02-28","2025-04-03","2025-04-04","2025-04-05","2025-04-06","2025-05-31",
    "2025-10-06","2025-10-10",
])
_CNY = set([
    "2016-02-07","2016-02-08","2016-02-09","2016-02-10","2016-02-11","2016-02-12",
    "2017-01-27","2017-01-28","2017-01-29","2017-01-30","2017-01-31","2017-02-01",
    "2018-02-15","2018-02-16","2018-02-17","2018-02-18","2018-02-19","2018-02-20",
    "2019-02-04","2019-02-05","2019-02-06","2019-02-07","2019-02-08","2019-02-09",
    "2020-01-24","2020-01-25","2020-01-26","2020-01-27","2020-01-28","2020-01-29",
    "2021-02-11","2021-02-12","2021-02-13","2021-02-14","2021-02-15","2021-02-16",
    "2022-01-31","2022-02-01","2022-02-02","2022-02-03","2022-02-04","2022-02-05",
    "2023-01-21","2023-01-22","2023-01-23","2023-01-24","2023-01-25","2023-01-26",
    "2024-02-09","2024-02-10","2024-02-11","2024-02-12","2024-02-13","2024-02-14",
    "2025-01-28","2025-01-29","2025-01-30","2025-01-31","2025-02-01","2025-02-02",
])


def _day_type(dt):
    d = dt.strftime("%Y-%m-%d")
    if d in _CNY:
        return 1
    if dt.month in [1, 7, 8] or (dt.month == 2 and dt.day <= 14):
        return 3
    if d in _NATIONAL or dt.weekday() >= 5:
        return 2
    return 0


def _season(dt):
    m, d = dt.month, dt.day
    if m == 1 or (m == 2 and d <= 14):
        return "winter_break"
    if (m == 2 and d > 14) or m in [3, 4, 5] or (m == 6 and d <= 20):
        return "spring"
    if (m == 6 and d > 20) or m in [7, 8]:
        return "summer_break"
    return "fall"


# ════════════════════════════════════════════════════════════════════
# DATA LOADING
# ════════════════════════════════════════════════════════════════════

def _sum_meters(*dfs):
    series = [df["kw"].copy() for df in dfs]
    series = [s[~s.index.duplicated(keep="first")] for s in series]
    return pd.concat(series, axis=1).sum(axis=1, min_count=1)


print("Loading data…")

df_ac       = pd.read_parquet(CLEANED / "ac_普通.parquet")
df_putong1  = pd.read_parquet(CLEANED / "putong1_普通新設一.parquet")
df_putong2  = pd.read_parquet(CLEANED / "putong2_普通新設二.parquet")
df_elevator = pd.read_parquet(CLEANED / "elevator_普通電梯.parquet")
df_boya1    = pd.read_parquet(CLEANED / "boya1_博雅館一.parquet")
df_boya2    = pd.read_parquet(CLEANED / "boya2_博雅館二.parquet")
df_boya3    = pd.read_parquet(CLEANED / "boya3_博雅三.parquet")
df_boya4    = pd.read_parquet(CLEANED / "boya4_博雅四.parquet")
df_gongtong = pd.read_parquet(CLEANED / "gongtong_共同教室.parquet")
df_xinsheng = pd.read_parquet(CLEANED / "xinsheng_新生大樓.parquet")
df_lixi     = pd.read_parquet(CLEANED / "lixian_禮賢樓.parquet")
df_xz       = pd.read_parquet(CLEANED / "xingzheng_行政大樓.parquet")

weather = pd.read_csv(
    CLEANED / "weather_data_2016_2025.csv",
    parse_dates=["ObsTime"], index_col="ObsTime",
)
weather.index = weather.index.tz_localize(None)
temp = weather["Temperature"].where(lambda x: x > -9).rename("T")

df_basic = pd.read_excel(SUS / "館舍用電基礎值.xlsx")

buildings_kw = {
    "普通教學館": _sum_meters(df_ac, df_putong1, df_putong2, df_elevator),
    "博雅教學館": _sum_meters(df_boya1, df_boya2, df_boya3, df_boya4),
    "共同教學館": df_gongtong["kw"].copy(),
    "新生教學館": df_xinsheng["kw"].copy(),
    "禮賢樓":    df_lixi["total_kw"].copy(),
    "行政大樓":  df_xz["total_kw"].copy(),
}
buildings_kw = {k: s[~s.index.duplicated(keep="first")] for k, s in buildings_kw.items()}

base_df = temp.to_frame(name="T")
base_df["day_type"] = base_df.index.map(_day_type)
base_df["season"]   = base_df.index.map(_season)
base_df["hour"]     = base_df.index.hour
base_df["month"]    = base_df.index.month
base_df["year"]     = base_df.index.year
for name, s in buildings_kw.items():
    base_df = base_df.join(s.rename(name))

# Cold-day baseline (for AC proxy)
cold_mask = (
    (base_df["day_type"] == 0) &
    (base_df["hour"].between(8, 21)) &
    (base_df["T"] < 20.0) &
    (base_df["T"] > 0)
)
baselines = {n: base_df.loc[cold_mask, n].dropna().median() for n in BLDG_LIST}
for name in BLDG_LIST:
    base_df[f"{name}_proxy"] = base_df[name] - baselines[name]

# Analysis mask
analysis_mask = (
    (base_df["day_type"] == 0) &
    (base_df["hour"].between(8, 21)) &
    (base_df["month"].between(3, 10)) &
    (base_df["season"].isin(["spring", "fall"])) &
    (base_df["T"].notna()) & (base_df["T"] > 0)
)
ops_mask = (
    (base_df["day_type"] == 0) &
    (base_df["hour"].between(8, 21)) &
    (base_df["season"].isin(["spring", "fall"])) &
    (base_df["T"].notna()) & (base_df["T"] > 0)
)
T_OPS = base_df.loc[ops_mask, "T"].values
N_YEARS = base_df["year"].nunique()
HRS_OPS = ops_mask.sum() / N_YEARS


# ── Piecewise linear setpoint estimation ────────────────────────────

def _piecewise_rss(t_break, T, Y):
    rss = 0.0
    for mask in [T <= t_break, T > t_break]:
        if mask.sum() < 3:
            return np.inf
        s, i, *_ = scipy_stats.linregress(T[mask], Y[mask])
        rss += ((Y[mask] - (s * T[mask] + i)) ** 2).sum()
    return rss


def _estimate_t_set(T_arr, Y_arr, t_min=20.0, t_max=30.0):
    valid = ~(np.isnan(T_arr) | np.isnan(Y_arr))
    T, Y = T_arr[valid], Y_arr[valid]
    if len(T) < 30:
        return np.nan
    res = minimize_scalar(_piecewise_rss, bounds=(t_min, t_max), method="bounded", args=(T, Y))
    return res.x


t_set_spring = {}
t_set_fall   = {}
for name in BLDG_LIST:
    spring_mask = analysis_mask & (base_df["season"] == "spring")
    fall_mask   = analysis_mask & (base_df["season"] == "fall")
    sub_sp = base_df[spring_mask]
    sub_fa = base_df[fall_mask]
    t_set_spring[name] = _estimate_t_set(sub_sp["T"].values, sub_sp[f"{name}_proxy"].values)
    t_set_fall[name]   = _estimate_t_set(sub_fa["T"].values, sub_fa[f"{name}_proxy"].values)


# ── Sustainability office AC loads ──────────────────────────────────

def _get_ac_kw(hint, exact):
    if exact:
        mask = df_basic["館舍名稱"] == exact
    else:
        mask = df_basic["館舍名稱"].str.contains(hint, na=False)
    matched = df_basic[mask]
    return matched["人員空調使用用電"].sum() if not matched.empty else None


_sus_cfg = {
    "普通教學館": ("普通", None),
    "博雅教學館": ("博雅", None),
    "共同教學館": ("共同", None),
    "新生教學館": ("新生", None),
    "禮賢樓":    ("禮賢", None),
    "行政大樓":  (None, "行政大樓(含北、南、東西側)"),
}
AC_KW = {}
for name, (hint, exact) in _sus_cfg.items():
    val = _get_ac_kw(hint, exact)
    if val and val > 0:
        AC_KW[name] = val
    else:
        AC_KW[name] = max(base_df.loc[analysis_mask, f"{name}_proxy"].dropna().mean(), 0)

print("Data loading complete.")


# ════════════════════════════════════════════════════════════════════
# HELPER: savings computation
# ════════════════════════════════════════════════════════════════════

def compute_savings(target_t: float):
    """Compute per-building savings when target setpoint = target_t °C."""
    rows = []
    for name in BLDG_LIST:
        t0 = t_set_spring[name]
        ac_kw = AC_KW[name]
        cdh_t0 = (T_OPS - t0).clip(min=0).sum() / N_YEARS
        cdh_tgt = (T_OPS - target_t).clip(min=0).sum() / N_YEARS
        if cdh_t0 > 0 and target_t > t0:
            sf = 1 - cdh_tgt / cdh_t0
        elif target_t <= t0:
            sf = 0.0
        else:
            sf = 1 - cdh_tgt / cdh_t0
        sf = max(0.0, min(1.0, sf))
        kwh = ac_kw * sf * HRS_OPS
        rows.append({
            "棟別": name,
            "空調負載 (kW)": int(round(ac_kw)),
            "現行 T* (°C)": round(t0, 1),
            "目標溫度 (°C)": target_t,
            "節電比例": sf,
            "年節電量 (MWh)": round(kwh / 1000, 1),
            "年節費 (萬元)": round(kwh * TARIFF / 1e4, 1),
            "年減碳 (公噸 CO₂)": round(kwh * EMISSION / 1e3, 1),
        })
    return pd.DataFrame(rows)


# ════════════════════════════════════════════════════════════════════
# PRE-COMPUTED FIGURES (static)
# ════════════════════════════════════════════════════════════════════

def fig_annual_trend():
    fig = make_subplots(rows=2, cols=3, subplot_titles=BLDG_LIST, shared_yaxes=False)
    positions = [(1,1),(1,2),(1,3),(2,1),(2,2),(2,3)]
    for (r, c), name in zip(positions, BLDG_LIST):
        s = base_df[name]
        annual = s.resample("YE").sum() / 1000
        annual = annual[annual.index.year <= 2025]
        fig.add_trace(
            go.Bar(
                x=annual.index.year.tolist(),
                y=annual.values.tolist(),
                marker_color=BLDG_COLORS[name],
                name=name,
                showlegend=False,
                hovertemplate="%{x}年: %{y:.0f} MWh<extra>" + name + "</extra>",
            ),
            row=r, col=c,
        )
    fig.update_layout(
        title_text="各棟年度合計用電量（2016–2025）",
        title_font_size=16,
        height=500,
        plot_bgcolor="#fafafa",
        paper_bgcolor="white",
    )
    fig.update_xaxes(tickmode="linear", dtick=2)
    fig.update_yaxes(title_text="MWh")
    return fig


def fig_load_curve():
    day_configs = [
        (0, "spring", "上課日（春學期）", "#e74c3c", 2.5),
        (0, "fall",   "上課日（秋學期）", "#e67e22", 2.0),
        (2, None,     "例假日",           "#3498db", 1.5),
        (3, None,     "寒暑假",           "#95a5a6", 1.5),
    ]
    fig = make_subplots(rows=2, cols=3, subplot_titles=BLDG_LIST, shared_xaxes=True)
    positions = [(1,1),(1,2),(1,3),(2,1),(2,2),(2,3)]
    shown_legend = set()
    for (r, c), name in zip(positions, BLDG_LIST):
        s = base_df[name]
        df_tmp = pd.DataFrame({
            "kw": s,
            "hour": s.index.hour,
            "day_type": base_df["day_type"],
            "season": base_df["season"],
        })
        for dt, season_val, label, color, lw in day_configs:
            sub = df_tmp[df_tmp["day_type"] == dt]
            if season_val:
                sub = sub[sub["season"] == season_val]
            curve = sub.groupby("hour")["kw"].mean()
            show = label not in shown_legend
            if show:
                shown_legend.add(label)
            fig.add_trace(
                go.Scatter(
                    x=curve.index.tolist(),
                    y=curve.values.tolist(),
                    mode="lines",
                    name=label,
                    line=dict(color=color, width=lw),
                    showlegend=show,
                    legendgroup=label,
                    hovertemplate=f"{label}<br>%{{x}}時: %{{y:.1f}} kW<extra></extra>",
                ),
                row=r, col=c,
            )
    fig.update_layout(
        title_text="各棟日負載曲線（上課日 vs 假日 vs 寒暑假）",
        title_font_size=16,
        height=500,
        plot_bgcolor="#fafafa",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(title_text="時刻", tickmode="linear", dtick=4)
    fig.update_yaxes(title_text="平均 kW")
    return fig


def fig_heatmap(selected_building):
    s = base_df[selected_building]
    df_tmp = pd.DataFrame({"kw": s, "month": s.index.month, "hour": s.index.hour})
    pivot = df_tmp.groupby(["hour", "month"])["kw"].mean().unstack("month")
    month_labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=month_labels,
        y=[f"{h:02d}:00" for h in range(24)],
        colorscale="RdYlGn_r",
        colorbar=dict(title="avg kW"),
        hovertemplate="月份: %{x}<br>時刻: %{y}<br>平均用電: %{z:.1f} kW<extra></extra>",
    ))
    fig.update_layout(
        title=f"{selected_building} — 月份 × 時刻 平均用電 (kW)",
        xaxis_title="月份",
        yaxis_title="時刻",
        yaxis=dict(autorange="reversed"),
        height=420,
        plot_bgcolor="#fafafa",
        paper_bgcolor="white",
    )
    return fig


def fig_temp_scatter(selected_building):
    proxy_col = f"{selected_building}_proxy"
    spring_mask = analysis_mask & (base_df["season"] == "spring")
    fall_mask   = analysis_mask & (base_df["season"] == "fall")

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=["下學期（2–6月）", "上學期（9–12月）"],
        shared_yaxes=True,
    )
    rng = np.random.default_rng(42)
    color = BLDG_COLORS[selected_building]

    for col_idx, (mask, t_set, season_label) in enumerate([
        (spring_mask, t_set_spring[selected_building], "下學期"),
        (fall_mask,   t_set_fall[selected_building],   "上學期"),
    ], start=1):
        sub = base_df[mask]
        T = sub["T"].values
        Y = sub[proxy_col].values
        valid = ~(np.isnan(T) | np.isnan(Y))
        idx = np.where(valid)[0]
        samp = rng.choice(idx, size=min(2000, len(idx)), replace=False)

        fig.add_trace(go.Scatter(
            x=T[samp].tolist(), y=Y[samp].tolist(),
            mode="markers",
            marker=dict(color=color, opacity=0.15, size=4),
            name=f"{season_label} 數據",
            showlegend=(col_idx == 1),
            hovertemplate="T: %{x:.1f}°C<br>AC proxy: %{y:.1f} kW<extra></extra>",
        ), row=1, col=col_idx)

        # Median per 0.5°C bin
        if valid.sum() > 20:
            Tv, Yv = T[valid], Y[valid]
            bins = np.arange(int(Tv.min()), int(Tv.max()) + 1, 0.5)
            med, edges, _ = scipy_stats.binned_statistic(Tv, Yv, statistic="median", bins=bins)
            bin_centers = (edges[:-1] + edges[1:]) / 2
            fig.add_trace(go.Scatter(
                x=bin_centers.tolist(), y=med.tolist(),
                mode="lines",
                line=dict(color="orange", width=2),
                name="每0.5°C中位數",
                showlegend=(col_idx == 1),
                hovertemplate="T: %{x:.1f}°C<br>中位數: %{y:.1f} kW<extra></extra>",
            ), row=1, col=col_idx)

            # Two-segment regression lines
            if not np.isnan(t_set):
                for seg, seg_color in [(Tv <= t_set, "navy"), (Tv > t_set, "tomato")]:
                    if seg.sum() >= 2:
                        s_, i_, *_ = scipy_stats.linregress(Tv[seg], Yv[seg])
                        xs = np.linspace(Tv[seg].min(), Tv[seg].max(), 80)
                        fig.add_trace(go.Scatter(
                            x=xs.tolist(), y=(s_ * xs + i_).tolist(),
                            mode="lines",
                            line=dict(color=seg_color, width=2),
                            showlegend=False,
                        ), row=1, col=col_idx)

        # Setpoint vertical line
        if not np.isnan(t_set):
            fig.add_vline(
                x=t_set, line_dash="dash", line_color="gold", line_width=2.5,
                annotation_text=f"T* = {t_set:.1f}°C",
                annotation_font_color="goldenrod",
                row=1, col=col_idx,
            )

    fig.update_layout(
        title=f"{selected_building} — AC Proxy vs 室外溫度（拐點分析）",
        title_font_size=15,
        height=430,
        plot_bgcolor="#fafafa",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig.update_xaxes(title_text="室外溫度 (°C)")
    fig.update_yaxes(title_text="AC Proxy (kW)", col=1)
    return fig


def fig_setpoint_compare():
    names = BLDG_LIST
    sp_vals = [t_set_spring[n] for n in names]
    fa_vals = [t_set_fall[n]   for n in names]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="下學期 T* (2–6月)",
        x=names,
        y=sp_vals,
        marker_color=[BLDG_COLORS[n] for n in names],
        text=[f"{v:.1f}°C" for v in sp_vals],
        textposition="outside",
        hovertemplate="%{x}<br>下學期 T*: %{y:.1f}°C<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="上學期 T* (9–12月)",
        x=names,
        y=fa_vals,
        marker_color=[BLDG_COLORS[n] for n in names],
        marker_pattern_shape="/",
        opacity=0.5,
        text=[f"{v:.1f}°C" for v in fa_vals],
        textposition="outside",
        hovertemplate="%{x}<br>上學期 T*: %{y:.1f}°C<extra></extra>",
    ))
    fig.add_hline(y=26, line_dash="dash", line_color="red", line_width=2,
                  annotation_text="政府標準 26°C", annotation_font_color="red",
                  annotation_position="top right")
    fig.update_layout(
        title="各棟推估冷氣室外啟動門檻 T*（分段線性回歸）",
        title_font_size=15,
        yaxis=dict(title="室外啟動門檻 T* (°C)", range=[16, 33]),
        barmode="group",
        height=420,
        plot_bgcolor="#fafafa",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def fig_savings_bar(df_sav):
    names = df_sav["棟別"].tolist()
    mwh   = df_sav["年節電量 (MWh)"].tolist()
    pct   = [f"{v:.1%}" for v in df_sav["節電比例"].tolist()]

    fig = go.Figure(go.Bar(
        x=names,
        y=mwh,
        marker_color=[BLDG_COLORS[n] for n in names],
        text=[f"{m:.0f} MWh<br>({p})" for m, p in zip(mwh, pct)],
        textposition="outside",
        hovertemplate="%{x}<br>年節電: %{y:.1f} MWh<extra></extra>",
    ))
    total = sum(mwh)
    fig.add_annotation(
        text=f"六棟合計：<b>{total:.0f} MWh/yr</b>",
        xref="paper", yref="paper", x=0.98, y=0.96,
        showarrow=False,
        font=dict(size=13),
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="#ccc", borderwidth=1,
    )
    fig.update_layout(
        title="各棟年節電量（依目標設定溫度試算）",
        yaxis=dict(title="年節電量 (MWh)"),
        height=380,
        plot_bgcolor="#fafafa",
        paper_bgcolor="white",
    )
    return fig


# ════════════════════════════════════════════════════════════════════
# LAYOUT
# ════════════════════════════════════════════════════════════════════

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], title="NTU 空調節電儀表板")

_HEADER = dbc.Navbar(
    dbc.Container([
        dbc.NavbarBrand("臺大空調用電減排效益分析儀表板", className="fw-bold fs-5"),
        dbc.Nav(
            dbc.NavItem(dbc.NavLink("114-2 環境與能源的資料科學 · 第三組", disabled=True,
                                    style={"color": "rgba(255,255,255,0.7)", "fontSize": "0.85rem"})),
            className="ms-auto",
        ),
    ], fluid=True),
    color="primary", dark=True, className="mb-3",
)

# KPI cards (computed once at startup from savings at 26°C)
_df_kpi = compute_savings(26.0)
_total_mwh  = _df_kpi["年節電量 (MWh)"].sum()
_total_cost = _df_kpi["年節費 (萬元)"].sum()
_total_co2  = _df_kpi["年減碳 (公噸 CO₂)"].sum()
_avg_t_star = np.mean([t_set_spring[n] for n in BLDG_LIST])

def _kpi_card(title, value, unit, color):
    return dbc.Card(
        dbc.CardBody([
            html.P(title, className="text-muted mb-1", style={"fontSize": "0.82rem"}),
            html.H4(value, className=f"text-{color} fw-bold mb-0"),
            html.Small(unit, className="text-muted"),
        ]),
        className="shadow-sm",
    )

_KPI_ROW = dbc.Row([
    dbc.Col(_kpi_card("六棟平均下學期 T*", f"{_avg_t_star:.1f} °C", "室外啟動門檻（春季）", "primary"), md=3),
    dbc.Col(_kpi_card("調至 26°C 年節電", f"{_total_mwh:.0f} MWh", "六棟合計/年", "success"), md=3),
    dbc.Col(_kpi_card("年節省電費", f"{_total_cost:.0f} 萬元", "六棟合計/年（電價 3.5 元/kWh）", "warning"), md=3),
    dbc.Col(_kpi_card("年減碳效益", f"{_total_co2:.0f} 公噸 CO₂", "六棟合計/年（排放係數 0.494 kg/kWh）", "danger"), md=3),
], className="g-3 mb-4")

_TABS = dbc.Tabs([
    dbc.Tab(label="📊 用電趨勢 EDA", tab_id="eda"),
    dbc.Tab(label="🌡️ 設定溫度推估", tab_id="setpoint"),
    dbc.Tab(label="💡 節電試算（互動）", tab_id="savings"),
], id="main-tabs", active_tab="eda", className="mb-3")

_EDA_CONTENT = html.Div([
    dbc.Row([
        dbc.Col(dcc.Graph(id="fig-annual", figure=fig_annual_trend()), md=12),
    ], className="mb-3"),
    dbc.Row([
        dbc.Col(dcc.Graph(id="fig-loadcurve", figure=fig_load_curve()), md=12),
    ], className="mb-3"),
    dbc.Row([
        dbc.Col([
            dbc.Label("選擇建物查看熱圖："),
            dcc.Dropdown(
                id="heatmap-bldg",
                options=[{"label": n, "value": n} for n in BLDG_LIST],
                value="普通教學館",
                clearable=False,
                style={"maxWidth": "260px"},
            ),
            dcc.Graph(id="fig-heatmap"),
        ], md=12),
    ]),
], id="eda-tab")

_SETPOINT_CONTENT = html.Div([
    dbc.Row([
        dbc.Col(dcc.Graph(id="fig-tset-compare", figure=fig_setpoint_compare()), md=12),
    ], className="mb-3"),
    dbc.Row([
        dbc.Col([
            dbc.Label("選擇建物查看拐點散佈圖："),
            dcc.Dropdown(
                id="scatter-bldg",
                options=[{"label": n, "value": n} for n in BLDG_LIST],
                value="普通教學館",
                clearable=False,
                style={"maxWidth": "260px"},
            ),
            dcc.Graph(id="fig-scatter"),
        ], md=12),
    ]),
], id="setpoint-tab")

_SAVINGS_CONTENT = html.Div([
    dbc.Card(dbc.CardBody([
        dbc.Row([
            dbc.Col([
                html.H6("目標設定溫度（室外啟動門檻）", className="fw-bold mb-1"),
                html.P(
                    "拖動滑桿調整目標室外啟動門檻溫度。"
                    "當目標溫度高於某棟現行 T*，該棟才有節電效益。",
                    className="text-muted small mb-3",
                ),
                dcc.Slider(
                    id="target-temp-slider",
                    min=20.0, max=30.0, step=0.5,
                    value=26.0,
                    marks={t: f"{t}°C" for t in range(20, 31)},
                    tooltip={"placement": "bottom", "always_visible": True},
                ),
                html.Div(id="slider-note", className="text-muted small mt-2"),
            ], md=12),
        ]),
    ]), className="shadow-sm mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(id="fig-savings-bar"), md=12),
    ], className="mb-3"),

    dbc.Row([
        dbc.Col([
            html.H6("各棟節電效益明細", className="fw-bold mb-2"),
            html.Div(id="savings-table"),
        ], md=12),
    ], className="mb-3"),

    dbc.Row([
        dbc.Col([
            dbc.Card(dbc.CardBody([
                html.H6("六棟合計", className="fw-bold mb-3"),
                dbc.Row([
                    dbc.Col(html.Div(id="total-kwh"), md=4),
                    dbc.Col(html.Div(id="total-cost"), md=4),
                    dbc.Col(html.Div(id="total-co2"), md=4),
                ]),
            ]), className="shadow-sm bg-light"),
        ], md=12),
    ]),
], id="savings-tab")

app.layout = dbc.Container([
    _HEADER,
    dbc.Container([
        _KPI_ROW,
        _TABS,
        html.Div(id="tab-content"),
    ], fluid=True),
], fluid=True, style={"backgroundColor": "#f0f2f5", "minHeight": "100vh", "paddingBottom": "40px"})


# ════════════════════════════════════════════════════════════════════
# CALLBACKS
# ════════════════════════════════════════════════════════════════════

@app.callback(Output("tab-content", "children"), Input("main-tabs", "active_tab"))
def render_tab(tab):
    if tab == "eda":
        return _EDA_CONTENT
    if tab == "setpoint":
        return _SETPOINT_CONTENT
    if tab == "savings":
        return _SAVINGS_CONTENT
    return html.Div()


@app.callback(Output("fig-heatmap", "figure"), Input("heatmap-bldg", "value"))
def update_heatmap(bldg):
    return fig_heatmap(bldg)


@app.callback(Output("fig-scatter", "figure"), Input("scatter-bldg", "value"))
def update_scatter(bldg):
    return fig_temp_scatter(bldg)


@app.callback(
    Output("fig-savings-bar", "figure"),
    Output("savings-table", "children"),
    Output("total-kwh", "children"),
    Output("total-cost", "children"),
    Output("total-co2", "children"),
    Output("slider-note", "children"),
    Input("target-temp-slider", "value"),
)
def update_savings(target_t):
    df = compute_savings(target_t)

    bar_fig = fig_savings_bar(df)

    # Table
    header = html.Thead(html.Tr([
        html.Th("棟別"), html.Th("現行 T* (°C)"), html.Th("節電比例"),
        html.Th("年節電量 (MWh)"), html.Th("年節費 (萬元)"), html.Th("年減碳 (公噸 CO₂)"),
    ]))
    rows = []
    for _, r in df.iterrows():
        pct = r["節電比例"]
        pct_color = "text-success" if pct >= 0.3 else ("text-warning" if pct >= 0.1 else "text-muted")
        gap = target_t - r["現行 T* (°C)"]
        gap_badge = dbc.Badge(
            f"+{gap:.1f}°C" if gap >= 0 else f"{gap:.1f}°C",
            color="success" if gap > 0 else "secondary",
            className="ms-1",
        )
        rows.append(html.Tr([
            html.Td([r["棟別"], gap_badge]),
            html.Td(f"{r['現行 T* (°C)']:.1f}°C"),
            html.Td(html.Span(f"{pct:.1%}", className=pct_color + " fw-bold")),
            html.Td(f"{r['年節電量 (MWh)']:.1f}"),
            html.Td(f"{r['年節費 (萬元)']:.1f}"),
            html.Td(f"{r['年減碳 (公噸 CO₂)']:.1f}"),
        ]))
    table = dbc.Table([header, html.Tbody(rows)], bordered=True, hover=True,
                      striped=True, responsive=True, size="sm", className="mb-0")

    total_kwh  = df["年節電量 (MWh)"].sum()
    total_cost = df["年節費 (萬元)"].sum()
    total_co2  = df["年減碳 (公噸 CO₂)"].sum()

    def _stat(label, value, unit, color):
        return html.Div([
            html.P(label, className="text-muted mb-0 small"),
            html.H5(f"{value:.1f}", className=f"text-{color} fw-bold mb-0"),
            html.Small(unit, className="text-muted"),
        ], className="text-center")

    kwh_out  = _stat("年節電量", total_kwh,  "MWh / 年", "success")
    cost_out = _stat("年節省電費", total_cost, "萬元 / 年", "warning")
    co2_out  = _stat("年減碳", total_co2, "公噸 CO₂ / 年", "danger")

    already = [n for n in BLDG_LIST if target_t <= t_set_spring[n]]
    note = ""
    if already:
        note = f"注意：{' / '.join(already)} 現行 T* ≥ 目標溫度，無節電效益（已達標或目標設定過低）。"

    return bar_fig, table, kwh_out, cost_out, co2_out, note


if __name__ == "__main__":
    app.run(debug=False, port=8050)
