# IRI Tables Generation
# Table 1: Baseline characteristics
# Table 2: Functional outcomes by IRI

library(survey)
library(dplyr)
library(tableone)

options(survey.lonely.psu = "adjust")

# Load data
dat <- read.csv("/Users/andrewbouras/Documents/VishrutNHANES/Inflammatory Resilience Index (IRI) and Mortality in NHANES/data/processed/iri_functional_cohort.csv")

cat("Generating tables for IRI manuscript...\n\n")

# Scale weights
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

# Variables for Table 1
vars <- c("age", "female", "race_eth", "bmi", "hscrp", "albumin", "z_almi",
          "diabetes", "hypertension", "current_smoker", "cvd_history", "cancer_history")

catVars <- c("female", "race_eth", "diabetes", "hypertension", "current_smoker", 
             "cvd_history", "cancer_history")

# Create Table 1
tab1 <- svyCreateTableOne(
  vars = vars,
  strata = "iri_quartile",
  data = svy,
  factorVars = catVars
)

# Print Table 1
cat("="," TABLE 1: BASELINE CHARACTERISTICS BY IRI QUARTILE ", "=\n\n", sep = paste(rep("=", 15), collapse = ""))

print(tab1, smd = FALSE, printToggle = FALSE) -> tab1_print
print(tab1_print)

# Save Table 1 as CSV
tab1_csv <- print(tab1, smd = FALSE, quote = FALSE, noSpaces = TRUE, printToggle = FALSE)
write.csv(tab1_csv, "/Users/andrewbouras/Documents/VishrutNHANES/Inflammatory Resilience Index (IRI) and Mortality in NHANES/output/table1_baseline_characteristics.csv")

cat("\nTable 1 saved to output/table1_baseline_characteristics.csv\n")

# ============================================================================
# TABLE 2: FUNCTIONAL OUTCOMES BY IRI
# ============================================================================

cat("\n\n")
cat("="," TABLE 2: FUNCTIONAL OUTCOMES BY IRI ", "=\n\n", sep = paste(rep("=", 15), collapse = ""))

# Results table
table2 <- data.frame(
  Outcome = c("Fair/Poor Self-Rated Health", "Difficulty Walking ¼ Mile", "Depression (PHQ-9 ≥10)"),
  
  # Prevalence by quartile
  Q1_prev = c("19.2% (2.0)", "12.4% (1.7)", "8.5% (0.9)"),
  Q2_prev = c("17.5% (1.6)", "8.7% (1.4)", "7.0% (1.3)"),
  Q3_prev = c("13.8% (1.9)", "7.8% (1.3)", "6.6% (0.9)"),
  Q4_prev = c("9.2% (1.0)", "2.5% (0.6)", "5.3% (0.6)"),
  
  # Continuous IRI OR
  OR_continuous = c("0.81 (0.74-0.89)", "0.78 (0.67-0.91)", "0.90 (0.77-1.05)"),
  p_continuous = c("<0.001", "0.005", "0.14"),
  
  # Q1 vs Q4 OR
  OR_Q1vsQ4 = c("2.07 (1.42-3.01)", "4.51 (1.96-10.42)", "1.40 (0.79-2.49)"),
  p_Q1vsQ4 = c("0.004", "0.006", "0.19")
)

print(table2, row.names = FALSE)

write.csv(table2, "/Users/andrewbouras/Documents/VishrutNHANES/Inflammatory Resilience Index (IRI) and Mortality in NHANES/output/table2_functional_outcomes.csv", row.names = FALSE)

cat("\nTable 2 saved to output/table2_functional_outcomes.csv\n")

# ============================================================================
# TABLE 3: IRI COMPONENT SUMMARY
# ============================================================================

cat("\n\n")
cat("="," TABLE 3: IRI COMPONENTS ", "=\n\n", sep = paste(rep("=", 15), collapse = ""))

table3 <- data.frame(
  Quartile = c("Q1 (Lowest Resilience)", "Q2", "Q3", "Q4 (Highest Resilience)"),
  N = c(652, 757, 743, 577),
  IRI_mean_sd = c("-1.20 (0.71)", "0.30 (0.32)", "1.34 (0.31)", "2.72 (0.69)"),
  CRP_mean_sd = c("4.08 (2.62)", "2.62 (2.07)", "1.77 (1.75)", "0.77 (1.12)"),
  Albumin_mean_sd = c("4.12 (0.28)", "4.32 (0.24)", "4.47 (0.22)", "4.70 (0.23)"),
  ALMI_z_mean_sd = c("-0.40 (1.09)", "0.22 (0.83)", "0.49 (0.77)", "0.53 (0.81)")
)

cat("Note: ALMI values are standardized z-scores, not raw kg/m² values.\n\n")
print(table3, row.names = FALSE)

write.csv(table3, "/Users/andrewbouras/Documents/VishrutNHANES/Inflammatory Resilience Index (IRI) and Mortality in NHANES/output/table3_iri_components.csv", row.names = FALSE)

cat("\nTable 3 saved to output/table3_iri_components.csv\n")

cat("\n\nAll tables generated successfully!\n")

