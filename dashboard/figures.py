"""Plotly figures in the dashboard palette. Every figure carries the source note."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dashboard.metrics import ATFM_CALCULATION_CHANGE, FOCUS_AIRPORTS, LOW_TRAFFIC_YEARS

# Palette (CLAUDE.md, Visual style)
WHITE = "#ffffff"
PANEL = "#f3f6f8"
GRID = "#d9e0e7"
TEXT = "#1f2d3d"
MUTED = "#5a6b7d"
ACCENT = "#0e6674"
FOCUS = "#eb6834"
LOW_TRAFFIC_GREY = "#e4e7ea"  # neutral grey, clearly apart from the petrol-blue selected year
MAP_SCALE = ["#d6eef0", "#a6d6dc", "#72b9c3", "#3f99a7", "#16798a", "#0e6674", "#0a4a55"]
FONT = "Inter, system-ui, sans-serif"

SOURCE_NOTE = "Source: EUROCONTROL"
MAP_SOURCE_NOTE = "Source: EUROCONTROL · Coordinates: OurAirports"


# Shared layout: white background, palette fonts, source note at the bottom of the figure.
def _style(fig, source_note, height, bottom=48, top=8):
    fig.update_layout(
        height=height, paper_bgcolor=WHITE, plot_bgcolor=WHITE,
        font={"family": FONT, "color": TEXT, "size": 13},
        hoverlabel={"font_family": FONT, "bgcolor": WHITE, "bordercolor": GRID},
        margin={"l": 8, "r": 8, "t": top, "b": bottom},
    )
    fig.add_annotation(text=source_note, xref="paper", yref="paper", x=0, y=0, yshift=8 - bottom,
                       xanchor="left", yanchor="bottom", showarrow=False, font={"size": 11, "color": MUTED})
    return fig


# Monthly Europe-wide ATFM delay minutes per arrival, with the 2016 calculation change, the
# low-traffic years shaded in grey and the selected year in petrol blue, labelled above the plot.
def trend_figure(by_month, selected_year, selected_label):
    fig = go.Figure(go.Scatter(
        x=by_month["date"], y=by_month["delay_min_per_arrival"], mode="lines",
        line={"color": ACCENT, "width": 2}, customdata=by_month["arr_with_atfm_delay_pct"],
        hovertemplate="%{x|%b %Y}<br>%{y:.2f} min per arrival<br>"
                      "%{customdata:.1f}% of arrivals with ATFM delay<extra></extra>",
    ))
    fig.add_vrect(x0=pd.Timestamp(LOW_TRAFFIC_YEARS[0], 1, 1), x1=pd.Timestamp(LOW_TRAFFIC_YEARS[-1] + 1, 1, 1),
                  fillcolor=LOW_TRAFFIC_GREY, line_width=0, layer="below")
    # placed below the calculation-change note, so the two do not overlap on narrow screens
    fig.add_annotation(x=pd.Timestamp(LOW_TRAFFIC_YEARS[0], 1, 1), y=0.84, xref="x", yref="paper",
                       text="Low traffic", showarrow=False, xanchor="left", yanchor="top",
                       font={"size": 11, "color": MUTED})
    selected = by_month[by_month["year"] == selected_year]["date"]
    start, end = selected.min(), selected.max() + pd.offsets.MonthBegin(1)
    fig.add_vrect(x0=start, x1=end, fillcolor=ACCENT, opacity=0.22, line_width=0, layer="below")
    # Label just above the plot area, so it never covers the notes inside it. Near either end of the
    # axis it is aligned with the band's outer edge, so it stays inside the figure on narrow screens.
    first, last = by_month["date"].min(), by_month["date"].max() + pd.offsets.MonthBegin(1)
    position = (start - first) / (last - first)
    x, anchor = ((end, "right") if position > 0.8 else (start, "left") if position < 0.2
                 else (start + (end - start) / 2, "center"))
    fig.add_annotation(x=x, y=1, xref="x", yref="paper", xanchor=anchor, yanchor="bottom",
                       text=f"<b>{selected_label}</b>", showarrow=False, font={"size": 12, "color": ACCENT})
    # Vertical line as a shape plus an annotation (add_vline's own annotation needs a numeric axis)
    fig.add_shape(type="line", x0=ATFM_CALCULATION_CHANGE, x1=ATFM_CALCULATION_CHANGE, y0=0, y1=1,
                  xref="x", yref="paper", line={"color": MUTED, "width": 1, "dash": "dot"})
    fig.add_annotation(x=ATFM_CALCULATION_CHANGE, y=1, xref="x", yref="paper", xanchor="left", yanchor="top",
                       text="ATFM delay calculation<br>changed", showarrow=False, align="left",
                       font={"size": 11, "color": MUTED})
    # fixed range: annotations near the edges must not widen the axis
    fig.update_xaxes(range=[first, last], showgrid=False, linecolor=GRID, ticks="outside", tickcolor=GRID,
                     dtick="M24", tickformat="%Y")
    # headroom above the highest month, so the notes at the top do not cover the line
    fig.update_yaxes(gridcolor=GRID, zeroline=False, range=[0, by_month["delay_min_per_arrival"].max() * 1.25],
                     title=None)
    return _style(fig, SOURCE_NOTE, height=360, top=26)


# Airports as bubbles on a map: size = arrivals, colour = ATFM delay minutes per arrival on a scale
# shared by all years (capped at color_max, shown as '≥' at the top of the colour bar). The bounds
# go into layout.meta; assets/map.js uses them to fit the map to the width of the screen.
def map_figure(airports, color_max, bounds):
    data = airports.reset_index()
    fig = px.scatter_map(
        data, lat="lat", lon="lon", size="arrivals", color="delay_min_per_arrival",
        color_continuous_scale=MAP_SCALE, range_color=[0, color_max], size_max=26, opacity=0.9,
        custom_data=["name", "icao", "country", "arrivals", "delay_min_per_arrival", "arr_with_atfm_delay_pct"],
        map_style="carto-positron", center={"lat": 46, "lon": 12}, zoom=2.7,
    )
    fig.update_traces(hovertemplate=(
        "<b>%{customdata[0]}</b> (%{customdata[1]}), %{customdata[2]}<br>"
        "%{customdata[3]:,} arrivals<br>%{customdata[4]:.2f} min of ATFM delay per arrival<br>"
        "%{customdata[5]:.1f}% of arrivals with ATFM delay<extra></extra>"))
    focus = data[data["icao"].isin(FOCUS_AIRPORTS)]
    # Labels for Lisbon, Porto and Faro. mode="text" alone raises "Map error" in the plotly.js bundled
    # with Plotly 7.1, so the labels sit on invisible markers.
    fig.add_trace(go.Scattermap(lat=focus["lat"], lon=focus["lon"], mode="markers+text", text=focus["name"],
                                marker={"size": 1, "opacity": 0},
                                textposition="middle left",
                                # map labels use the glyph fonts of the CARTO tiles (Semibold is not served)
                                textfont={"family": "Open Sans Bold", "color": TEXT, "size": 12},
                                hoverinfo="skip", showlegend=False))
    # Horizontal colour bar under the map, so the map keeps the full width on phones
    ticks = [color_max * i / 4 for i in range(5)]
    fig.update_coloraxes(colorbar={
        "orientation": "h", "x": 0, "xanchor": "left", "y": 0, "yanchor": "top", "ypad": 12,
        "len": 0.6, "thickness": 10, "outlinewidth": 0,
        "title": {"text": "ATFM delay minutes per arrival", "side": "top", "font": {"size": 12, "color": MUTED}},
        "tickvals": ticks, "ticktext": [f"{t:.1f}" for t in ticks[:-1]] + [f"≥ {ticks[-1]:.1f}"],
        "tickfont": {"color": MUTED},
    })
    fig.update_layout(meta={"bounds": bounds})
    return _style(fig, MAP_SOURCE_NOTE, height=620, bottom=110)
