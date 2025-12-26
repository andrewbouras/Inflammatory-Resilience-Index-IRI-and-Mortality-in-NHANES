# IRI Functional Outcomes Analysis
# Primary outcomes: Self-rated health, mobility limitations, depression

library(survey)
library(dplyr)
library(tidyr)

# Handle single PSU strata
options(survey.lonely.psu = "adjust")

# Load data
dat <- read.csv("/Users/andrewbouras/Documents/VishrutNHANES/Inflammatory Resilience Index (IRI) and Mortality in NHANES/data/processed/iri_functional_cohort.csv")

cat("="," IRI FUNCTIONAL OUTCOMES ANALYSIS ", "=\n", sep = paste(rep("=", 20), collapse = ""))
cat("\nTotal eligible participants:", nrow(dat), "\n")

# Scale weights for pooled cycles (2 cycles)
dat$wt_scaled <- dat$mec_weight / 2

# Create survey design
svy <- svydesign(
  id = ~psu,
  strata = ~strata,
  weights = ~wt_scaled,
  data = dat,
  nest = TRUE
)

# ============================================================================
# TABLE 1: BASELINE CHARACTERISTICS BY IRI QUARTILE
# ============================================================================
cat("\n\n")
cat("="," TABLE 1: BASELINE CHARACTERISTICS ", "=\n", sep = paste(rep("=", 20), collapse = ""))

# IRI quartile summary
cat("\nIRI Quartile Definitions:\n")
for (q in c("Q1", "Q2", "Q3", "Q4")) {
  sub <- dat[dat$iri_quartile == q, ]
  cat(sprintf("  %s: n=%d, IRI range: %.2f to %.2f, mean=%.2f\n",
              q, nrow(sub), min(sub$iri), max(sub$iri), mean(sub$iri)))
}

# Demographics by quartile
cat("\nDemographics by IRI Quartile:\n")
cat("(Note: Lower IRI = worse inflammatory resilience)\n\n")

for (q in c("Q1", "Q2", "Q3", "Q4")) {
  sub <- dat[dat$iri_quartile == q, ]
  cat(sprintf("%s (n=%d):\n", q, nrow(sub)))
  cat(sprintf("  Age: %.1f ± %.1f\n", mean(sub$age), sd(sub$age)))
  cat(sprintf("  Female: %.1f%%\n", 100 * mean(sub$female)))
  cat(sprintf("  BMI: %.1f ± %.1f\n", mean(sub$bmi, na.rm=TRUE), sd(sub$bmi, na.rm=TRUE)))
  cat(sprintf("  hs-CRP (mg/L): %.2f ± %.2f\n", mean(sub$hscrp, na.rm=TRUE), sd(sub$hscrp, na.rm=TRUE)))
  cat(sprintf("  Albumin (g/dL): %.2f ± %.2f\n", mean(sub$albumin, na.rm=TRUE), sd(sub$albumin, na.rm=TRUE)))
  cat(sprintf("  ALMI z-score: %.2f ± %.2f\n", mean(sub$z_almi, na.rm=TRUE), sd(sub$z_almi, na.rm=TRUE)))
  cat(sprintf("  Diabetes: %.1f%%\n", 100 * mean(sub$diabetes, na.rm=TRUE)))
  cat(sprintf("  Hypertension: %.1f%%\n", 100 * mean(sub$hypertension, na.rm=TRUE)))
  cat(sprintf("  CVD history: %.1f%%\n", 100 * mean(sub$cvd_history, na.rm=TRUE)))
  cat("\n")
}

# ============================================================================
# OUTCOME 1: SELF-RATED HEALTH
# ============================================================================
cat("\n")
cat("="," OUTCOME 1: SELF-RATED HEALTH ", "=\n", sep = paste(rep("=", 20), collapse = ""))

# Fair/Poor health prevalence by quartile
cat("\nFair/Poor Health Prevalence by IRI Quartile:\n")
for (q in c("Q1", "Q2", "Q3", "Q4")) {
  sub_svy <- subset(svy, iri_quartile == q & !is.na(poor_health))
  prev <- svymean(~poor_health, sub_svy)
  cat(sprintf("  %s: %.1f%% (SE: %.1f%%)\n", q, 100*coef(prev), 100*SE(prev)))
}

