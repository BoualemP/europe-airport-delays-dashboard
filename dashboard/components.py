"""Page pieces shared by several screens: year selector options, KPI cards, number formats, tables."""

from dash import html

from dashboard import metrics


# Year options, newest first; a partial year is labelled with its months ('2026 (Jan–Oct)').
def year_options(data):
    options = []
    for year in sorted(data.coverage.index, reverse=True):
        label = metrics.period_label(data.coverage, data.monthly, year)
        options.append({"label": label if label == str(year) else f"{year} ({label.removesuffix(f' {year}')})",
                        "value": year})
    return options


# The latest complete year, shown first.
def default_year(data):
    return max(metrics.complete_years(data.coverage))


# Signed number with a true minus sign, e.g. '+0.04' or '−0.2'.
def signed(value, decimals):
    return f"{value:+,.{decimals}f}".replace("-", "−")


# English ordinal for a rank: 1st, 2nd, 3rd, 4th, 11th, 21st...
def ordinal(n):
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def kpi_card(label, value, note):
    return html.Div(className="kpi", children=[
        html.Div(label, className="kpi-label"),
        html.Div(value, className="kpi-value"),
        html.Div(note, className="kpi-change"),
    ])


# Three KPI cards from metrics.period_kpis: ATFM delay per arrival, arrivals with ATFM delay, arrivals;
# each against the previous year.
def kpi_cards(kpis):
    now, before = kpis["current"], kpis["previous"]
    values = [f"{now['delay_min_per_arrival']:.2f} min", f"{now['arr_with_atfm_delay_pct']:.1f}%",
              f"{now['arrivals']:,.0f}"]
    if before is None:
        changes = [kpis["previous_note"]] * 3
    else:
        changes = [f"{text} against {kpis['previous_label']}" for text in (
            f"{signed(now['delay_min_per_arrival'] - before['delay_min_per_arrival'], 2)} min",
            f"{signed(now['arr_with_atfm_delay_pct'] - before['arr_with_atfm_delay_pct'], 1)} pp",
            f"{signed((now['arrivals'] / before['arrivals'] - 1) * 100, 1)}%",
        )]
    labels = ["ATFM delay per arrival", "Arrivals with ATFM delay", "Arrivals"]
    return [kpi_card(*card) for card in zip(labels, values, changes)]


# Legend as HTML: a colour swatch and the name in text colour for each series, in a fixed order.
def legend(colors):
    return html.Ul(className="legend", children=[
        html.Li([html.Span(className="swatch", style={"background": color}), name]) for name, color in colors.items()
    ])


# A plain HTML table: header row, then one row per item of 'rows' (lists of cell texts).
# Rows whose index is in 'highlight' get the 'highlight' class; 'footer' rows are set apart.
# Columns from 'numeric_from' on are right-aligned, or the columns listed in 'numeric' when it is given.
# Columns whose index is in 'hide_on_phones' are hidden below 600px (class 'hide-mobile').
def table(header, rows, highlight=(), footer=(), numeric_from=1, hide_on_phones=(), numeric=None):
    def is_numeric(i):
        return i in numeric if numeric is not None else i >= numeric_from

    def cells(values, tag):
        return [tag(v, className=" ".join(filter(None, ["num" if is_numeric(i) else "",
                                                        "hide-mobile" if i in hide_on_phones else ""])) or None)
                for i, v in enumerate(values)]

    body = [html.Tr(cells(r, html.Td), className="highlight" if i in highlight else None) for i, r in enumerate(rows)]
    foot = [html.Tr(cells(r, html.Td)) for r in footer]
    return html.Div(className="table-wrap", children=html.Table([
        html.Thead(html.Tr(cells(header, html.Th))), html.Tbody(body), html.Tfoot(foot) if foot else None,
    ]))
