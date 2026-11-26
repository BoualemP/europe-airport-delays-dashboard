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
# Reason groups in stack order, seven hue families (green, blue, crimson, yellow, brown, violet, pink).
# Validated with the dataviz palette validator (light mode, adjacent pairs): worst CVD ΔE 19.9, worst
# normal-vision ΔE 23.0. No orange or bright red, so orange stays for Lisbon, Porto and Faro; these colours
# never share a chart with the orange marks (the Capacity green is close to that orange for colour-blind
# readers). Two colours are below 3:1 on white, so values are also given by hover and a table.
CAUSE_COLORS = {
    "Capacity": "#008300", "Weather": "#2a78d6", "Capacity (ATC)": "#b8325f", "Staffing (ATC)": "#eda100",
    "Disruptions (ATC)": "#9c5f24", "Disruptions": "#6250d6", "Events": "#e87ba4",
}
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


# ---------------------------------------------------------------- airport explorer

# Selected-year label just above the plot area, aligned with the band's outer edge near either end.
def _selected_label(fig, x0, x1, first, last, label):
    position = (x0 - first) / (last - first)
    x, anchor = ((x1, "right") if position > 0.8 else (x0, "left") if position < 0.2 else ((x0 + x1) / 2, "center"))
    fig.add_annotation(x=x, y=1, xref="x", yref="paper", xanchor=anchor, yanchor="bottom",
                       text=f"<b>{label}</b>", showarrow=False, font={"size": 12, "color": ACCENT})


# On a yearly axis: low-traffic years in grey, the selected year in petrol blue (when it is on the axis).
def _year_bands(fig, years, selected_year, selected_label):
    low = [y for y in LOW_TRAFFIC_YEARS if y in years]
    if low:
        fig.add_vrect(x0=low[0] - 0.5, x1=low[-1] + 0.5, fillcolor=LOW_TRAFFIC_GREY, line_width=0, layer="below")
        fig.add_annotation(x=low[0] - 0.5, y=1, xref="x", yref="paper", text="Low traffic", showarrow=False,
                           xanchor="left", yanchor="top", font={"size": 11, "color": MUTED})
    if selected_year in years:
        fig.add_vrect(x0=selected_year - 0.5, x1=selected_year + 0.5, fillcolor=ACCENT, opacity=0.22,
                      line_width=0, layer="below")
        _selected_label(fig, selected_year - 0.5, selected_year + 0.5, years[0] - 0.5, years[-1] + 0.5,
                        selected_label)
    fig.update_xaxes(range=[years[0] - 0.5, years[-1] + 0.5], dtick=2, showgrid=False, linecolor=GRID,
                     ticks="outside", tickcolor=GRID)


# Legend under the plot, above the source note (the space above the plot holds the selected-year label).
def _legend_below(fig):
    fig.update_layout(legend={"orientation": "h", "x": 0, "xanchor": "left", "y": -0.1, "yanchor": "top",
                              "font": {"size": 12}, "traceorder": "normal"})


# ATFM delay minutes per arrival by year: one airport and the median of its fixed traffic peers.
def peers_figure(table, airport_name, selected_year, selected_label):
    years = table.index.tolist()
    marker = {"size": 8, "line": {"color": WHITE, "width": 2}}
    fig = go.Figure([
        go.Scatter(x=years, y=table["airport"], name=airport_name, mode="lines+markers",
                   line={"color": ACCENT, "width": 2}, marker={**marker, "color": ACCENT},
                   hovertemplate="%{y:.3f} min per arrival"),
        go.Scatter(x=years, y=table["peer_median"], name="Median of its traffic peers", mode="lines+markers",
                   line={"color": MUTED, "width": 2, "dash": "dash"}, marker={**marker, "color": MUTED},
                   hovertemplate="%{y:.3f} min per arrival"),
    ])
    _year_bands(fig, years, selected_year, selected_label)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, rangemode="tozero", title=None)
    fig.update_layout(hovermode="x unified")
    _legend_below(fig)
    return _style(fig, SOURCE_NOTE, height=380, top=26, bottom=96)


