"""
St. Andrew — Statement of Activities Dashboard
A professional Streamlit app for analyzing monthly church financial reports.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from parser import parse_soa

# ──────────────────────────────────────────────
#  Configuration
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="St. Andrew — Financial Dashboard",
    page_icon="⛪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Color palette
GREEN = "#2E7D32"
RED = "#C62828"
BLUE = "#1565C0"
GRAY_BG = "#F5F5F5"
LIGHT_GREEN = "#E8F5E9"
LIGHT_RED = "#FFEBEE"
AMBER = "#FF8F00"

# ──────────────────────────────────────────────
#  Custom CSS
# ──────────────────────────────────────────────
st.markdown("""
<style>
    .main .block-container { padding-top: 1.5rem; }
    .kpi-card {
        background: #F5F5F5;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        text-align: center;
        border-left: 5px solid #1565C0;
    }
    .kpi-card.green { border-left-color: #2E7D32; }
    .kpi-card.red { border-left-color: #C62828; }
    .kpi-card.blue { border-left-color: #1565C0; }
    .kpi-card.amber { border-left-color: #FF8F00; }
    .kpi-label {
        font-size: 0.85rem;
        color: #666;
        margin-bottom: 0.3rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .kpi-sub {
        font-size: 0.8rem;
        color: #888;
    }
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #333;
        margin: 1.5rem 0 0.5rem 0;
        padding-bottom: 0.3rem;
        border-bottom: 2px solid #1565C0;
    }
    .alert-box {
        background: #FFEBEE;
        border-left: 4px solid #C62828;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
    }
    div[data-testid="stSidebar"] {
        background: #FAFAFA;
    }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────
def fmt(val: float) -> str:
    """Format as currency with $ and thousands separator."""
    if val < 0:
        return f"-${abs(val):,.0f}"
    return f"${val:,.0f}"


def fmt_pct(val: float) -> str:
    """Format as percentage."""
    if pd.isna(val) or val == float("inf") or val == float("-inf"):
        return "N/A"
    return f"{val:+.1f}%"


def variance_color(actual, budget):
    """Return color based on whether actual meets budget."""
    if budget == 0:
        return BLUE
    return GREEN if actual >= budget else RED


def kpi_card(label, value, subtitle="", card_class="blue"):
    """Render a styled KPI card."""
    return f"""
    <div class="kpi-card {card_class}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{subtitle}</div>
    </div>
    """


def traffic_light(actual, budget, flow_type="Income"):
    """Return emoji + class for budget comparison."""
    if budget == 0:
        return "blue", "—"
    ratio = actual / budget
    if flow_type == "Income":
        if ratio >= 1.0:
            return "green", "On Track"
        elif ratio >= 0.9:
            return "amber", "Close"
        else:
            return "red", "Below Budget"
    else:  # Expense — under budget is good
        if ratio <= 1.0:
            return "green", "Under Budget"
        elif ratio <= 1.1:
            return "amber", "Slightly Over"
        else:
            return "red", "Over Budget"


# ──────────────────────────────────────────────
#  Sidebar — File upload & filters
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⛪ St. Andrew")
    st.markdown("##### Financial Dashboard")
    st.markdown("---")

    uploaded_files = st.file_uploader(
        "Upload SOA Reports (.xlsx)",
        type=["xlsx"],
        accept_multiple_files=True,
        help="Upload one or more monthly Statement of Activities Excel files.",
    )

    st.markdown("---")

# ──────────────────────────────────────────────
#  Parse uploaded files
# ──────────────────────────────────────────────
if not uploaded_files:
    st.markdown("""
    <div style="text-align: center; margin-top: 5rem;">
        <h2 style="color: #1565C0;">Welcome to the St. Andrew Financial Dashboard</h2>
        <p style="color: #666; font-size: 1.1rem; max-width: 500px; margin: 1rem auto;">
            Upload one or more monthly Statement of Activities (.xlsx) files
            using the sidebar to get started.
        </p>
        <p style="font-size: 3rem; margin-top: 2rem;">📊</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Parse all files
all_dfs = []
for f in uploaded_files:
    try:
        df = parse_soa(f)
        if df.empty:
            st.sidebar.warning(f"⚠️ {f.name}: No data extracted.")
        else:
            all_dfs.append(df)
    except Exception as e:
        st.sidebar.error(f"❌ {f.name}: {str(e)[:80]}")

if not all_dfs:
    st.error("No valid data could be extracted from the uploaded files.")
    st.stop()

data = pd.concat(all_dfs, ignore_index=True).sort_values("report_month")
months = sorted(data["report_month"].unique())

# Sidebar filters
with st.sidebar:
    selected_month = st.selectbox(
        "Select Month",
        months,
        index=len(months) - 1,
        format_func=lambda m: pd.Timestamp(m + "-01").strftime("%B %Y"),
    )

    all_categories = sorted(data["category"].dropna().unique())
    selected_categories = st.multiselect(
        "Filter Categories",
        all_categories,
        default=all_categories,
    )

    st.markdown("---")

    # Extraordinary items toggle
    exclude_extraordinary = st.checkbox(
        "Exclude Extraordinary Items",
        value=False,
        help="Hide unbudgeted one-off items (annual budget = $0) to focus on operating performance.",
    )

    st.markdown("---")
    st.markdown(
        f"<small style='color:#999;'>📁 {len(uploaded_files)} file(s) loaded<br>"
        f"📅 {len(months)} month(s) available<br>"
        f"📋 {len(data)} line items total</small>",
        unsafe_allow_html=True,
    )

# Filter data
month_data = data[
    (data["report_month"] == selected_month)
    & (data["category"].isin(selected_categories))
]

# Identify extraordinary items BEFORE filtering
extraordinary = month_data[
    (month_data["annual_budget"] == 0) & (month_data["ytd_actual"].abs() > 100)
].copy()
extraordinary["impact_type"] = extraordinary["flow_type"].map(
    {"Income": "Unbudgeted Income", "Expense": "Unbudgeted Expense"}
)

# Also find items massively over budget (>200% and >$5K over)
budgeted_items = month_data[month_data["annual_budget"] > 0].copy()
if not budgeted_items.empty:
    budgeted_items["_ytd_var"] = budgeted_items["ytd_actual"] - budgeted_items["ytd_budget"]
    budgeted_items["_ytd_pct"] = budgeted_items.apply(
        lambda r: (r["ytd_actual"] / r["ytd_budget"] - 1) * 100
        if r["ytd_budget"] != 0 else 0, axis=1
    )
    over_budget_outliers = budgeted_items[
        (budgeted_items["_ytd_var"] > 5000) & (budgeted_items["_ytd_pct"] > 100)
    ].copy()
    over_budget_outliers["impact_type"] = "Massively Over Budget"
else:
    over_budget_outliers = pd.DataFrame()

# Apply extraordinary filter if toggle is on
if exclude_extraordinary:
    month_data = month_data[month_data["annual_budget"] != 0]

income = month_data[month_data["flow_type"] == "Income"]
expense = month_data[month_data["flow_type"] == "Expense"]

month_label = pd.Timestamp(selected_month + "-01").strftime("%B %Y")

# ──────────────────────────────────────────────
#  TABS
# ──────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Executive Summary",
    "💰 Income Breakdown",
    "💸 Expense Breakdown",
    "📈 YTD Progress",
    "📊 Multi-Month Trends",
])


# ──────────────────────────────────────────────
#  TAB 1 — Executive Summary
# ──────────────────────────────────────────────
with tab1:
    st.markdown(f"### Executive Summary — {month_label}")

    inc_actual = income["current_actual"].sum()
    inc_budget = income["current_budget"].sum()
    exp_actual = expense["current_actual"].sum()
    exp_budget = expense["current_budget"].sum()
    net_actual = inc_actual - exp_actual
    net_budget = inc_budget - exp_budget

    ytd_inc = income["ytd_actual"].sum()
    ytd_exp = expense["ytd_actual"].sum()
    ytd_net = ytd_inc - ytd_exp
    annual_inc_budget = income["annual_budget"].sum()
    annual_exp_budget = expense["annual_budget"].sum()
    annual_net_budget = annual_inc_budget - annual_exp_budget

    # KPI row 1
    c1, c2, c3, c4 = st.columns(4)
    inc_cls, inc_status = traffic_light(inc_actual, inc_budget, "Income")
    exp_cls, exp_status = traffic_light(exp_actual, exp_budget, "Expense")
    net_cls = "green" if net_actual >= 0 else "red"
    ytd_cls = "green" if ytd_net >= 0 else "red"

    with c1:
        var_inc = ((inc_actual / inc_budget - 1) * 100) if inc_budget else 0
        st.markdown(kpi_card(
            "Total Income",
            fmt(inc_actual),
            f"Budget: {fmt(inc_budget)} · {inc_status}",
            inc_cls,
        ), unsafe_allow_html=True)

    with c2:
        st.markdown(kpi_card(
            "Total Expenses",
            fmt(exp_actual),
            f"Budget: {fmt(exp_budget)} · {exp_status}",
            exp_cls,
        ), unsafe_allow_html=True)

    with c3:
        st.markdown(kpi_card(
            "Net Income",
            fmt(net_actual),
            f"Budget: {fmt(net_budget)}",
            net_cls,
        ), unsafe_allow_html=True)

    with c4:
        st.markdown(kpi_card(
            "YTD Net",
            fmt(ytd_net),
            f"Annual Budget: {fmt(annual_net_budget)}",
            ytd_cls,
        ), unsafe_allow_html=True)

    st.markdown("")

    # Income vs Expense bar
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('<div class="section-header">Current Month: Actual vs Budget</div>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=["Income", "Expenses"],
            y=[inc_actual, exp_actual],
            name="Actual",
            marker_color=[GREEN, RED],
            text=[fmt(inc_actual), fmt(exp_actual)],
            textposition="outside",
        ))
        fig.add_trace(go.Bar(
            x=["Income", "Expenses"],
            y=[inc_budget, exp_budget],
            name="Budget",
            marker_color=["#A5D6A7", "#EF9A9A"],
            text=[fmt(inc_budget), fmt(exp_budget)],
            textposition="outside",
        ))
        fig.update_layout(
            barmode="group",
            height=350,
            margin=dict(t=20, b=40, l=40, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            yaxis_tickformat="$,.0f",
            plot_bgcolor="white",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown('<div class="section-header">YTD: Actual vs Annual Budget</div>', unsafe_allow_html=True)
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=["Income", "Expenses", "Net"],
            y=[ytd_inc, ytd_exp, ytd_net],
            name="YTD Actual",
            marker_color=[GREEN, RED, BLUE],
            text=[fmt(ytd_inc), fmt(ytd_exp), fmt(ytd_net)],
            textposition="outside",
        ))
        fig2.add_trace(go.Bar(
            x=["Income", "Expenses", "Net"],
            y=[annual_inc_budget, annual_exp_budget, annual_net_budget],
            name="Annual Budget",
            marker_color=["#A5D6A7", "#EF9A9A", "#90CAF9"],
            text=[fmt(annual_inc_budget), fmt(annual_exp_budget), fmt(annual_net_budget)],
            textposition="outside",
        ))
        fig2.update_layout(
            barmode="group",
            height=350,
            margin=dict(t=20, b=40, l=40, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            yaxis_tickformat="$,.0f",
            plot_bgcolor="white",
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Extraordinary Items Alert ──
    if not extraordinary.empty or not over_budget_outliers.empty:
        st.markdown('<div class="section-header">Extraordinary & High-Impact Items</div>',
                    unsafe_allow_html=True)

        if exclude_extraordinary:
            st.info("Extraordinary items are currently **excluded** from the numbers above. "
                    "Uncheck the sidebar toggle to include them.")

        # Unbudgeted items
        if not extraordinary.empty:
            ext_sorted = extraordinary.sort_values("ytd_actual", key=abs, ascending=False)
            ext_inc = ext_sorted[ext_sorted["flow_type"] == "Income"]
            ext_exp = ext_sorted[ext_sorted["flow_type"] == "Expense"]

            if not ext_inc.empty:
                total_ext_inc = ext_inc["ytd_actual"].sum()
                st.markdown(
                    f'<div style="background:#E8F5E9; border-left:4px solid #2E7D32; '
                    f'border-radius:8px; padding:0.8rem 1rem; margin-bottom:0.8rem;">'
                    f'<strong style="color:#2E7D32;">Unbudgeted Income — '
                    f'YTD Total: {fmt(total_ext_inc)}</strong></div>',
                    unsafe_allow_html=True,
                )
                for _, r in ext_inc.iterrows():
                    st.markdown(
                        f'<div style="background:#F5F5F5; border-radius:6px; padding:0.5rem 1rem; '
                        f'margin-bottom:0.3rem; margin-left:1rem; font-size:0.88rem;">'
                        f'<strong>{r["account_name"]}</strong> '
                        f'<span style="color:#888;">({r["category"]})</span> — '
                        f'YTD: <strong>{fmt(r["ytd_actual"])}</strong> · '
                        f'This Month: {fmt(r["current_actual"])}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            if not ext_exp.empty:
                total_ext_exp = ext_exp["ytd_actual"].sum()
                st.markdown(
                    f'<div style="background:#FFEBEE; border-left:4px solid #C62828; '
                    f'border-radius:8px; padding:0.8rem 1rem; margin-top:0.8rem; margin-bottom:0.8rem;">'
                    f'<strong style="color:#C62828;">Unbudgeted Expenses — '
                    f'YTD Total: {fmt(total_ext_exp)}</strong></div>',
                    unsafe_allow_html=True,
                )
                for _, r in ext_exp.iterrows():
                    st.markdown(
                        f'<div style="background:#F5F5F5; border-radius:6px; padding:0.5rem 1rem; '
                        f'margin-bottom:0.3rem; margin-left:1rem; font-size:0.88rem;">'
                        f'<strong>{r["account_name"]}</strong> '
                        f'<span style="color:#888;">({r["category"]})</span> — '
                        f'YTD: <strong>{fmt(r["ytd_actual"])}</strong> · '
                        f'This Month: {fmt(r["current_actual"])}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        # Over-budget outliers
        if not over_budget_outliers.empty:
            st.markdown(
                f'<div style="background:#FFF3E0; border-left:4px solid #FF8F00; '
                f'border-radius:8px; padding:0.8rem 1rem; margin-top:0.8rem; margin-bottom:0.8rem;">'
                f'<strong style="color:#E65100;">Massively Over Budget (>100% & >$5K)</strong></div>',
                unsafe_allow_html=True,
            )
            for _, r in over_budget_outliers.sort_values("_ytd_var", ascending=False).iterrows():
                st.markdown(
                    f'<div style="background:#F5F5F5; border-radius:6px; padding:0.5rem 1rem; '
                    f'margin-bottom:0.3rem; margin-left:1rem; font-size:0.88rem;">'
                    f'<strong>{r["account_name"]}</strong> '
                    f'<span style="color:#888;">({r["category"]})</span> — '
                    f'YTD Actual: <strong>{fmt(r["ytd_actual"])}</strong> vs '
                    f'Budget: {fmt(r["ytd_budget"])} · '
                    f'<span style="color:#C62828;">Over by {fmt(r["_ytd_var"])} ({r["_ytd_pct"]:+.0f}%)</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ──────────────────────────────────────────────
#  TAB 2 — Income Breakdown
# ──────────────────────────────────────────────
with tab2:
    st.markdown(f"### Income Breakdown — {month_label}")

    if income.empty:
        st.info("No income data for this selection.")
    else:
        # Category summary
        cat_inc = income.groupby("category").agg(
            Actual=("current_actual", "sum"),
            Budget=("current_budget", "sum"),
        ).reset_index()
        cat_inc["Variance $"] = cat_inc["Actual"] - cat_inc["Budget"]
        cat_inc["Variance %"] = cat_inc.apply(
            lambda r: (r["Actual"] / r["Budget"] - 1) * 100 if r["Budget"] != 0 else 0, axis=1
        )
        cat_inc = cat_inc.sort_values("Actual", ascending=True)

        # Bar chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=cat_inc["category"],
            x=cat_inc["Actual"],
            name="Actual",
            orientation="h",
            marker_color=GREEN,
            text=cat_inc["Actual"].apply(fmt),
            textposition="outside",
        ))
        fig.add_trace(go.Bar(
            y=cat_inc["category"],
            x=cat_inc["Budget"],
            name="Budget",
            orientation="h",
            marker_color="#A5D6A7",
            text=cat_inc["Budget"].apply(fmt),
            textposition="outside",
        ))
        fig.update_layout(
            barmode="group",
            height=max(300, len(cat_inc) * 80),
            margin=dict(t=20, b=40, l=10, r=80),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            xaxis_tickformat="$,.0f",
            plot_bgcolor="white",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Detail table
        st.markdown('<div class="section-header">Line Item Detail</div>', unsafe_allow_html=True)
        detail = income[["category", "account_code", "account_name",
                         "current_actual", "current_budget"]].copy()
        detail["Variance $"] = detail["current_actual"] - detail["current_budget"]
        detail["Variance %"] = detail.apply(
            lambda r: (r["current_actual"] / r["current_budget"] - 1) * 100
            if r["current_budget"] != 0 else 0, axis=1
        )
        detail = detail.rename(columns={
            "category": "Category",
            "account_code": "Account",
            "account_name": "Description",
            "current_actual": "Actual",
            "current_budget": "Budget",
        })

        st.dataframe(
            detail.style.format({
                "Actual": "${:,.2f}",
                "Budget": "${:,.2f}",
                "Variance $": "${:,.2f}",
                "Variance %": "{:+.1f}%",
            }),
            use_container_width=True,
            height=500,
        )


# ──────────────────────────────────────────────
#  TAB 3 — Expense Breakdown
# ──────────────────────────────────────────────
with tab3:
    st.markdown(f"### Expense Breakdown — {month_label}")

    if expense.empty:
        st.info("No expense data for this selection.")
    else:
        # Category summary
        cat_exp = expense.groupby("category").agg(
            Actual=("current_actual", "sum"),
            Budget=("current_budget", "sum"),
        ).reset_index()
        cat_exp["Variance $"] = cat_exp["Actual"] - cat_exp["Budget"]
        cat_exp["Variance %"] = cat_exp.apply(
            lambda r: (r["Actual"] / r["Budget"] - 1) * 100 if r["Budget"] != 0 else 0, axis=1
        )
        cat_exp = cat_exp.sort_values("Actual", ascending=False)

        # Bar chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=cat_exp["category"],
            x=cat_exp["Actual"],
            name="Actual",
            orientation="h",
            marker_color=RED,
            text=cat_exp["Actual"].apply(fmt),
            textposition="outside",
        ))
        fig.add_trace(go.Bar(
            y=cat_exp["category"],
            x=cat_exp["Budget"],
            name="Budget",
            orientation="h",
            marker_color="#EF9A9A",
            text=cat_exp["Budget"].apply(fmt),
            textposition="outside",
        ))
        fig.update_layout(
            barmode="group",
            height=max(400, len(cat_exp) * 55),
            margin=dict(t=20, b=40, l=10, r=80),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            xaxis_tickformat="$,.0f",
            plot_bgcolor="white",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Over-budget alerts
        over = expense.copy()
        over["over_amount"] = over["current_actual"] - over["current_budget"]
        over = over[over["over_amount"] > 0].sort_values("over_amount", ascending=False).head(5)

        if not over.empty:
            st.markdown('<div class="section-header">⚠️ Top Items Over Budget</div>', unsafe_allow_html=True)
            for _, row in over.iterrows():
                pct = (row["over_amount"] / row["current_budget"] * 100) if row["current_budget"] != 0 else 0
                st.markdown(
                    f'<div class="alert-box">'
                    f'<strong>{row["account_name"]}</strong> ({row["category"]})<br>'
                    f'Actual: {fmt(row["current_actual"])} · Budget: {fmt(row["current_budget"])} · '
                    f'Over by: <strong>{fmt(row["over_amount"])}</strong> ({pct:+.0f}%)'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # Detail table
        st.markdown('<div class="section-header">Line Item Detail</div>', unsafe_allow_html=True)

        filter_cat = st.selectbox(
            "Filter by category",
            ["All"] + sorted(expense["category"].unique()),
            key="exp_cat_filter",
        )

        detail_exp = expense.copy()
        if filter_cat != "All":
            detail_exp = detail_exp[detail_exp["category"] == filter_cat]

        detail_exp = detail_exp[["category", "account_code", "account_name",
                                  "current_actual", "current_budget"]].copy()
        detail_exp["Variance $"] = detail_exp["current_actual"] - detail_exp["current_budget"]
        detail_exp["Variance %"] = detail_exp.apply(
            lambda r: (r["current_actual"] / r["current_budget"] - 1) * 100
            if r["current_budget"] != 0 else 0, axis=1
        )
        detail_exp = detail_exp.rename(columns={
            "category": "Category",
            "account_code": "Account",
            "account_name": "Description",
            "current_actual": "Actual",
            "current_budget": "Budget",
        })

        st.dataframe(
            detail_exp.style.format({
                "Actual": "${:,.2f}",
                "Budget": "${:,.2f}",
                "Variance $": "${:,.2f}",
                "Variance %": "{:+.1f}%",
            }),
            use_container_width=True,
            height=500,
        )


# ──────────────────────────────────────────────
#  TAB 4 — YTD Progress
# ──────────────────────────────────────────────
with tab4:
    st.markdown(f"### Year-to-Date Progress — {month_label}")

    # YTD by category
    ytd_data = month_data.groupby(["flow_type", "category"]).agg(
        ytd_actual=("ytd_actual", "sum"),
        annual_budget=("annual_budget", "sum"),
        ytd_last_year=("ytd_last_year", "sum"),
    ).reset_index()

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="section-header">YTD Actual vs Annual Budget</div>', unsafe_allow_html=True)
        for flow in ["Income", "Expense"]:
            st.markdown(f"**{flow}**")
            subset = ytd_data[ytd_data["flow_type"] == flow].sort_values("ytd_actual", ascending=False)
            for _, row in subset.iterrows():
                pct = (row["ytd_actual"] / row["annual_budget"] * 100) if row["annual_budget"] > 0 else 0
                color = GREEN if flow == "Income" else RED
                bar_pct = min(pct, 100)
                st.markdown(
                    f"<div style='margin-bottom:0.8rem;'>"
                    f"<div style='display:flex; justify-content:space-between; font-size:0.85rem;'>"
                    f"<span>{row['category']}</span>"
                    f"<span>{fmt(row['ytd_actual'])} / {fmt(row['annual_budget'])} ({pct:.0f}%)</span>"
                    f"</div>"
                    f"<div style='background:#E0E0E0; border-radius:6px; height:12px; overflow:hidden;'>"
                    f"<div style='width:{bar_pct}%; background:{color}; height:100%; border-radius:6px;'></div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

    with col_b:
        st.markdown('<div class="section-header">YTD Actual vs Last Year</div>', unsafe_allow_html=True)
        for flow in ["Income", "Expense"]:
            subset = ytd_data[ytd_data["flow_type"] == flow].sort_values("ytd_actual", ascending=False)
            if subset.empty:
                continue

            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=subset["category"],
                x=subset["ytd_actual"],
                name="This Year",
                orientation="h",
                marker_color=GREEN if flow == "Income" else RED,
            ))
            fig.add_trace(go.Bar(
                y=subset["category"],
                x=subset["ytd_last_year"],
                name="Last Year",
                orientation="h",
                marker_color="#BDBDBD",
            ))
            fig.update_layout(
                title=flow,
                barmode="group",
                height=max(250, len(subset) * 45),
                margin=dict(t=40, b=20, l=10, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                xaxis_tickformat="$,.0f",
                plot_bgcolor="white",
            )
            st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────
#  TAB 5 — Multi-Month Trends
# ──────────────────────────────────────────────
with tab5:
    st.markdown("### Multi-Month Trends")

    if len(months) < 2:
        st.info("Upload two or more monthly files to see trends over time.")
    else:
        # Monthly totals
        monthly = data[data["category"].isin(selected_categories)].groupby(
            ["report_month", "flow_type"]
        )["current_actual"].sum().reset_index()

        inc_trend = monthly[monthly["flow_type"] == "Income"].set_index("report_month")["current_actual"]
        exp_trend = monthly[monthly["flow_type"] == "Expense"].set_index("report_month")["current_actual"]
        all_months_idx = sorted(monthly["report_month"].unique())
        inc_trend = inc_trend.reindex(all_months_idx, fill_value=0)
        exp_trend = exp_trend.reindex(all_months_idx, fill_value=0)
        net_trend = inc_trend - exp_trend

        month_labels = [pd.Timestamp(m + "-01").strftime("%b %Y") for m in all_months_idx]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="section-header">Income & Expense by Month</div>', unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=month_labels, y=inc_trend.values,
                name="Income", mode="lines+markers",
                line=dict(color=GREEN, width=3),
                marker=dict(size=8),
                text=[fmt(v) for v in inc_trend.values],
                hoverinfo="text+name",
            ))
            fig.add_trace(go.Scatter(
                x=month_labels, y=exp_trend.values,
                name="Expenses", mode="lines+markers",
                line=dict(color=RED, width=3),
                marker=dict(size=8),
                text=[fmt(v) for v in exp_trend.values],
                hoverinfo="text+name",
            ))
            fig.update_layout(
                height=400,
                margin=dict(t=20, b=40, l=40, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                yaxis_tickformat="$,.0f",
                plot_bgcolor="white",
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown('<div class="section-header">Net Income Trend</div>', unsafe_allow_html=True)
            colors = [GREEN if v >= 0 else RED for v in net_trend.values]
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=month_labels, y=net_trend.values,
                marker_color=colors,
                text=[fmt(v) for v in net_trend.values],
                textposition="outside",
            ))
            fig2.update_layout(
                height=400,
                margin=dict(t=20, b=40, l=40, r=20),
                yaxis_tickformat="$,.0f",
                plot_bgcolor="white",
                showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True)

        # Category trends
        st.markdown('<div class="section-header">Category Trends Over Time</div>', unsafe_allow_html=True)
        trend_flow = st.radio("Show", ["Income", "Expense"], horizontal=True, key="trend_flow")
        cat_monthly = data[
            (data["flow_type"] == trend_flow)
            & (data["category"].isin(selected_categories))
        ].groupby(["report_month", "category"])["current_actual"].sum().reset_index()

        if not cat_monthly.empty:
            cat_monthly["month_label"] = cat_monthly["report_month"].apply(
                lambda m: pd.Timestamp(m + "-01").strftime("%b %Y")
            )
            fig3 = px.line(
                cat_monthly,
                x="month_label",
                y="current_actual",
                color="category",
                markers=True,
                labels={"current_actual": "Amount", "month_label": "Month", "category": "Category"},
            )
            fig3.update_layout(
                height=450,
                margin=dict(t=20, b=40, l=40, r=20),
                yaxis_tickformat="$,.0f",
                plot_bgcolor="white",
                hovermode="x unified",
            )
            st.plotly_chart(fig3, use_container_width=True)
