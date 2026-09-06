from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = ROOT / "sql"
DB_NAME = "park_ads"

BLUE_SEQUENTIAL = [
    [0.00, "#cde2fb"],
    [0.25, "#86b6ef"],
    [0.50, "#3987e5"],
    [0.75, "#1c5cab"],
    [1.00, "#0d366b"],
]
COLOR_WEEKDAY = "#2a78d6"
COLOR_WEEKEND = "#eb6834"
INK_MUTED = "#898781"
INK_PRIMARY = "#0b0b0b"
INK_ON_DARK = "#fcfcfb"


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _srgb_to_linear(c):
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color):
    r, g, b = _hex_to_rgb(hex_color)
    return 0.2126 * _srgb_to_linear(r) + 0.7152 * _srgb_to_linear(g) + 0.0722 * _srgb_to_linear(b)


def _contrast_ratio(hex1, hex2):
    l1, l2 = _relative_luminance(hex1), _relative_luminance(hex2)
    l1, l2 = max(l1, l2), min(l1, l2)
    return (l1 + 0.05) / (l2 + 0.05)


def _interpolated_color(t, stops):
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t0 <= t <= t1:
            frac = (t - t0) / (t1 - t0) if t1 > t0 else 0
            r0, g0, b0 = _hex_to_rgb(c0)
            r1, g1, b1 = _hex_to_rgb(c1)
            r = r0 + (r1 - r0) * frac
            g = g0 + (g1 - g0) * frac
            b = b0 + (b1 - b0) * frac
            return f"#{int(r):02x}{int(g):02x}{int(b):02x}"
    return stops[-1][1]


def best_text_color(cell_hex):
    if _contrast_ratio(cell_hex, INK_ON_DARK) > _contrast_ratio(cell_hex, INK_PRIMARY):
        return INK_ON_DARK
    return INK_PRIMARY

SEGMENT_ORDER = ["toddlers", "kids", "teens", "adults", "seniors"]
SEGMENT_LABELS = {
    "toddlers": "Малыши (0-3)",
    "kids": "Дети (4-11)",
    "teens": "Подростки (12-15)",
    "adults": "Взрослые (16-59)",
    "seniors": "Пожилые (60+)",
}
WEEKDAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

st.set_page_config(page_title="Ad Placement Analytics - детский парк ТРЦ", layout="wide")


@st.cache_resource
def get_engine():
    return create_engine(f"postgresql+psycopg2:///{DB_NAME}")


@st.cache_data
def run_sql_file(filename: str) -> pd.DataFrame:
    sql = (SQL_DIR / filename).read_text()
    return pd.read_sql_query(text(sql), get_engine())


@st.cache_data
def run_sql(query: str, params: dict | None = None) -> pd.DataFrame:
    return pd.read_sql_query(text(query), get_engine(), params=params or {})


st.title("Аналитика размещения рекламы в детском парке ТРЦ")
st.caption(
    "Данные: синтетический датасет, 2026-06-01 – 2026-08-31 (см. docs/data_assumptions.md). "
    "Бренды: Coca-Cola, Lay's, Snickers, Air Astana, Freedom Bank."
)

st.header("1. Профиль аудитории по зонам")
st.caption("% посетителей зоны, приходящихся на каждый сегмент аудитории, за весь период наблюдения.")

profile = run_sql_file("02_audience_profile.sql")
pivot = profile.pivot(index="zone", columns="segment", values="pct_of_zone_traffic").fillna(0)
pivot = pivot[[s for s in SEGMENT_ORDER if s in pivot.columns]]
zone_order = profile.groupby("zone")["visitors"].sum().sort_values(ascending=False).index
pivot = pivot.loc[zone_order]

NAN = float("nan")
zmin, zmax = float(pivot.values.min()), float(pivot.values.max())


def is_light_text(v):
    t = (v - zmin) / (zmax - zmin) if zmax > zmin else 0
    cell_color = _interpolated_color(t, BLUE_SEQUENTIAL)
    return best_text_color(cell_color) == INK_PRIMARY