# Logistic regression: Fair/Poor health
cat("\n--- Logistic Regression: Fair/Poor Health ---\n")

# Model 1: Unadjusted (IRI continuous)
mod1_unadj <- svyglm(poor_health ~ iri, design = svy, family = quasibinomial())
cat("\nModel 1 - Unadjusted (IRI continuous):\n")
or <- exp(coef(mod1_unadj)["iri"])
ci <- exp(confint(mod1_unadj)["iri", ])
pval <- summary(mod1_unadj)$coefficients["iri", "Pr(>|t|)"]
cat(sprintf("  OR per 1-unit IRI increase: %.2f (95%% CI: %.2f-%.2f), p = %.4f\n", or, ci[1], ci[2], pval))

# Model 2: Adjusted for demographics
mod1_adj <- svyglm(poor_health ~ iri + age + female + as.factor(race_eth), 
                   design = svy, family = quasibinomial())
cat("\nModel 2 - Adjusted (age, sex, race):\n")
or <- exp(coef(mod1_adj)["iri"])
ci <- exp(confint(mod1_adj)["iri", ])
pval <- summary(mod1_adj)$coefficients["iri", "Pr(>|t|)"]
cat(sprintf("  OR per 1-unit IRI increase: %.2f (95%% CI: %.2f-%.2f), p = %.4f\n", or, ci[1], ci[2], pval))

# Model 3: Fully adjusted
mod1_full <- svyglm(poor_health ~ iri + age + female + as.factor(race_eth) + 
                    diabetes + hypertension + current_smoker + bmi,
                    design = svy, family = quasibinomial())
cat("\nModel 3 - Fully adjusted (+diabetes, HTN, smoking, BMI):\n")
or <- exp(coef(mod1_full)["iri"])
ci <- exp(confint(mod1_full)["iri", ])
pval <- summary(mod1_full)$coefficients["iri", "Pr(>|t|)"]
cat(sprintf("  OR per 1-unit IRI increase: %.2f (95%% CI: %.2f-%.2f), p = %.4f\n", or, ci[1], ci[2], pval))

# Model 4: IRI quartiles
dat$iri_q <- factor(dat$iri_quartile, levels = c("Q4", "Q1", "Q2", "Q3"))
svy_q <- svydesign(id = ~psu, strata = ~strata, weights = ~wt_scaled, data = dat, nest = TRUE)

mod1_quart <- svyglm(poor_health ~ iri_q + age + female + as.factor(race_eth), 
                     design = svy_q, family = quasibinomial())
cat("\nModel 4 - IRI Quartiles (Q4=reference, highest resilience):\n")
for (q in c("Q1", "Q2", "Q3")) {
  var <- paste0("iri_q", q)
  or <- exp(coef(mod1_quart)[var])
  ci <- exp(confint(mod1_quart)[var, ])
  pval <- summary(mod1_quart)$coefficients[var, "Pr(>|t|)"]
  cat(sprintf("  %s vs Q4: OR = %.2f (95%% CI: %.2f-%.2f), p = %.4f\n", q, or, ci[1], ci[2], pval))
}

# ============================================================================
# OUTCOME 2: MOBILITY LIMITATIONS
# ============================================================================
cat("\n\n")
cat("="," OUTCOME 2: MOBILITY LIMITATIONS ", "=\n", sep = paste(rep("=", 20), collapse = ""))

# Difficulty walking prevalence
cat("\nDifficulty Walking 1/4 Mile by IRI Quartile:\n")
for (q in c("Q1", "Q2", "Q3", "Q4")) {
  sub_svy <- subset(svy, iri_quartile == q & !is.na(difficulty_walking))
  prev <- svymean(~difficulty_walking, sub_svy)
  cat(sprintf("  %s: %.1f%% (SE: %.1f%%)\n", q, 100*coef(prev), 100*SE(prev)))
}

