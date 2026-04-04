################################################################################
# IRI Validation Study - Mortality Analysis
# Survey-weighted Cox Proportional Hazards Models
# NHANES 1999-2006 with mortality follow-up through 2019
################################################################################

library(tidyverse)
library(survey)
library(survival)
library(broom)

options(survey.lonely.psu = "adjust")

# Project paths
project_root <- normalizePath(file.path(dirname(sys.frame(1)$ofile %||% "."), ".."), mustWork = FALSE)
if (!dir.exists(project_root)) {
  project_root <- normalizePath(file.path(getwd(), ".."), mustWork = FALSE)
}

data_processed <- file.path(project_root, "data", "processed")
output_dir <- file.path(project_root, "output")
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

cat("============================================================\n")
cat("IRI VALIDATION STUDY - MORTALITY ANALYSIS\n")
cat("============================================================\n\n")

# Load validation cohort
df <- read.csv(file.path(data_processed, "iri_validation_cohort.csv"))
cat("Loaded", nrow(df), "participants\n")

# Filter to eligible
eligible <- df %>% filter(eligible == 1)
cat("Eligible for analysis:", nrow(eligible), "\n\n")

# Create age groups for stratification
eligible <- eligible %>%
    mutate(
        age_group = cut(RIDAGEYR,
            breaks = c(20, 40, 60, 80, Inf),
            labels = c("20-39", "40-59", "60-79", "80+"),
            right = FALSE
        ),
        iri_quartile = factor(iri_quartile,
            levels = c("Q4 (highest)", "Q3", "Q2", "Q1 (lowest)")
        ),
        sex_cat = factor(RIAGENDR, levels = c(1, 2), labels = c("Male", "Female"))
    )

# Recode IRI quartile for reference group = Q4 (highest)
eligible$iri_q4_ref <- relevel(eligible$iri_quartile, ref = "Q4 (highest)")

################################################################################
# SURVEY DESIGN
################################################################################

cat("Setting up survey design...\n")

# For NHANES 1999-2006, need to handle different weight names
# Using WTMEC2YR or weight_mec from the processed data

# Check available weight column
if ("weight_mec" %in% names(eligible)) {
    weight_col <- "weight_mec"
} else if ("WTMEC2YR" %in% names(eligible)) {
    weight_col <- "WTMEC2YR"
} else {
    weight_col <- NA
}

# Check for PSU and strata
# NHANES 1999-2006 = 4 two-year cycles; divide weights by n_cycles
n_cycles <- 4

if ("SDMVPSU" %in% names(eligible) && "SDMVSTRA" %in% names(eligible)) {
    eligible$wt_scaled <- eligible[[weight_col]] / n_cycles
    # Full survey design
    design <- svydesign(
        ids = ~SDMVPSU,
        strata = ~SDMVSTRA,
        weights = ~wt_scaled,
        nest = TRUE,
        data = eligible
    )
    cat("Using full survey design with PSU, strata, and weights (scaled by 1/", n_cycles, ")\n")
} else {
    cat("ERROR: PSU/strata columns missing. Cannot create proper survey design.\n")
    stop("Survey design variables (SDMVPSU, SDMVSTRA) are required for NHANES analysis.")
}

################################################################################
# DESCRIPTIVE STATISTICS
################################################################################

cat("\n============================================================\n")
cat("DESCRIPTIVE STATISTICS BY IRI QUARTILE\n")
cat("============================================================\n\n")

# Basic counts
quartile_summary <- eligible %>%
    group_by(iri_quartile) %>%
    summarise(
        N = n(),
        Deaths = sum(mort_all, na.rm = TRUE),
        CV_Deaths = sum(mort_cv, na.rm = TRUE),
        Mortality_Rate = mean(mort_all, na.rm = TRUE) * 100,
        CV_Mortality_Rate = mean(mort_cv, na.rm = TRUE) * 100,
        Mean_Followup = mean(followup_years, na.rm = TRUE),
        .groups = "drop"
    ) %>%
    arrange(desc(iri_quartile))

print(quartile_summary)

################################################################################
# COX PROPORTIONAL HAZARDS - ALL-CAUSE MORTALITY
################################################################################

cat("\n============================================================\n")
cat("COX REGRESSION: ALL-CAUSE MORTALITY\n")
cat("============================================================\n\n")

