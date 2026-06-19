
"""
SpaceX IPO Market Impact Analysis
Author: Kiran Kanth Madigani

This project analyzes the SpaceX IPO using a clean official-pricing dataset,
historical IPO comparisons, recent IPO peer comparisons, investor paper-gain
scenarios, and Elon Musk ownership-benefit scenarios.

Run:
    python src/spacex_ipo_market_impact.py

Outputs:
    outputs/tables/*.csv
    outputs/tables/*.xlsx
    outputs/figures/*.png
    reports/SpaceX_IPO_Executive_Report.html

Disclaimer:
    This project is for analytics and education only. It is not investment advice.
"""

from pathlib import Path
from datetime import datetime
import math
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.io as pio

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
TABLE_DIR = OUTPUT_DIR / "tables"
REPORT_DIR = ROOT / "reports"

for folder in [FIGURE_DIR, TABLE_DIR, REPORT_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Visual brand colors
SPACEX_BLUE = "#00A3FF"
DEEP_NAVY = "#07111F"
SLATE = "#334155"
PURPLE = "#7C3AED"
GREEN = "#10B981"
RED = "#EF4444"
GOLD = "#F59E0B"
TEXT = "#E5E7EB"
GRID = "#233044"

plt.rcParams.update({
    "figure.facecolor": DEEP_NAVY,
    "axes.facecolor": DEEP_NAVY,
    "axes.edgecolor": GRID,
    "axes.labelcolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "text.color": TEXT,
    "font.size": 11,
    "axes.titleweight": "bold",
    "axes.titlesize": 18,
    "axes.labelsize": 12,
    "grid.color": GRID,
    "grid.alpha": 0.35,
    "savefig.facecolor": DEEP_NAVY,
    "savefig.bbox": "tight",
})


def money_b(x: float) -> str:
    return f"${x:,.2f}B"


def pct(x: float) -> str:
    return f"{x:,.2f}%"


def load_data():
    recent = pd.read_csv(DATA_DIR / "recent_ipos.csv")
    historical = pd.read_csv(DATA_DIR / "historical_ipos.csv")
    scenarios = pd.read_csv(DATA_DIR / "scenario_prices.csv")
    assumptions = pd.read_csv(DATA_DIR / "musk_assumptions.csv")

    recent["ipo_date"] = pd.to_datetime(recent["ipo_date"])
    recent["shares_offered"] = pd.to_numeric(recent["shares_offered"])
    recent["ipo_price_usd"] = pd.to_numeric(recent["ipo_price_usd"])
    recent["ipo_valuation_b"] = pd.to_numeric(recent["ipo_valuation_b"])
    recent["ipo_proceeds_b"] = (recent["shares_offered"] * recent["ipo_price_usd"]) / 1_000_000_000

    historical["ipo_proceeds_b"] = pd.to_numeric(historical["ipo_proceeds_b"])
    scenarios["ipo_price_usd"] = pd.to_numeric(scenarios["ipo_price_usd"])
    scenarios["scenario_market_price_usd"] = pd.to_numeric(scenarios["scenario_market_price_usd"], errors="coerce")
    scenarios["first_close_usd"] = pd.to_numeric(scenarios["first_close_usd"], errors="coerce")

    return recent, historical, scenarios, assumptions


def calculate_metrics(recent, historical, scenarios, assumptions):
    spacex_proceeds = recent.loc[recent["ticker"] == "SPCX", "ipo_proceeds_b"].iloc[0]
    previous_record = historical.loc[historical["company"] != "SpaceX", "ipo_proceeds_b"].max()
    recent_peer_median = recent.loc[recent["ticker"] != "SPCX", "ipo_proceeds_b"].median()

    recent = recent.copy()
    historical = historical.copy()

    recent["spacex_size_multiple"] = spacex_proceeds / recent["ipo_proceeds_b"]
    recent["share_of_recent_peer_group_pct"] = recent["ipo_proceeds_b"] / recent["ipo_proceeds_b"].sum() * 100

    historical["spacex_size_multiple"] = spacex_proceeds / historical["ipo_proceeds_b"]
    historical["share_of_historical_group_pct"] = historical["ipo_proceeds_b"] / historical["ipo_proceeds_b"].sum() * 100

    # Custom impact score: transparent scoring for business storytelling.
    # This intentionally combines quantitative size with qualitative market narrative.
    max_proceeds = recent["ipo_proceeds_b"].max()
    recent["proceeds_component"] = recent["ipo_proceeds_b"] / max_proceeds * 40
    recent["innovation_component"] = recent["innovation_score"] * 2
    recent["attention_component"] = recent["global_attention_score"] * 2
    recent["strategic_component"] = recent["strategic_importance_score"] * 2
    recent["market_impact_score"] = (
        recent["proceeds_component"]
        + recent["innovation_component"]
        + recent["attention_component"]
        + recent["strategic_component"]
    ).round(2)

    # Investor benefit scenario
    scenario = recent.merge(scenarios[["ticker", "scenario_market_price_usd", "first_close_usd"]], on="ticker", how="left")
    scenario["paper_gain_per_share_usd"] = scenario["scenario_market_price_usd"] - scenario["ipo_price_usd"]
    scenario["paper_return_from_ipo_price_pct"] = scenario["paper_gain_per_share_usd"] / scenario["ipo_price_usd"] * 100
    scenario["paper_gain_on_offered_shares_b"] = scenario["paper_gain_per_share_usd"] * scenario["shares_offered"] / 1_000_000_000
    scenario["first_day_gain_per_share_usd"] = scenario["first_close_usd"] - scenario["ipo_price_usd"]
    scenario["first_day_paper_gain_offered_shares_b"] = scenario["first_day_gain_per_share_usd"] * scenario["shares_offered"] / 1_000_000_000

    # Musk benefit scenario from valuation move
    musk_pct = float(assumptions.loc[assumptions["assumption"] == "musk_ownership_pct", "value"].iloc[0]) / 100
    ipo_valuation_b = float(assumptions.loc[assumptions["assumption"] == "ipo_implied_valuation_b", "value"].iloc[0])
    spacex_market_price = scenario.loc[scenario["ticker"] == "SPCX", "scenario_market_price_usd"].iloc[0]
    spacex_ipo_price = scenario.loc[scenario["ticker"] == "SPCX", "ipo_price_usd"].iloc[0]
    implied_market_cap_b = ipo_valuation_b * (spacex_market_price / spacex_ipo_price)
    valuation_gain_b = implied_market_cap_b - ipo_valuation_b

    musk = pd.DataFrame([
        {
            "assumption": "IPO implied valuation",
            "value_b": ipo_valuation_b,
            "explanation": "Approximate SpaceX value at IPO pricing."
        },
        {
            "assumption": "Scenario implied valuation",
            "value_b": implied_market_cap_b,
            "explanation": "IPO valuation scaled by scenario market price divided by IPO price."
        },
        {
            "assumption": "Total valuation increase",
            "value_b": valuation_gain_b,
            "explanation": "Paper market value increase from IPO valuation to scenario valuation."
        },
        {
            "assumption": "Musk ownership scenario benefit",
            "value_b": valuation_gain_b * musk_pct,
            "explanation": f"Scenario paper gain assuming {musk_pct:.0%} ownership. Not cash unless shares are sold."
        },
        {
            "assumption": "Musk stake scenario value",
            "value_b": implied_market_cap_b * musk_pct,
            "explanation": f"Scenario value of ownership stake assuming {musk_pct:.0%} ownership."
        },
    ])

    executive = {
        "spacex_proceeds_b": spacex_proceeds,
        "previous_record_b": previous_record,
        "spacex_vs_previous_record_multiple": spacex_proceeds / previous_record,
        "spacex_extra_vs_previous_record_b": spacex_proceeds - previous_record,
        "recent_peer_median_b": recent_peer_median,
        "spacex_vs_recent_peer_median_multiple": spacex_proceeds / recent_peer_median,
        "musk_ownership_pct": musk_pct,
        "spacex_scenario_market_price": spacex_market_price,
        "spacex_scenario_implied_market_cap_b": implied_market_cap_b,
        "musk_scenario_paper_gain_b": valuation_gain_b * musk_pct,
    }

    return recent, historical, scenario, musk, executive


def save_tables(recent, historical, scenario, musk, executive):
    recent.round(4).to_csv(TABLE_DIR / "recent_ipo_analysis.csv", index=False)
    historical.round(4).to_csv(TABLE_DIR / "historical_ipo_comparison.csv", index=False)
    scenario.round(4).to_csv(TABLE_DIR / "investor_benefit_scenario.csv", index=False)
    musk.round(4).to_csv(TABLE_DIR / "musk_benefit_scenario.csv", index=False)

    exec_df = pd.DataFrame([executive])
    exec_df.round(4).to_csv(TABLE_DIR / "executive_summary_metrics.csv", index=False)

    excel_path = TABLE_DIR / "SpaceX_IPO_Market_Impact_Analysis.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        exec_df.round(4).to_excel(writer, sheet_name="Executive_Summary", index=False)
        recent.round(4).to_excel(writer, sheet_name="Recent_IPOs", index=False)
        historical.round(4).to_excel(writer, sheet_name="Historical_IPOs", index=False)
        scenario.round(4).to_excel(writer, sheet_name="Investor_Benefit", index=False)
        musk.round(4).to_excel(writer, sheet_name="Musk_Benefit", index=False)

    return excel_path


def add_bar_labels(ax, values, prefix="$", suffix="B", decimals=1):
    for i, value in enumerate(values):
        label = f"{prefix}{value:.{decimals}f}{suffix}"
        ax.text(value + max(values) * 0.01, i, label, va="center", ha="left", fontsize=10, color=TEXT, weight="bold")


def chart_historical_ipos(historical):
    df = historical.sort_values("ipo_proceeds_b", ascending=True)
    colors = [SPACEX_BLUE if c == "SpaceX" else SLATE for c in df["company"]]

    fig, ax = plt.subplots(figsize=(15, 8))
    ax.barh(df["company"], df["ipo_proceeds_b"], color=colors, height=0.72)
    ax.set_title("SpaceX vs Largest IPOs in History: IPO Proceeds", loc="left", pad=20)
    ax.set_xlabel("IPO Proceeds, USD Billions")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    add_bar_labels(ax, df["ipo_proceeds_b"].values, decimals=1)
    ax.set_xlim(0, df["ipo_proceeds_b"].max() * 1.15)
    fig.tight_layout()
    path = FIGURE_DIR / "01_spacex_vs_largest_ipos.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def chart_recent_ipos(recent):
    df = recent.sort_values("ipo_proceeds_b", ascending=True)
    colors = [SPACEX_BLUE if c == "SpaceX" else PURPLE for c in df["company"]]

    fig, ax = plt.subplots(figsize=(15, 7))
    ax.barh(df["company"], df["ipo_proceeds_b"], color=colors, height=0.72)
    ax.set_title("SpaceX vs Recent Tech/Fintech IPOs: Offering Size", loc="left", pad=20)
    ax.set_xlabel("IPO Proceeds, USD Billions")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    add_bar_labels(ax, df["ipo_proceeds_b"].values, decimals=2)
    ax.set_xlim(0, df["ipo_proceeds_b"].max() * 1.15)
    fig.tight_layout()
    path = FIGURE_DIR / "02_recent_ipo_proceeds.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def chart_impact_score(recent):
    df = recent.sort_values("market_impact_score", ascending=True)
    colors = [SPACEX_BLUE if c == "SpaceX" else SLATE for c in df["company"]]

    fig, ax = plt.subplots(figsize=(15, 7))
    ax.barh(df["company"], df["market_impact_score"], color=colors, height=0.72)
    ax.set_title("Custom Market Impact Score: Size + Innovation + Attention + Strategic Importance", loc="left", pad=20)
    ax.set_xlabel("Impact Score")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    for i, value in enumerate(df["market_impact_score"]):
        ax.text(value + 1, i, f"{value:.1f}", va="center", ha="left", fontsize=10, color=TEXT, weight="bold")
    ax.set_xlim(0, max(df["market_impact_score"]) * 1.15)
    fig.tight_layout()
    path = FIGURE_DIR / "03_market_impact_score.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def chart_size_multiple(historical):
    df = historical[historical["company"] != "SpaceX"].sort_values("spacex_size_multiple", ascending=True)
    values = df["spacex_size_multiple"].values
    norm = (values - values.min()) / (values.max() - values.min())
    colors = [plt.cm.cool(0.25 + 0.7 * n) for n in norm]

    fig, ax = plt.subplots(figsize=(15, 8))
    ax.barh(df["company"], values, color=colors, height=0.72)
    ax.set_title("How Many Times Larger Was SpaceX Than Previous Major IPOs?", loc="left", pad=20)
    ax.set_xlabel("SpaceX IPO Size Multiple")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    for i, value in enumerate(values):
        ax.text(value + values.max() * 0.01, i, f"{value:.1f}x", va="center", ha="left", fontsize=10, color=TEXT, weight="bold")
    ax.set_xlim(0, values.max() * 1.15)
    fig.tight_layout()
    path = FIGURE_DIR / "04_spacex_size_multiple.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def chart_bubble(recent):
    df = recent.copy()
    sizes = (df["shares_offered"] / df["shares_offered"].max()) * 2500 + 180
    colors = [SPACEX_BLUE if c == "SpaceX" else PURPLE for c in df["company"]]

    fig, ax = plt.subplots(figsize=(14, 8))
    ax.scatter(df["ipo_price_usd"], df["ipo_proceeds_b"], s=sizes, c=colors, alpha=0.85, edgecolors="white", linewidths=1.2)
    for _, row in df.iterrows():
        ax.text(row["ipo_price_usd"], row["ipo_proceeds_b"] + 2.2, row["ticker"], ha="center", fontsize=10, weight="bold")
    ax.set_title("IPO Price vs IPO Proceeds: Bubble Size = Shares Offered", loc="left", pad=20)
    ax.set_xlabel("IPO Price ($)")
    ax.set_ylabel("IPO Proceeds ($B)")
    ax.grid(True)
    ax.set_axisbelow(True)
    fig.tight_layout()
    path = FIGURE_DIR / "05_ipo_price_vs_proceeds_bubble.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def chart_investor_benefit(scenario):
    df = scenario.sort_values("paper_gain_on_offered_shares_b", ascending=True)
    colors = [SPACEX_BLUE if c == "SpaceX" else (GREEN if v >= 0 else RED) for c, v in zip(df["company"], df["paper_gain_on_offered_shares_b"])]

    fig, ax = plt.subplots(figsize=(15, 7))
    ax.barh(df["company"], df["paper_gain_on_offered_shares_b"], color=colors, height=0.72)
    ax.axvline(0, color=TEXT, linewidth=0.9)
    ax.set_title("Investor Paper Gain/Loss on IPO Share Block: Scenario Market Price", loc="left", pad=20)
    ax.set_xlabel("Paper Gain/Loss on Offered Shares, USD Billions")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    for i, value in enumerate(df["paper_gain_on_offered_shares_b"]):
        ha = "left" if value >= 0 else "right"
        offset = 0.4 if value >= 0 else -0.4
        ax.text(value + offset, i, f"${value:.2f}B", va="center", ha=ha, fontsize=10, color=TEXT, weight="bold")
    fig.tight_layout()
    path = FIGURE_DIR / "06_investor_paper_gain_scenario.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def chart_musk_benefit(musk):
    df = musk[musk["assumption"].isin(["IPO implied valuation", "Scenario implied valuation", "Musk stake scenario value", "Musk ownership scenario benefit"])].copy()
    df = df.sort_values("value_b", ascending=True)
    colors = [SPACEX_BLUE if "Scenario" in x else GOLD if "Musk" in x else SLATE for x in df["assumption"]]

    fig, ax = plt.subplots(figsize=(15, 7))
    ax.barh(df["assumption"], df["value_b"], color=colors, height=0.72)
    ax.set_title("Elon Musk Benefit Scenario: Paper Value, Not Cash", loc="left", pad=20)
    ax.set_xlabel("USD Billions")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    for i, value in enumerate(df["value_b"]):
        ax.text(value + max(df["value_b"]) * 0.01, i, f"${value:.1f}B", va="center", ha="left", fontsize=10, color=TEXT, weight="bold")
    ax.set_xlim(0, df["value_b"].max() * 1.18)
    fig.tight_layout()
    path = FIGURE_DIR / "07_musk_paper_value_scenario.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def create_dashboard_html(recent, historical, scenario, musk, executive, chart_paths):
    # Convert relative paths for HTML report
    cards = [
        ("SpaceX IPO proceeds", money_b(executive["spacex_proceeds_b"])),
        ("Larger than previous record", f"{executive['spacex_vs_previous_record_multiple']:.2f}x"),
        ("Extra capital vs previous record", money_b(executive["spacex_extra_vs_previous_record_b"])),
        ("Larger than median recent peer", f"{executive['spacex_vs_recent_peer_median_multiple']:.1f}x"),
        ("Scenario market price", f"${executive['spacex_scenario_market_price']:.2f}"),
        ("Musk scenario paper gain", money_b(executive["musk_scenario_paper_gain_b"])),
    ]

    card_html = "\n".join([f"<div class='card'><div class='metric'>{value}</div><div class='label'>{label}</div></div>" for label, value in cards])

    chart_html = "\n".join([
        f"<section><h2>{Path(path).stem.replace('_', ' ').title()}</h2><img src='../outputs/figures/{Path(path).name}'></section>"
        for path in chart_paths
    ])

    recent_table = recent[["company", "ticker", "sector", "ipo_proceeds_b", "spacex_size_multiple", "share_of_recent_peer_group_pct", "market_impact_score"]].round(2).to_html(index=False, classes="data-table")
    scenario_table = scenario[["company", "ticker", "ipo_price_usd", "scenario_market_price_usd", "paper_return_from_ipo_price_pct", "paper_gain_on_offered_shares_b"]].round(2).to_html(index=False, classes="data-table")
    musk_table = musk.round(2).to_html(index=False, classes="data-table")

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SpaceX IPO Market Impact Report</title>
  <style>
    body {{ margin: 0; background: #07111F; color: #E5E7EB; font-family: Arial, Helvetica, sans-serif; }}
    .container {{ max-width: 1180px; margin: 0 auto; padding: 34px; }}
    .hero {{ background: linear-gradient(135deg, #0F172A, #1E3A8A, #00A3FF); padding: 34px; border-radius: 24px; margin-bottom: 24px; box-shadow: 0 20px 60px rgba(0,0,0,.35); }}
    h1 {{ margin: 0 0 12px; font-size: 42px; }}
    h2 {{ margin-top: 0; color: #38BDF8; }}
    p {{ line-height: 1.65; color: #CBD5E1; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; margin-bottom: 26px; }}
    .card {{ background: #111827; border: 1px solid #1F2937; padding: 22px; border-radius: 18px; }}
    .metric {{ font-size: 30px; font-weight: 800; color: #38BDF8; margin-bottom: 6px; }}
    .label {{ color: #CBD5E1; font-size: 14px; }}
    section {{ background: #111827; border: 1px solid #1F2937; padding: 24px; border-radius: 18px; margin-bottom: 24px; }}
    img {{ width: 100%; border-radius: 14px; border: 1px solid #253247; }}
    .data-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    .data-table th {{ color: #38BDF8; text-align: left; border-bottom: 1px solid #334155; padding: 9px; }}
    .data-table td {{ border-bottom: 1px solid #1F2937; padding: 9px; color: #E5E7EB; }}
    .note {{ color: #94A3B8; font-size: 13px; }}
    @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} h1 {{ font-size: 32px; }} }}
  </style>
</head>
<body>
<div class="container">
  <div class="hero">
    <h1>SpaceX IPO Market Impact Analysis</h1>
    <p>This report analyzes the SpaceX IPO through historical IPO comparisons, recent IPO peer comparisons, investor paper-gain scenarios, and Elon Musk ownership-benefit scenarios. The focus is not only stock return; it is size, liquidity, investor attention, sector influence, and market narrative.</p>
  </div>
  <div class="grid">{card_html}</div>
  <section>
    <h2>Executive Insight</h2>
    <p>SpaceX is different because it combines reusable rockets, Starlink satellite internet, government and defense contracts, AI infrastructure potential, global brand power, and retail investor attention. Its IPO scale makes it a market event rather than just a normal company listing.</p>
    <p class="note">Important: Musk and investor benefits are paper-value scenarios, not guaranteed cash profits. Realized gains require selling shares and depend on market price, lockups, taxes, and liquidity.</p>
  </section>
  <section><h2>Recent IPO Comparison Table</h2>{recent_table}</section>
  <section><h2>Investor Paper Gain Scenario</h2>{scenario_table}</section>
  <section><h2>Elon Musk Benefit Scenario</h2>{musk_table}</section>
  {chart_html}
  <section><h2>Disclaimer</h2><p class="note">This project is for education, analytics, and portfolio demonstration only. It is not investment advice.</p></section>
</div>
</body>
</html>
"""
    path = REPORT_DIR / "SpaceX_IPO_Executive_Report.html"
    path.write_text(html, encoding="utf-8")
    return path


def create_readme_summary(executive):
    readme = f"""# SpaceX IPO Market Impact Analysis

A professional business analytics portfolio project analyzing SpaceX's IPO impact through historical IPO comparisons, recent tech/fintech peer comparisons, investor paper-gain scenarios, and Elon Musk ownership-benefit scenarios.

## Project Highlights

- SpaceX IPO proceeds: **{money_b(executive['spacex_proceeds_b'])}**
- SpaceX vs previous historical IPO record: **{executive['spacex_vs_previous_record_multiple']:.2f}x larger**
- SpaceX vs median recent IPO peer: **{executive['spacex_vs_recent_peer_median_multiple']:.1f}x larger**
- Scenario implied SpaceX market cap: **{money_b(executive['spacex_scenario_implied_market_cap_b'])}**
- Musk scenario paper gain: **{money_b(executive['musk_scenario_paper_gain_b'])}**

## Business Question

How different is the SpaceX IPO compared with recent IPOs and the largest IPOs in history, and how much market impact can it create for investors, Elon Musk, and the broader stock market?

## What Makes SpaceX Different?

SpaceX is not a normal single-sector IPO. It combines:

- Reusable rocket technology
- Starlink satellite internet
- Aerospace and defense infrastructure
- Government contracts
- AI infrastructure narrative
- Global brand power
- Retail investor attention
- Future liquidity, ETF, and index-demand potential

## Repository Structure

```text
spacex_ipo_market_impact_github/
|-- data/
|   |-- recent_ipos.csv
|   |-- historical_ipos.csv
|   |-- scenario_prices.csv
|   |-- musk_assumptions.csv
|-- src/
|   |-- spacex_ipo_market_impact.py
|-- outputs/
|   |-- figures/
|   |-- tables/
|-- reports/
|   |-- SpaceX_IPO_Executive_Report.html
|-- docs/
|   |-- linkedin_post.md
|   |-- project_summary.md
|-- requirements.txt
|-- README.md
```

## Tools Used

- Python
- pandas
- NumPy
- Matplotlib
- Plotly
- Excel output using openpyxl

## How to Run

```bash
pip install -r requirements.txt
python src/spacex_ipo_market_impact.py
```

Then open:

```text
reports/SpaceX_IPO_Executive_Report.html
```

## Main Outputs

### SpaceX vs Largest IPOs

![SpaceX vs Largest IPOs](outputs/figures/01_spacex_vs_largest_ipos.png)

### SpaceX vs Recent IPOs

![Recent IPO Comparison](outputs/figures/02_recent_ipo_proceeds.png)

### Market Impact Score

![Market Impact Score](outputs/figures/03_market_impact_score.png)

### Investor Paper Gain Scenario

![Investor Gain Scenario](outputs/figures/06_investor_paper_gain_scenario.png)

### Elon Musk Benefit Scenario

![Musk Benefit Scenario](outputs/figures/07_musk_paper_value_scenario.png)

## Data Notes

- SpaceX IPO share count and IPO price are based on official IPO pricing data.
- Historical IPO proceeds are approximate and can vary depending on whether over-allotment/greenshoe options are included.
- Investor and Musk benefit numbers are scenario-based paper-value estimates, not realized cash profits.
- This project is not investment advice.

## Author

**Kiran Kanth Madigani**  
Business Analytics | Data Analytics | SQL | Python | Tableau | Power BI | Financial Analytics

"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")


def main():
    recent, historical, scenarios, assumptions = load_data()
    recent, historical, scenario, musk, executive = calculate_metrics(recent, historical, scenarios, assumptions)
    excel_path = save_tables(recent, historical, scenario, musk, executive)

    chart_paths = [
        chart_historical_ipos(historical),
        chart_recent_ipos(recent),
        chart_impact_score(recent),
        chart_size_multiple(historical),
        chart_bubble(recent),
        chart_investor_benefit(scenario),
        chart_musk_benefit(musk),
    ]

    report_path = create_dashboard_html(recent, historical, scenario, musk, executive, chart_paths)
    create_readme_summary(executive)

    print("\n" + "=" * 90)
    print("SPACEX IPO MARKET IMPACT PROJECT COMPLETED")
    print("=" * 90)
    print(f"Excel workbook: {excel_path}")
    print(f"HTML report: {report_path}")
    print(f"Figures folder: {FIGURE_DIR}")
    print("\nKey metrics:")
    print(f"- SpaceX IPO proceeds: {money_b(executive['spacex_proceeds_b'])}")
    print(f"- SpaceX vs previous record: {executive['spacex_vs_previous_record_multiple']:.2f}x")
    print(f"- SpaceX vs median recent peer: {executive['spacex_vs_recent_peer_median_multiple']:.1f}x")
    print(f"- Musk scenario paper gain: {money_b(executive['musk_scenario_paper_gain_b'])}")
    print("\nOpen reports/SpaceX_IPO_Executive_Report.html in your browser.")


if __name__ == "__main__":
    main()
