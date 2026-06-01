"""
NTU Lecture Hall Energy Dashboard — Streamlit version
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from scipy.optimize import minimize_scalar
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="臺大空調節電儀表板",
    page_icon="🏫",
    layout="wide",
)

CLEANED = Path("cleaned_data")
SUS = Path("永續辦公室")
TARIFF = 3.5
EMISSION = 0.494

BLDG_COLORS = {
    "普通教學館": "#2196F3",
    "博雅教學館": "#E91E63",
    "共同教學館": "#FF9800",
    "新生教學館": "#4CAF50",
    "禮賢樓":    "#9C27B0",
    "行政大樓":  "#795548",
}
BLDG_LIST = list(BLDG_COLORS.keys())

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
# CACHED DATA LOADING
# ════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner="載入資料中…")
def load_all():
    def sum_meters(*dfs):
        series = [df["kw"].copy() for df in dfs]
        series = [s[~s.index.duplicated(keep="first")] for s in series]
        return pd.concat(series, axis=1).sum(axis=1, min_count=1)

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
        "普通教學館": sum_meters(df_ac, df_putong1, df_putong2, df_elevator),
        "博雅教學館": sum_meters(df_boya1, df_boya2, df_boya3, df_boya4),
        "共同教學館": df_gongtong["kw"].copy(),
        "新生教學館": df_xinsheng["kw"].copy(),
        "禮賢樓":    df_lixi["total_kw"].copy(),
        "行政大樓":  df_xz["total_kw"].copy(),
    }
    buildings_kw = {k: s[~s.index.duplicated(keep="first")] for k, s in buildings_kw.items()}

    base = temp.to_frame(name="T")
    base["day_type"] = base.index.map(_day_type)
    base["season"]   = base.index.map(_season)
    base["hour"]     = base.index.hour
    base["month"]    = base.index.month
    base["year"]     = base.index.year
    for name, s in buildings_kw.items():
        base = base.join(s.rename(name))

    cold_mask = (
        (base["day_type"] == 0) & (base["hour"].between(8, 21)) &
        (base["T"] < 20.0) & (base["T"] > 0)
    )
    for name in BLDG_LIST:
        baseline = base.loc[cold_mask, name].dropna().median()
        base[f"{name}_proxy"] = base[name] - baseline

    analysis_mask = (
        (base["day_type"] == 0) & (base["hour"].between(8, 21)) &
        (base["month"].between(3, 10)) & (base["season"].isin(["spring", "fall"])) &
        (base["T"].notna()) & (base["T"] > 0)
    )
    ops_mask = (
        (base["day_type"] == 0) & (base["hour"].between(8, 21)) &
        (base["season"].isin(["spring", "fall"])) &
        (base["T"].notna()) & (base["T"] > 0)
    )
    T_ops = base.loc[ops_mask, "T"].values
    n_years = base["year"].nunique()
    hrs_ops = ops_mask.sum() / n_years

    # Piecewise setpoint estimation
    def piecewise_rss(t_break, T, Y):
        rss = 0.0
        for mask in [T <= t_break, T > t_break]:
            if mask.sum() < 3:
                return np.inf
            s, i, *_ = scipy_stats.linregress(T[mask], Y[mask])
            rss += ((Y[mask] - (s * T[mask] + i)) ** 2).sum()
        return rss

    def estimate_t_set(T_arr, Y_arr):
        valid = ~(np.isnan(T_arr) | np.isnan(Y_arr))
        T, Y = T_arr[valid], Y_arr[valid]
        if len(T) < 30:
            return np.nan
        res = minimize_scalar(piecewise_rss, bounds=(20.0, 30.0), method="bounded", args=(T, Y))
        return res.x

    t_set_spring, t_set_fall = {}, {}
    for name in BLDG_LIST:
        sp = base[analysis_mask & (base["season"] == "spring")]
        fa = base[analysis_mask & (base["season"] == "fall")]
        t_set_spring[name] = estimate_t_set(sp["T"].values, sp[f"{name}_proxy"].values)
        t_set_fall[name]   = estimate_t_set(fa["T"].values, fa[f"{name}_proxy"].values)

    # AC loads from sustainability office
    sus_cfg = {
        "普通教學館": ("普通", None),
        "博雅教學館": ("博雅", None),
        "共同教學館": ("共同", None),
        "新生教學館": ("新生", None),
        "禮賢樓":    ("禮賢", None),
        "行政大樓":  (None, "行政大樓(含北、南、東西側)"),
    }
    ac_kw = {}
    for name, (hint, exact) in sus_cfg.items():
        if exact:
            matched = df_basic[df_basic["館舍名稱"] == exact]
        else:
            matched = df_basic[df_basic["館舍名稱"].str.contains(hint, na=False)]
        val = matched["人員空調使用用電"].sum() if not matched.empty else 0
        if val > 0:
            ac_kw[name] = val
        else:
            ac_kw[name] = max(base.loc[analysis_mask, f"{name}_proxy"].dropna().mean(), 0)

    return base, T_ops, n_years, hrs_ops, t_set_spring, t_set_fall, ac_kw, analysis_mask


base_df, T_OPS, N_YEARS, HRS_OPS, t_set_spring, t_set_fall, AC_KW, analysis_mask = load_all()


# ════════════════════════════════════════════════════════════════════
# SAVINGS COMPUTATION
# ════════════════════════════════════════════════════════════════════

def compute_savings(target_t: float) -> pd.DataFrame:
    rows = []
    for name in BLDG_LIST:
        t0 = t_set_spring[name]
        ac_kw = AC_KW[name]
        cdh_t0  = (T_OPS - t0).clip(min=0).sum() / N_YEARS
        cdh_tgt = (T_OPS - target_t).clip(min=0).sum() / N_YEARS
        sf = max(0.0, min(1.0, 1 - cdh_tgt / cdh_t0)) if cdh_t0 > 0 else 0.0
        if target_t <= t0:
            sf = 0.0
        kwh = ac_kw * sf * HRS_OPS
        rows.append({
            "棟別": name,
            "空調負載 (kW)": int(round(ac_kw)),
            "現行 T* (°C)": round(t0, 1),
            "差距 (°C)": round(target_t - t0, 1),
            "節電比例": sf,
            "年節電量 (MWh)": round(kwh / 1000, 1),
            "年節費 (萬元)": round(kwh * TARIFF / 1e4, 1),
            "年減碳 (公噸 CO₂)": round(kwh * EMISSION / 1e3, 1),
        })
    return pd.DataFrame(rows)


# ════════════════════════════════════════════════════════════════════
# FIGURE BUILDERS
# ════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def fig_annual_trend():
    fig = make_subplots(rows=2, cols=3, subplot_titles=BLDG_LIST)
    for i, name in enumerate(BLDG_LIST):
        r, c = divmod(i, 3)
        s = base_df[name]
        annual = s.resample("YE").sum() / 1000
        annual = annual[annual.index.year <= 2025]
        fig.add_trace(go.Bar(
            x=annual.index.year.tolist(), y=annual.values.tolist(),
            marker_color=BLDG_COLORS[name], showlegend=False,
            hovertemplate="%{x}年: %{y:.0f} MWh<extra>" + name + "</extra>",
        ), row=r + 1, col=c + 1)
    fig.update_layout(title_text="各棟年度合計用電量（2016–2025）", height=480,
                      plot_bgcolor="#fafafa", paper_bgcolor="white")
    fig.update_xaxes(tickmode="linear", dtick=2)
    fig.update_yaxes(title_text="MWh")
    return fig


@st.cache_data(show_spinner=False)
def fig_load_curve():
    configs = [
        (0, "spring", "上課日（春學期）", "#e74c3c", 2.5),
        (0, "fall",   "上課日（秋學期）", "#e67e22", 2.0),
        (2, None,     "例假日",           "#3498db", 1.5),
        (3, None,     "寒暑假",           "#95a5a6", 1.5),
    ]
    fig = make_subplots(rows=2, cols=3, subplot_titles=BLDG_LIST, shared_xaxes=True)
    shown = set()
    for i, name in enumerate(BLDG_LIST):
        r, c = divmod(i, 3)
        s = base_df[name]
        df_tmp = pd.DataFrame({"kw": s, "hour": s.index.hour,
                               "day_type": base_df["day_type"], "season": base_df["season"]})
        for dt, sv, label, color, lw in configs:
            sub = df_tmp[df_tmp["day_type"] == dt]
            if sv:
                sub = sub[sub["season"] == sv]
            curve = sub.groupby("hour")["kw"].mean()
            fig.add_trace(go.Scatter(
                x=curve.index.tolist(), y=curve.values.tolist(), mode="lines",
                name=label, line=dict(color=color, width=lw),
                showlegend=(label not in shown), legendgroup=label,
            ), row=r + 1, col=c + 1)
            shown.add(label)
    fig.update_layout(title_text="各棟日負載曲線", height=480,
                      plot_bgcolor="#fafafa", paper_bgcolor="white",
                      legend=dict(orientation="h", y=1.05))
    fig.update_xaxes(title_text="時刻", tickmode="linear", dtick=4)
    return fig


@st.cache_data(show_spinner=False)
def fig_heatmap(building: str):
    s = base_df[building]
    df_tmp = pd.DataFrame({"kw": s, "month": s.index.month, "hour": s.index.hour})
    pivot = df_tmp.groupby(["hour", "month"])["kw"].mean().unstack("month")
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=months,
        y=[f"{h:02d}:00" for h in range(24)],
        colorscale="RdYlGn_r", colorbar=dict(title="avg kW"),
        hovertemplate="月份: %{x}<br>時刻: %{y}<br>平均用電: %{z:.1f} kW<extra></extra>",
    ))
    fig.update_layout(title=f"{building} — 月份 × 時刻 平均用電 (kW)",
                      yaxis=dict(autorange="reversed"), height=420,
                      plot_bgcolor="#fafafa", paper_bgcolor="white")
    return fig


@st.cache_data(show_spinner=False)
def fig_setpoint_compare():
    sp = [t_set_spring[n] for n in BLDG_LIST]
    fa = [t_set_fall[n]   for n in BLDG_LIST]
    fig = go.Figure([
        go.Bar(name="下學期 T* (2–6月)", x=BLDG_LIST, y=sp,
               marker_color=[BLDG_COLORS[n] for n in BLDG_LIST],
               text=[f"{v:.1f}°C" for v in sp], textposition="outside",
               hovertemplate="%{x}<br>下學期 T*: %{y:.1f}°C<extra></extra>"),
        go.Bar(name="上學期 T* (9–12月)", x=BLDG_LIST, y=fa,
               marker_color=[BLDG_COLORS[n] for n in BLDG_LIST],
               marker_pattern_shape="/", opacity=0.5,
               text=[f"{v:.1f}°C" for v in fa], textposition="outside",
               hovertemplate="%{x}<br>上學期 T*: %{y:.1f}°C<extra></extra>"),
    ])
    fig.add_hline(y=26, line_dash="dash", line_color="red", line_width=2,
                  annotation_text="政府標準 26°C", annotation_font_color="red",
                  annotation_position="top right")
    fig.update_layout(title="各棟推估冷氣室外啟動門檻 T*", barmode="group",
                      yaxis=dict(title="T* (°C)", range=[16, 33]), height=420,
                      plot_bgcolor="#fafafa", paper_bgcolor="white",
                      legend=dict(orientation="h", y=1.05))
    return fig


@st.cache_data(show_spinner=False)
def fig_scatter(building: str):
    proxy_col = f"{building}_proxy"
    rng = np.random.default_rng(42)
    fig = make_subplots(rows=1, cols=2, subplot_titles=["下學期（2–6月）", "上學期（9–12月）"],
                        shared_yaxes=True)
    color = BLDG_COLORS[building]
    for col_i, (season_val, t_set) in enumerate([
        ("spring", t_set_spring[building]),
        ("fall",   t_set_fall[building]),
    ], 1):
        mask = analysis_mask & (base_df["season"] == season_val)
        sub = base_df[mask]
        T, Y = sub["T"].values, sub[proxy_col].values
        valid = ~(np.isnan(T) | np.isnan(Y))
        idx = np.where(valid)[0]
        samp = rng.choice(idx, size=min(2000, len(idx)), replace=False)
        fig.add_trace(go.Scatter(
            x=T[samp].tolist(), y=Y[samp].tolist(), mode="markers",
            marker=dict(color=color, opacity=0.15, size=4),
            name="數據點", showlegend=(col_i == 1),
        ), row=1, col=col_i)
        if valid.sum() > 20:
            Tv, Yv = T[valid], Y[valid]
            bins = np.arange(int(Tv.min()), int(Tv.max()) + 1, 0.5)
            med, edges, _ = scipy_stats.binned_statistic(Tv, Yv, statistic="median", bins=bins)
            fig.add_trace(go.Scatter(
                x=((edges[:-1] + edges[1:]) / 2).tolist(), y=med.tolist(),
                mode="lines", line=dict(color="orange", width=2),
                name="每0.5°C中位數", showlegend=(col_i == 1),
            ), row=1, col=col_i)
            if not np.isnan(t_set):
                for seg, sc in [(Tv <= t_set, "navy"), (Tv > t_set, "tomato")]:
                    if seg.sum() >= 2:
                        s_, i_, *_ = scipy_stats.linregress(Tv[seg], Yv[seg])
                        xs = np.linspace(Tv[seg].min(), Tv[seg].max(), 80)
                        fig.add_trace(go.Scatter(
                            x=xs.tolist(), y=(s_ * xs + i_).tolist(), mode="lines",
                            line=dict(color=sc, width=2), showlegend=False,
                        ), row=1, col=col_i)
        if not np.isnan(t_set):
            fig.add_vline(x=t_set, line_dash="dash", line_color="gold", line_width=2.5,
                          annotation_text=f"T* = {t_set:.1f}°C",
                          annotation_font_color="goldenrod", row=1, col=col_i)
    fig.update_layout(title=f"{building} — AC Proxy vs 室外溫度", height=420,
                      plot_bgcolor="#fafafa", paper_bgcolor="white",
                      legend=dict(orientation="h", y=1.08))
    fig.update_xaxes(title_text="室外溫度 (°C)")
    fig.update_yaxes(title_text="AC Proxy (kW)", col=1)
    return fig


def fig_savings_bar(df_sav: pd.DataFrame):
    mwh = df_sav["年節電量 (MWh)"].tolist()
    pct = [f"{v:.1%}" for v in df_sav["節電比例"].tolist()]
    fig = go.Figure(go.Bar(
        x=df_sav["棟別"].tolist(), y=mwh,
        marker_color=[BLDG_COLORS[n] for n in BLDG_LIST],
        text=[f"{m:.0f} MWh\n({p})" for m, p in zip(mwh, pct)],
        textposition="outside",
        hovertemplate="%{x}<br>年節電: %{y:.1f} MWh<extra></extra>",
    ))
    fig.add_annotation(
        text=f"六棟合計：<b>{sum(mwh):.0f} MWh/yr</b>",
        xref="paper", yref="paper", x=0.98, y=0.96,
        showarrow=False, font=dict(size=13),
        bgcolor="rgba(255,255,255,0.85)", bordercolor="#ccc", borderwidth=1,
    )
    fig.update_layout(title="各棟年節電量（依目標設定溫度試算）",
                      yaxis=dict(title="年節電量 (MWh)"), height=380,
                      plot_bgcolor="#fafafa", paper_bgcolor="white")
    return fig


# ════════════════════════════════════════════════════════════════════
# PAGE LAYOUT
# ════════════════════════════════════════════════════════════════════

st.title("🏫 臺大空調用電減排效益分析儀表板")
st.caption("114-2 環境與能源的資料科學 · 第三組　邱雲茗、李適軒、楊思柔、呂沐田、李怡慧、黃宗軒")
st.divider()

# KPI cards
df_kpi = compute_savings(26.0)
avg_t  = np.mean([t_set_spring[n] for n in BLDG_LIST])
k1, k2, k3, k4 = st.columns(4)
k1.metric("六棟平均下學期 T*",      f"{avg_t:.1f} °C",  "室外啟動門檻（春季）")
k2.metric("調至 26°C 年節電",        f"{df_kpi['年節電量 (MWh)'].sum():.0f} MWh",   "六棟合計 / 年")
k3.metric("年節省電費",              f"{df_kpi['年節費 (萬元)'].sum():.0f} 萬元",    "電價 3.5 元/kWh")
k4.metric("年減碳效益",              f"{df_kpi['年減碳 (公噸 CO₂)'].sum():.0f} 公噸 CO₂", "排放係數 0.494 kg/kWh")

st.divider()

tab_eda, tab_setpoint, tab_savings = st.tabs(["📊 用電趨勢 EDA", "🌡️ 設定溫度推估", "💡 節電試算（互動）"])

# ── Tab 1: EDA ───────────────────────────────────────────────────────
with tab_eda:
    st.plotly_chart(fig_annual_trend(), use_container_width=True)
    st.plotly_chart(fig_load_curve(),   use_container_width=True)
    st.subheader("月份 × 時刻 用電熱圖")
    bldg_hm = st.selectbox("選擇建物", BLDG_LIST, key="heatmap_sel")
    st.plotly_chart(fig_heatmap(bldg_hm), use_container_width=True)

# ── Tab 2: Setpoint ──────────────────────────────────────────────────
with tab_setpoint:
    st.plotly_chart(fig_setpoint_compare(), use_container_width=True)
    with st.expander("方法說明"):
        st.markdown("""
