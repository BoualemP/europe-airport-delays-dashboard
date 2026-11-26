"""Overview: Europe-wide KPIs, monthly trend and map of airports for a selected year."""

import dash
from dash import ClientsideFunction, Input, Output, State, callback, clientside_callback, dcc, html

from dashboard.data import get_data
from dashboard.components import default_year, year_options
from dashboard.overview import update_overview

dash.register_page(__name__, path="/", name="Overview", title="Overview · European Airport ATFM Delays",
                   order=0)


def layout(**_):
    data = get_data()
    return html.Div(className="page", children=[
        html.H1("Arrival ATFM delay at European airports"),
        html.P(id="overview-intro", className="intro"),
        html.Div(className="controls", children=[
            html.Label("Year", htmlFor="overview-year"),
            dcc.Dropdown(id="overview-year", options=year_options(data), value=default_year(data),
                         clearable=False, searchable=False, className="year-select"),
        ]),
        html.Div(id="overview-kpis", className="kpis"),
        html.Section(className="card", children=[
            html.H2("ATFM delay minutes per arrival, by month"),
            dcc.Graph(id="overview-trend", config={"displayModeBar": False}),
        ]),
        html.Section(className="card", children=[
            html.H2(id="overview-map-title"),
            dcc.Store(id="overview-map-figure"),
            dcc.Graph(id="overview-map", config={"displayModeBar": False, "scrollZoom": False}),
            html.P(id="overview-map-caption", className="caption"),
        ]),
    ])


@callback(
    Output("overview-intro", "children"),
    Output("overview-kpis", "children"),
    Output("overview-trend", "figure"),
    Output("overview-map-title", "children"),
    Output("overview-map-figure", "data"),
    Output("overview-map-caption", "children"),
    Input("overview-year", "value"),
)
def update(year):
    return update_overview(get_data(), year)


# The map figure is fitted to the graph's size in the browser (assets/map.js).
clientside_callback(
    ClientsideFunction(namespace="overview", function_name="fitMap"),
    Output("overview-map", "figure"),
    Input("overview-map-figure", "data"),
    State("overview-map", "id"),
)
