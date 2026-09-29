"""Unit tests for the pipeline's derivations.

These run on synthetic fixtures and need no IPUMS extract, so they work in CI
and for anyone who has cloned the repository but not yet registered with IPUMS.
The R-parity tests, which do need the real data, live in test_parity.py.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.build_sample import (
    FLOOR_RTN,
    add_covariates,
    add_migration_groups,
    add_outcomes,
    load_rpp,
)


@pytest.fixture
def people() -> pd.DataFrame:
    """One person per migration group, plus an out-of-scope arrival."""
    return pd.DataFrame({
        "YEAR": [2022] * 7,
        "SERIAL": [1, 2, 3, 4, 5, 6, 7],
        "PERNUM": [1] * 7,
        "PERWT": [100.0] * 7,
        "STATEFIP": [6, 6, 48, 48, 48, 6, 48],
        "PUMA": [100] * 7,
        "MIGPLAC1": [0, 6, 0, 48, 6, 48, 36],
        "POVERTY": [200, 300, 200, 150, 250, 400, 200],
        "SPMTOTRES": [50000.0] * 7,
        "SPMTHRESH": [25000.0] * 7,
        "SPMGEOADJ": [1.1] * 7,
        "AGE": [40] * 7,
        "SEX": [1] * 7,
        "RACE": [1] * 7,
        "HISPAN": [0] * 7,
        "EDUC": [10] * 7,
        "CITIZEN": [0] * 7,
        "MARST": [1] * 7,
        "NCHILD": [0] * 7,
        "FAMSIZE": [2] * 7,
        "GQ": [1] * 7,
    })


@pytest.fixture
def rpp() -> pd.DataFrame:
    """California above the national average, Texas below it."""
    return pd.DataFrame({
        "STATEFIP": [6, 48],
        "YEAR": [2022, 2022],
        "rpp": [112.0, 97.0],
    })


class TestMigrationGroups:
    def test_all_six_groups_are_assigned(self, people):
        got = add_migration_groups(people)["grp"].tolist()
        assert got[:6] == [
            "CA_stay", "CA_to_CA", "TX_stay", "TX_to_TX", "CA_to_TX", "TX_to_CA",
        ]

    def test_third_state_arrivals_become_na(self, people):
        # MIGPLAC1 = 36 (New York) -> neither a Texas stayer nor a California
        # leaver, so it must not be folded into either group.
        assert pd.isna(add_migration_groups(people)["grp"].iloc[6])

    def test_reference_level_is_california_stayers(self, people):
        # Every coefficient in Table 1 is relative to this level. If it moves,
        # the whole table silently rebases.
        assert add_migration_groups(people)["grp"].cat.categories[0] == "CA_stay"

    def test_ca_stay_means_same_house_not_merely_same_state(self, people):
        # MIGPLAC1 = 6 in California is a within-state mover, a separate group.
        out = add_migration_groups(people)
        assert out["grp"].iloc[1] == "CA_to_CA"


class TestPriceAdjustment:
    def test_expensive_state_lowers_the_ratio(self, people, rpp):
        """The single most consequential line in the pipeline.

        California prices sit above the national average, so repricing the
        threshold to local costs must make the same income cover LESS need.
        Multiplying instead of dividing reverses the paper's finding while
        leaving a sample that looks perfectly plausible.
        """
        out = add_outcomes(add_migration_groups(people), rpp)
        ca = out[out["STATEFIP"] == 6]
        assert (ca["ratio_repriced"] < ca["ratio_official"]).all()

    def test_cheap_state_raises_the_ratio(self, people, rpp):
        out = add_outcomes(add_migration_groups(people), rpp)
        tx = out[out["STATEFIP"] == 48]
        assert (tx["ratio_repriced"] > tx["ratio_official"]).all()

    def test_exact_division(self, people, rpp):
        out = add_outcomes(add_migration_groups(people), rpp)
        row = out.iloc[0]
        assert row["ratio_repriced"] == pytest.approx(2.00 / 1.12)

    def test_missing_rpp_year_propagates_as_na(self, people):
        """A short RPP table must not silently drop a survey wave.

        The join failure has to surface as NaN so the attrition table counts
        it, rather than lm() quietly fitting on a third fewer rows.
        """
        short = pd.DataFrame({"STATEFIP": [6, 48], "YEAR": [2023, 2023],
                              "rpp": [112.0, 97.0]})
        out = add_outcomes(add_migration_groups(people), short)
        assert out["ratio_repriced"].isna().all()


class TestOutcomes:
    def test_poverty_zero_is_not_a_zero_ratio(self, people, rpp):
        # POVERTY = 000 codes 'N/A', not zero income. Treating it as 0.0 would
        # put people at the very bottom of the distribution instead of out of
        # the poverty universe entirely.
        people.loc[0, "POVERTY"] = 0
        out = add_outcomes(add_migration_groups(people), rpp)
        assert pd.isna(out["ratio_official"].iloc[0])

    def test_log_outcomes_are_floored(self, people, rpp):
        people.loc[0, "POVERTY"] = 1  # bottom code: zero or negative income
        out = add_outcomes(add_migration_groups(people), rpp)
        assert out["log_official"].iloc[0] == pytest.approx(np.log(FLOOR_RTN))

    def test_floor_does_not_fabricate_values_for_missing_rows(self, people, rpp):
        people.loc[0, "POVERTY"] = 0
        out = add_outcomes(add_migration_groups(people), rpp)
        assert pd.isna(out["log_official"].iloc[0])

    def test_topcode_flagged(self, people, rpp):
        people.loc[0, "POVERTY"] = 501
        out = add_outcomes(add_migration_groups(people), rpp)
        assert out["topcoded"].iloc[0] == 1


class TestCovariates:
    def test_hhid_includes_the_survey_year(self, people):
        """SERIAL is unique only within a wave.

        Without the year in the key, unrelated households from different years
        collapse into one cluster and the clustered standard errors are wrong.
        """
        two_waves = pd.concat([people, people.assign(YEAR=2023)], ignore_index=True)
        out = add_covariates(two_waves)
        assert out["hhid"].nunique() == 14

    def test_hispanic_takes_precedence_over_race(self, people):
        # Order in the case chain is load-bearing: a Hispanic respondent coded
        # RACE = 1 must land in Hispanic, not NH White.
        people.loc[0, "HISPAN"] = 1
        people.loc[0, "RACE"] = 1
        assert add_covariates(people)["raceth"].iloc[0] == "Hispanic"

    @pytest.mark.parametrize("educ,expected", [
        (0, "< HS"), (5, "< HS"), (6, "HS grad"),
        (7, "Some college"), (9, "Some college"), (10, "BA or more"),
    ])
    def test_education_boundaries(self, people, educ, expected):
        people.loc[0, "EDUC"] = educ
        assert add_covariates(people)["educ4"].iloc[0] == expected

    def test_famsize_is_top_coded_at_eight(self, people):
        people.loc[0, "FAMSIZE"] = 15
        assert add_covariates(people)["famsize"].iloc[0] == 8.0


class TestLoadRpp:
    def _write(self, tmp_path, text):
        path = tmp_path / "sarpp.csv"
        path.write_text(text)
        return path

    def test_keeps_only_all_items_line_code(self, tmp_path):
        """The published download stacks five sub-indexes per state.

        Without the filter the join multiplies every person by five.
        """
        path = self._write(tmp_path, (
            "GeoFIPS,GeoName,LineCode,2022\n"
            '"06000",California,1,112.0\n'
            '"06000",California,2,140.0\n'
            '"06000",California,3,105.0\n'
        ))
        out = load_rpp(path)
        assert len(out) == 1
        assert out["rpp"].iloc[0] == 112.0

    def test_strips_quotes_from_geofips(self, tmp_path):
        path = self._write(tmp_path,
                           'GeoFIPS,LineCode,2022\n"48000",1,97.0\n')
        assert load_rpp(path)["STATEFIP"].iloc[0] == 48.0

    def test_rejects_duplicate_state_years(self, tmp_path):
        path = self._write(tmp_path, (
            "GeoFIPS,LineCode,2022\n"
            '"06000",1,112.0\n'
            '"06000",1,113.0\n'
        ))
        with pytest.raises(ValueError, match="duplicate"):
            load_rpp(path)

    def test_suppressed_cells_become_na_rather_than_crashing(self, tmp_path):
        path = self._write(tmp_path,
                           'GeoFIPS,LineCode,2022\n"06000",1,(NA)\n')
        assert pd.isna(load_rpp(path)["rpp"].iloc[0])