def masked(keep_if_light: bool):
    z_rows, text_rows = [], []
    for row in pivot.values:
        z_row, text_row = [], []
        for v in row:
            keep = is_light_text(v) == keep_if_light
            z_row.append(v if keep else NAN)
            text_row.append(f"{v:.0f}%" if keep else "")
        z_rows.append(z_row)
        text_rows.append(text_row)
    return z_rows, text_rows


z_light, text_light = masked(keep_if_light=True)
z_dark, text_dark = masked(keep_if_light=False)

heatmap_common = dict(
    x=[SEGMENT_LABELS[s] for s in pivot.columns],
    y=pivot.index,
    colorscale=BLUE_SEQUENTIAL,
    zmin=zmin,
    zmax=zmax,
    texttemplate="%{text}",
    hovertemplate="Зона: %{y}<br>Сегмент: %{x}<br>Доля: %{z:.1f}%<extra></extra>",
)
fig_heatmap = go.Figure()
fig_heatmap.add_trace(go.Heatmap(
    z=z_light, text=text_light, **heatmap_common,
    textfont=dict(size=13, color=INK_PRIMARY), colorbar=dict(title="%"),
))
fig_heatmap.add_trace(go.Heatmap(
    z=z_dark, text=text_dark, **heatmap_common,
    textfont=dict(size=13, color=INK_ON_DARK), showscale=False,
))
fig_heatmap.update_layout(
    height=380,
    margin=dict(l=10, r=10, t=10, b=10),
    plot_bgcolor="#fcfcfb",
    paper_bgcolor="#fcfcfb",
    font=dict(color=INK_PRIMARY),
    yaxis=dict(autorange="reversed", automargin=True),
    xaxis=dict(automargin=True),
)
st.plotly_chart(fig_heatmap, width="stretch", theme=None)
with st.expander("Показать таблицей"):
    st.dataframe(pivot.style.format("{:.1f}%"), width="stretch")

st.header("2. Бренд × зона: расчётная эффективность и рекомендации")
st.caption(
    "match_score - совпадение состава аудитории зоны с таргетингом бренда (0..1). "
    "Строки, запрещённые бизнес-правилами (`zone_category_restrictions`), в таблице отсутствуют."
)

matching = run_sql_file("03_brand_zone_matching.sql")
recommendations = run_sql_file("05_recommendations.sql")
placements = run_sql(
    """
    SELECT b.name AS brand, z.name AS zone, p.start_date, p.end_date, p.cost_total
    FROM placements p
    JOIN brands b ON b.id = p.brand_id
    JOIN zones z ON z.id = p.zone_id
    """
)

table = matching.merge(
    placements[["brand", "zone"]].drop_duplicates().assign(is_current=True),
    on=["brand", "zone"], how="left",
)
table["is_current"] = table["is_current"].fillna(False)

reloc_pairs = set(zip(recommendations["brand"], recommendations["current_zone"]))


def status(row):
    if row["rank_for_brand"] == 1:
        return "Лучшая зона для бренда"
    if row["is_current"] and (row["brand"], row["zone"]) in reloc_pairs:
        return "Размещено, рекомендован перенос"
    if row["is_current"]:
        return "Размещено, есть вариант лучше"
    return ""


table["Статус"] = table.apply(status, axis=1)
table = table.rename(columns={
    "brand": "Бренд", "category": "Категория", "zone": "Зона",
    "match_score": "Match score", "rank_for_brand": "Ранг у бренда",
})

brand_filter = st.selectbox("Фильтр по бренду", ["Все бренды"] + sorted(table["Бренд"].unique()))
view = table if brand_filter == "Все бренды" else table[table["Бренд"] == brand_filter]

