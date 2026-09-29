"""Parity against the original R implementation.

The Python port has to reproduce the R results, not merely produce plausible
ones. A port is exactly where a sign flip or an off-by-one filter slips in
unnoticed, because the output still looks like a reasonable table.

These tests need two things the unit tests do not:

  1. The built sample -- run `python -m src.data.make_data` first.
  2. tests/reference_r_output.json -- generate it by running
     `Rscript tests/export_reference.R` against the original R code.

Both are skipped, not failed, when absent, so `pytest` still passes for
someone who has only cloned the repository.

On tolerance: statsmodels' clustered covariance and sandwich::vcovCL(type =
"HC1") agree to floating-point precision here -- measured worst case across all
five models is 7.5e-11 relative on coefficients and 1.3e-12 on standard errors.
The tolerances below sit far above that, so they absorb library-version drift
without ever admitting a real divergence. A failure means something actually
differs; do not loosen the tolerance to make it pass.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = ROOT / "data" / "processed" / "analysis_sample.parquet"
REFERENCE_PATH = Path(__file__).parent / "reference_r_output.json"

needs_sample = pytest.mark.skipif(
    not SAMPLE_PATH.exists(),
    reason="no built sample; run `python -m src.data.make_data` first",
)
needs_reference = pytest.mark.skipif(
    not REFERENCE_PATH.exists(),
    reason="no R reference; run `Rscript tests/export_reference.R`",
)


@pytest.fixture(scope="module")
def sample():
    from src.analysis.models import load_sample
    return load_sample()


@pytest.fixture(scope="module")
def fits(sample):
    from src.analysis.models import RHS, fit
    out = {name: fit(sample, "log_repriced", rhs) for name, rhs in RHS.items()}
    out["hh_official"] = fit(sample, "log_official", RHS["hh"])
    return out


@pytest.fixture(scope="module")
def reference():
    return json.loads(REFERENCE_PATH.read_text())


# --------------------------------------------------------------------------
# Sample-level parity
# --------------------------------------------------------------------------

@needs_sample
@needs_reference
def test_row_count_matches_r(sample, reference):
    assert len(sample) == reference["n"]


@needs_sample
@needs_reference
def test_group_counts_match_r(sample, reference):
    got = sample["grp"].value_counts().to_dict()
    assert got == {k: v for k, v in reference["group_counts"].items()}


@needs_sample
@needs_reference
def test_household_count_matches_r(sample, reference):
    # Guards the hhid construction. A mismatch here means the clustering
    # differs, which changes every standard error in the table.
    assert sample["hhid"].nunique() == reference["n_households"]


@needs_sample
@needs_reference
def test_attrition_matches_r(reference):
    import pandas as pd
    path = ROOT / "data" / "processed" / "attrition.csv"
    if not path.exists():
        pytest.skip("attrition.csv not written")
    got = pd.read_csv(path)["rows"].tolist()
    assert got == reference["attrition_rows"]


# --------------------------------------------------------------------------
# Coefficient parity
# --------------------------------------------------------------------------

@needs_sample
@needs_reference
@pytest.mark.parametrize("model", ["base", "demo", "edu", "hh", "hh_official"])
def test_coefficients_match_r(fits, reference, model):
    ref = reference["models"][model]["coefficients"]
    got = fits[model].params
    for term, expected in ref.items():
        assert term in got.index, f"{model}: missing term {term}"
        assert got[term] == pytest.approx(expected, rel=1e-6, abs=1e-9), (
            f"{model}: {term} = {got[term]!r}, R had {expected!r}"
        )


@needs_sample
@needs_reference
@pytest.mark.parametrize("model", ["base", "demo", "edu", "hh", "hh_official"])
def test_clustered_standard_errors_match_r(fits, reference, model):
    # Looser than the point estimates: this is where the finite-sample
    # correction difference lives.
    ref = reference["models"][model]["std_errors"]
    got = fits[model].bse
    for term, expected in ref.items():
        assert got[term] == pytest.approx(expected, rel=1e-4), (
            f"{model}: SE for {term} = {got[term]!r}, R had {expected!r}"
        )


# --------------------------------------------------------------------------
# The report's inline statistics
#
# These are the numbers the paper quotes in prose, and each hides a definition
# choice that a reimplementation naturally gets wrong in a defensible way. All
# three alternatives below are reasonable; none of them is what the paper says.
# --------------------------------------------------------------------------

@needs_sample
@needs_reference
def test_topcode_share_is_unweighted(sample, reference):
    """The paper quotes the unweighted share at the ceiling.

    Weighting by PERWT gives roughly 41.5% / 34.0% -- a few points lower,
    because the weights pull down groups that cluster below the ceiling.
    Defensible, but not what the paper reports.
    """
    ref = reference["report_stats"]
    for dest, key in (("CA", "topcode_share_ca"), ("TX", "topcode_share_tx")):
        got = sample.loc[sample["dest"] == dest, "topcoded"].mean()
        assert got == pytest.approx(ref[key], rel=1e-9)


@needs_sample
@needs_reference
def test_caption_price_levels_are_a_single_wave(sample, reference):
    """Price levels come from 2023 alone, not a mean across waves.

    BEA revises RPP and it drifts year to year, so an average matches no
    published figure. The mean over 2021-2023 would give Texas 97.62 instead
    of 97.14 -- enough to turn the caption's "3% below" into "2% below".
    """
    from src.analysis.figures import price_levels

    ref = reference["report_stats"]
    rpp_ca, rpp_tx = price_levels(sample)
    assert rpp_ca == pytest.approx(ref["rpp_ca_2023"], rel=1e-9)
    assert rpp_tx == pytest.approx(ref["rpp_tx_2023"], rel=1e-9)


@needs_sample
@needs_reference
def test_joined_household_definition(sample, reference):
    """'Joined an established household' = the household holds more than one
    migration group.

    The narrower reading -- the household holds a non-mover -- misses
    households containing two different mover groups and gives 12.3% instead
    of 16.7%, which in turn moves the sensitivity estimate.
    """
    from src.analysis.models import RHS, fit, pct_gap

    ref = reference["report_stats"]
    groups_per_hh = sample.groupby("hhid")["grp"].nunique()
    mixed_hh = set(groups_per_hh[groups_per_hh > 1].index)

    movers = sample["grp"].eq("CA_to_TX")
    joined = movers & sample["hhid"].isin(mixed_hh)

    assert (joined.sum() / movers.sum()) == pytest.approx(
        ref["share_joined"], rel=1e-9)

    gap = 100 * pct_gap(fit(sample[~joined], "log_repriced", RHS["hh"]))
    assert gap == pytest.approx(ref["gap_no_joined_pct"], rel=1e-6)


# --------------------------------------------------------------------------
# Figure predictions
# --------------------------------------------------------------------------

@needs_sample
@needs_reference
def test_figure_predictions_match_r(sample, reference):
    """Every plotted point and interval bound, against the R ggplot version.

    The figure is where a reference-profile mistake hides: modal instead of
    mean, a dropped factor level, an unclustered covariance for the interval.
    None of those would look wrong in the rendered image.
    """
    import pandas as pd

    from src.analysis.figures import (
        LABEL_OFFICIAL, LABEL_REPRICED, predict_with_ci, reference_profile,
    )
    from src.analysis.models import RHS, fit

    ref_profile = reference_profile(sample)
    got = pd.concat([
        predict_with_ci(fit(sample, "log_repriced", RHS["hh"]),
                        ref_profile, "repriced"),
        predict_with_ci(fit(sample, "log_official", RHS["hh"]),
                        ref_profile, "official"),
    ], ignore_index=True)

    expected = pd.DataFrame(reference["figure_predictions"])
    merged = expected.merge(got, on=["grp", "threshold"], suffixes=("_r", "_py"))
    assert len(merged) == len(expected) == 12

    for col in ("ratio", "lo", "hi"):
        for _, row in merged.iterrows():
            assert row[f"{col}_py"] == pytest.approx(row[f"{col}_r"], rel=1e-8), (
                f"{row['grp']} / {row['threshold']}: {col}"
            )

    # Guard the labels the figure actually renders, so the CSV table view and
    # the legend cannot drift apart from the series they describe.
    assert "state-priced" in LABEL_REPRICED
    assert "national" in LABEL_OFFICIAL


# --------------------------------------------------------------------------
# Headline invariants -- these hold without the R reference
# --------------------------------------------------------------------------

@needs_sample
def test_headline_is_a_sign_reversal(fits):
    """The paper's finding is that the two poverty lines disagree in sign.

    Repriced positive, official negative. If both come out the same sign the
    result has collapsed and nothing downstream is worth reading.
    """
    from src.analysis.models import pct_gap

    repriced = pct_gap(fits["hh"])
    official = pct_gap(fits["hh_official"])
    assert repriced > 0, f"repriced gap should be positive, got {repriced:+.1%}"
    assert official < 0, f"official gap should be negative, got {official:+.1%}"


@needs_sample
def test_headline_magnitudes(fits):
    """Pinned to the reported figures.

    Loose enough to survive an IPUMS or BEA data revision, tight enough that a
    pipeline bug cannot slip past. Update the constants deliberately, with the
    paper, when a data refresh genuinely moves them -- never to make a red test
    green.
    """
    from src.analysis.models import pct_gap

    assert pct_gap(fits["hh"]) == pytest.approx(0.101, abs=0.005)
    assert pct_gap(fits["hh_official"]) == pytest.approx(-0.039, abs=0.005)


@needs_sample
def test_reference_level_is_california_stayers(fits):
    # If CA_stay stops being the omitted category, every coefficient in the
    # table is measured against a different baseline and the prose is wrong.
    terms = fits["hh"].params.index
    assert "grp[T.CA_stay]" not in terms
    assert "grp[T.CA_to_TX]" in terms


@needs_sample
def test_estimation_uses_weights_and_clustering(fits):
    res = fits["hh"]
    assert res.cov_type == "cluster", (
        "standard errors must be clustered by household; IPUMS samples whole "
        "households and their members are not independent"
    )
    assert res.model.weights is not None and (res.model.weights != 1).any(), (
        "observations must be weighted by PERWT"
    )
