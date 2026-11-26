"""About: ATFM delay, the data, the method, limitations, data use and links."""

import dash

from dashboard.about import about_page
from dashboard.data import get_data

dash.register_page(__name__, path="/about", name="About", title="About · European Airport ATFM Delays", order=3)


def layout(**_):
    return about_page(get_data())
