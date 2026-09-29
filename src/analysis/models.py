"""Fit the model ladder and write the regression table.

    python -m src.analysis.models

Four nested specifications on the repriced outcome, plus the full
specification refit on the official outcome. The comparison between those last
two is the paper's headline: the only thing that differs is the poverty line
each income is divided by.

Estimation details that must not drift:

* Observations are weighted by PERWT. IPUMS oversamples some groups by design,
  so unweighted estimates describe the sample rather than the population. Use
  WLS, not OLS.
* Standard errors are cluster-robust by household, not merely
  heteroskedasticity-robust. IPUMS samples entire households; people sharing a
  household share family income and are not independent observations. Treating
  them as independent understates the standard errors substantially, and the
  two small cross-state mover groups are exactly where that would matter.

This corresponds to R's

    lm(f, data = d, weights = PERWT)
    sandwich::vcovCL(m, cluster = d$hhid, type = "HC1")

The two agree to floating-point precision on this sample: measured against the
R implementation, the worst coefficient deviation is 7.5e-11 relative and the
worst standard-error deviation 1.3e-12. tests/test_parity.py pins that, so a
real divergence cannot hide behind an assumed one.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PATH = ROOT / "data" / "processed" / "analysis_sample.parquet"
TABLE_DIR = ROOT / "reports" / "tables"

# Nested ladder, matching the columns of Table 1.
RHS = {
    "base": "grp",
    "demo": "grp + female + age + raceth + nativity",
    "edu": "grp + female + age + raceth + nativity + educ4",
    "hh": "grp + female + age + raceth + nativity + educ4 + married + kids + famsize",
}

# The full specification is the one the paper's headline quotes.
HEADLINE_SPEC = "hh"
TREATMENT_COEF = "grp[T.CA_to_TX]"

CATEGORICALS = ("grp", "raceth", "educ4", "nativity")


def load_sample(path: Path = SAMPLE_PATH) -> pd.DataFrame:
    """Read the built sample, restoring category order.

    Parquet round-trips pandas Categoricals but not always their order, and
    category order determines the regression reference level. Restoring it
    explicitly means a reordered file cannot silently rebase every
    coefficient in the table.
    """
    from src.data.build_sample import (
        EDUC4_LEVELS, GRP_LEVELS, NATIVITY_LEVELS, RACETH_LEVELS,
    )

    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python -m src.data.make_data` first."
        )

    df = pd.read_parquet(path)
    levels = {
        "grp": GRP_LEVELS, "raceth": RACETH_LEVELS,
        "educ4": EDUC4_LEVELS, "nativity": NATIVITY_LEVELS,
    }
    for col, order in levels.items():
        present = [c for c in order if c in set(df[col].dropna().unique())]
        df[col] = pd.Categorical(df[col], categories=present)
    return df


def fit(df: pd.DataFrame, outcome: str, rhs: str):
    """Weighted least squares with household-clustered standard errors."""
    model = smf.wls(f"{outcome} ~ {rhs}", data=df, weights=df["PERWT"])
    return model.fit(cov_type="cluster", cov_kwds={"groups": df["hhid"]})


def pct_gap(result, coef: str = TREATMENT_COEF) -> float:
    """Convert a log-outcome coefficient into a percentage difference.

    The outcome is logged, so exp(beta) - 1 is the proportional difference
    against the reference group -- not beta itself, which only approximates it
    and drifts as the coefficient grows.
    """
    return float(np.exp(result.params[coef]) - 1.0)


def coefficient_frame(results: dict[str, object]) -> pd.DataFrame:
    """Long-format coefficient table: one row per (model, term)."""
    rows = []
    for name, res in results.items():
        for term in res.params.index:
            rows.append({
                "model": name,
                "term": term,
                "estimate": float(res.params[term]),
                "std_error": float(res.bse[term]),
                "statistic": float(res.tvalues[term]),
                "p_value": float(res.pvalues[term]),
            })
    return pd.DataFrame(rows)


def main() -> int:
    df = load_sample()

    results = {name: fit(df, "log_repriced", rhs) for name, rhs in RHS.items()}
    # Same right-hand side, official poverty line. The only difference between
    # this and results["hh"] is the threshold the income is divided by.
    results["hh_official"] = fit(df, "log_official", RHS[HEADLINE_SPEC])

    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    coefs = coefficient_frame(results)
    coefs.to_csv(TABLE_DIR / "coefficients.csv", index=False)

    gap_repriced = pct_gap(results[HEADLINE_SPEC])
    gap_official = pct_gap(results["hh_official"])

    headline = {
        "spec": HEADLINE_SPEC,
        "coefficient": TREATMENT_COEF,
        "n": int(results[HEADLINE_SPEC].nobs),
        "n_households": int(df["hhid"].nunique()),
        "gap_repriced": gap_repriced,
        "gap_official": gap_official,
        "se_repriced": float(results[HEADLINE_SPEC].bse[TREATMENT_COEF]),
        "se_official": float(results["hh_official"].bse[TREATMENT_COEF]),
        "r2": {name: float(res.rsquared) for name, res in results.items()},
    }
    (TABLE_DIR / "headline.json").write_text(json.dumps(headline, indent=2))

    print(f"n = {headline['n']:,} people in "
          f"{headline['n_households']:,} households\n")
    print("California-to-Texas movers vs. California stayers, full specification:")
    print(f"  price-adjusted poverty line : {gap_repriced:+.1%}")
    print(f"  official poverty line       : {gap_official:+.1%}")
    if gap_repriced * gap_official >= 0:
        print("\n  NOTE: the two measures agree in sign. The paper's finding is "
              "\n  a sign REVERSAL -- check the price adjustment before writing "
              "\n  this up.")
    print(f"\nwrote {TABLE_DIR / 'coefficients.csv'}")
    print(f"wrote {TABLE_DIR / 'headline.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