**冷天基礎扣除法**：以上課日、08–21h、室外溫度 < 20°C 的中位數用電作為非空調基礎負載，
相減後得到 AC proxy。
**分段線性回歸**：對 20–30°C 搜尋使兩段 RSS 之和最小的轉折點 T*，即推估的室外啟動門檻。
T* 為**室外**啟動門檻，非室內設定溫度（室內設定 ≈ T* + 1–3°C）。
政府標準為室內 26°C，**下學期 T* 低於 26°C 代表存在節電空間**。
        """)
    st.subheader("各棟拐點散佈圖")
    bldg_sc = st.selectbox("選擇建物", BLDG_LIST, key="scatter_sel")
    st.plotly_chart(fig_scatter(bldg_sc), use_container_width=True)

# ── Tab 3: Savings calculator ────────────────────────────────────────
with tab_savings:
    st.subheader("目標室外啟動門檻溫度")
    st.caption("拖動滑桿調整目標溫度；當目標高於某棟現行 T* 時，該棟才有節電效益。")

    target_t = st.slider(
        "目標溫度 (°C)",
        min_value=20.0, max_value=30.0, value=26.0, step=0.5,
        format="%.1f °C",
    )

    df_sav = compute_savings(target_t)

    already_met = [n for n in BLDG_LIST if target_t <= t_set_spring[n]]
    if already_met:
        st.warning(f"**{' / '.join(already_met)}** 的現行 T* ≥ 目標溫度，節電效益為零（已達標或目標過低）。")

    st.plotly_chart(fig_savings_bar(df_sav), use_container_width=True)

    # Totals
    c1, c2, c3 = st.columns(3)
    c1.metric("六棟合計年節電量", f"{df_sav['年節電量 (MWh)'].sum():.1f} MWh")
    c2.metric("六棟合計年節費",   f"{df_sav['年節費 (萬元)'].sum():.1f} 萬元")
    c3.metric("六棟合計年減碳",   f"{df_sav['年減碳 (公噸 CO₂)'].sum():.1f} 公噸 CO₂")

    st.subheader("各棟節電效益明細")
    display_df = df_sav.copy()
    display_df["節電比例"] = display_df["節電比例"].map("{:.1%}".format)
    display_df["差距 (°C)"] = display_df["差距 (°C)"].map(lambda x: f"+{x:.1f}" if x >= 0 else f"{x:.1f}")
    st.dataframe(display_df, use_container_width=True, hide_index=True)
