"""
AWARE-AI Plotly Charting Helpers.

Provides interactive enterprise charts:
- Risk Gauge Indicator
- Global Maritime Route Map (Scattergeo)
- SHAP Feature Attribution Waterfall / Bar Chart
- Risk Breakdown Radar / Polar Chart
- Multi-Criteria Plan Comparison Bar Chart
- Inventory Health / Stockout Risk Chart
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def create_risk_gauge(score: float, title: str = "Composite Risk Score") -> go.Figure:
    """
    Generate an interactive gauge meter (0.0 to 1.0) colored by severity zones.
    """
    val = max(0.0, min(1.0, float(score)))
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=val,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": title, "font": {"size": 18, "color": "#f9fafb"}},
            number={"valueformat": ".2f", "font": {"size": 36, "color": "#f9fafb"}},
            gauge={
                "axis": {"range": [0, 1], "tickwidth": 1, "tickcolor": "#9ca3af"},
                "bar": {"color": "#38bdf8", "thickness": 0.28},
                "bgcolor": "#111827",
                "borderwidth": 1,
                "bordercolor": "#374151",
                "steps": [
                    {"range": [0.0, 0.35], "color": "rgba(16, 185, 129, 0.45)"},
                    {"range": [0.35, 0.65], "color": "rgba(245, 158, 11, 0.45)"},
                    {"range": [0.65, 0.85], "color": "rgba(239, 68, 68, 0.45)"},
                    {"range": [0.85, 1.0], "color": "rgba(220, 38, 38, 0.75)"},
                ],
                "threshold": {
                    "line": {"color": "#ef4444", "width": 4},
                    "thickness": 0.75,
                    "value": 0.75,
                },
            },
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=40, b=20),
        height=220,
    )
    return fig


def create_fleet_map(
    shipments: Sequence[Dict[str, Any]],
    ports: Sequence[Dict[str, Any]] | None = None,
) -> go.Figure:
    """
    Render an interactive dark-theme world map with port nodes, active vessels,
    and transit corridors.
    """
    fig = go.Figure()

    # Add Port Markers
    if ports:
        port_lats = [p["latitude"] for p in ports]
        port_lons = [p["longitude"] for p in ports]
        port_texts = [f"<b>{p['name']}</b> ({p['code']})<br>{p['country']}" for p in ports]

        fig.add_trace(
            go.Scattergeo(
                lat=port_lats,
                lon=port_lons,
                text=port_texts,
                hoverinfo="text",
                mode="markers",
                name="Global Ports",
                marker=dict(
                    size=8,
                    color="#38bdf8",
                    symbol="circle",
                    line=dict(width=1, color="#0284c7"),
                ),
            )
        )

    # Add Shipment Routes & Positions
    for s in shipments:
        o_lat = s.get("origin_lat")
        o_lon = s.get("origin_lon")
        d_lat = s.get("dest_lat")
        d_lon = s.get("dest_lon")
        c_lat = s.get("current_lat", o_lat)
        c_lon = s.get("current_lon", o_lon)
        tid = s.get("tracking_id", "Unknown")
        status = s.get("status", "IN_TRANSIT")
        risk = s.get("risk_level", "LOW")

        # Color based on risk
        color = "#10b981" if risk == "LOW" else "#f59e0b" if risk == "MEDIUM" else "#ef4444"

        # Route Line
        if o_lat is not None and d_lat is not None:
            fig.add_trace(
                go.Scattergeo(
                    lat=[o_lat, d_lat],
                    lon=[o_lon, d_lon],
                    mode="lines",
                    line=dict(width=1.5, color="rgba(156, 163, 175, 0.4)", dash="dot"),
                    hoverinfo="none",
                    showlegend=False,
                )
            )

        # Vessel Position
        if c_lat is not None and c_lon is not None:
            hover_text = (
                f"<b>Shipment: {tid}</b><br>"
                f"Status: {status}<br>"
                f"Risk: {risk}<br>"
                f"Cargo: {s.get('cargo', 'N/A')}"
            )
            fig.add_trace(
                go.Scattergeo(
                    lat=[c_lat],
                    lon=[c_lon],
                    hovertext=[hover_text],
                    hoverinfo="text",
                    mode="markers+text",
                    name=tid,
                    text=[tid],
                    textposition="top center",
                    textfont=dict(size=10, color="#f3f4f6"),
                    marker=dict(
                        size=12,
                        color=color,
                        symbol="arrow-up",
                        line=dict(width=2, color="#ffffff"),
                    ),
                )
            )

    fig.update_layout(
        geo=dict(
            projection_type="natural earth",
            showland=True,
            landcolor="#111827",
            showocean=True,
            oceancolor="#090d16",
            showlakes=True,
            lakecolor="#090d16",
            showcountries=True,
            countrycolor="#1f2937",
            coastlinecolor="#374151",
            bgcolor="rgba(0,0,0,0)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        height=480,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#9ca3af"),
        ),
    )
    return fig


def create_shap_bar_chart(attributions: Sequence[Dict[str, Any]]) -> go.Figure:
    """
    Render horizontal bar chart for TreeSHAP feature attributions.
    Positive impacts (increasing delay risk) in Red, negative (decreasing) in Blue/Green.
    """
    if not attributions:
        fig = go.Figure()
        fig.add_annotation(text="No SHAP attributions available", showarrow=False, font=dict(color="#9ca3af"))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=300)
        return fig

    df = pd.DataFrame(attributions)
    # Sort by absolute attribution
    if "importance" in df.columns:
        df["abs_val"] = df["importance"].abs()
        df = df.sort_values(by="abs_val", ascending=True)
        values = df["importance"]
    elif "attribution" in df.columns:
        df["abs_val"] = df["attribution"].abs()
        df = df.sort_values(by="abs_val", ascending=True)
        values = df["attribution"]
    else:
        values = [0] * len(df)

    feature_names = df["feature"]
    colors = ["#ef4444" if v > 0 else "#0ea5e9" for v in values]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=feature_names,
            orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            text=[f"{v:+.3f}" for v in values],
            textposition="auto",
        )
    )

    fig.update_layout(
        title="SHAP Local Feature Attributions (Impact on Delay Probability)",
        title_font=dict(color="#f9fafb", size=14),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            title=dict(text="Attribution (SHAP value)", font=dict(color="#9ca3af")),
            gridcolor="#1f2937",
            zerolinecolor="#4b5563",
            tickfont=dict(color="#9ca3af"),
        ),
        yaxis=dict(
            tickfont=dict(color="#f3f4f6"),
        ),
        margin=dict(l=140, r=20, t=40, b=40),
        height=340,
    )
    return fig


def create_risk_radar(breakdown: Dict[str, float]) -> go.Figure:
    """
    Render radar chart displaying multi-dimensional risk scores.
    """
    categories = list(breakdown.keys())
    values = [float(v) for v in breakdown.values()]

    # Close the radar loop
    if categories:
        categories.append(categories[0])
        values.append(values[0])

    fig = go.Figure(
        go.Scatterpolar(
            r=values,
            theta=categories,
            fill="toself",
            fillcolor="rgba(239, 68, 68, 0.25)",
            line=dict(color="#ef4444", width=2),
            marker=dict(size=6, color="#f87171"),
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1.0], gridcolor="#374151", tickfont=dict(color="#9ca3af")),
            angularaxis=dict(gridcolor="#374151", tickfont=dict(color="#f3f4f6", size=11)),
            bgcolor="rgba(17, 24, 39, 0.6)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=30, b=30),
        height=280,
    )
    return fig


def create_plan_comparison_chart(plans_data: Sequence[Dict[str, Any]]) -> go.Figure:
    """
    Grouped bar chart comparing candidate resilience plans across:
    Transit Days, Total Cost ($k), and Risk Reduction Score (%).
    """
    if not plans_data:
        fig = go.Figure()
        fig.add_annotation(text="No candidate plans to compare", showarrow=False, font=dict(color="#9ca3af"))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=320)
        return fig

    names = [p.get("name", f"Plan {i+1}") for i, p in enumerate(plans_data)]
    transit_days = [p.get("transit_days", 0) for p in plans_data]
    costs = [p.get("estimated_cost", 0) / 1000.0 for p in plans_data]
    risk_reductions = [p.get("risk_reduction_score", 0) * 100.0 for p in plans_data]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Transit (Days)", x=names, y=transit_days, marker_color="#38bdf8"))
    fig.add_trace(go.Bar(name="Cost ($k)", x=names, y=costs, marker_color="#f59e0b"))
    fig.add_trace(go.Bar(name="Risk Reduction (%)", x=names, y=risk_reductions, marker_color="#10b981"))

    fig.update_layout(
        barmode="group",
        title="Candidate Resilience Plan Comparison",
        title_font=dict(color="#f9fafb", size=14),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(font=dict(color="#9ca3af")),
        xaxis=dict(tickfont=dict(color="#f3f4f6")),
        yaxis=dict(gridcolor="#1f2937", tickfont=dict(color="#9ca3af")),
        margin=dict(l=30, r=30, t=50, b=30),
        height=320,
    )
    return fig
