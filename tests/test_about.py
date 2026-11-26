import pathlib

from dash import html

from dashboard import about, metrics


def _text(component):
    if isinstance(component, str):
        return component
    children = getattr(component, "children", None)
    if children is None:
        return ""
    if isinstance(children, (list, tuple)):
        return "".join(_text(c) for c in children)
    return _text(children)


# Every html.A in the page, in order.
def _anchors(component, found=None):
    found = [] if found is None else found
    if isinstance(component, html.A):
        found.append(component)
    children = getattr(component, "children", None)
    for child in children if isinstance(children, (list, tuple)) else [children]:
        if child is not None and not isinstance(child, str):
            _anchors(child, found)
    return found


def _links(component):
    return [a.href for a in _anchors(component)]


def test_data_facts_come_from_the_data(dataset):
    facts = about.data_facts(dataset)
    assert facts["airports"] == dataset.monthly["icao"].nunique()
    assert facts["countries"] == dataset.airports.loc[dataset.monthly["icao"].unique(), "country"].nunique()
    text = _text(about.about_page(dataset))
    assert (f"It covers {facts['airports']} airports in {facts['countries']} countries from "
            f"{facts['first']:%B %Y} to {facts['last']:%B %Y}.") in text
    assert f"at least {metrics.MIN_ARRIVALS:,} arrivals" in text
    change = metrics.ATFM_CALCULATION_CHANGE
    assert f"changed on {change.day} {change:%B %Y}" in text


def test_links_open_outside_the_app(dataset):
    page = about.about_page(dataset)
    links = _links(page)
    assert about.ANALYSIS_URL in links and about.CODE_URL in links and about.AUTHOR_URL in links
    assert all(link.startswith("https://") for link in links)
    # each link opens in a new tab, without giving the new page access to this one
    anchors = _anchors(page)
    assert all(a.target == "_blank" and a.rel == "noopener noreferrer" for a in anchors)


def test_atfm_is_explained_on_the_about_page_only():
    root = pathlib.Path(__file__).parents[1]
    sources = [*root.glob("dashboard/*.py"), *root.glob("pages/*.py"), root / "app.py"]
    explaining = {p.relative_to(root).as_posix() for p in sources
                  if "air traffic flow management" in p.read_text(encoding="utf-8")}
    assert explaining == {"dashboard/about.py"}


def test_data_use_names_the_source_and_the_licences(dataset):
    text = _text(about.about_page(dataset))
    assert "Source: EUROCONTROL." in text
    assert "Code: MIT licence. Data: EUROCONTROL, under its own terms." in text
    assert "Author: Boualem Pereira (boualemp.github.io)" in text
    links = _links(about.about_page(dataset))
    assert about.DISCLAIMER_URL in links and about.LICENSE_URL in links
