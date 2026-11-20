"""European airport ATFM delays: Dash app (run locally with `python app.py`, in production with gunicorn app:server)."""

import logging

import dash
from dash import Dash, dcc, html

from dashboard.data import get_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

DATA = get_data()  # download (or reuse) and aggregate the data before serving any page

FONTS = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"

app = Dash(__name__, use_pages=True, title="European Airport ATFM Delays", external_stylesheets=[FONTS])
server = app.server


def header():
    return html.Header(className="site-header", children=[
        html.Div("European Airport ATFM Delays", className="brand"),
        html.Nav([dcc.Link(page["name"], href=page["relative_path"], className="nav-link")
                  for page in dash.page_registry.values()]),
    ])


def footer():
    return html.Footer(className="site-footer", children=[
        "Source: EUROCONTROL Aviation Intelligence Portal · Airport coordinates: OurAirports · "
        f"Data retrieved {DATA.retrieved}",
    ])


app.layout = html.Div([header(), html.Main(dash.page_container), footer()])

if __name__ == "__main__":
    app.run(debug=True)
