# export_reference.R -- dump the ORIGINAL R implementation's results to JSON
# so the Python port can be tested against them.
#
# Run this once, from the root of the *old R project*, with the R pipeline's
# built sample available:
#
#     Rscript path/to/tests/export_reference.R /path/to/old-r-project
#
# It writes tests/reference_r_output.json next to this script. That JSON is the
# only thing that needs to travel to the Python repository -- it contains
# coefficients and counts, no microdata, so it is safe to commit.
#
# This file is scaffolding for the port and can be deleted once parity is
# established and the R code is retired.

args <- commandArgs(trailingOnly = TRUE)
r_project <- if (length(args) >= 1) args[1] else getwd()

suppressPackageStartupMessages({
  library(dplyr)
  library(sandwich)
  library(jsonlite)
})

sample_path <- file.path(r_project, "data", "processed", "analysis_sample.rds")
if (!file.exists(sample_path)) {
  stop("no analysis_sample.rds at ", sample_path,
       " -- run Rscript src/data/make_data.R in the R project first")
}
analysis_sample <- readRDS(sample_path)

# Same ladder as src/analysis/models.py
formulas <- list(
  base        = log_repriced ~ grp,
  demo        = log_repriced ~ grp + female + age + raceth + nativity,
  edu         = log_repriced ~ grp + female + age + raceth + nativity + educ4,
  hh          = log_repriced ~ grp + female + age + raceth + nativity + educ4 +
                  married + kids + famsize,
  hh_official = log_official ~ grp + female + age + raceth + nativity + educ4 +
                  married + kids + famsize
)

# Translate R's coefficient names into patsy's, so the JSON keys match what
# statsmodels produces and the test can compare them directly.
#   R:     grpCA_to_TX          raceth1Hispanic
#   patsy: grp[T.CA_to_TX]      raceth[T.Hispanic]
factor_vars <- c("grp", "raceth", "educ4", "nativity")
to_patsy <- function(nm) {
  if (nm == "(Intercept)") return("Intercept")
  for (v in factor_vars) {
    if (startsWith(nm, v)) {
      lvl <- substring(nm, nchar(v) + 1)
      if (nzchar(lvl)) return(sprintf("%s[T.%s]", v, lvl))
    }
  }
  nm
}

extract <- function(f) {
  m  <- lm(f, data = analysis_sample, weights = PERWT)
  V  <- vcovCL(m, cluster = analysis_sample$hhid, type = "HC1")
  se <- sqrt(diag(V))
  nm <- vapply(names(coef(m)), to_patsy, character(1), USE.NAMES = FALSE)
  list(
    coefficients = as.list(setNames(unname(coef(m)), nm)),
    std_errors   = as.list(setNames(unname(se), nm)),
    r_squared    = summary(m)$r.squared,
    nobs         = stats::nobs(m)
  )
}

attrition <- attr(analysis_sample, "attrition")
grp_counts <- analysis_sample %>% count(grp) %>% filter(n > 0)

# ---------------------------------------------------------------------------
# The report's inline quantities. These are computed in final-report.Rmd
# rather than in src/, so they are the ones most likely to drift silently in a
# port -- each has a definition choice buried in it.
# ---------------------------------------------------------------------------

# Top-coded share by destination state.
topcode_share <- analysis_sample %>% group_by(dest) %>% summarise(share = mean(topcoded))

# Price levels quoted in the report and the figure caption: the 2023 wave
# ONLY, not a mean across years.
rpp_2023 <- analysis_sample %>% filter(YEAR == 2023) %>% distinct(dest, rpp)

# "Joined an established household" = lives in a household containing MORE
# THAN ONE migration group. Note this is broader than "lives with a non-mover":
# a household holding two different mover groups also counts.
mixed_hh <- analysis_sample %>%
  group_by(hhid) %>%
  summarise(k = n_distinct(as.character(grp)), .groups = "drop") %>%
  filter(k > 1) %>%
  pull(hhid)
share_joined <- analysis_sample %>%
  filter(grp == "CA_to_TX") %>%
  summarise(s = mean(hhid %in% mixed_hh)) %>%
  pull(s)