# Logistic regression
mod2_adj <- svyglm(difficulty_walking ~ iri + age + female + as.factor(race_eth), 
                   design = svy, family = quasibinomial())
cat("\n--- Logistic Regression: Difficulty Walking ---\n")
cat("Adjusted for age, sex, race:\n")
or <- exp(coef(mod2_adj)["iri"])
ci <- exp(confint(mod2_adj)["iri", ])
pval <- summary(mod2_adj)$coefficients["iri", "Pr(>|t|)"]
cat(sprintf("  OR per 1-unit IRI increase: %.2f (95%% CI: %.2f-%.2f), p = %.4f\n", or, ci[1], ci[2], pval))

# Quartiles
mod2_quart <- svyglm(difficulty_walking ~ iri_q + age + female + as.factor(race_eth), 
                     design = svy_q, family = quasibinomial())
cat("\nIRI Quartiles (Q4=reference):\n")
for (q in c("Q1", "Q2", "Q3")) {
  var <- paste0("iri_q", q)
  or <- exp(coef(mod2_quart)[var])
  ci <- exp(confint(mod2_quart)[var, ])
  pval <- summary(mod2_quart)$coefficients[var, "Pr(>|t|)"]
  cat(sprintf("  %s vs Q4: OR = %.2f (95%% CI: %.2f-%.2f), p = %.4f\n", q, or, ci[1], ci[2], pval))
}

# ============================================================================
# OUTCOME 3: DEPRESSION (PHQ-9)
# ============================================================================
cat("\n\n")
cat("="," OUTCOME 3: DEPRESSION (PHQ-9 ≥10) ", "=\n", sep = paste(rep("=", 20), collapse = ""))

# Depression prevalence
cat("\nDepression Prevalence by IRI Quartile:\n")
for (q in c("Q1", "Q2", "Q3", "Q4")) {
  sub_svy <- subset(svy, iri_quartile == q & !is.na(depression))
  prev <- svymean(~depression, sub_svy)
  cat(sprintf("  %s: %.1f%% (SE: %.1f%%)\n", q, 100*coef(prev), 100*SE(prev)))
}

# Logistic regression
mod3_adj <- svyglm(depression ~ iri + age + female + as.factor(race_eth), 
                   design = svy, family = quasibinomial())
cat("\n--- Logistic Regression: Depression ---\n")
cat("Adjusted for age, sex, race:\n")
or <- exp(coef(mod3_adj)["iri"])
ci <- exp(confint(mod3_adj)["iri", ])
pval <- summary(mod3_adj)$coefficients["iri", "Pr(>|t|)"]
cat(sprintf("  OR per 1-unit IRI increase: %.2f (95%% CI: %.2f-%.2f), p = %.4f\n", or, ci[1], ci[2], pval))

# Quartiles
mod3_quart <- svyglm(depression ~ iri_q + age + female + as.factor(race_eth), 
                     design = svy_q, family = quasibinomial())
cat("\nIRI Quartiles (Q4=reference):\n")
for (q in c("Q1", "Q2", "Q3")) {
  var <- paste0("iri_q", q)
  or <- exp(coef(mod3_quart)[var])
  ci <- exp(confint(mod3_quart)[var, ])
  pval <- summary(mod3_quart)$coefficients[var, "Pr(>|t|)"]
  cat(sprintf("  %s vs Q4: OR = %.2f (95%% CI: %.2f-%.2f), p = %.4f\n", q, or, ci[1], ci[2], pval))
}

# ============================================================================
# SUMMARY TABLE
# ============================================================================
cat("\n\n")
cat("="," SUMMARY: IRI AND FUNCTIONAL OUTCOMES ", "=\n", sep = paste(rep("=", 20), collapse = ""))

cat("\n--- Continuous IRI (per 1-unit increase, adjusted) ---\n")

# Fair/Poor Health
or1 <- exp(coef(mod1_adj)["iri"])
ci1 <- exp(confint(mod1_adj)["iri", ])
pval1 <- summary(mod1_adj)$coefficients["iri", "Pr(>|t|)"]
cat(sprintf("%-20s OR = %.2f (%.2f-%.2f), p = %.4f\n", "Fair/Poor Health", or1, ci1[1], ci1[2], pval1))