# Model 1: Age and sex adjusted
cat("Model 1: Age + Sex adjusted\n")
model1_all <- svycoxph(
    Surv(followup_years, mort_all) ~ iri_q4_ref + RIDAGEYR + RIAGENDR,
    design = design
)
print(summary(model1_all))

# Extract HRs for Model 1
hr_model1_all <- broom::tidy(model1_all, exponentiate = TRUE, conf.int = TRUE) %>%
    filter(grepl("iri_q4_ref", term)) %>%
    select(term, estimate, conf.low, conf.high, p.value) %>%
    mutate(
        outcome = "All-cause mortality",
        model = "Age + Sex adjusted",
        quartile = gsub("iri_q4_ref", "", term)
    )

print(hr_model1_all)

# Model 2: Fully adjusted (if variables available)
available_covariates <- c()
if ("race_eth" %in% names(eligible)) {
    eligible$race_eth_f <- as.factor(eligible$race_eth)
    available_covariates <- c(available_covariates, "race_eth_f")
}
if ("bmi" %in% names(eligible)) available_covariates <- c(available_covariates, "bmi")
if ("diabetes" %in% names(eligible)) available_covariates <- c(available_covariates, "diabetes")
if ("hypertension" %in% names(eligible)) available_covariates <- c(available_covariates, "hypertension")
if ("current_smoker" %in% names(eligible)) available_covariates <- c(available_covariates, "current_smoker")

if (length(available_covariates) > 0) {
    cat("\nModel 2: Fully adjusted (Age + Sex + ", paste(available_covariates, collapse = " + "), ")\n")

    formula_full <- as.formula(paste(
        "Surv(followup_years, mort_all) ~ iri_q4_ref + RIDAGEYR + RIAGENDR +",
        paste(available_covariates, collapse = " + ")
    ))

    model2_all <- svycoxph(formula_full, design = design)

    hr_model2_all <- broom::tidy(model2_all, exponentiate = TRUE, conf.int = TRUE) %>%
        filter(grepl("iri_q4_ref", term)) %>%
        select(term, estimate, conf.low, conf.high, p.value) %>%
        mutate(
            outcome = "All-cause mortality",
            model = "Fully adjusted",
            quartile = gsub("iri_q4_ref", "", term)
        )

    print(hr_model2_all)
}

################################################################################
# COX PROPORTIONAL HAZARDS - CARDIOVASCULAR MORTALITY
################################################################################

cat("\n============================================================\n")
cat("COX REGRESSION: CARDIOVASCULAR MORTALITY\n")
cat("============================================================\n\n")

# Model 1: Age and sex adjusted
cat("Model 1: Age + Sex adjusted\n")
model1_cv <- svycoxph(
    Surv(followup_years, mort_cv) ~ iri_q4_ref + RIDAGEYR + RIAGENDR,
    design = design
)
print(summary(model1_cv))

hr_model1_cv <- broom::tidy(model1_cv, exponentiate = TRUE, conf.int = TRUE) %>%
    filter(grepl("iri_q4_ref", term)) %>%
    select(term, estimate, conf.low, conf.high, p.value) %>%
    mutate(
        outcome = "CV mortality",
        model = "Age + Sex adjusted",
        quartile = gsub("iri_q4_ref", "", term)
    )

print(hr_model1_cv)

# Fully adjusted CV mortality
if (length(available_covariates) > 0) {
    cat("\nModel 2: Fully adjusted\n")

    formula_full_cv <- as.formula(paste(
        "Surv(followup_years, mort_cv) ~ iri_q4_ref + RIDAGEYR + RIAGENDR +",
        paste(available_covariates, collapse = " + ")
    ))

    model2_cv <- svycoxph(formula_full_cv, design = design)

    hr_model2_cv <- broom::tidy(model2_cv, exponentiate = TRUE, conf.int = TRUE) %>%
        filter(grepl("iri_q4_ref", term)) %>%
        select(term, estimate, conf.low, conf.high, p.value) %>%
        mutate(
            outcome = "CV mortality",
            model = "Fully adjusted",
            quartile = gsub("iri_q4_ref", "", term)
        )

    print(hr_model2_cv)
}

################################################################################
# CONTINUOUS IRI ANALYSIS
################################################################################

cat("\n============================================================\n")
cat("CONTINUOUS IRI ANALYSIS (per 1-unit increase)\n")
cat("============================================================\n\n")

# All-cause mortality - continuous IRI
model_cont_all <- svycoxph(
    Surv(followup_years, mort_all) ~ iri + RIDAGEYR + RIAGENDR,
    design = design
)

