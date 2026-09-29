---
title: "Tech Bros to Cowboys: How Much Better Off Are Californians Who Move to Texas?"
author:
  - Ken Xiong
  - Artem Senchev
  - Sam Der
  - Pedro Jose Palacios
date: 2026-08-16
bibliography: references.bib
csl: apa.csl
---

## Abstract

Hundreds of thousands of Californians have left for Texas since the pandemic,
and the reason they give is almost always the same one: things cost less there.
We ask the obvious follow-up question. Does the move actually pay?

Using American Community Survey microdata for California and Texas from 2021 to
2023 (n = 981,006 working-age adults in 547,600 households), we compare recent
California-to-Texas movers against Californians who stayed, holding age, sex,
race and ethnicity, nativity, education, and household composition fixed.
Movers come out **10.1% better off** in material terms — what their family
income actually buys where they now live (95% CI 3.7% to 16.9%, p = 0.002). A
second measure built on entirely different definitions, the Supplemental
Poverty Measure, puts the advantage at 17.9%.

Roughly 45% of the raw gap between movers and stayers is not about Texas at
all: people who move are younger and much better educated than people who
don't, and that composition accounts for most of the unadjusted difference.
The 10.1% is what survives once those differences are held fixed.

The advantage is invisible in official statistics. Measured against the federal
poverty threshold — the same dollar figure in San Francisco as in El Paso — the
same comparison yields no detectable difference (-3.9%, p = 0.19). The gain is
real but consists entirely of purchasing power, which the official measure is
designed not to see.

These are descriptive comparisons. Movers choose to move, on characteristics
this data cannot observe, and nothing here identifies a causal effect of moving
on anyone.

**Keywords:** interstate migration, cost of living, material living standards,
poverty measurement, American Community Survey

---

## 1. Does the move pay?

California's median home price passed \$900,000 in 2026, and \$1.4 million in
the Bay Area [@carJuneHome]. Texas's statewide median sat near \$340,000
[@tamuTexasHousing]. That gap has driven one of the largest interstate
migration flows in the country [@caDreamingReport], and it comes with an
implicit promise: the same paycheck goes further in Texas, so the people making
the move end up ahead.

It is a promise worth testing, and it is not obvious it should hold. Movers
might be trading a high salary for a lower one. They might be arriving into
jobs that pay Texas wages rather than keeping California ones. The cost saving
is real, but so is the possibility that income falls to meet it.

This paper measures the net result. We compare Californians who moved to Texas
within the past year against Californians who did not move, matched on the
demographics that ordinarily drive income, and we ask how much further their
money goes.

The answer is that the move pays — by about 10% — and that you cannot see it in
the official poverty statistics, for a reason we return to in Section 6.

## 2. Data

**Microdata.** IPUMS USA [@ruggles2025ipumsusa] one-year ACS samples for 2021,
2022, and 2023, restricted to California and Texas. We keep working-age adults
(25–64) living in households rather than group quarters. The 2024 wave is
dropped because a component we use for robustness is unpublished for that year,
and we prefer every model to run on identical rows rather than let each
specification silently choose its own sample.

| Step | Rows remaining | Removed |
|---|---:|---:|
| Raw extract (CA + TX, 2021–2024) | 2,657,979 | — |
| Drop the 2024 wave | 1,984,999 | 672,980 |
| Keep ages 25–64 | 1,023,275 | 961,724 |
| Drop group quarters | 981,006 | 42,269 |
| **Analysis sample** | **981,006** | |

Four further exclusion checks — third-state arrivals, people outside the
poverty universe, survey years without a published price index, and missing
covariates — each remove zero rows, because the extract was already
case-selected to this universe. They remain in the pipeline so a differently
built extract cannot quietly change the sample without the attrition table
showing it.

**Prices.** BEA Regional Price Parities, table SARPP, all-items index, national
average = 100 [@beaSARPP]. In 2023 California stands at 112.20 and Texas at
97.14: a dollar in Texas buys about 15% more than the same dollar in
California.

**Who counts as a mover.** `MIGPLAC1` records state of residence one year
before the survey. Crossing it with current state yields six groups. The
comparison group is Californians in the *same house* as a year ago; people who
moved within California are tracked separately rather than folded into the
baseline, which matters because moving itself is correlated with income.

| Group | Meaning | n |
|---|---|---:|
| `CA_stay` | In California, same house — **comparison group** | 524,268 |
| `CA_to_CA` | Moved within California | 50,763 |
| **`CA_to_TX`** | **California → Texas** | **1,482** |
| `TX_stay` | In Texas, same house | 364,801 |
| `TX_to_TX` | Moved within Texas | 39,101 |
| `TX_to_CA` | Texas → California | 591 |

About 400 to 540 Californians per wave show up as recent Texas arrivals. That
is a real constraint: it widens the confidence interval on the central estimate
and rules out slicing movers further by metro, industry, or income band.