st.dataframe(
    view[["Бренд", "Категория", "Зона", "Match score", "Ранг у бренда", "Статус"]]
        .sort_values(["Бренд", "Match score"], ascending=[True, False]),
    width="stretch",
    hide_index=True,
    column_config={
        "Match score": st.column_config.ProgressColumn(
            "Match score", format="%.3f", min_value=0, max_value=1
        ),
    },
)

if not recommendations.empty:
    with st.expander(f"Детали рекомендаций по переносу ({len(recommendations)})"):
        st.dataframe(recommendations, width="stretch", hide_index=True)

st.header("3. Динамика трафика")

zones_list = run_sql("SELECT name FROM zones ORDER BY name")["name"].tolist()
zone_choice = st.selectbox("Зона", ["Все зоны"] + zones_list)
zone_param = None if zone_choice == "Все зоны" else zone_choice

daily = run_sql(
    """
    SELECT zt.date AS date, SUM(zt.visitor_count) AS visitors
    FROM zone_traffic zt
    JOIN zones z ON z.id = zt.zone_id
    WHERE (:zone IS NULL OR z.name = :zone)
    GROUP BY zt.date
    """,
    {"zone": zone_param},
)
hourly = run_sql(
    """
    SELECT zt.hour AS hour, zt.date AS date, SUM(zt.visitor_count) AS visitors
    FROM zone_traffic zt
    JOIN zones z ON z.id = zt.zone_id
    WHERE (:zone IS NULL OR z.name = :zone)
    GROUP BY zt.hour, zt.date
    """,
    {"zone": zone_param},
)

daily["date"] = pd.to_datetime(daily["date"])
daily["weekday_idx"] = daily["date"].dt.weekday
daily["day_type"] = daily["weekday_idx"].apply(lambda i: "Выходные" if i >= 5 else "Будни")
hourly["date"] = pd.to_datetime(hourly["date"])
hourly["day_type"] = hourly["date"].dt.weekday.apply(lambda i: "Выходные" if i >= 5 else "Будни")

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("По часам суток")
    by_hour = hourly.groupby(["hour", "day_type"])["visitors"].mean().round().astype(int).reset_index()
    fig_hour = go.Figure()
    for day_type, color in [("Будни", COLOR_WEEKDAY), ("Выходные", COLOR_WEEKEND)]:
        sub = by_hour[by_hour["day_type"] == day_type].sort_values("hour")
        fig_hour.add_trace(go.Scatter(
            x=sub["hour"], y=sub["visitors"], mode="lines+markers",
            name=day_type, line=dict(color=color, width=2), marker=dict(size=6),
            hovertemplate="%{x}:00 - %{y} чел.<extra></extra>",
        ))
    fig_hour.update_layout(
        height=360, margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb", font=dict(color=INK_PRIMARY),
        xaxis_title="Час", yaxis_title="Средний трафик (чел.)",
        xaxis=dict(automargin=True), yaxis=dict(automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_hour, width="stretch", theme=None)

with col_b:
    st.subheader("По дням недели")
    by_weekday = daily.groupby("weekday_idx")["visitors"].mean().round().astype(int).reset_index()
    by_weekday["label"] = by_weekday["weekday_idx"].apply(lambda i: WEEKDAY_NAMES[i])
    by_weekday["color"] = by_weekday["weekday_idx"].apply(
        lambda i: COLOR_WEEKEND if i >= 5 else COLOR_WEEKDAY
    )
    fig_week = go.Figure(go.Bar(
        x=by_weekday["label"], y=by_weekday["visitors"],
        marker_color=by_weekday["color"],
        hovertemplate="%{x}: %{y:.0f} чел.<extra></extra>",
    ))
    fig_week.update_layout(
        height=360, margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb", font=dict(color=INK_PRIMARY),
        yaxis_title="Средний трафик (чел./день)",
        xaxis=dict(automargin=True), yaxis=dict(automargin=True),
    )
    st.plotly_chart(fig_week, width="stretch", theme=None)

st.caption("Синий - будни, оранжевый - выходные (единое цветовое соответствие для обоих графиков).")