hr_cont_all <- broom::tidy(model_cont_all, exponentiate = TRUE, conf.int = TRUE) %>%
    filter(term == "iri")

cat("All-cause mortality per 1-unit IRI increase:\n")
cat(sprintf(
    "  HR: %.3f (95%% CI: %.3f - %.3f), p = %.4f\n",
    hr_cont_all$estimate, hr_cont_all$conf.low, hr_cont_all$conf.high, hr_cont_all$p.value
))

# CV mortality - continuous IRI
model_cont_cv <- svycoxph(
    Surv(followup_years, mort_cv) ~ iri + RIDAGEYR + RIAGENDR,
    design = design
)

hr_cont_cv <- broom::tidy(model_cont_cv, exponentiate = TRUE, conf.int = TRUE) %>%
    filter(term == "iri")

cat("CV mortality per 1-unit IRI increase:\n")
cat(sprintf(
    "  HR: %.3f (95%% CI: %.3f - %.3f), p = %.4f\n",
    hr_cont_cv$estimate, hr_cont_cv$conf.low, hr_cont_cv$conf.high, hr_cont_cv$p.value
))

################################################################################
# COMBINE ALL RESULTS
################################################################################

cat("\n============================================================\n")
cat("COMBINED RESULTS TABLE\n")
cat("============================================================\n\n")

# Combine all HR results
all_results <- bind_rows(
    hr_model1_all,
    hr_model1_cv
)

if (exists("hr_model2_all")) {
    all_results <- bind_rows(all_results, hr_model2_all)
}
if (exists("hr_model2_cv")) {
    all_results <- bind_rows(all_results, hr_model2_cv)
}

# Format for output
results_table <- all_results %>%
    mutate(
        HR_CI = sprintf("%.2f (%.2f - %.2f)", estimate, conf.low, conf.high),
        P = case_when(
            p.value < 0.001 ~ "<0.001",
            TRUE ~ sprintf("%.3f", p.value)
        )
    ) %>%
    select(outcome, model, quartile, HR_CI, P)

print(results_table)

# Save results
write.csv(results_table, file.path(output_dir, "validation_mortality_results.csv"), row.names = FALSE)
cat("\nSaved: validation_mortality_results.csv\n")

################################################################################
# SUMMARY FOR MANUSCRIPT
################################################################################

cat("\n============================================================\n")
cat("MANUSCRIPT SUMMARY\n")
cat("============================================================\n\n")

cat("VALIDATION COHORT RESULTS (NHANES 1999-2006)\n\n")
cat(sprintf("N = %d eligible participants\n", nrow(eligible)))
cat(sprintf(
    "All-cause deaths: %d (%.1f%%)\n",
    sum(eligible$mort_all, na.rm = TRUE),
    100 * mean(eligible$mort_all, na.rm = TRUE)
))
cat(sprintf(
    "CV deaths: %d (%.1f%%)\n",
    sum(eligible$mort_cv, na.rm = TRUE),
    100 * mean(eligible$mort_cv, na.rm = TRUE)
))
cat(sprintf("Mean follow-up: %.1f years\n\n", mean(eligible$followup_years, na.rm = TRUE)))

cat("All-cause mortality by IRI quartile (age/sex adjusted):\n")
print(hr_model1_all[, c("quartile", "estimate", "conf.low", "conf.high", "p.value")])

cat("\nCV mortality by IRI quartile (age/sex adjusted):\n")
print(hr_model1_cv[, c("quartile", "estimate", "conf.low", "conf.high", "p.value")])

cat("\n\nKEY FINDING: Lowest IRI quartile (Q1) vs highest (Q4):\n")
q1_all <- hr_model1_all %>% filter(grepl("Q1", quartile))
q1_cv <- hr_model1_cv %>% filter(grepl("Q1", quartile))

if (nrow(q1_all) > 0) {
    cat(sprintf(
        "  All-cause mortality: HR = %.2f (95%% CI: %.2f - %.2f)\n",
        q1_all$estimate, q1_all$conf.low, q1_all$conf.high
    ))
}
if (nrow(q1_cv) > 0) {
    cat(sprintf(
        "  CV mortality: HR = %.2f (95%% CI: %.2f - %.2f)\n",
        q1_cv$estimate, q1_cv$conf.low, q1_cv$conf.high
    ))
}

cat("\n============================================================\n")
cat("ANALYSIS COMPLETE\n")
cat("============================================================\n")