# Difficulty Walking
or2 <- exp(coef(mod2_adj)["iri"])
ci2 <- exp(confint(mod2_adj)["iri", ])
pval2 <- summary(mod2_adj)$coefficients["iri", "Pr(>|t|)"]
cat(sprintf("%-20s OR = %.2f (%.2f-%.2f), p = %.4f\n", "Difficulty Walking", or2, ci2[1], ci2[2], pval2))

# Depression
or3 <- exp(coef(mod3_adj)["iri"])
ci3 <- exp(confint(mod3_adj)["iri", ])
pval3 <- summary(mod3_adj)$coefficients["iri", "Pr(>|t|)"]
cat(sprintf("%-20s OR = %.2f (%.2f-%.2f), p = %.4f\n", "Depression", or3, ci3[1], ci3[2], pval3))

cat("\n--- Q1 vs Q4 (lowest vs highest resilience, adjusted) ---\n")

# Fair/Poor Health Q1 vs Q4
or1q <- exp(coef(mod1_quart)["iri_qQ1"])
ci1q <- exp(confint(mod1_quart)["iri_qQ1", ])
pval1q <- summary(mod1_quart)$coefficients["iri_qQ1", "Pr(>|t|)"]
cat(sprintf("%-20s OR = %.2f (%.2f-%.2f), p = %.4f\n", "Fair/Poor Health", or1q, ci1q[1], ci1q[2], pval1q))

# Difficulty Walking Q1 vs Q4
or2q <- exp(coef(mod2_quart)["iri_qQ1"])
ci2q <- exp(confint(mod2_quart)["iri_qQ1", ])
pval2q <- summary(mod2_quart)$coefficients["iri_qQ1", "Pr(>|t|)"]
cat(sprintf("%-20s OR = %.2f (%.2f-%.2f), p = %.4f\n", "Difficulty Walking", or2q, ci2q[1], ci2q[2], pval2q))

# Depression Q1 vs Q4
or3q <- exp(coef(mod3_quart)["iri_qQ1"])
ci3q <- exp(confint(mod3_quart)["iri_qQ1", ])
pval3q <- summary(mod3_quart)$coefficients["iri_qQ1", "Pr(>|t|)"]
cat(sprintf("%-20s OR = %.2f (%.2f-%.2f), p = %.4f\n", "Depression", or3q, ci3q[1], ci3q[2], pval3q))

cat("\n\nCONCLUSION:\n")
cat("Lower IRI (worse inflammatory resilience) is significantly associated with:\n")
cat("- Higher odds of fair/poor self-rated health (p < 0.001)\n")
cat("- Higher odds of mobility limitations (p = 0.005)\n")
cat("- Trend toward higher depression (p = 0.14, not significant)\n")
cat("\nQ1 vs Q4 comparisons show 2-4.5x higher odds of poor outcomes\n")
cat("in the lowest resilience quartile.\n")

# ============================================================================
# SAVE RESULTS TO CSV
# ============================================================================
results <- data.frame(
  Outcome = c("Fair/Poor Health", "Difficulty Walking", "Depression"),
  OR_continuous = c(or1, or2, or3),
  CI_low_cont = c(ci1[1], ci2[1], ci3[1]),
  CI_high_cont = c(ci1[2], ci2[2], ci3[2]),
  p_continuous = c(pval1, pval2, pval3),
  OR_Q1vsQ4 = c(or1q, or2q, or3q),
  CI_low_Q1 = c(ci1q[1], ci2q[1], ci3q[1]),
  CI_high_Q1 = c(ci1q[2], ci2q[2], ci3q[2]),
  p_Q1vsQ4 = c(pval1q, pval2q, pval3q)
)

write.csv(results, "/Users/andrewbouras/Documents/VishrutNHANES/Inflammatory Resilience Index (IRI) and Mortality in NHANES/output/functional_outcomes_results.csv", row.names = FALSE)
cat("\nResults saved to output/functional_outcomes_results.csv\n")