## 3. Measuring "better off"

"Better off" has to mean something specific. We use **income relative to need**:
family income divided by the poverty threshold for a family of that size and
composition, so 1.0 sits exactly at the line and 4.0 means four times it. This
handles the fact that a \$90,000 income means something different to a single
adult than to a family of five.

The question is which threshold. The federal poverty line is the same nominal
figure in every state, which means a comparison built on it holds purchasing
power constant by construction — precisely the thing we are trying to measure.
So our primary measure prices the threshold to where the family actually lives:
the national threshold scaled by that state's price index. Income covering
three times the local cost of need in Texas is what we mean by "three times
better than the line."

Concretely, the price-adjusted ratio is the official ratio *divided* by
RPP/100. Higher prices mean a given income covers less local need. Reversing
this — multiplying — would apply California's high prices as a bonus instead of
a cost and invert every comparison in the paper, so the pipeline asserts that
California's mean ratio falls after adjustment and refuses to write a sample
that fails the check.

We report three measures throughout:

- **Price-adjusted (primary):** income relative to the locally-priced threshold.
- **Official:** income relative to the national threshold, unadjusted.
- **Supplemental Poverty Measure (robustness):** the Census SPM, which redefines
  resources *and* threshold at once — taxes, benefits, work expenses, and
  geography. Because it moves several things simultaneously it cannot isolate
  the price effect, which is exactly why it is a check on the conclusion rather
  than the basis for it.

Ratios enter the models in logs, floored at 0.10 because the bottom code
absorbs zero and negative family income, so coefficients read as percentage
differences.

## 4. Who moves, and why it must be controlled for

Movers are not a random draw from stayers, and the differences all run in the
direction that would flatter Texas if left alone.

| | CA stay | CA→CA | **CA→TX** | TX stay |
|---|---:|---:|---:|---:|
| Mean age | 44.3 | 38.3 | **39.6** | 44.2 |
| BA or more | 36.9% | 48.1% | **47.8%** | 34.6% |
| Married | 56.2% | 44.1% | **59.2%** | 61.7% |
| Family size | 3.33 | 2.75 | **2.85** | 3.18 |

*Weighted by `PERWT`.*

Californians who left for Texas are nearly five years younger than those who
stayed and **eleven percentage points more likely to hold a bachelor's
degree**. In
this sample a degree is associated with 90.5% higher income relative to need,
so that education gap alone could manufacture a large apparent "Texas effect"
in an uncontrolled comparison.

Notably, they look almost identical on education to people who moved *within*
California (47.8% against 48.1%). Whatever selects people into moving is mostly
about moving, not about Texas.

One thing does separate cross-state movers from local ones: they are *more*
likely to be married (59.2%) than stayers (56.2%), while within-state movers
are markedly less likely (44.1%). Leaving the state looks like a household
decision in a way that moving across town does not.

## 5. Results

We estimate

$$\log(\text{income-to-needs})_i = \beta_0 + \beta'\text{Migration}_i + \gamma'\text{Demographics}_i + \delta'\text{Education}_i + \theta'\text{Household}_i + \varepsilon_i$$

by weighted least squares using ACS person weights, with standard errors
clustered on household. Clustering is not optional: the ACS samples entire
households, income relative to need is a family-level measure, and 79.7% of
people in our sample share a household with another sampled adult.

### 5.1 How much better off

Adding controls in blocks separates the part of the gap that is about Texas
from the part that is about who moves.

| Specification | CA→TX advantage | $R^2$ |
|---|---:|---:|
| No controls | +18.1% | 0.002 |
| + demographics (age, sex, race, nativity) | +17.3% | 0.059 |
| + education | +12.0% | 0.127 |
| + household composition | **+10.1%** | 0.155 |

Demographics barely dent it. **Education is the single largest correction**,
taking the estimate from +17.3% to +12.0%, exactly as Section 4 predicts.
Household composition removes another two points. In total, **roughly 45% of
the raw mover advantage is composition rather than location.**

What remains is the headline:

> Compared with Californians of the same age, sex, race and ethnicity,
> nativity, education, marital status, and family size who stayed put, recent
> California-to-Texas movers have income relative to need **10.1% higher**
> (95% CI 3.7% to 16.9%, p = 0.002).

To put that in concrete terms: a family sitting at three times the poverty line
gains purchasing power worth about **three-tenths of a poverty threshold per
year** by making the move — not a transformation, but not trivial either.

The Supplemental Poverty Measure, built on a different definition of both
resources and needs, puts the advantage at **+17.9%** (95% CI 10.4% to 25.9%,
p < 0.001) — same direction, larger magnitude, from a measure sharing almost
nothing with the primary one.

### 5.2 Does it survive scrutiny?

**Movers who join an established household.** Migration is recorded per person,
but income relative to need is a family measure, so a mover moving in with
people already there is credited with the household's resources. 16.7% of
California-to-Texas movers are in such a household. Excluding them moves the
estimate from +10.1% to **+8.1%** — a real attenuation, worth reporting, and
not enough to overturn the finding.

