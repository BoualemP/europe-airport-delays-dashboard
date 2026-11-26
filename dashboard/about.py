"""About: what ATFM delay is, the data, how the numbers are calculated, limitations and links.
ATFM is explained here only (CLAUDE.md, Definitions); every number comes from the data or a constant."""

from dash import html

from dashboard import metrics

SOURCE_URL = "https://ansperformance.eu/csv/"
DATASET_URL = "https://ansperformance.eu/reference/dataset/airport-arrival-atfm-delay/"
DISCLAIMER_URL = "https://ansperformance.eu/about/disclaimer/"
# the OurAirports data page on GitHub, where the app downloads the file (ourairports.com had an expired
# certificate in November 2026)
OURAIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/"
ANALYSIS_URL = "https://github.com/BoualemP/europe-airport-delays-analysis"
CODE_URL = "https://github.com/BoualemP/europe-airport-delays-dashboard"
LICENSE_URL = f"{CODE_URL}/blob/main/LICENSE"
AUTHOR_URL = "https://boualemp.github.io"


def _link(text, href):
    return html.A(text, href=href, target="_blank", rel="noopener noreferrer")


# Airports, countries and the months covered, from the loaded data.
def data_facts(data):
    icaos = data.monthly["icao"].unique()
    return {
        "airports": len(icaos),
        "countries": data.airports.loc[icaos, "country"].nunique(),
        "first": data.coverage["first"].min(),
        "last": data.coverage["last"].max(),
    }


def _years_text(years):
    return " and ".join(str(y) for y in years) if len(years) <= 2 else f"{years[0]}–{years[-1]}"


def about_page(data):
    facts = data_facts(data)
    change = metrics.ATFM_CALCULATION_CHANGE
    return html.Div(className="prose", children=[
        html.H1("About this dashboard"),
        html.P("This dashboard shows arrival ATFM delay at the airports EUROCONTROL reports, with a focus on "
               "Lisbon, Porto and Faro. It builds on an analysis notebook that explains each step.",
               className="intro"),

        html.H2("What ATFM delay is"),
        html.P("ATFM (air traffic flow management) delay is the delay given to a flight before departure because "
               "its destination airport cannot take more arrivals at that time. Capacity, weather, staffing or an "
               "event at the airport can cause it. It is not total flight delay: late departures, en-route delay "
               "and delay on the ground are not counted."),

        html.H2("The data"),
        html.Ul([
            html.Li(["Airport Arrival ATFM Delay (", _link("dataset description", DATASET_URL), "), from the ",
                     _link("EUROCONTROL Aviation Intelligence Portal", SOURCE_URL),
                     f". It covers {facts['airports']} airports in {facts['countries']} countries from "
                     f"{facts['first']:%B %Y} to {facts['last']:%B %Y}."]),
            html.Li("“Europe” means every airport EUROCONTROL reports, some of them outside geographic "
                    "Europe."),
            html.Li(["The app downloads the yearly files when it starts; the retrieval date is in the footer. "
                     "Airport coordinates come from ", _link("OurAirports", OURAIRPORTS_URL), " (public domain)."]),
        ]),

        html.H2("How the numbers are calculated"),
        html.Ul([
            html.Li("ATFM delay minutes per arrival and the share of arrivals with ATFM delay are ratios of sums: "
                    "total minutes over total arrivals."),
            html.Li("A partial year is compared with the same months of the previous year."),
            html.Li(f"The map and the rankings only include airports with at least {metrics.MIN_ARRIVALS:,} "
                    "arrivals in the period shown, because values at small airports change a lot from a few "
                    "flights."),
            html.Li("Delay causes are the reason groups reported by the source."),
        ]),

        html.H2("Limitations"),
        html.Ul([
            html.Li(f"The way EUROCONTROL calculates ATFM delay changed on {change.day} {change:%B %Y}, so values "
                    "before and after that date are not fully comparable."),
            html.Li(f"Traffic fell sharply in {_years_text(metrics.LOW_TRAFFIC_YEARS)}, so ATFM delay in those "
                    "years is not typical."),
            html.Li("Each delay is assigned to one reason group by the source; the app does not check that choice."),
        ]),

        html.H2("Data use"),
        html.P(["Source: EUROCONTROL. EUROCONTROL publishes this data for information purposes. It may be copied "
                "provided that EUROCONTROL is mentioned as the source and it is not used for commercial purposes, "
                "and EUROCONTROL makes no warranty for it (see its ",
                _link("copyright notice and disclaimer", DISCLAIMER_URL),
                "). This is a portfolio project, not offered for sale. The app does not change or republish the "
                "source files: it downloads them when it starts and shows totals and ratios computed from them."]),
        html.P(["Code: ", _link("MIT licence", LICENSE_URL), ". Data: EUROCONTROL, under its own terms."]),

        html.H2("Links"),
        html.Ul([
            html.Li(["Analysis notebook: ", _link("europe-airport-delays-analysis", ANALYSIS_URL)]),
            html.Li(["Dashboard code: ", _link("europe-airport-delays-dashboard", CODE_URL)]),
            html.Li(["Author: Boualem Pereira (", _link("boualemp.github.io", AUTHOR_URL), ")"]),
        ]),
    ])
