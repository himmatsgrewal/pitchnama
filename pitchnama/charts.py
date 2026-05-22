"""
charts.py — Plotly visualisations for PitchNama.

Each function takes analysis output and returns a Plotly figure ready for
st.plotly_chart(). Charts are designed to be clean, readable, and to make
the matchup story obvious at a glance.
"""

import plotly.graph_objects as go


# PitchNama palette (we'll formalise this in the beautification phase)
COLOR_MATCHUP = "#E8633A"    # warm orange — "this matchup"
COLOR_BASELINE = "#6B7280"   # cool grey — "career baseline"


def matchup_vs_baseline_bars(data: dict, batter_label: str, bowler_label: str):
    """
    Grouped bar chart: batter's Average and Strike Rate in this matchup
    vs their career baseline (in the same scope).

    Expects data from compare_matchup_to_baseline():
        data['overall_matchup'] = {'avg':..., 'sr':...}
        data['overall_baseline'] = {'avg':..., 'sr':...}
    """
    m = data['overall_matchup']
    b = data['overall_baseline']

    metrics = ['Average', 'Strike Rate']
    matchup_vals = [m.get('avg') or 0, m.get('sr') or 0]
    baseline_vals = [b.get('avg') or 0, b.get('sr') or 0]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=f"vs {bowler_label}",
        x=metrics,
        y=matchup_vals,
        marker_color=COLOR_MATCHUP,
        text=[f"{v:.1f}" for v in matchup_vals],
        textposition='outside',
    ))
    fig.add_trace(go.Bar(
        name="Career baseline",
        x=metrics,
        y=baseline_vals,
        marker_color=COLOR_BASELINE,
        text=[f"{v:.1f}" for v in baseline_vals],
        textposition='outside',
    ))

    fig.update_layout(
        barmode='group',
        title=f"{batter_label} vs {bowler_label} — matchup vs career",
        yaxis_title="Value",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=80, b=40, l=40, r=20),
        height=380,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.2)")

    return fig