f_sens <- log_repriced ~ grp + female + age + raceth + nativity + educ4 +
                         married + kids + famsize
pct_ca_tx <- function(dat) {
  m <- lm(f_sens, data = dat, weights = PERWT)
  100 * (exp(coef(m)[["grpCA_to_TX"]]) - 1)
}
gap_all       <- pct_ca_tx(analysis_sample)
gap_no_joined <- pct_ca_tx(
  analysis_sample %>% filter(!(hhid %in% mixed_hh & grp == "CA_to_TX"))
)

# ---------------------------------------------------------------------------
# Figure predictions: predicted ratio and 95% CI per group under both
# thresholds, at a reference profile of modal categoricals and mean continuous
# covariates.
# ---------------------------------------------------------------------------
modal <- function(x) names(which.max(table(x)))
ref <- data.frame(
  grp      = factor(levels(analysis_sample$grp), levels = levels(analysis_sample$grp)),
  female   = as.integer(modal(analysis_sample$female)),
  age      = mean(analysis_sample$age),
  raceth   = factor(modal(analysis_sample$raceth), levels = levels(analysis_sample$raceth)),
  nativity = factor(modal(analysis_sample$nativity), levels = levels(analysis_sample$nativity)),
  educ4    = factor(modal(analysis_sample$educ4), levels = levels(analysis_sample$educ4)),
  married  = as.integer(modal(analysis_sample$married)),
  kids     = as.integer(modal(analysis_sample$kids)),
  famsize  = mean(analysis_sample$famsize)
)
pred_ci <- function(f, label) {
  mdl <- lm(f, data = analysis_sample, weights = PERWT)
  X   <- model.matrix(delete.response(terms(mdl)), ref, xlev = mdl$xlevels)
  V   <- vcovCL(mdl, cluster = analysis_sample$hhid, type = "HC1")
  est <- as.vector(X %*% coef(mdl))
  se  <- sqrt(rowSums((X %*% V) * X))
  data.frame(grp = as.character(ref$grp), threshold = label,
             ratio = exp(est), lo = exp(est - 1.96 * se), hi = exp(est + 1.96 * se))
}
preds <- rbind(
  pred_ci(formulas$hh, "repriced"),
  pred_ci(formulas$hh_official, "official")
)

out <- list(
  generated_by   = "tests/export_reference.R",
  r_version      = paste(R.version$major, R.version$minor, sep = "."),
  n              = nrow(analysis_sample),
  n_households   = dplyr::n_distinct(analysis_sample$hhid),
  attrition_rows = as.integer(attrition$rows),
  group_counts   = as.list(setNames(as.integer(grp_counts$n),
                                    as.character(grp_counts$grp))),
  models         = lapply(formulas, extract),
  report_stats   = list(
    topcode_share_ca = topcode_share$share[topcode_share$dest == "CA"],
    topcode_share_tx = topcode_share$share[topcode_share$dest == "TX"],
    rpp_ca_2023      = rpp_2023$rpp[rpp_2023$dest == "CA"],
    rpp_tx_2023      = rpp_2023$rpp[rpp_2023$dest == "TX"],
    share_joined     = share_joined,
    gap_all_pct      = gap_all,
    gap_no_joined_pct = gap_no_joined
  ),
  figure_predictions = preds
)

out_path <- file.path(dirname(sub("^--file=", "", grep("^--file=",
              commandArgs(FALSE), value = TRUE)[1])), "reference_r_output.json")
if (is.na(out_path) || out_path == "") out_path <- "reference_r_output.json"

write_json(out, out_path, auto_unbox = TRUE, digits = 15, pretty = TRUE)
cat("wrote", out_path, "\n")
cat("n =", out$n, "in", out$n_households, "households\n")
cat("CA->TX repriced gap:",
    sprintf("%+.2f%%", 100 * (exp(out$models$hh$coefficients[["grp[T.CA_to_TX]"]]) - 1)), "\n")
cat("CA->TX official gap:",
    sprintf("%+.2f%%", 100 * (exp(out$models$hh_official$coefficients[["grp[T.CA_to_TX]"]]) - 1)), "\n")
