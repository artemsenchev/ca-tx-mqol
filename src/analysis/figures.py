"""Generate the paper's figures.

    python -m src.analysis.figures

No model fitting happens here beyond what the figure plots -- the estimates
come from the same specification as the tabled model in src/analysis/models.py,
so the figure and Table 1 cannot drift apart.

The figure answers the paper's question directly: predicted income relative to
need for each migration group, under two poverty lines that differ only in
whether the threshold is repriced to local costs. Both series use the same
incomes. The reordering between them is the finding.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

from src.analysis.models import RHS, fit, load_sample

# Note: the non-interactive backend is selected in main(), not at import.
# Forcing it here would switch the backend for anything that imports this
# module for its palette or helpers -- which is what a notebook does, and it
# would silently stop inline plots from rendering.

ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "reports" / "figures"

# Two-series categorical palette. Validated against the six-check color
# formula on the light chart surface: worst adjacent CVD separation is
# dE 24.7 (protan) / 32.7 (tritan), normal-vision 33.6, both series inside
# the lightness band and above the chroma floor and the 3:1 contrast floor.
# Warm/cool poles, so the pair also reads correctly in grayscale print.
COLOR_OFFICIAL = "#eb6834"
COLOR_REPRICED = "#2a78d6"

# Text and chrome wear ink tokens, never the series colors.
INK = "#1a1a1a"
INK_MUTED = "#6b6b6b"
GRID = "#e4e4e2"
SURFACE = "#ffffff"

LABEL_OFFICIAL = "Income ÷ national poverty line (same in every state)"
LABEL_REPRICED = "Income ÷ state-priced poverty line"

# Reading order within each panel: stayers, within-state movers, then the
# cross-state arrivals the paper is about.
ROW_ORDER = ["CA_stay", "CA_to_CA", "TX_to_CA", "TX_stay", "TX_to_TX", "CA_to_TX"]
ROW_LABELS = {
    "CA_stay": "Same home as last year",
    "CA_to_CA": "Moved within California",
    "TX_to_CA": "Moved here from Texas",
    "TX_stay": "Same home as last year",
    "TX_to_TX": "Moved within Texas",
    "CA_to_TX": "Moved here from California",
}
PANEL_OF = {
    "CA_stay": "Now in\nCalifornia", "CA_to_CA": "Now in\nCalifornia",
    "TX_to_CA": "Now in\nCalifornia", "TX_stay": "Now in\nTexas",
    "TX_to_TX": "Now in\nTexas", "CA_to_TX": "Now in\nTexas",
}


def reference_profile(df: pd.DataFrame) -> pd.DataFrame:
    """One row per migration group, everything else held at a typical value.

    Categorical covariates take their modal level and continuous ones their
    mean, so the six rows differ in exactly one thing: the group. Without
    holding the rest fixed the comparison would confound migration with the
    demographic mix of each group, which is what the controls exist to remove.
    """
    groups = list(df["grp"].cat.categories)
    profile = {
        "grp": pd.Categorical(groups, categories=groups),
        "female": int(df["female"].mode().iloc[0]),
        "age": float(df["age"].mean()),
        "married": int(df["married"].mode().iloc[0]),
        "kids": int(df["kids"].mode().iloc[0]),
        "famsize": float(df["famsize"].mean()),
    }
    for col in ("raceth", "nativity", "educ4"):
        profile[col] = pd.Categorical(
            [df[col].mode().iloc[0]] * len(groups),
            categories=list(df[col].cat.categories),
        )
    return pd.DataFrame(profile)


def predict_with_ci(result, ref: pd.DataFrame, label: str) -> pd.DataFrame:
    """Predicted ratio and 95% CI for each row of the reference profile.

    Standard errors come from the model's clustered covariance, so the
    intervals inherit the household clustering rather than assuming
    independence. Exponentiating turns the log-scale prediction back into a
    multiple of the poverty line.

    get_prediction applies the fitted formula to ``ref`` through the public
    API, so this works whether statsmodels builds designs with patsy (<0.15)
    or formulaic (>=0.15). Its se_mean is sqrt(diag(X V X')) under the
    clustered V; the interval is formed here with a fixed 1.96 to match R.
    """
    pred = result.get_prediction(ref)
    est = np.asarray(pred.predicted_mean)
    se = np.asarray(pred.se_mean)

    return pd.DataFrame({
        "grp": ref["grp"].astype(str),
        "threshold": label,
        "ratio": np.exp(est),
        "lo": np.exp(est - 1.96 * se),
        "hi": np.exp(est + 1.96 * se),
    })


CAPTION_YEAR = 2023


def price_levels(df: pd.DataFrame, year: int = CAPTION_YEAR) -> tuple[float, float]:
    """RPP for each state in a single year, for the figure caption.

    A single wave, not a mean across waves. RPP is revised and drifts year to
    year, and the caption quotes a concrete "prices are N% higher in
    California" -- averaging 2021-2023 would give a number matching no
    published BEA figure. The 2023 values are what the paper quotes.
    """
    wave = df[df["YEAR"] == year]
    if wave.empty:
        raise ValueError(f"no rows for year {year}; cannot compute caption prices")
    levels = wave.groupby("dest", observed=True)["rpp"].first()
    return float(levels["CA"]), float(levels["TX"])


def figure_ratio_by_group(df: pd.DataFrame, out_path: Path) -> Path:
    ref = reference_profile(df)
    m_rep = fit(df, "log_repriced", RHS["hh"])
    m_off = fit(df, "log_official", RHS["hh"])

    preds = pd.concat([
        predict_with_ci(m_off, ref, LABEL_OFFICIAL),
        predict_with_ci(m_rep, ref, LABEL_REPRICED),
    ], ignore_index=True)

    counts = df["grp"].value_counts()
    panels = ["Now in\nCalifornia", "Now in\nTexas"]
    rows_by_panel = {p: [g for g in ROW_ORDER if PANEL_OF[g] == p] for p in panels}

    # Sized to the paper's text width. Margins are set explicitly rather than
    # via bbox_inches="tight": the row labels are long, and letting a tight
    # bbox expand the canvas would silently produce a figure wider than the
    # column it has to sit in.
    fig, axes = plt.subplots(
        nrows=2, ncols=1, figsize=(6.5, 3.2), sharex=True,
        gridspec_kw={"height_ratios": [len(rows_by_panel[p]) for p in panels],
                     "hspace": 0.22},
    )
    fig.subplots_adjust(left=0.335, right=0.865, top=0.775, bottom=0.155)
    fig.patch.set_facecolor(SURFACE)

    xmin = preds["lo"].min()
    xmax = preds["hi"].max()
    pad = (xmax - xmin) * 0.08

    for ax, panel in zip(axes, panels):
        rows = rows_by_panel[panel]
        ax.set_facecolor(SURFACE)
        # Recessive chrome: solid hairline vertical grid only, one shade off
        # the surface. No dashes -- dashing reads as "threshold" when it is
        # only a grid.
        ax.set_axisbelow(True)
        ax.xaxis.grid(True, color=GRID, linewidth=0.6, linestyle="-")
        ax.yaxis.grid(False)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.spines["bottom"].set_linewidth(0.6)

        ypos = {g: len(rows) - 1 - i for i, g in enumerate(rows)}
        for series, color in ((LABEL_OFFICIAL, COLOR_OFFICIAL),
                              (LABEL_REPRICED, COLOR_REPRICED)):
            sub = preds[(preds["threshold"] == series) & (preds["grp"].isin(rows))]
            y = [ypos[g] for g in sub["grp"]]
            ax.hlines(y, sub["lo"], sub["hi"], color=color, linewidth=1.4,
                      zorder=2)
            # 2px surface ring so the two series stay legible where they
            # overlap, instead of a border drawn to separate them.
            ax.plot(sub["ratio"], y, "o", color=color, markersize=5.5,
                    markeredgecolor=SURFACE, markeredgewidth=1.4,
                    linestyle="none", zorder=3)

        ax.set_yticks([ypos[g] for g in rows])
        ax.set_yticklabels(
            [f"{ROW_LABELS[g]}  (n = {counts[g]:,})" for g in rows],
            fontsize=7.5, color=INK,
        )
        ax.tick_params(axis="y", length=0, pad=4)
        ax.tick_params(axis="x", colors=INK_MUTED, labelsize=8, length=0)
        ax.set_ylim(-0.6, len(rows) - 0.4)
        ax.set_xlim(xmin - pad, xmax + pad)

        # Panel label on the right, out of the way of the row labels.
        ax.text(1.012, 0.5, panel, transform=ax.transAxes, fontsize=8,
                color=INK_MUTED, va="center", ha="left", linespacing=1.25)

    axes[-1].set_xlabel("Predicted family income (multiple of the poverty line)",
                        fontsize=8.5, color=INK_MUTED, labelpad=6)

    # Legend is always present for two series -- identity is never carried by
    # color alone. Marker-only handles: a line through the dot would imply the
    # series is a trend rather than a point estimate.
    handles = [
        Line2D([0], [0], marker="o", color=c, markersize=5.5, linestyle="none",
               markeredgecolor=SURFACE, markeredgewidth=1.2, label=lab)
        for lab, c in ((LABEL_OFFICIAL, COLOR_OFFICIAL),
                       (LABEL_REPRICED, COLOR_REPRICED))
    ]
    leg = fig.legend(handles=handles, loc="upper left",
                     bbox_to_anchor=(0.012, 0.925), ncol=1, frameon=False,
                     fontsize=7.5, handletextpad=0.4, labelspacing=0.28)
    for text in leg.get_texts():
        text.set_color(INK)

    fig.text(0.012, 0.965,
             "Count local prices, and Californians who moved to Texas come out ahead",
             ha="left", va="top", fontsize=10, color=INK, fontweight="semibold")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, facecolor=SURFACE)
    fig.savefig(out_path.with_suffix(".pdf"), facecolor=SURFACE)
    plt.close(fig)

    # The table view: identity and values are recoverable without seeing color.
    preds.to_csv(out_path.with_suffix(".csv"), index=False)
    return out_path


def main() -> int:
    import matplotlib

    matplotlib.use("Agg")  # headless: write files, never open a window
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "axes.unicode_minus": False,
    })

    df = load_sample()
    out = figure_ratio_by_group(df, FIG_DIR / "ratio_by_group.png")

    rpp_ca, rpp_tx = price_levels(df)
    print(f"wrote {out}")
    print(f"wrote {out.with_suffix('.pdf')}")
    print(f"wrote {out.with_suffix('.csv')}  (table view)")
    print(
        f"\ncaption numbers ({CAPTION_YEAR}): prices run {rpp_ca - 100:+.0f}% against "
        f"the national average in California and {rpp_tx - 100:+.0f}% in Texas "
        f"(RPP {rpp_ca:.2f} / {rpp_tx:.2f})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
