"""RoadPulse interactive dashboard built from validated project aggregates."""
from __future__ import annotations

from pathlib import Path

from dash import Dash, Input, Output, callback, dash_table, dcc, html
import numpy as np
import pandas as pd
import plotly.express as px

DATA = Path(__file__).parent / "data" / "dashboard"
COLORS = {
    "bg": "#07111f", "panel": "#0e1b2d", "text": "#eef5ff",
    "muted": "#91a4be", "cyan": "#2dd4bf", "orange": "#fb923c",
    "red": "#fb7185", "blue": "#60a5fa",
}
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name)


def rate(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["Severe_Rate"] = 100 * result["Severe_Accidents"] / result["Total_Accidents"]
    return result


trend = rate(load("state_trend_source2.csv"))
states = rate(load("state_rank_source2.csv"))
state_year = rate(load("state_summary.csv"))
counties = rate(load("counties.csv"))
temporal = rate(load("temporal.csv"))
conditions = rate(load("conditions.csv"))
road_features = rate(load("road_features.csv"))
compound = rate(load("compound_risk.csv"))
severity = load("severity_stats.csv")

TOTAL = int(severity["Count"].sum())
SEVERE = int(severity.loc[severity["Severity"].isin([3, 4]), "Count"].sum())


def style(fig, title: str, subtitle: str | None = None):
    fig.update_layout(
        title={"text": title + (f"<br><sup>{subtitle}</sup>" if subtitle else "")},
        paper_bgcolor=COLORS["panel"], plot_bgcolor=COLORS["panel"],
        font_color=COLORS["text"], margin=dict(l=35, r=25, t=75, b=40),
        hoverlabel=dict(bgcolor="#172a42"), legend_title_text="",
    )
    fig.update_xaxes(gridcolor="#20334c", zeroline=False)
    fig.update_yaxes(gridcolor="#20334c", zeroline=False)
    return fig


def card(label: str, value: str, note: str, accent: str = "cyan"):
    return html.Div([
        html.P(label, className="kpi-label"), html.H2(value),
        html.P(note, className="kpi-note"),
    ], className=f"kpi {accent}")


app = Dash(__name__, title="RoadPulse | US Accident Intelligence", suppress_callback_exceptions=True)
server = app.server
app.layout = html.Div([
    html.Header([
        html.Div([html.Span("ROAD", className="brand"), html.Span("PULSE", className="brand pulse")]),
        html.P("US Accident Intelligence • 7.7M reported incidents", className="subtitle"),
    ]),
    html.Div("REAL AGGREGATED DATA • Generated from the complete US Accidents 2016–2023 dataset", className="mode-banner"),
    html.Div([
        html.Label("Minimum observations"),
        dcc.Slider(100, 5000, 100, value=500, id="minimum", marks={100: "100", 500: "500", 2000: "2k", 5000: "5k"}),
        html.Div("Comparable rankings and trends use Source2 only. Other analytical cuts combine sources and are labelled descriptive.", className="callout"),
    ], className="controls compact"),
    dcc.Tabs(id="tabs", value="overview", children=[
        dcc.Tab(label="Executive overview", value="overview"),
        dcc.Tab(label="Geographic priorities", value="geo"),
        dcc.Tab(label="Time & conditions", value="conditions"),
        dcc.Tab(label="Road & compound risk", value="roads"),
        dcc.Tab(label="Data trust", value="trust"),
    ]),
    html.Main(id="page"),
], className="shell")


@callback(Output("page", "children"), Input("tabs", "value"), Input("minimum", "value"))
def render(tab: str, minimum: int):
    if tab == "overview":
        severe_rate = 100 * SEVERE / TOTAL
        source2_total = int(trend["Total_Accidents"].sum())
        source2_severe = int(trend["Severe_Accidents"].sum())
        trend_fig = style(
            px.line(trend, x="Year", y="Severe_Rate", markers=True, custom_data=["Total_Accidents", "Severe_Accidents"]),
            "Comparable severe-record rate", "Source2 only • 2016–2022",
        )
        trend_fig.update_traces(line_color=COLORS["cyan"], line_width=3,
            hovertemplate="%{x}: %{y:.2f}%<br>Total %{customdata[0]:,}<br>Severe %{customdata[1]:,}<extra></extra>")
        impact = severity.melt(id_vars="Severity", value_vars=["Avg_Duration_Min", "Avg_Distance_Mi"], var_name="Metric", value_name="Value")
        impact_fig = style(px.bar(impact, x="Severity", y="Value", color="Metric", barmode="group",
            color_discrete_sequence=[COLORS["orange"], COLORS["blue"]]),
            "Operational impact by severity", "Duration (minutes) and affected distance (miles)")
        return html.Div([
            html.Div([
                card("Reported incidents", f"{TOTAL/1e6:.2f}M", "Complete cleaned dataset"),
                card("Severe records", f"{SEVERE/1e6:.2f}M", "Traffic-impact levels 3–4", "orange"),
                card("Overall severe mix", f"{severe_rate:.2f}%", "Descriptive; source-mix affected", "red"),
                card("Comparable Source2", f"{source2_total/1e6:.2f}M", f"{100*source2_severe/source2_total:.2f}% severe mix"),
            ], className="kpis"),
            html.Div([dcc.Graph(figure=trend_fig), dcc.Graph(figure=impact_fig)], className="grid2"),
            html.Div([html.H3("Executive conclusion"), html.P(
                "Reporting-source composition is the dominant comparability risk. Source2 shows a decline through 2019 followed by a rebound to 34.46% in 2022. Severity 4 incidents create the longest and widest disruption, making duration and affected distance operational priorities."
            )], className="insight"),
        ])

    if tab == "geo":
        ranked = states[states["Total_Accidents"] >= minimum].sort_values("Severe_Rate", ascending=False)
        state_fig = style(px.bar(ranked.head(15).sort_values("Severe_Rate"), x="Severe_Rate", y="State", orientation="h",
            color="Severe_Rate", color_continuous_scale="Tealgrn", custom_data=["Total_Accidents", "Severe_Accidents"]),
            f"Source2 state investigation priorities (n ≥ {minimum:,})", "Comparable reporting source; rate is not population- or VMT-adjusted")
        state_fig.update_traces(hovertemplate="%{y}: %{x:.2f}%<br>Total %{customdata[0]:,}<br>Severe %{customdata[1]:,}<extra></extra>")
        county_volume = counties[counties["Total_Accidents"] >= minimum].nlargest(25, "Total_Accidents")
        columns = [{"name": x.replace("_", " "), "id": x, "type": "numeric" if x not in {"State", "County"} else "text"}
                   for x in ["State", "County", "Total_Accidents", "Severe_Accidents", "Severe_Rate"]]
        return html.Div([
            html.Div([dcc.Graph(figure=state_fig), html.Div([
                html.H3("Highest-volume counties"),
                html.P("All sources • use for workload lookup, not cross-county safety ranking", className="kpi-note"),
                dash_table.DataTable(county_volume.round(2).to_dict("records"), columns, sort_action="native", filter_action="native",
                    page_size=12, style_table={"overflowX": "auto"},
                    style_cell={"backgroundColor": COLORS["panel"], "color": COLORS["text"], "border": "1px solid #20334c", "padding": "8px"},
                    style_header={"backgroundColor": "#172a42", "fontWeight": "bold"}),
            ], className="panel")], className="grid2"),
            html.Div("State rates are Source2-corrected. County output combines sources, so it is deliberately ranked by operational volume rather than severe rate.", className="callout"),
        ])

    if tab == "conditions":
        time = temporal.groupby(["DayOfWeek", "Hour"], as_index=False)[["Total_Accidents", "Severe_Accidents"]].sum()
        time = rate(time)
        matrix = time.pivot(index="DayOfWeek", columns="Hour", values="Severe_Rate").reindex(DAY_ORDER)
        heat = style(px.imshow(matrix, aspect="auto", color_continuous_scale="YlOrRd", labels={"color": "Severe %"}),
            "Reported severe mix by day and hour", "All sources • descriptive scheduling signal")
        weather = conditions[conditions["Total_Accidents"] >= minimum].sort_values("Severe_Rate", ascending=False).head(18)
        weather_fig = style(px.bar(weather.sort_values("Severe_Rate"), x="Severe_Rate", y="Weather_Category",
            color="Visibility_Band", orientation="h", custom_data=["Total_Accidents"]),
            "Weather and visibility combinations", f"All sources • combinations with n ≥ {minimum:,}")
        return html.Div([
            html.Div([dcc.Graph(figure=heat), dcc.Graph(figure=weather_fig)], className="grid2"),
            html.Div([html.H3("How to use this"), html.P(
                "These panels support staffing, messaging, and incident-response hypotheses. They do not prove weather or time causes severe outcomes; exposure volume and source composition are not controlled."
            )], className="insight"),
        ])

    if tab == "roads":
        present = road_features[road_features["Present"]].sort_values("Severe_Rate")
        roads_fig = style(px.bar(present, x="Severe_Rate", y="Feature", orientation="h", color="Total_Accidents",
            color_continuous_scale="Blues", custom_data=["Total_Accidents", "Severe_Accidents"]),
            "Severe mix when a road feature is present", "All sources • association, not causal effect")
        labels = compound.assign(Scenario=lambda x: x["Sunrise_Sunset"] + " • signal=" + x["Traffic_Signal"].astype(str) + " • visibility=" + x["Visibility_Level"])
        comp_fig = style(px.bar(labels.sort_values("Severe_Rate"), x="Severe_Rate", y="Scenario", orientation="h",
            color="Total_Accidents", color_continuous_scale="OrRd", custom_data=["Severe_Accidents"]),
            "Compound operating scenarios", "Day/night × traffic signal × visibility")
        return html.Div([
            html.Div([dcc.Graph(figure=roads_fig), dcc.Graph(figure=comp_fig)], className="grid2"),
            html.Div("Use these combinations to prioritize detailed roadway studies. A lower observed severe mix around a feature may reflect reporting, urban context, speed, or traffic volume—not a protective causal effect.", className="callout"),
        ])

    source_rates = pd.DataFrame({
        "Source": ["Source1", "Source2", "Source3"],
        "Records": [4_325_632, 3_305_373, 97_389],
        "Severe_Rate": [8.13, 33.92, 31.73],
    })
    source_fig = style(px.bar(source_rates, x="Source", y="Severe_Rate", color="Source", text_auto=".2f",
        custom_data=["Records"]), "Why raw comparisons fail", "Severity mix differs sharply by collection source")
    return html.Div([
        html.Div([
            card("Aggregate tables", "9", "All validated; zero missing rows"),
            card("Source1 severe mix", "8.13%", "4.33M reported records"),
            card("Source2 severe mix", "33.92%", "Comparison basis", "orange"),
            card("Cramér’s V", "0.0416", "Weather association is weak"),
        ], className="kpis"),
        dcc.Graph(figure=source_fig),
        html.Div([html.H3("Interpretation guardrails"), html.Ul([
            html.Li("Severity is traffic impact, not injury or fatality severity."),
            html.Li("2023 is partial and contains Source1 only."),
            html.Li("State comparisons use Source2; other supplied aggregates combine sources."),
            html.Li("Statistical significance at 7.7M rows does not imply a meaningful effect."),
            html.Li("No causal or per-driver risk claims without exposure denominators such as VMT."),
        ])], className="insight"),
    ])


if __name__ == "__main__":
    app.run(debug=True)
