"""Airport explorer: one airport's ATFM delay over time, its causes, and its traffic peers."""

import dash
from dash import Input, Output, callback, dcc, html

from dashboard.airport import airport_options, initial_selection, update_airport
from dashboard.components import legend, year_options
from dashboard.data import get_data
from dashboard.figures import CAUSE_COLORS

dash.register_page(__name__, path="/airport", name="Airport explorer",
                   title="Airport explorer · European Airport ATFM Delays", order=1)

GRAPH_CONFIG = {"displayModeBar": False}


# The airport and year can come from the URL: /airport?icao=LPPT&year=2025
def layout(icao=None, year=None, **_):
    data = get_data()
    icao, year = initial_selection(data, icao, year)
    return html.Div(className="page", children=[
        html.H1("Airport explorer"),
        html.P("How ATFM delay changed at one airport, what caused it, and how it compares with airports "
               "of similar traffic.", className="intro"),
        html.Div(className="controls", children=[
            html.Label("Airport", htmlFor="airport-icao"),
            dcc.Dropdown(id="airport-icao", options=airport_options(data), value=icao, clearable=False,
                         searchable=True, className="airport-select"),
            html.Label("Year", htmlFor="airport-year"),
            dcc.Dropdown(id="airport-year", options=year_options(data), value=year, clearable=False,
                         searchable=False, className="year-select"),
        ]),
        html.Div(id="airport-kpis", className="kpis"),
        html.Section(className="card", children=[
            html.H2(id="airport-peers-title"),
            html.P(id="airport-peers-caption", className="caption"),
            dcc.Graph(id="airport-peers", config=GRAPH_CONFIG),
            html.H3(id="airport-peers-table-title"),
            html.Div(id="airport-peers-table"),
        ]),
        html.Section(className="card", children=[
            html.H2(id="airport-causes-title"),
            html.P("Bar height is ATFM delay minutes per arrival; each segment is one reason group. "
                   "Complete years only.", className="caption"),
            legend(CAUSE_COLORS),
            dcc.Graph(id="airport-causes", config=GRAPH_CONFIG),
            html.Div(id="airport-causes-table"),
        ]),
        html.Section(className="card", children=[
            html.H2(id="airport-heatmap-title"),
            html.P("Blank cells are months without data. The colour scale is this airport's own.",
                   className="caption"),
            dcc.Graph(id="airport-heatmap", config=GRAPH_CONFIG),
        ]),
    ])


@callback(
    Output("airport-kpis", "children"),
    Output("airport-peers-title", "children"),
    Output("airport-peers-caption", "children"),
    Output("airport-peers", "figure"),
    Output("airport-peers-table-title", "children"),
    Output("airport-peers-table", "children"),
    Output("airport-causes-title", "children"),
    Output("airport-causes", "figure"),
    Output("airport-causes-table", "children"),
    Output("airport-heatmap-title", "children"),
    Output("airport-heatmap", "figure"),
    Input("airport-icao", "value"),
    Input("airport-year", "value"),
)
def update(icao, year):
    return update_airport(get_data(), icao, year)