# ATFM delay minutes per arrival by year, stacked by reason group: the bar height is the year's ATFM
# delay per arrival, each segment one group's minutes per arrival. The legend is HTML, next to the
# figure (components.legend), because seven entries wrap onto several rows on phones.
def causes_figure(causes, selected_year, selected_label):
    years = causes["per_arrival"].index.tolist()
    fig = go.Figure()
    for group, color in CAUSE_COLORS.items():
        fig.add_trace(go.Bar(
            x=years, y=causes["per_arrival"][group], name=group, marker={"color": color, "line": {"color": WHITE,
                                                                                                   "width": 1}},
            customdata=list(zip(causes["minutes"][group], causes["shares"][group].fillna(0))),
            hovertemplate=f"<b>{group}</b><br>%{{x}}: %{{y:.3f}} min per arrival<br>"
                          "%{customdata[0]:,.0f} min, %{customdata[1]:.1f}% of the year's ATFM delay<extra></extra>",
        ))
    _year_bands(fig, years, selected_year, selected_label)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, rangemode="tozero", title=None)
    fig.update_layout(barmode="stack", bargap=0.3, showlegend=False)
    return _style(fig, SOURCE_NOTE, height=380, top=26, bottom=56)


# Month x year heatmap of ATFM delay minutes per arrival for one airport, on the airport's own scale;
# blank cells are months without data. The selected year's column is outlined.
def heatmap_figure(matrix, selected_year, selected_label):
    years = matrix.columns.tolist()
    months = [pd.Timestamp(2000, m, 1).strftime("%b") for m in matrix.index]
    top = float(matrix.max().max()) if matrix.notna().any().any() else 1.0
    scale = [[i / (len(MAP_SCALE) - 1), c] for i, c in enumerate(MAP_SCALE)]
    fig = go.Figure(go.Heatmap(
        z=matrix.to_numpy(dtype=float), x=years, y=months, colorscale=scale, zmin=0, zmax=top or 1.0,
        xgap=2, ygap=2, hoverongaps=False,
        hovertemplate="%{y} %{x}: %{z:.2f} min per arrival<extra></extra>",
        colorbar={"orientation": "h", "x": 0, "xanchor": "left", "y": 0, "yanchor": "top", "ypad": 28,
                  "len": 0.6, "thickness": 10, "outlinewidth": 0, "tickfont": {"color": MUTED},
                  "title": {"text": "ATFM delay minutes per arrival", "side": "top",
                            "font": {"size": 12, "color": MUTED}}},
    ))
    if selected_year in years:
        fig.add_shape(type="rect", x0=selected_year - 0.5, x1=selected_year + 0.5, y0=-0.5, y1=len(months) - 0.5,
                      xref="x", yref="y", line={"color": ACCENT, "width": 2})
        _selected_label(fig, selected_year - 0.5, selected_year + 0.5, years[0] - 0.5, years[-1] + 0.5,
                        selected_label)
    fig.update_xaxes(range=[years[0] - 0.5, years[-1] + 0.5], dtick=2, showgrid=False, ticks="")
    fig.update_yaxes(autorange="reversed", showgrid=False, ticks="")
    return _style(fig, SOURCE_NOTE, height=470, top=26, bottom=120)


# ---------------------------------------------------------------- rankings

# Horizontal bars of ranked airports, highest at the top, with the value at the end of each bar.
# Lisbon, Porto and Faro are orange; 'extra' holds those of them outside 'top', shown after an empty row.
def rankings_figure(top, extra, measure, value_format):
    rows = pd.concat([top, extra])
    bars = [{"y": f"{r['rank']}. {r['name']}", "x": r[measure], "text": value_format.format(r[measure]),
             "color": FOCUS if icao in FOCUS_AIRPORTS else ACCENT,
             "custom": (icao, r["country"], r["arrivals"], r["delay_min_per_arrival"], r["arr_with_atfm_delay_pct"])}
            for icao, r in rows.iterrows()]
    if len(extra):
        bars.insert(len(top), {"y": " ", "x": None, "text": "", "color": WHITE, "custom": ("", "", 0, 0, 0)})
    fig = go.Figure(go.Bar(
        x=[b["x"] for b in bars], y=[b["y"] for b in bars], orientation="h", text=[b["text"] for b in bars],
        textposition="outside", cliponaxis=False, textfont={"color": TEXT, "size": 12},
        marker={"color": [b["color"] for b in bars]}, customdata=[b["custom"] for b in bars],
        hovertemplate="<b>%{y}</b> (%{customdata[0]}), %{customdata[1]}<br>%{customdata[2]:,} arrivals<br>"
                      "%{customdata[3]:.3f} min of ATFM delay per arrival<br>"
                      "%{customdata[4]:.1f}% of arrivals with ATFM delay<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", showgrid=False, ticks="", automargin=True)
    fig.update_xaxes(gridcolor=GRID, zeroline=False, range=[0, rows[measure].max() * 1.2], title=None, side="top")
    fig.update_layout(bargap=0.35, showlegend=False)
    return _style(fig, SOURCE_NOTE, height=26 * len(bars) + 90, top=30)
