"""RoadPulse interactive dashboard (Dash + Plotly)."""
from __future__ import annotations

from dash import Dash, Input, Output, callback, dash_table, dcc, html
import pandas as pd
import plotly.express as px

from roadpulse.config import DEMO_DIR, PROCESSED_DIR

COLORS = {"bg": "#07111f", "panel": "#0e1b2d", "text": "#eef5ff", "muted": "#91a4be", "cyan": "#2dd4bf", "orange": "#fb923c", "red": "#fb7185"}


def load_table(name: str) -> pd.DataFrame:
    parquet = PROCESSED_DIR / f"{name}.parquet"
    csv = DEMO_DIR / f"{name}.csv"
    return pd.read_parquet(parquet) if parquet.exists() else pd.read_csv(csv)


yearly, states, counties, temporal, weather = (load_table(n) for n in ("yearly", "state", "county", "temporal", "weather"))
IS_DEMO = not (PROCESSED_DIR / "yearly.parquet").exists()
US_STATES = {"KS":"Kansas","MO":"Missouri","CT":"Connecticut","RI":"Rhode Island","GA":"Georgia","IA":"Iowa","MS":"Mississippi","KY":"Kentucky","WI":"Wisconsin","MD":"Maryland","TX":"Texas","PA":"Pennsylvania","LA":"Louisiana","DC":"District of Columbia","AZ":"Arizona","SC":"South Carolina","NE":"Nebraska","NC":"North Carolina","OK":"Oklahoma","DE":"Delaware"}


def style(fig, title: str):
    fig.update_layout(title=title, paper_bgcolor=COLORS["panel"], plot_bgcolor=COLORS["panel"], font_color=COLORS["text"], margin=dict(l=35,r=20,t=55,b=35), hoverlabel=dict(bgcolor="#172a42"), legend_title_text="")
    fig.update_xaxes(gridcolor="#20334c", zeroline=False); fig.update_yaxes(gridcolor="#20334c", zeroline=False)
    return fig


def card(label: str, value: str, note: str, accent: str = "cyan"):
    return html.Div([html.P(label, className="kpi-label"), html.H2(value), html.P(note, className="kpi-note")], className=f"kpi {accent}")


app = Dash(__name__, title="RoadPulse | US Accident Intelligence", suppress_callback_exceptions=True)
server = app.server
app.layout = html.Div([
    html.Header([html.Div([html.Span("ROAD", className="brand"), html.Span("PULSE", className="brand pulse")]), html.P("US Accident Intelligence • 2016–2023", className="subtitle")]),
    html.Div("DEMO SNAPSHOT • Run the pipeline for the full dashboard. Geography and annual figures come from the completed notebook; temporal/weather panels are clearly marked illustrative." if IS_DEMO else "FULL PROCESSED DATA • Generated locally from the source dataset.", className="mode-banner"),
    html.Div([html.Label("Comparable analytical source"), dcc.Dropdown(sorted(yearly.Source.unique()), "Source2", id="source", clearable=False), html.Label("Minimum observations"), dcc.Slider(100, 5000, 100, value=500, id="minimum", marks={100:"100",500:"500",2000:"2k",5000:"5k"}), html.Div("Why Source2? Source collection methods have radically different severity mixes. Source2 is used for apples-to-apples geographic and temporal comparisons.", className="callout")], className="controls"),
    dcc.Tabs(id="tabs", value="overview", children=[dcc.Tab(label="Executive overview", value="overview"), dcc.Tab(label="Geographic priorities", value="geo"), dcc.Tab(label="Risk conditions", value="risk"), dcc.Tab(label="Data trust", value="trust")]),
    html.Main(id="page")
], className="shell")


