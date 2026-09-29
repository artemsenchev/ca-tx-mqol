"""Single source of truth for the analysis sample.

Every data-handling step between the raw IPUMS extract and the frame the models
are fit on lives in this file, one function per step:

    load_raw()              read the IPUMS DDI + fixed-width microdata
    load_rpp()              read BEA SARPP regional price parities, long format
    add_migration_groups()  classify each person into the six origin/dest groups
    add_outcomes()          derive resource-to-need outcomes
    add_covariates()        derive model covariates from raw codes

plus the counted cohort/exclusion filters applied inline in
build_analysis_sample(), which chains them and records how many rows each step
removed. The attrition table and the data come from the same code path, so the
paper's observations-removed table cannot drift from the sample it describes.

THE REPRICED OUTCOME DIVIDES BY (RPP/100). RPP > 100 means prices are higher,
so the same income covers less of the local cost of need: the state-priced
threshold is threshold * RPP/100, hence

    ratio_repriced = ratio_official / (RPP / 100)

Multiplying instead applies California's price level as a bonus rather than a
cost and flips the sign of every cross-state comparison in the paper. The
sanity check is that California's mean repriced ratio must come out BELOW its
mean official ratio; make_data.py asserts exactly that.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Floor for log outcomes. SPM resources can be zero or negative (business and
# investment losses), and POVERTY = 001 is a bottom code absorbing zero and
# negative family income, so the raw ratio is not log-safe.
FLOOR_RTN = 0.10

# The extract carries ~420 columns, 160 of them replicate weights the analysis
# never touches. Reading only what the pipeline uses keeps the load tractable.
PIPELINE_VARS = [
    "YEAR", "SERIAL", "PERNUM", "PERWT", "STATEFIP", "PUMA", "GQ",
    "AGE", "SEX", "RACE", "HISPAN", "EDUC", "CITIZEN", "MARST",
    "NCHILD", "FAMSIZE", "MIGPLAC1", "POVERTY",
    "SPMTOTRES", "SPMTHRESH", "SPMGEOADJ",
]

# Reference level FIRST -- California same-house residents are the baseline
# every other group is compared against.
GRP_LEVELS = ["CA_stay", "CA_to_CA", "CA_to_TX", "TX_stay", "TX_to_TX", "TX_to_CA"]
RACETH_LEVELS = ["NH White", "Hispanic", "NH Black", "NH Asian/PI", "NH Other/Multi"]
EDUC4_LEVELS = ["< HS", "HS grad", "Some college", "BA or more"]
NATIVITY_LEVELS = ["US born", "Naturalized", "Non-citizen"]


@dataclass
class AnalysisSample:
    """The built sample plus the attrition record that produced it.

    Kept together deliberately: R attached attrition as an attribute of the
    data frame, and pandas silently drops `.attrs` through most operations, so
    a plain DataFrame would lose the provenance the paper cites.
    """

    data: pd.DataFrame
    attrition: pd.DataFrame

    def __len__(self) -> int:
        return len(self.data)


def load_raw(ddi_path) -> pd.DataFrame:
    """Read the IPUMS extract via its DDI codebook.

    Never hand-parse the fixed-width .dat: column offsets live in the DDI and
    change between extracts. ipumspy reads the two together.
    """
    from pathlib import Path

    from ipumspy import readers

    ddi_path = Path(ddi_path)
    # IPUMS ships the microdata gzipped; some workflows decompress it.
    candidates = [ddi_path.with_suffix(".dat.gz"), ddi_path.with_suffix(".dat")]
    data_path = next((p for p in candidates if p.exists()), None)
    if data_path is None:
        raise FileNotFoundError(
            f"found the DDI at {ddi_path} but no microdata beside it; "
            f"expected one of {[p.name for p in candidates]}"
        )

    ddi = readers.read_ipums_ddi(str(ddi_path))
    df = readers.read_microdata(ddi, str(data_path), subset=PIPELINE_VARS)
    missing = set(PIPELINE_VARS) - set(df.columns)
    if missing:
        raise ValueError(
            f"extract is missing pipeline variables: {sorted(missing)}. "
            "Rebuild it with the variable list in data/README.md."
        )
    return df


def load_rpp(sarpp_path) -> pd.DataFrame:
    """BEA table SARPP, LineCode 1 ('RPPs: All items'), US = 100.

    Two failure modes this guards against:

    1. The as-published download stacks five price sub-indexes per state.
       Joining without the LineCode filter multiplies every person by five.
    2. The file must cover every survey year in the extract. An RPP table
       starting in 2022 NA-joins the entire 2021 wave, and the join-failure
       filter then removes about a third of the sample. The attrition table
       makes that visible instead of silent.
    """
    rpp = pd.read_csv(sarpp_path, dtype=str)

    if "LineCode" in rpp.columns:
        rpp = rpp[pd.to_numeric(rpp["LineCode"], errors="coerce") == 1]

    # BEA quotes GeoFIPS ("06000"); strip before coercing or every row is NaN.
    geo = rpp["GeoFIPS"].str.strip().str.strip('"')
    rpp = rpp.assign(STATEFIP=pd.to_numeric(geo, errors="coerce") / 1000)
    rpp = rpp[rpp["STATEFIP"].notna()]

    year_cols = [c for c in rpp.columns if re.fullmatch(r"20[0-9]{2}", c)]
    if not year_cols:
        raise ValueError(f"no year columns found in {sarpp_path}")

    long = rpp.melt(
        id_vars=["STATEFIP"], value_vars=year_cols,
        var_name="YEAR", value_name="rpp",
    )
    long["YEAR"] = long["YEAR"].astype(int)
    # BEA marks suppressed cells with (NA)/(D); coerce them rather than crash.
    long["rpp"] = pd.to_numeric(long["rpp"], errors="coerce")
    long = long[["STATEFIP", "YEAR", "rpp"]]

    dupes = long.duplicated(subset=["STATEFIP", "YEAR"]).sum()
    if dupes:
        raise ValueError(
            f"{dupes} duplicate STATEFIP-YEAR rows in the RPP table; the "
            "LineCode filter did not collapse the sub-indexes."
        )
    return long


def add_migration_groups(df: pd.DataFrame) -> pd.DataFrame:
    """Classify each person by where they lived a year ago and where they are now.

    MIGPLAC1 is state of residence one year ago: 0 = same house (did not move),
    6 = California, 48 = Texas, anything else = a third state or abroad. The
    third-state rows become NaN and are removed (and counted) in
    build_analysis_sample(): someone who arrived in Texas from New York is
    neither a Texas stayer nor a California leaver, and folding them into
    either group would misstate both.

    Note that CA_stay means *same house*, not merely "still in California" --
    within-California movers are their own group, deliberately.
    """
    orig = np.select(
        [df["MIGPLAC1"] == 0, df["MIGPLAC1"] == 6, df["MIGPLAC1"] == 48],
        ["same", "CA", "TX"],
        default="other",
    )
    dest = np.where(df["STATEFIP"] == 6, "CA", "TX")

    pair = pd.Series(orig, index=df.index) + "|" + pd.Series(dest, index=df.index)
    grp = pair.map({
        "same|CA": "CA_stay",
        "CA|CA": "CA_to_CA",
        "TX|CA": "TX_to_CA",
        "same|TX": "TX_stay",
        "TX|TX": "TX_to_TX",
        "CA|TX": "CA_to_TX",
    })  # "other|*" falls through to NaN

    return df.assign(
        orig=orig,
        dest=dest,
        grp=pd.Categorical(grp, categories=GRP_LEVELS),
    )


def add_outcomes(df: pd.DataFrame, rpp: pd.DataFrame) -> pd.DataFrame:
    """Three operationalizations of income relative to need, all as ratios
    where 1.0 sits exactly at the poverty line.

        ratio_official  POVERTY/100 -- Census threshold, identical in every state
        ratio_repriced  official divided by (RPP/100) -- the same threshold
                        repriced to the destination state's cost level
        rtn             SPMTOTRES/SPMTHRESH -- Supplemental Poverty Measure,
                        a wholly different resource and threshold definition,
                        carried as a robustness outcome

    POVERTY = 000 means 'N/A', not zero income. It becomes NaN here and those
    rows are removed and counted downstream.
    """
    out = df.merge(rpp, on=["STATEFIP", "YEAR"], how="left")

    ratio_official = np.where(out["POVERTY"] == 0, np.nan, out["POVERTY"] / 100.0)
    ratio_repriced = ratio_official / (out["rpp"] / 100.0)
    rtn = out["SPMTOTRES"] / out["SPMTHRESH"]

    # numpy matches R here: log(0) -> -inf, log(negative) -> nan. The warnings
    # are expected, not a defect, so silence them rather than let them mask
    # real ones at the call site.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        out = out.assign(
            ratio_official=ratio_official,
            ratio_repriced=ratio_repriced,
            log_official=np.log(np.maximum(ratio_official, FLOOR_RTN)),
            log_repriced=np.log(np.maximum(ratio_repriced, FLOOR_RTN)),
            topcoded=(out["POVERTY"] == 501).astype(int),
            rtn=rtn,
            rtn_floor=(rtn.notna() & (rtn < FLOOR_RTN)).astype(int),
            log_rtn=np.where(rtn.isna(), np.nan, np.log(np.maximum(rtn, FLOOR_RTN))),
            log_res=np.where(
                rtn.isna(), np.nan,
                np.log(np.maximum(out["SPMTOTRES"], FLOOR_RTN * out["SPMTHRESH"])),
            ),
            log_thr=np.log(out["SPMTHRESH"]),
            log_geo=np.log(out["SPMGEOADJ"]),
            log_needs=np.log(out["SPMTHRESH"] / out["SPMGEOADJ"]),
        )
    return out


def add_covariates(df: pd.DataFrame) -> pd.DataFrame:
    """Derive model covariates from raw IPUMS codes.

    Category order is load-bearing: the first level of each categorical is the
    regression reference level, and changing it silently rebases every
    coefficient in Table 1.
    """
    hispan = df["HISPAN"].isin([1, 2, 3, 4])
    raceth = np.select(
        [hispan, df["RACE"] == 1, df["RACE"] == 2, df["RACE"].isin([4, 5, 6])],
        ["Hispanic", "NH White", "NH Black", "NH Asian/PI"],
        default="NH Other/Multi",
    )
    educ4 = np.select(
        [df["EDUC"] <= 5, df["EDUC"] == 6, df["EDUC"] <= 9],
        ["< HS", "HS grad", "Some college"],
        default="BA or more",
    )
    nativity = np.select(
        [df["CITIZEN"].isin([0, 1]), df["CITIZEN"] == 2],
        ["US born", "Naturalized"],
        default="Non-citizen",
    )

    return df.assign(
        year=pd.Categorical(df["YEAR"]),
        female=(df["SEX"] == 2).astype(int),
        age=df["AGE"].astype(float),
        age2=df["AGE"].astype(float) ** 2,
        raceth=pd.Categorical(raceth, categories=RACETH_LEVELS),
        educ4=pd.Categorical(educ4, categories=EDUC4_LEVELS),
        ba=(df["EDUC"] >= 10).astype(int),
        nativity=pd.Categorical(nativity, categories=NATIVITY_LEVELS),
        married=df["MARST"].isin([1, 2]).astype(int),
        kids=(df["NCHILD"] > 0).astype(int),
        famsize=np.minimum(df["FAMSIZE"], 8).astype(float),
        # Household id for cluster-robust standard errors. SERIAL is unique
        # only within a survey year, so the year must be part of the key --
        # without it, unrelated households in different waves collapse into
        # one cluster and the standard errors come out wrong.
        hhid=df["YEAR"].astype(str) + "_" + df["SERIAL"].astype(str),
        pumaid=df["STATEFIP"].astype(str) + "_" + df["PUMA"].astype(str),
    )


def build_analysis_sample(ddi_path, sarpp_path) -> AnalysisSample:
    """Run the pipeline end to end, counting every row removed along the way.

    Cohort restrictions, applied one at a time so each is counted separately:

        YEAR < 2024      the SPM geographic adjustment is unpublished for the
                         2024 wave, so 2024 cannot support the SPM robustness
                         outcome. Dropping it keeps every model on identical
                         rows instead of letting each silently choose its own.
        AGE 25-64        working-age adults
        GQ in {1, 2, 5}  households only, not group quarters
    """
    rpp = load_rpp(sarpp_path)

    steps: list[tuple[str, int]] = []

    def note(frame: pd.DataFrame, label: str) -> pd.DataFrame:
        steps.append((label, len(frame)))
        return frame

    df = note(load_raw(ddi_path), "raw extract")
    df = note(df[df["YEAR"] < 2024],
              "drop the 2024 wave (SPM geographic adjustment unpublished)")
    df = note(df[(df["AGE"] > 24) & (df["AGE"] < 65)],
              "keep working-age adults (25-64)")
    df = note(df[df["GQ"].isin([1, 2, 5])],
              "drop group quarters (institutions, dorms, barracks)")

    df = add_migration_groups(df)
    df = add_outcomes(df, rpp)
    df = add_covariates(df)

    df = note(df[df["grp"].notna()], "drop arrivals from third states or abroad")
    df = note(df[df["ratio_official"].notna()],
              "drop POVERTY = N/A (poverty universe excludes these people)")
    df = note(df[df["ratio_repriced"].notna()],
              "drop survey years without a published RPP")
    df = note(df[df["log_rtn"].notna() & df["log_geo"].notna()],
              "drop rows without an SPM resource or threshold")
    df = note(
        df[df["educ4"].notna() & df["raceth"].notna()
           & df["nativity"].notna() & (df["PERWT"] > 0)],
        "drop rows missing covariates or with zero person weight",
    )

    # Unused categories break design matrices and produce all-zero dummy
    # columns; R's droplevels() equivalent.
    df = df.copy()
    for col in ("grp", "raceth", "educ4", "nativity", "year"):
        df[col] = df[col].cat.remove_unused_categories()

    rows = [n for _, n in steps]
    attrition = pd.DataFrame({
        "step": [s for s, _ in steps],
        "rows": rows,
        "removed": [pd.NA] + [rows[i - 1] - rows[i] for i in range(1, len(rows))],
    })

    return AnalysisSample(data=df.reset_index(drop=True), attrition=attrition)
