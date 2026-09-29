# Roadmap to publication

Phase 1 (build) is complete: pipeline, models, figure, notebook, tests, licenses,
consent record, and a written paper that builds to PDF. Everything below is what
remains between here and a citable public preprint.

Status legend: ☐ not started · ◐ in progress · ☑ done

---

## Phase 2 — Team review

The paper was **reframed after the first draft** and the team has not seen the
current version. This is the gate before anything is published; do not skip
straight to Phase 3.

- ☑ **Circulate `reports/paper.pdf` to Ken, Sam, and Pedro.** Approved by all
  three (confirmed 2026-09-28). What changed and
  needs their sign-off specifically:
  - **Framing.** The paper is now about *how much better off movers are*, with
    the price adjustment as the measurement method rather than the subject.
    The earlier draft led with the measurement question.
  - **Title.** Now *"Tech Bros to Cowboys: How Much Better Off Are Californians
    Who Move to Texas?"* Ken chose the original "Tech Bros to Cowboys" title —
    the hook is kept, the subtitle is new and is his call to accept.
  - **The official-line result is reported as null.** The class report treated
    -3.9% as a finding. It is p = 0.19 with a CI spanning zero, so the paper
    now says "no detectable difference." This is the single most important
    change and the one a reviewer would have caught. It weakens the clean
    "sign reversal" story and the team should understand why.
  - **New material not in the class report:** the non-mover evidence in §6
    (TX_stay -5.6% -> +8.2%), the control ladder decomposition (~45% of the raw
    gap is composition), and the joined-household sensitivity at 16.7%.
- ☐ **Agree author order.** Currently alphabetical-by-nothing: Xiong, Senchev,
  Der, Palacios. `AUTHORS.md` has the contribution table; adjust to reflect the
  final division of work.
- ☐ **Fill the Record column in `AUTHORS.md`** with links to the actual consent
  messages. Checked boxes with nothing behind them are not a record.

## Phase 3 — Publish the repository

- ☑ **Create the public GitHub repo** (personal account, NOT `github-ucb` /
  `kenxiong-crypto`). Suggested name: `ca-tx-mqol`.
- ☑ **Single squashed initial commit.** Do not push the course repo's history —
  `prompt/assignment.pdf` survives in it even after deletion, and that file is
  the instructional team's.
- ☑ **Fill in `[repository URL]`** in `reports/paper.md` §8, then rebuild
  (`python reports/build_paper.py`).
- ☐ **Add `CITATION.cff`** — `README.md` already points at it. Needs the DOI
  from Phase 4, so this lands after the Zenodo deposit.
- ☑ Move off system Python: create a venv and `pip install -e ".[dev,paper]"`.
  The clean install pulled statsmodels 0.15 (formulaic replaces patsy), which
  broke `predict_with_ci`; it now uses the public `get_prediction` API and
  passes on both 0.14 and 0.15.

## Phase 4 — Zenodo (the DOI)

- ☐ Enable the Zenodo–GitHub integration on the new repo.
- ☐ Tag `v1.0.0` and publish a release; Zenodo mints the DOI automatically.
- ☐ Deposit metadata: license **CC BY 4.0** (the deposit is paper-centric; the
  README carries the MIT-for-code split), all four authors with ORCIDs if they
  have them.
- ☐ **Do not upload the IPUMS extract.** `data/raw/` is gitignored for a
  reason — redistribution violates the IPUMS terms. The 44 MB
  `analysis_sample.parquet` is derived from it and must not go either.
- ☐ Add the DOI to `CITATION.cff` and to `reports/paper.md` §8.

## Phase 5 — Preprint

- ☐ **SocArXiv via OSF Preprints.** No endorsement needed, indexed by Google
  Scholar, natural home for a migration / cost-of-living paper. Cite the Zenodo
  DOI for code and data.
- ☐ Consider SSRN as a second posting for the policy-economics audience.
- ☐ **arXiv is deliberately deferred.** `econ.GN` requires an endorsement from
  an existing contributor that nobody on the author line has, and moderators
  reject work that reads as coursework. Revisit only after a substantive
  methods revision — realistically after the metro-RPP extension below.

---

## Backlog — what would make this a stronger paper

Roughly in order of value per unit of effort.

1. **Metro-level price parities.** The single biggest methodological weakness
   is one statewide index per year. Movers cluster in Austin, Dallas, and
   Houston, which are not rural Texas, so the statewide figure likely
   *overstates* the saving they realize. BEA publishes MSA-level RPPs and the
   sample already carries `PUMA`. This is the extension that would most change
   what the paper can claim — and it is also what would make an arXiv
   submission defensible as new research rather than a term paper.
2. **Replicate weights.** `PERWT` plus household clustering is a reasonable
   approximation but not a design-based estimator. IPUMS ships `REPWTP1-80`.
   This would let §7 item 5 be deleted rather than caveated.
3. **Widen beyond CA and TX.** The extract is case-selected to two states,
   which makes the finding a corridor study. The same design across all state
   pairs would say something general about how price adjustment reorders
   interstate comparisons.
4. **`notebooks/02-*.ipynb` for the robustness work** — top-coding sensitivity,
   alternative floors, year-by-year estimates. Currently only summarized in the
   paper.
5. **Bootstrap or randomization inference for the mover groups.** n = 1,482 and
   591 are small enough that the normal approximation is worth checking.

---

## Things that must not silently change

Guardrails already enforced by `tests/`, listed here so a future contributor
knows they are deliberate rather than incidental.

- **RPP is DIVIDED, never multiplied.** Inverting it flips the paper's sign and
  produces an entirely plausible-looking sample. `make_data.py` asserts
  California's mean ratio falls after adjustment and exits non-zero otherwise.
- **`hhid` is `YEAR_SERIAL`.** `SERIAL` alone repeats across waves and would
  merge unrelated households into single clusters.
- **`CA_stay` is the reference level.** Reordering the categorical rebases every
  coefficient in the paper.
- **Three definitions match the R report and are pinned by
  `tests/test_parity.py`:** price levels are the 2023 wave alone (not a
  multi-year mean); the top-coded share is unweighted; "joined a household"
  means the household holds more than one migration group (not merely a
  non-mover). Each alternative is defensible and each gives a different number.
- **R parity.** `tests/export_reference.R` regenerates
  `tests/reference_r_output.json` from the original R project. Re-run it after
  any change to the R side; the Python suite compares against it.