@callback(Output("page", "children"), Input("tabs", "value"), Input("source", "value"), Input("minimum", "value"))
def render(tab: str, source: str, minimum: int):
    y = yearly[yearly.Source.eq(source)].sort_values("year")
    s = states[(states.Source.eq(source)) & (states.total_accidents.ge(minimum))].sort_values("severe_rate", ascending=False)
    c = counties[(counties.Source.eq(source)) & (counties.total_accidents.ge(minimum))].sort_values("severe_rate", ascending=False)
    total, severe = int(y.total_accidents.sum()), int(y.severe_accidents.sum())
    rate = 100 * severe / total if total else 0
    if tab == "overview":
        trend = style(px.line(y, x="year", y="severe_rate", markers=True, custom_data=["total_accidents","severe_accidents"]), "Comparable severe-accident rate over time")
        trend.update_traces(line_color=COLORS["cyan"], hovertemplate="%{x}: %{y:.2f}%<br>Total: %{customdata[0]:,}<br>Severe: %{customdata[1]:,}<extra></extra>")
        volume = style(px.bar(y, x="year", y=["severe_accidents","total_accidents"], barmode="group", color_discrete_sequence=[COLORS["red"],"#355c85"]), "Reported volume and severe subset")
        return html.Div([html.Div([card("Comparable records",f"{total/1e6:.2f}M","Selected source and years"),card("Severe records",f"{severe/1e6:.2f}M","Severity levels 3–4","orange"),card("Severe-record rate",f"{rate:.2f}%","Not a crash probability","red"),card("Coverage",f"{int(y.year.min())}–{int(y.year.max())}","Latest year may be partial")],className="kpis"),html.Div([dcc.Graph(figure=trend),dcc.Graph(figure=volume)],className="grid2"),html.Div([html.H3("Decision signal"),html.P("Use stable-source rates to prioritize deeper engineering and exposure-adjusted studies. Never interpret raw state totals as road danger: population, vehicle miles travelled, reporting coverage, and source mix are not controlled here.")],className="insight")])
    if tab == "geo":
        top=s.head(15).copy(); top["state_name"]=top.State.map(US_STATES).fillna(top.State)
        bars=style(px.bar(top.sort_values("severe_rate"),x="severe_rate",y="state_name",orientation="h",color="severe_rate",color_continuous_scale="Tealgrn",custom_data=["total_accidents","ci_low","ci_high"]),f"Highest severe-record rates (n ≥ {minimum:,})")
        bars.update_traces(hovertemplate="%{y}: %{x:.2f}%<br>n=%{customdata[0]:,}<br>95% CI %{customdata[1]:.2f}–%{customdata[2]:.2f}%<extra></extra>")
        cols=[{"name":x,"id":x} for x in ["State","County","total_accidents","severe_accidents","severe_rate","ci_low","ci_high"]]
        return html.Div([html.Div([dcc.Graph(figure=bars),html.Div([html.H3("County investigation queue"),dash_table.DataTable(c.head(25).to_dict("records"),cols,sort_action="native",filter_action="native",page_size=12,style_table={"overflowX":"auto"},style_cell={"backgroundColor":COLORS["panel"],"color":COLORS["text"],"border":"1px solid #20334c","padding":"8px"},style_header={"backgroundColor":"#172a42","fontWeight":"bold"})],className="panel")],className="grid2"),html.Div("Rates are filtered by sample size and include Wilson intervals, but remain descriptive. Join exposure and fatality data before allocating safety funding.",className="callout")])
    if tab == "risk":
        heat=temporal.pivot_table(index="day_of_week",columns="hour",values="severe_rate",aggfunc="mean").reindex(["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"])
        heatfig=style(px.imshow(heat,aspect="auto",color_continuous_scale="YlOrRd",labels={"color":"Severe %"}),"When severe records concentrate")
        w=weather.sort_values("severe_rate",ascending=False).head(20)
        weatherfig=style(px.bar(w.sort_values("severe_rate"),x="severe_rate",y="weather_category",color="visibility_band",orientation="h",hover_data=["total_accidents"]),"Weather and visibility risk profile")
        demo_note = html.Div("Illustrative component preview: run `python -m roadpulse.pipeline` before interpreting these two panels.", className="callout") if IS_DEMO else None
        return html.Div([demo_note,html.Div([dcc.Graph(figure=heatfig),dcc.Graph(figure=weatherfig)],className="grid2"),html.Div([html.H3("How to act"),html.P("Use the heatmap for patrol and incident-response scheduling, and weather/visibility cuts for targeted warnings. These are associations in reported incidents—not causal effects—and should be validated with traffic exposure.")],className="insight")])
    source_rates=yearly.groupby("Source",as_index=False)[["total_accidents","severe_accidents"]].sum(); source_rates["severe_rate"]=100*source_rates.severe_accidents/source_rates.total_accidents
    sf=style(px.bar(source_rates,x="Source",y="severe_rate",color="Source",text_auto=".2f"),"Why naive comparisons fail: severity mix by source")
    return html.Div([html.Div([card("Raw dataset","7.73M","Reported accidents after cleaning"),card("Source1 severe rate","8.13%","Large mix shift over time"),card("Source2 severe rate","33.92%","Comparison basis","orange"),card("Cramér’s V","0.0416","Weather × severity: weak association")],className="kpis"),dcc.Graph(figure=sf),html.Div([html.H3("Interpretation guardrails"),html.Ul([html.Li("Coverage is not a census; reporting mechanisms, geography, and years differ."),html.Li("Severity means traffic impact (levels 1–4), not injury or fatality severity."),html.Li("2023 contains Source1 only and is partial; exclude it from source-comparable trends."),html.Li("Statistical significance is expected at 7.7M rows; effect size and practical importance matter."),html.Li("No causal or per-driver risk claims without exposure denominators such as VMT.")])],className="insight")])


if __name__ == "__main__":
    app.run(debug=True)
