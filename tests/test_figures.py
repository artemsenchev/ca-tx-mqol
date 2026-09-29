"""Tests for the figure's reference profile.

The figure's whole claim is that the six rows differ in *one* thing -- the
migration group. If any other covariate varies across rows, the plotted
differences confound migration with demographic mix, which is exactly what the
controls exist to remove. That is invisible in the rendered image, so it is
tested here rather than eyeballed.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.analysis.figures import ROW_LABELS, ROW_ORDER, PANEL_OF, reference_profile
from src.data.build_sample import (
    EDUC4_LEVELS, GRP_LEVELS, NATIVITY_LEVELS, RACETH_LEVELS,
)


@pytest.fixture
def sample() -> pd.DataFrame:
    """A frame with the columns reference_profile() reads, deliberately
    unbalanced so the modal levels are unambiguous."""
    n = 10
    return pd.DataFrame({
        "grp": pd.Categorical(["CA_stay"] * n, categories=GRP_LEVELS),
        "female": [1] * 7 + [0] * 3,
        "age": [30.0] * 5 + [50.0] * 5,
        "married": [1] * 6 + [0] * 4,
        "kids": [0] * 8 + [1] * 2,
        "famsize": [2.0] * 5 + [4.0] * 5,
        "raceth": pd.Categorical(["Hispanic"] * 6 + ["NH White"] * 4,
                                 categories=RACETH_LEVELS),
        "nativity": pd.Categorical(["US born"] * 9 + ["Naturalized"],
                                   categories=NATIVITY_LEVELS),
        "educ4": pd.Categorical(["HS grad"] * 7 + ["BA or more"] * 3,
                                categories=EDUC4_LEVELS),
    })


def test_one_row_per_group(sample):
    ref = reference_profile(sample)
    assert list(ref["grp"].astype(str)) == GRP_LEVELS


def test_only_the_group_varies(sample):
    ref = reference_profile(sample)
    for col in ref.columns.drop("grp"):
        assert ref[col].nunique() == 1, (
            f"{col} varies across the reference rows; the figure would then "
            "confound migration group with demographic mix"
        )


def test_continuous_covariates_take_the_mean(sample):
    ref = reference_profile(sample)
    assert ref["age"].iloc[0] == pytest.approx(40.0)
    assert ref["famsize"].iloc[0] == pytest.approx(3.0)


def test_categorical_covariates_take_the_mode(sample):
    ref = reference_profile(sample)
    assert ref["raceth"].iloc[0] == "Hispanic"
    assert ref["nativity"].iloc[0] == "US born"
    assert ref["educ4"].iloc[0] == "HS grad"
    assert ref["female"].iloc[0] == 1
    assert ref["married"].iloc[0] == 1
    assert ref["kids"].iloc[0] == 0


def test_categorical_levels_are_preserved(sample):
    # The design matrix is built from the fitted model's design_info, so a
    # reference frame missing a level would silently produce wrong dummies.
    ref = reference_profile(sample)
    assert list(ref["raceth"].cat.categories) == RACETH_LEVELS
    assert list(ref["educ4"].cat.categories) == EDUC4_LEVELS
    assert list(ref["nativity"].cat.categories) == NATIVITY_LEVELS


def test_every_group_has_a_label_and_a_panel():
    assert set(ROW_ORDER) == set(GRP_LEVELS)
    assert set(ROW_LABELS) == set(GRP_LEVELS)
    assert set(PANEL_OF) == set(GRP_LEVELS)


def test_panels_split_by_destination():
    ca = {g for g, p in PANEL_OF.items() if "California" in p}
    assert ca == {"CA_stay", "CA_to_CA", "TX_to_CA"}
