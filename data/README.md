# Data

The pipeline needs two inputs. One is in this repository; the other you have to
obtain yourself, because its license does not permit us to redistribute it.

## 1. BEA Regional Price Parities — included

`data/external/sarpp_state_2008_2024.csv` — Regional Price Parities by state,
BEA table SARPP, 2008–2024. Committed here because it is small and in the
public domain as a US federal government work.

Two things about this file matter:

**Coverage.** It must span every ACS wave in the analysis. A shorter file
covering only 2022–2024 will silently fail the price join for every 2021 row —
roughly a third of the sample — and the pipeline will report a sample of about
665,000 instead of 981,006. The loader counts and prints join failures rather
than dropping them quietly, so this shows up as an attrition-table anomaly
rather than a wrong answer.

**Line code.** The loader filters to `LineCode == 1` ("RPPs: All items"). The
as-published BEA download stacks five price sub-indexes per state; joining
without that filter multiplies every person by five.

To refresh: bea.gov → Tools → Interactive Data (iTable) → Regional → *Real
Personal Income and Regional Price Parities by State and Metropolitan Area* →
table SARPP. BEA revises back years, so a fresh pull will change prior numbers.

**Direction.** RPP is indexed with the national average at 100. Price-adjusted
income-to-needs is nominal **divided by** `RPP/100`. See `src/README.md` — this
is the single most common way to get the sign of the result backwards.

## 2. IPUMS USA extract — you supply this

    data/raw/usa_XXXXX.xml       DDI codebook
    data/raw/usa_XXXXX.dat.gz    microdata, ~800 MB for the full extract

Both are gitignored. IPUMS extracts are built per user account and cannot be
shared as a download URL or redistributed by us — see the
[IPUMS terms of use](https://www.ipums.org/about/terms). Registration is free.

### Building an equivalent extract

| Setting | Value |
|---|---|
| Collection | IPUMS USA |
| Samples | ACS 1-year: 2021, 2022, 2023, 2024 |
| Case selection | `STATEFIP` = 06 (California) and 48 (Texas) |
| Structure | Rectangular, person level |

The pipeline reads 21 variables (see `PIPELINE_VARS` in
`src/data/build_sample.py`):

    YEAR SERIAL PERNUM PERWT STATEFIP PUMA GQ AGE SEX RACE HISPAN
    EDUC CITIZEN MARST NCHILD FAMSIZE MIGPLAC1 POVERTY
    SPMTOTRES SPMTHRESH SPMGEOADJ

Requesting only these makes the extract dramatically smaller and runs the whole
analysis.

### Programmatic extracts

`ipumspy` can define and submit the extract with an API key from
<https://account.ipums.org/api_keys>:

```python
from ipumspy import IpumsApiClient, UsaExtract

extract = UsaExtract(
    ["us2021a", "us2022a", "us2023a", "us2024a"],
    ["YEAR", "SERIAL", "PERNUM", "PERWT", "STATEFIP", "PUMA", "GQ",
     "AGE", "SEX", "RACE", "HISPAN", "EDUC", "CITIZEN", "MARST",
     "NCHILD", "FAMSIZE", "MIGPLAC1", "POVERTY",
     "SPMTOTRES", "SPMTHRESH", "SPMGEOADJ"],
)
client = IpumsApiClient(API_KEY)
client.submit_extract(extract)
client.wait_for_extract(extract)
client.download_extract(extract, download_dir="data/raw")
```

The same library reads the result — `readers.read_microdata(ddi, path)` parses
the DDI XML and the fixed-width `.dat.gz` together. Do not hand-parse the
fixed-width file; column offsets come from the DDI and change between extracts.

### A note on universe filters

The extract above is already case-selected to California and Texas. The
pipeline still applies its own state and universe filters, and on this extract
they each remove zero rows. They stay in the code so that a differently built
extract cannot silently change the sample without the attrition table showing
it.

## Running it

    python -m src.data.make_data

Writes `data/processed/analysis_sample.parquet` and prints the attrition table,
the per-group row counts, and the price-adjustment direction check.
