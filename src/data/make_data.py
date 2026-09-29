"""Run the pipeline end to end and write the analysis sample to disk.

    python -m src.data.make_data

Writes data/processed/analysis_sample.parquet, which everything downstream
reads. Nothing else re-parses the ~800 MB raw extract.

The RPP direction check at the bottom is not decoration. Getting the price
adjustment backwards -- multiplying by RPP/100 instead of dividing -- produces
a sample that looks entirely reasonable and reverses the paper's headline
finding. This script exits non-zero rather than write a sample that fails it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from src.data.build_sample import build_analysis_sample

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
SARPP_PATH = ROOT / "data" / "external" / "sarpp_state_2008_2024.csv"
OUT_PATH = ROOT / "data" / "processed" / "analysis_sample.parquet"
ATTRITION_PATH = ROOT / "data" / "processed" / "attrition.csv"


def find_ddi(raw_dir: Path = RAW_DIR) -> Path | None:
    """Locate the DDI codebook in data/raw/.

    Extract numbers differ per IPUMS account, so the filename is discovered
    rather than hard-coded. More than one is ambiguous and must be resolved
    explicitly -- picking arbitrarily would silently change the sample.
    """
    found = sorted(raw_dir.glob("*.xml"))
    if len(found) > 1:
        raise ValueError(
            f"multiple DDI files in {raw_dir}: {[p.name for p in found]}. "
            "Pass --ddi to choose one."
        )
    return found[0] if found else None


def check_rpp_direction(df: pd.DataFrame) -> bool:
    """California's mean ratio must FALL after the price adjustment.

    California prices run above the national average, so repricing the poverty
    threshold to local costs makes the same income cover less need. If the
    adjusted mean rises, the division was inverted somewhere.
    """
    summary = (
        df.groupby("dest", observed=True)[["ratio_official", "ratio_repriced"]]
        .mean()
        .rename(columns={"ratio_official": "mean_official",
                         "ratio_repriced": "mean_repriced"})
    )
    print("\n== RPP direction check (CA repriced must be BELOW official) ==")
    print(summary.to_string())

    ca = summary.loc["CA"]
    ok = ca["mean_repriced"] < ca["mean_official"]
    if not ok:
        print(
            "\nFAIL: California's mean repriced ratio "
            f"({ca['mean_repriced']:.4f}) is not below its official ratio "
            f"({ca['mean_official']:.4f}).\n"
            "The price adjustment is inverted. ratio_repriced must be\n"
            "  ratio_official / (rpp / 100)\n"
            "not ratio_official * (rpp / 100). See src/data/build_sample.py.",
            file=sys.stderr,
        )
    return bool(ok)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ddi", type=Path, default=None,
                        help="IPUMS DDI .xml (default: the one in data/raw/)")
    parser.add_argument("--sarpp", type=Path, default=SARPP_PATH,
                        help="BEA SARPP csv")
    parser.add_argument("--out", type=Path, default=OUT_PATH,
                        help="where to write the analysis sample")
    args = parser.parse_args(argv)

    ddi_path = args.ddi or find_ddi()
    if ddi_path is None or not ddi_path.exists():
        print(
            f"no IPUMS DDI found in {RAW_DIR}.\n"
            "  The microdata is not redistributable and is not in this repo.\n"
            "  See data/README.md for how to build an equivalent extract.",
            file=sys.stderr,
        )
        return 1
    if not args.sarpp.exists():
        print(f"missing BEA price table: {args.sarpp}", file=sys.stderr)
        return 1

    sample = build_analysis_sample(ddi_path=ddi_path, sarpp_path=args.sarpp)
    df = sample.data

    print("\n== attrition ==")
    print(sample.attrition.to_string(index=False))

    print("\n== rows by survey year ==")
    print(df["YEAR"].value_counts().sort_index().to_string())

    print("\n== rows by migration group ==")
    print(df["grp"].value_counts().reindex(df["grp"].cat.categories).to_string())

    print("\n== share top-coded (POVERTY = 501) ==")
    print(df.groupby("dest", observed=True)["topcoded"].mean().to_string())

    if not check_rpp_direction(df):
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, index=False)
    sample.attrition.to_csv(ATTRITION_PATH, index=False)
    print(f"\nwrote {args.out}  ({len(df):,} rows)")
    print(f"wrote {ATTRITION_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
