"""Dash application for MP expenses audit prioritisation."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, quote

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dcc, html
from dash.dash_table import DataTable

import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DASHBOARD_PATH = PROJECT_ROOT / "data" / "processed" / "dashboard_dataset.csv"
PROCESSED_ANALYTICS_PATH = PROJECT_ROOT / "data" / "processed" / "mp_expenses_audit_dataset.csv"
VALIDATION_REPORT_PATH = PROJECT_ROOT / "outputs" / "validation" / "validation_report.csv"
LIMITATIONS_SUMMARY_PATH = PROJECT_ROOT / "outputs" / "validation" / "limitations_summary.csv"
RISK_COLORS = {"High": "#b02a37", "Medium": "#d39e00", "Low": "#2b6cb0"}
PAGE_TITLES = {
    "overview": "Overview",
    "explorer": "MP Explorer",
    "risk-review": "Audit Risk Review",
}


def load_dataframe(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def build_app() -> Dash:
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    dashboard_df = load_dataframe(PROCESSED_DASHBOARD_PATH)
    analytics_df = load_dataframe(PROCESSED_ANALYTICS_PATH)
    validation_df = load_dataframe(VALIDATION_REPORT_PATH)
    limitations_df = load_dataframe(LIMITATIONS_SUMMARY_PATH)
    year_options = [{"label": "All years", "value": "ALL"}] + [
        {"label": year, "value": year}
        for year in sorted(analytics_df["financial_year"].dropna().unique().tolist())
    ]

    if dashboard_df.empty or analytics_df.empty:
        app.layout = dbc.Container(
            [
                html.H1("MP Expenses Audit Prioritisation Tool"),
                html.P("Processed audit datasets are not available yet. Run the pipeline first."),
            ],
            fluid=True,
            className="py-4",
        )
        return app

    app.layout = dbc.Container(
        [
            dcc.Store(id="dashboard-store", data=dashboard_df.to_dict("records")),
            dcc.Store(id="analytics-store", data=analytics_df.to_dict("records")),
            dcc.Store(id="validation-store", data=validation_df.to_dict("records")),
            dcc.Store(id="limitations-store", data=limitations_df.to_dict("records")),
            dcc.Location(id="url", refresh=False),
            _build_header(),
            dbc.Card(
                dbc.CardBody(
                    dbc.Row(
                        [
                            dbc.Col(html.Div("Review window", className="panel-kicker mb-2 mb-md-0"), md=2, lg=2),
                            dbc.Col(
                                dcc.Dropdown(
                                    id="year-filter",
                                    options=year_options,
                                    value="ALL",
                                    clearable=False,
                                    className="year-filter",
                                ),
                                md=4,
                                lg=3,
                            ),
                            dbc.Col(
                                html.Div(
                                    "This filter narrows review outputs by financial year while keeping the dashboard focused on prioritisation rather than open-ended exploration.",
                                    className="small text-muted year-filter-note",
                                ),
                                md=6,
                                lg=7,
                            ),
                        ],
                        className="align-items-center g-3",
                    )
                ),
                className="surface-card mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(_build_sidebar(), md=3, lg=2, className="mb-4"),
                    dbc.Col(html.Div(id="page-content"), md=9, lg=10),
                ],
                className="g-4",
            ),
        ],
        fluid=True,
        className="py-4 px-4",
        style={"backgroundColor": "#f7f4ef", "minHeight": "100vh"},
    )

    @app.callback(
        Output("page-content", "children"),
        Input("url", "pathname"),
        Input("url", "search"),
        Input("dashboard-store", "data"),
        Input("analytics-store", "data"),
        Input("validation-store", "data"),
        Input("limitations-store", "data"),
        Input("year-filter", "value"),
    )
    def render_page(
        pathname: str,
        search: str,
        dashboard_records: list[dict],
        analytics_records: list[dict],
        validation_records: list[dict],
        limitations_records: list[dict],
        year_filter: str,
    ):
        dashboard_data = pd.DataFrame(dashboard_records)
        analytics_data = pd.DataFrame(analytics_records)
        validation_data = pd.DataFrame(validation_records)
        limitations_data = pd.DataFrame(limitations_records)
        dashboard_data = _filter_to_year(dashboard_data, year_filter)
        analytics_data = _filter_to_year(analytics_data, year_filter)
        year_label = "All years" if year_filter == "ALL" else year_filter
        selected_page = _normalise_page(pathname)
        if selected_page == "explorer":
            return _build_explorer_page(analytics_data, _selected_mp_from_search(search, analytics_data), year_label)
        if selected_page == "risk-review":
            return _build_risk_review_page(dashboard_data, analytics_data, validation_data, year_label)
        return _build_overview_page(dashboard_data, analytics_data, validation_data, limitations_data, year_label)

    @app.callback(
        Output("mp-explorer-content", "children"),
        Input("mp-selector", "value"),
        Input("analytics-store", "data"),
        Input("year-filter", "value"),
        prevent_initial_call=False,
    )
    def render_mp_explorer(selected_mp: str | None, analytics_records: list[dict], year_filter: str):
        filtered_records = _filter_to_year(pd.DataFrame(analytics_records), year_filter).to_dict("records")
        if not filtered_records:
            return html.Div("No MP records are available for the selected review window.")
        filtered_df = pd.DataFrame(filtered_records)
        effective_mp = selected_mp if selected_mp in set(filtered_df["mp_name"].dropna().tolist()) else filtered_df["mp_name"].dropna().iloc[0]
        if not effective_mp:
            return html.Div("No MP is available for review.")
        return _build_mp_profile_content(effective_mp, filtered_records)

    return app


def _build_header() -> html.Div:
    return html.Div(
        [
            html.Div("MP Expenses Audit Prioritisation Tool", className="hero-title"),
            html.Div(
                "This tool supports prioritisation of audit review using explainable analytics. Outputs are review indicators only and do not imply wrongdoing.",
                className="hero-subtitle mt-2",
            ),
        ],
        className="hero-panel mb-4",
    )


def _build_sidebar() -> dbc.Card:
    nav_links = [
        dbc.NavLink(title, href=f"/{page_key}", active="exact", className="mb-2")
        for page_key, title in PAGE_TITLES.items()
    ]
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div("Audit Workflow", className="panel-kicker mb-3"),
                dbc.Nav(nav_links, vertical=True, pills=True),
                html.Hr(),
                html.Div("Usage note", className="panel-kicker mb-2"),
                html.P(
                    "Use the risk review page to decide who merits further audit attention, then move to the MP explorer for peer-context explanation.",
                    className="small mb-0",
                ),
            ]
        ),
        className="surface-card sticky-card",
    )


def _build_overview_page(
    dashboard_df: pd.DataFrame,
    analytics_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    limitations_df: pd.DataFrame,
    year_label: str,
) -> html.Div:
    if analytics_df.empty or dashboard_df.empty:
        return _build_empty_page("Overview", year_label)

    high_priority_count = int((dashboard_df["risk_priority"] == "High").sum())
    medium_priority_count = int((dashboard_df["risk_priority"] == "Medium").sum())
    total_spend = float(analytics_df["total_spend"].fillna(0).sum())
    average_utilisation = float(analytics_df["overall_utilisation_pct"].fillna(0).mean())
    top_peer_group = (
        analytics_df.groupby("peer_group")["risk_flag_count"].mean().sort_values(ascending=False).index[0]
        if not analytics_df.empty
        else "Not available"
    )

    distribution_fig = px.histogram(
        analytics_df,
        x="total_spend",
        color="risk_priority",
        nbins=30,
        title="Spend Distribution by Review Priority",
        category_orders={"risk_priority": ["High", "Medium", "Low"]},
        color_discrete_map=RISK_COLORS,
    )
    distribution_fig.update_layout(margin={"l": 20, "r": 20, "t": 60, "b": 20}, plot_bgcolor="#fffdf9", paper_bgcolor="#fffdf9")

    priority_fig = px.bar(
        dashboard_df.groupby("risk_priority", as_index=False)["mp_name"].count().rename(columns={"mp_name": "record_count"}),
        x="risk_priority",
        y="record_count",
        color="risk_priority",
        title="Review Priority Distribution",
        category_orders={"risk_priority": ["High", "Medium", "Low"]},
        color_discrete_map=RISK_COLORS,
    )
    priority_fig.update_layout(showlegend=False, margin={"l": 20, "r": 20, "t": 60, "b": 20}, plot_bgcolor="#fffdf9", paper_bgcolor="#fffdf9")

    insight_text = (
        f"High review priority records total {high_priority_count:,}, and the peer group with the highest average flag count is {top_peer_group.replace('|', ' / ')}. "
        "This points auditors toward a concentrated area of notable variance rather than a broad exploratory review."
    )

    validation_panel = _build_validation_summary_panel(validation_df, limitations_df)

    return html.Div(
        [
            html.H2("Overview", className="h3 mb-3"),
            html.P(f"Current review window: {year_label}", className="text-muted mb-4"),
            dbc.Row(
                [
                    _metric_card("Records reviewed", f"{len(analytics_df):,}"),
                    _metric_card("High review priority", f"{high_priority_count:,}"),
                    _metric_card("Medium review priority", f"{medium_priority_count:,}"),
                    _metric_card("Aggregate total spend", f"£{total_spend:,.0f}"),
                    _metric_card("Average utilisation", f"{average_utilisation:.1f}%"),
                ],
                className="g-3 mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(figure=distribution_fig, config={"displayModeBar": False})), className="surface-card chart-card"), md=7),
                    dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(figure=priority_fig, config={"displayModeBar": False})), className="surface-card chart-card"), md=5),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Div("Key audit insight", className="panel-kicker mb-2"),
                                    html.P(insight_text, className="mb-0"),
                                ]
                            ),
                            className="surface-card tall-card",
                        ),
                        md=6,
                    ),
                    dbc.Col(validation_panel, md=6),
                ],
                className="g-3",
            ),
        ]
    )


def _build_explorer_page(analytics_df: pd.DataFrame, selected_mp: str | None, year_label: str) -> html.Div:
    if analytics_df.empty:
        return _build_empty_page("MP Explorer", year_label)

    mp_options = [{"label": name, "value": name} for name in sorted(analytics_df["mp_name"].dropna().unique())]
    default_mp = selected_mp if selected_mp else (mp_options[0]["value"] if mp_options else None)

    return html.Div(
        [
            html.H2("MP Explorer", className="h3 mb-3"),
            html.P(f"Current review window: {year_label}", className="text-muted mb-2"),
            html.P(
                "Select an MP to review their individual profile against the relevant peer group and understand why any review flags were raised.",
                className="text-muted",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Dropdown(id="mp-selector", options=mp_options, value=default_mp, clearable=False, className="mp-selector"),
                        md=6,
                    ),
                ],
                className="mb-4",
            ),
            html.Div(id="mp-explorer-content"),
        ]
    )


def _build_risk_review_page(
    dashboard_df: pd.DataFrame,
    analytics_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    year_label: str,
) -> html.Div:
    if analytics_df.empty or dashboard_df.empty:
        return _build_empty_page("Audit Risk Review", year_label)

    top_travel = analytics_df.nlargest(10, "travel_spend")[["mp_name", "financial_year", "travel_spend", "risk_priority"]]
    top_uncapped = analytics_df.nlargest(10, "uncapped_spend_total")[["mp_name", "financial_year", "uncapped_spend_total", "risk_priority"]]
    top_utilisation = analytics_df.nlargest(10, "overall_utilisation_pct")[["mp_name", "financial_year", "overall_utilisation_pct", "risk_priority"]]

    return html.Div(
        [
            html.H2("Audit Risk Review", className="h3 mb-3"),
            html.P(f"Current review window: {year_label}", className="text-muted mb-2"),
            html.P(
                "This page is the primary prioritisation surface. It defaults to the highest-priority records and highlights the main drivers of review interest.",
                className="text-muted",
            ),
            _build_qa_exception_strip(analytics_df, validation_df),
            dbc.Row(
                [
                    dbc.Col(dbc.Card(dbc.CardBody([html.Div("Top travel spenders", className="panel-kicker mb-2"), _simple_table(top_travel)]), className="surface-card"), md=4),
                    dbc.Col(dbc.Card(dbc.CardBody([html.Div("Top uncapped spend", className="panel-kicker mb-2"), _simple_table(top_uncapped)]), className="surface-card"), md=4),
                    dbc.Col(dbc.Card(dbc.CardBody([html.Div("High utilisation MPs", className="panel-kicker mb-2"), _simple_table(top_utilisation)]), className="surface-card"), md=4),
                ],
                className="g-3 mb-4",
            ),
            html.H3("Top MPs for Review", className="h5 mb-3"),
            _review_table(dashboard_df.head(25)),
        ]
    )


def _simple_table(df: pd.DataFrame) -> DataTable:
    numeric_columns = [column for column in df.columns if pd.api.types.is_numeric_dtype(df[column])]
    columns = []
    for column in df.columns:
        column_def = {"name": column.replace("_", " ").title(), "id": column}
        if column in numeric_columns:
            column_def.update({"type": "numeric", "format": {"specifier": ",.2f"}})
        columns.append(column_def)

    return DataTable(
        data=df.round(2).to_dict("records"),
        columns=columns,
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left", "padding": "8px", "fontSize": "0.9rem", "whiteSpace": "normal", "height": "auto"},
        style_header={"fontWeight": "bold", "backgroundColor": "#f3ede2"},
        page_action="none",
    )


def _review_table(df: pd.DataFrame) -> DataTable:
    table_df = df[
        [
            "review_rank",
            "mp_name",
            "constituency",
            "financial_year",
            "risk_priority",
            "risk_flag_count",
            "total_spend",
            "overall_utilisation_pct",
            "risk_explanations",
        ]
    ].copy()
    table_df["follow_up"] = table_df["mp_name"].map(lambda name: f"[Open MP review](/explorer?mp={quote(str(name))})")
    return DataTable(
        data=table_df.round(2).to_dict("records"),
        columns=[
            {"name": "Rank", "id": "review_rank"},
            {"name": "MP", "id": "mp_name"},
            {"name": "Follow-up", "id": "follow_up", "presentation": "markdown"},
            {"name": "Constituency", "id": "constituency"},
            {"name": "Financial year", "id": "financial_year"},
            {"name": "Review priority", "id": "risk_priority"},
            {"name": "Flag count", "id": "risk_flag_count"},
            {"name": "Total spend", "id": "total_spend", "type": "numeric", "format": {"specifier": ",.2f"}},
            {"name": "Overall utilisation %", "id": "overall_utilisation_pct", "type": "numeric", "format": {"specifier": ",.1f"}},
            {"name": "Explanation", "id": "risk_explanations"},
        ],
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left", "padding": "10px", "whiteSpace": "normal", "height": "auto", "fontSize": "0.95rem"},
        style_header={"fontWeight": "bold", "backgroundColor": "#f3ede2"},
        style_data_conditional=[
            {"if": {"filter_query": '{risk_priority} = "High"', "column_id": "risk_priority"}, "backgroundColor": "#f8d7da", "color": "#6b1d23", "fontWeight": "bold"},
            {"if": {"filter_query": '{risk_priority} = "Medium"', "column_id": "risk_priority"}, "backgroundColor": "#fff3cd", "color": "#6b4e00", "fontWeight": "bold"},
            {"if": {"filter_query": '{risk_priority} = "Low"', "column_id": "risk_priority"}, "backgroundColor": "#dcecff", "color": "#143a5c", "fontWeight": "bold"},
            {"if": {"column_id": "follow_up"}, "fontWeight": "bold"},
        ],
        markdown_options={"link_target": "_self"},
        page_size=25,
    )


def _metric_card(title: str, value: str) -> dbc.Col:
    return dbc.Col(
        dbc.Card(
            dbc.CardBody([html.Div(title, className="text-muted small"), html.Div(value, className="fs-4 fw-bold")]),
            className="surface-card metric-card",
        ),
        md=6,
        lg=2,
    )


def _normalise_page(pathname: str | None) -> str:
    page = (pathname or "/overview").strip("/")
    return page if page in PAGE_TITLES else "overview"


def _filter_to_year(df: pd.DataFrame, year_filter: str | None) -> pd.DataFrame:
    if df.empty or not year_filter or year_filter == "ALL" or "financial_year" not in df.columns:
        return df.copy()
    return df[df["financial_year"] == year_filter].copy()


def _selected_mp_from_search(search: str | None, analytics_df: pd.DataFrame) -> str | None:
    if analytics_df.empty:
        return None
    if not search:
        return None
    parsed = parse_qs(search.lstrip("?"))
    selected_mp = parsed.get("mp", [None])[0]
    if selected_mp in set(analytics_df["mp_name"].dropna().tolist()):
        return selected_mp
    return None


def _format_currency(value: float | int | None) -> str:
    if pd.isna(value):
        return "Not available"
    return f"£{float(value):,.0f}"


def _format_pct(value: float | int | None) -> str:
    if pd.isna(value):
        return "Not available"
    return f"{float(value):.1f}%"


def _build_mp_profile_content(selected_mp: str, analytics_records: list[dict]) -> html.Div:
    analytics_df = pd.DataFrame(analytics_records)
    mp_row = analytics_df[analytics_df["mp_name"] == selected_mp].sort_values("financial_year", ascending=False).iloc[0]
    peer_df = analytics_df[analytics_df["peer_group"] == mp_row["peer_group"]].copy()
    peer_df = peer_df.sort_values("total_spend", ascending=False).reset_index(drop=True)

    comparison_df = pd.DataFrame(
        {
            "Metric": ["Total spend", "Overall utilisation", "Travel spend", "Uncapped spend"],
            "Selected MP": [
                float(mp_row.get("total_spend", 0) or 0),
                float(mp_row.get("overall_utilisation_pct", 0) or 0),
                float(mp_row.get("travel_spend", 0) or 0),
                float(mp_row.get("uncapped_spend_total", 0) or 0),
            ],
            "Peer average": [
                float(peer_df["total_spend"].mean()),
                float(peer_df["overall_utilisation_pct"].mean()),
                float(peer_df["travel_spend"].mean()),
                float(peer_df["uncapped_spend_total"].mean()),
            ],
        }
    )
    comparison_fig = px.bar(
        comparison_df,
        x="Metric",
        y=["Selected MP", "Peer average"],
        barmode="group",
        title="Selected MP Versus Peer Group",
        color_discrete_sequence=["#8b2f39", "#667085"],
    )
    comparison_fig.update_layout(margin={"l": 20, "r": 20, "t": 60, "b": 20}, plot_bgcolor="#fffdf9", paper_bgcolor="#fffdf9")

    peer_rank = int(peer_df.index[peer_df["mp_name"] == selected_mp][0] + 1)
    peer_count = int(len(peer_df))

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H3(selected_mp, className="h4 mb-2"),
                                    html.P(mp_row.get("constituency") or "Constituency not available", className="text-muted mb-3"),
                                    html.Div(f"Review priority: {mp_row['risk_priority']}", className="fw-semibold mb-1"),
                                    html.Div(f"Peer group: {str(mp_row['peer_group']).replace('|', ' / ')}", className="small text-muted mb-3"),
                                    html.Div(f"Total spend: {_format_currency(mp_row.get('total_spend'))}"),
                                    html.Div(f"Overall utilisation: {_format_pct(mp_row.get('overall_utilisation_pct'))}"),
                                    html.Div(f"Travel spend: {_format_currency(mp_row.get('travel_spend'))}"),
                                    html.Div(f"Uncapped spend: {_format_currency(mp_row.get('uncapped_spend_total'))}"),
                                    html.Div(f"Peer-group spend rank: {peer_rank} of {peer_count}", className="mt-2"),
                                ]
                            ),
                            className="surface-card tall-card",
                        ),
                        md=4,
                    ),
                    dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(figure=comparison_fig, config={"displayModeBar": False})), className="surface-card chart-card"), md=8),
                ],
                className="mb-4",
            ),
            dbc.Card(
                dbc.CardBody(
                    [
                        html.Div("Risk explanation", className="panel-kicker mb-2"),
                        html.P(mp_row.get("risk_explanations") or "No notable variance flags were triggered for this record.", className="mb-0"),
                    ]
                ),
                className="mb-4",
                style={"backgroundColor": "#fffdf9", "border": "1px solid #e8dfd0"},
            ),
            html.H3("Peer Group Comparison", className="h5 mb-3"),
            _simple_table(
                peer_df[["mp_name", "financial_year", "risk_priority", "risk_flag_count", "total_spend", "overall_utilisation_pct", "travel_spend", "uncapped_spend_total"]].head(15)
            ),
        ]
    )


def _build_validation_summary_panel(validation_df: pd.DataFrame, limitations_df: pd.DataFrame) -> dbc.Card:
    reviewed_items = validation_df[validation_df["status"] == "review"].copy()
    top_review_items = reviewed_items.sort_values(["issue_pct", "issue_count"], ascending=False).head(3)
    limitation_items = limitations_df[limitations_df["category"] == "data_limitation"]["description"].tolist()[:2]
    assumption_items = limitations_df[limitations_df["category"] == "assumption"]["description"].tolist()[:2]

    review_list = [
        html.Li(f"{row['column_name']}: {row['issue_pct']:.2f}% flagged for review")
        for _, row in top_review_items.iterrows()
    ]
    limitation_list = [html.Li(text) for text in limitation_items]
    assumption_list = [html.Li(text) for text in assumption_items]

    return dbc.Card(
        dbc.CardBody(
            [
                html.Div("Data limitations and assumptions", className="panel-kicker mb-2"),
                html.Div("Current QA highlights", className="small text-muted mb-2"),
                html.Ul(review_list, className="small ps-3 mb-3") if review_list else html.P("No QA review items were generated.", className="small mb-3"),
                html.Div("Limitations", className="small text-muted mb-2"),
                html.Ul(limitation_list, className="small ps-3 mb-3"),
                html.Div("Assumptions", className="small text-muted mb-2"),
                html.Ul(assumption_list, className="small ps-3 mb-0"),
            ]
        ),
        className="surface-card tall-card",
    )


def _build_qa_exception_strip(analytics_df: pd.DataFrame, validation_df: pd.DataFrame) -> html.Div:
    review_df = validation_df[validation_df["status"] == "review"].copy()
    review_check_count = int(len(review_df))

    critical_fields = [
        "mp_name",
        "financial_year",
        "total_spend",
        "risk_priority",
        "risk_flag_count",
        "overall_utilisation_pct",
        "source_url",
        "source_file",
    ]
    available_critical_fields = [column for column in critical_fields if column in analytics_df.columns]
    missing_record_count = 0
    if available_critical_fields:
        missing_record_count = int(analytics_df[available_critical_fields].isna().any(axis=1).sum())

    negative_columns = [
        column
        for column in [
            "office_spend",
            "staffing_spend",
            "winding_up_spend",
            "accommodation_spend",
            "travel_spend",
            "other_costs_spend",
            "uncapped_spend_total",
            "total_remaining_budget",
        ]
        if column in analytics_df.columns
    ]
    negative_record_count = 0
    if negative_columns:
        negative_record_count = int(analytics_df[negative_columns].fillna(0).lt(0).any(axis=1).sum())

    logic_record_count = 0
    duplicate_keys = [column for column in ["mp_name", "financial_year"] if column in analytics_df.columns]
    if len(duplicate_keys) == 2:
        logic_record_count += int(analytics_df.duplicated(subset=duplicate_keys).sum())

    utilisation_columns = [
        column
        for column in [
            "office_utilisation_pct",
            "staffing_utilisation_pct",
            "winding_up_utilisation_pct",
            "accommodation_utilisation_pct",
            "startup_utilisation_pct",
            "overall_utilisation_pct",
        ]
        if column in analytics_df.columns
    ]
    if utilisation_columns:
        logic_record_count += int(
            analytics_df[utilisation_columns]
            .apply(pd.to_numeric, errors="coerce")
            .pipe(lambda frame: ((frame < 0) | (frame > 150)).any(axis=1))
            .sum()
        )

    chips = [
        _exception_chip("Review checks", str(review_check_count), "QA checks with at least one review item in the current validation output"),
        _exception_chip("Records missing critical fields", f"{missing_record_count:,}", "Rows missing at least one core field used for audit review"),
        _exception_chip("Records with negative or offset values", f"{negative_record_count:,}", "Rows containing negative or offset monetary values"),
        _exception_chip("Records with logic exceptions", f"{logic_record_count:,}", "Rows with duplicate keys or utilisation values outside expected bounds"),
    ]

    return dbc.Card(
        dbc.CardBody(
            [
                html.Div("Recent QA exceptions", className="panel-kicker mb-3"),
                dbc.Row([dbc.Col(chip, md=6, lg=3) for chip in chips], className="g-3"),
            ]
        ),
        className="surface-card mb-4",
    )


def _exception_chip(title: str, value: str, note: str) -> dbc.Card:
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(title, className="small text-muted mb-1"),
                html.Div(value, className="fs-4 fw-bold qa-chip-value"),
                html.Div(note, className="small text-muted"),
            ]
        ),
        className="qa-chip",
    )


def _build_empty_page(title: str, year_label: str) -> html.Div:
    return html.Div(
        [
            html.H2(title, className="h3 mb-3"),
            html.P(f"Current review window: {year_label}", className="text-muted mb-3"),
            dbc.Card(
                dbc.CardBody("No records are available for the selected review window. Choose a different year or return to All years."),
                className="surface-card",
            ),
        ]
    )


app = build_app()

if __name__ == "__main__":
    app.run(debug=False)