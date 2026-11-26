"""Rankings: airports ranked by ATFM delay in a year, Europe-wide or in one country."""

import dash
from dash import Input, Output, callback, dcc, html

from dashboard.components import year_options
from dashboard.data import get_data
from dashboard.rankings import country_options, initial_selection, measure_options, update_rankings

dash.register_page(__name__, path="/rankings", name="Rankings", title="Rankings · European Airport ATFM Delays",
                   order=2)


# The year, country and measure can come from the URL: /rankings?year=2025&country=Portugal&by=share
def layout(year=None, country=None, by=None, **_):
    data = get_data()
    year, country, by = initial_selection(data, year, country, by)
    return html.Div(className="page", children=[
        html.H1("Rankings"),
        html.P("Which airports had the most ATFM delay in a year, among the airports with enough traffic "
               "to compare.", className="intro"),
        html.Div(className="controls", children=[
            # each label stays next to its selector when the row wraps on phones
            html.Div(className="control", children=[
                html.Label("Year", htmlFor="rankings-year"),
                dcc.Dropdown(id="rankings-year", options=year_options(data), value=year, clearable=False,
                             searchable=False, className="year-select"),
            ]),
            html.Div(className="control", children=[
                html.Label("Country", htmlFor="rankings-country"),
                dcc.Dropdown(id="rankings-country", options=country_options(data, year), value=country,
                             clearable=False, searchable=True, className="year-select"),
            ]),
        ]),
        html.Div(className="controls", children=[
            html.Span("Rank by", className="control-label"),
            dcc.RadioItems(id="rankings-by", options=measure_options(), value=by, inline=True,
                           className="radio"),
        ]),
        html.Section(className="card", children=[
            html.H2(id="rankings-chart-title"),
            html.P(id="rankings-chart-caption", className="caption"),
            html.Div(id="rankings-chart"),
        ]),
        html.Section(className="card", children=[
            html.H2(id="rankings-table-title"),
            html.P(id="rankings-table-caption", className="caption"),
            html.Div(id="rankings-table"),
        ]),
    ])


@callback(
    Output("rankings-country", "options"),
    Output("rankings-country", "value"),
    Output("rankings-chart-title", "children"),
    Output("rankings-chart-caption", "children"),
    Output("rankings-chart", "children"),
    Output("rankings-table-title", "children"),
    Output("rankings-table-caption", "children"),
    Output("rankings-table", "children"),
    Input("rankings-year", "value"),
    Input("rankings-country", "value"),
    Input("rankings-by", "value"),
)
def update(year, country, by):
    return update_rankings(get_data(), year, country, by)
