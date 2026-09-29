# How Much Better Off Are Californians Who Move to Texas?

Hundreds of thousands of Californians have left for Texas since the pandemic,
and the reason they give is almost always that things cost less there. This
repository holds an analysis of whether the move actually pays, using ACS
microdata and BEA Regional Price Parities.

**Headline:** compared with Californians of the same age, sex, race and
ethnicity, nativity, education, marital status, and family size who stayed put,
recent California-to-Texas movers have income relative to need **10.1% higher**
in price-adjusted terms (95% CI 3.7% to 16.9%, p = 0.002). The Supplemental
Poverty Measure, built on entirely different definitions, puts it at +17.9%.

Roughly 45% of the raw gap is composition rather than location — movers are
younger and much better educated than stayers. The 10.1% is what survives
holding that fixed.

Measured against the unadjusted federal poverty threshold, the same comparison
shows **no detectable difference** (-3.9%, p = 0.19, CI spanning zero). The gain
consists entirely of purchasing power, which the official measure is designed
not to see.

This is a **descriptive** study. Movers select themselves, and nothing here
identifies a causal effect of moving.

## Authors

Ken Xiong, Artem Senchev, Sam Der, Pedro Jose Palacios

## Status

Working paper, pending team review before publication. `reports/paper.pdf` is
the current draft; `ROADMAP.md` tracks what remains between here and a citable
preprint.

## Quickstart

```bash
git clone <repo-url>
cd ca-tx-mqol
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Acquire the IPUMS extract first — see data/README.md
python -m src.data.make_data          # builds data/processed/analysis_sample.parquet
python -m src.analysis.models         # fits the models, writes reports/tables/
python -m src.analysis.figures        # writes reports/figures/
pytest                                # parity + invariant checks
```

The unit tests run without the IPUMS extract. The R-parity tests need both the
built sample and `tests/reference_r_output.json`, and skip cleanly without them.

The IPUMS microdata is **not** in this repository and cannot be redistributed.
`data/README.md` documents exactly how to rebuild an equivalent extract from a
free IPUMS account.

## Layout

    ├── LICENSE                  MIT — covers src/, notebooks/, tests/
    ├── LICENSE-CC-BY-4.0.md     CC BY 4.0 — covers reports/
    ├── AUTHORS.md               Authorship and licensing consent record
    ├── ROADMAP.md               Remaining path to publication
    ├── pyproject.toml           Dependencies and pinned environment
    ├── data
    │   ├── README.md            How to obtain every input
    │   ├── external/            BEA Regional Price Parities (committed, public domain)
    │   ├── raw/                 IPUMS extract (gitignored — you supply this)
    │   └── processed/           Derived analysis sample (gitignored)
    ├── src
    │   ├── data/                Extract → analysis sample
    │   └── analysis/            Models, tables, figures
    ├── notebooks/               01-exploratory.ipynb — committed with outputs
    ├── reports/                 Paper draft, generated tables and figures
    └── tests/                   Parity and invariant checks

## Data

| Input | Source | Terms |
|---|---|---|
| ACS microdata | IPUMS USA, Ruggles et al. (2025), [doi:10.18128/D010.V16.0](https://doi.org/10.18128/D010.V16.0) | Redistribution prohibited — not included here |
| Regional Price Parities | BEA table SARPP | US federal government work, public domain |

## License

This repository is licensed in three parts. Please respect the split.

| Component | License |
|---|---|
| Source code — `src/`, `notebooks/`, `tests/` | [MIT](LICENSE) |
| Written report, figures, tables — `reports/` | [CC BY 4.0](LICENSE-CC-BY-4.0.md) |
| `data/external/` (BEA SARPP) | US federal government work, public domain. Cite BEA. |
| IPUMS extract | Not distributed. Governed by the [IPUMS terms of use](https://www.ipums.org/about/terms). |

All four authors have consented to this licensing — see `AUTHORS.md`.

## Citation

If you use this work, please cite the paper (see `CITATION.cff`, or GitHub's
"Cite this repository" button) and, separately, the underlying data sources:

- Ruggles, S., et al. (2025). *IPUMS USA: Version 16.0* \[dataset\].
  Minneapolis, MN: IPUMS. https://doi.org/10.18128/D010.V16.0
- U.S. Bureau of Economic Analysis. *Real Personal Income and Regional Price
  Parities by State and Metropolitan Area*, table SARPP.

## Provenance

This analysis began as a graduate course project and has since been rewritten
and extended for release. The published code is an independent Python
implementation; no course-provided template material, assignment text, or
instructional scaffolding is included in this repository.
