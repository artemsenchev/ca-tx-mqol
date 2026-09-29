# Source

Two rules keep this reproducible:

1. **All variable construction happens in `src/data/`.** If a column is derived
   anywhere else — in a notebook, in the modeling code, in a figure — it is a
   bug. There must be exactly one canonical definition of every variable, and
   it must live here.
2. **Notebooks never define results.** They read the built sample and explore
   it. Anything that lands in the paper is produced by a script in
   `src/analysis/` and written to `reports/tables/` or `reports/figures/`.
   Notebooks execute out of order, do not diff, and cannot be trusted as the
   record of what produced a number.

   `notebooks/01-exploratory.ipynb` follows this: it constructs nothing, and
   imports its palette and model helpers from `src/`. It is committed **with
   its outputs**, because the microdata requires an IPUMS account and the
   executed outputs are the only way most readers will see any results at all.
   The obligation that comes with it: re-execute top-to-bottom before
   committing (`jupyter nbconvert --to notebook --execute --inplace`), and
   never commit a partially-run notebook — stale outputs beside changed code
   are worse than no outputs.

## `src/data/`

| Module | Responsibility |
|---|---|
| `build_sample.py` | Read the IPUMS DDI + fixed-width extract, apply the universe filters, classify migration groups, construct the three income-to-needs measures. Pure functions, no I/O side effects beyond reading inputs. |
| `make_data.py` | Entry point. Runs the build, prints the attrition table and group counts, writes `data/processed/analysis_sample.parquet`. |

Run it:

    python -m src.data.make_data

It prints an attrition table (how many rows each filter drops and why), the row
count per migration group, and a direction check.

### The direction check is not optional

Regional Price Parities are expressed with the national average at 100. To
convert a nominal income-to-needs ratio into a price-adjusted one you **divide
by `RPP/100`**. Multiplying inverts the adjustment and flips the sign of the
headline result — California, an expensive state, would appear to get *richer*
after adjusting for its own high prices.

`make_data.py` asserts that California's mean ratio **falls** after the price
adjustment and fails loudly if it does not. Keep that assertion. It has caught
this exact error before.

### Migration groups

`MIGPLAC1` is state of residence one year ago: `0` = same house (did not move),
`6` = California, `48` = Texas, anything else = a third state or abroad.
Combined with current `STATEFIP` this yields six groups, with `CA_stay` as the
reference level:

| Group | Meaning |
|---|---|
| `CA_stay` | In California, same house a year ago — the baseline |
| `CA_to_CA` | Moved within California |
| `CA_to_TX` | California → Texas, the group of interest |
| `TX_stay` | In Texas, same house a year ago |
| `TX_to_TX` | Moved within Texas |
| `TX_to_CA` | Texas → California |

Arrivals from a third state are mapped to `other` and dropped. Someone who
arrived in Texas from New York is neither a Texas stayer nor a California
leaver, and folding them into either group would misstate both.

Note that `CA_stay` means *same house*, not merely "still in California" —
within-California movers are their own group, deliberately.

## `src/analysis/`

| Module | Responsibility |
|---|---|
| `models.py` | Fits the weighted specifications and writes regression tables. |
| `figures.py` | Generates the paper's figures. It refits the full specification rather than reading saved estimates, so the figure and Table 1 cannot drift apart. |

Figures are written to `reports/figures/` as PNG (300 dpi) and PDF, plus a CSV
of the plotted values — the table view, so every number in the figure is
recoverable without reading colors off an image.

### Estimation details that must not drift

- Observations are weighted by `PERWT` (ACS person weights). Use
  `statsmodels.WLS`, not `OLS`.
- Standard errors are **cluster-robust by household** (`hhid`), not merely
  heteroskedasticity-robust. People in the same household share income and are
  not independent observations.

      sm.WLS(y, X, weights=df["PERWT"]).fit(
          cov_type="cluster", cov_kwds={"groups": df["hhid"]}
      )

  This corresponds to R's `sandwich::vcovCL(m, cluster = hhid, type = "HC1")`.
  The two apply slightly different finite-sample corrections by default;
  `tests/test_parity.py` pins the tolerance.

- `PERWT` used as a regression weight gives precision weighting, not a full
  design-based estimator with replicate weights. Combined with household
  clustering this is a reasonable approximation, and the paper says so. Do not
  quietly upgrade the claim.

## `tests/`

`pytest` checks that the pipeline still produces the sample and the headline
estimates it is supposed to. If a refactor changes a number, the test should
fail before a reader notices.