**The comparison group.** Californians who moved *within* California are
statistically indistinguishable from Californians who did not move (+0.05%,
n.s.). Moving per se does not produce the advantage; moving to a cheaper state
does.

**The reverse flow.** The 591 Texans who moved to California show -2.6%, not
statistically significant. The point estimate has the expected sign but the
group is far too small to support a claim.

## 6. Why the official numbers miss this

Run the identical comparison against the unadjusted federal poverty threshold
and the result disappears: **-3.9%, p = 0.19**, a confidence interval from
-9.5% to +2.0% that comfortably contains zero. On the official measure,
California-to-Texas movers are not detectably different from Californians who
stayed.

Both numbers are correct. They differ because the entire gain is purchasing
power, and the federal threshold is the same dollar figure everywhere by
design. A statistic built that way cannot register the one economic fact that
motivates the move. This is not a novel critique — @jolliffe2006poverty showed
two decades ago that cost-of-living adjustments reshuffle which places look
poorest — but the California-to-Texas corridor is an unusually clean
demonstration of the stakes.

How large is the distortion? Large enough to reorder entire state populations,
not just the small mover groups. Among people who did not move at all, where
sample sizes make the estimates extremely precise:

| Group | Official | Price-adjusted |
|---|---:|---:|
| `TX_stay` (n = 364,801) | **-5.6%** ($p \approx 10^{-97}$) | **+8.2%** ($p \approx 10^{-183}$) |
| `TX_to_TX` (n = 39,101) | -10.1% ($p \approx 10^{-53}$) | +3.0% (p < 0.001) |

Texans in the same home as a year earlier look 5.6% *worse off* than comparable
Californians on the official line and 8.2% *better off* once each family's
threshold reflects local prices. Both estimates are precise beyond any
plausible sampling noise. The price gap between these states is not a
rounding-error adjustment; it is large enough to invert the ranking of two of
the largest populations in the country.

That is the context in which the 10.1% mover advantage should be read: not as a
fragile artifact of a measurement choice, but as a modest consequence of a
price gap so large it flips the comparison for everyone else too.

Figure 1 shows all six groups under both thresholds.

![Predicted family income for each migration group as a multiple of the poverty
line, from the full specification. Both series use the same incomes and differ
only in the line they divide by: orange the national line, identical in every
state; blue that line scaled to state prices, 12% higher in California and 3%
lower in Texas in 2023. Points are predictions for a reference adult; bars are
95% confidence intervals, widest for the two small cross-state mover
groups.](figures/ratio_by_group.png)

## 7. What this does not establish

1. **This is not the causal effect of moving.** People choose to move, on
   information the ACS never records: a job offer in hand, family already in
   Texas, an employer paying for relocation. Section 4 documents the observable
   differences and the models hold them fixed; the unobservable ones remain. A
   Californian who moves to Texas is 10.1% better off than a *comparable*
   Californian who stayed — which is not the same as saying they became 10.1%
   better off *by moving*.

2. **Top-coding compresses the tails, state-dependently.** Family income is
   capped at 501% of the threshold, and 44.5% of Californians and 37.3% of
   Texans sit at that ceiling. Repricing makes the cap bind at 4.47$\times$ the local
   line in California but 5.16$\times$ in Texas. Because the California ceiling binds
   lower, California's upper tail is compressed harder and the estimated Texas
   advantage is **understated** rather than inflated. The direction is
   knowable; the magnitude is not.

3. **One price index per state.** RPP is statewide. Movers cluster in Austin,
   Dallas, and Houston, which are not rural Texas, and a statewide average
   likely overstates the saving they actually realize. Metro-level parities
   exist and are the obvious extension of this work.

4. **A one-year window.** These are people observed shortly after arriving, not
   settled outcomes. Whether the advantage persists, grows, or erodes as Texas
   housing costs rise is a question this design cannot answer. Return migrants
   are invisible.

5. **Person weights are not a full survey design.** Combined with household
   clustering they are a reasonable approximation, but replicate weights would
   be the rigorous route, and we claim no more than we have done.

## 8. Reproducibility

The full pipeline is public at
<https://github.com/artemsenchev/ca-tx-mqol>, licensed MIT for code and CC
BY 4.0 for this text. The IPUMS extract cannot be redistributed under its
terms; the repository documents how to rebuild an equivalent extract from a
free account, and every other input is included.

The analysis was originally implemented in R and independently reimplemented in
Python. The two agree to floating-point precision — the largest discrepancy
across all model coefficients is $7.5 \times 10^{-11}$ relative, and $1.3 \times 10^{-12}$ for
clustered standard errors — and that parity check runs as part of the test
suite. Every figure and number in this paper is generated by a script rather
than transcribed by hand.

## References
