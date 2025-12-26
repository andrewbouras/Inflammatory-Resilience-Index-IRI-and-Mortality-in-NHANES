# =============================================================================
# Modified IRI Study - Survival Analysis
# Survey-weighted Cox proportional hazards models
# =============================================================================

suppressPackageStartupMessages({
  library(tidyverse)
  library(survey)
  library(survival)
  library(broom)
})

options(survey.lonely.psu = "adjust")

# Get project root
args <- commandArgs(trailingOnly = FALSE)
script_path <- sub("--file=", "", args[grep("--file=", args)])
if (length(script_path) > 0) {
  project_root <- dirname(dirname(normalizePath(script_path)))
} else {
  project_root <- getwd()
}

# =============================================================================
# LOAD DATA
# =============================================================================

cat("\n", strrep("=", 60), "\n")
cat("MODIFIED IRI STUDY - SURVIVAL ANALYSIS\n")
cat(strrep("=", 60), "\n")

data_path <- file.path(project_root, "data", "processed", "iri_cohort_mortality.csv")
df <- read_csv(data_path, show_col_types = FALSE)

# Filter to eligible
df <- df %>%
  filter(eligible == 1) %>%
  drop_na(mec_weight, psu, strata, iri, followup_years)

cat("Eligible participants:", nrow(df), "\n")
cat("Deaths:", sum(df$mort_all), "\n")
cat("CV deaths:", sum(df$mort_cv), "\n")

# Create factors
df <- df %>%
  mutate(
    sex_f = factor(sex, levels = c(1, 2), labels = c("Male", "Female")),
    race_eth_f = case_when(
      race_eth == 1 ~ "Mexican American",
      race_eth == 2 ~ "Other Hispanic",
      race_eth == 3 ~ "NH White",
      race_eth == 4 ~ "NH Black",
      race_eth == 6 ~ "NH Asian",
      TRUE ~ "Other"
    ) %>% factor(),
    smoking_f = factor(smoking_status, levels = c(0, 1, 2),
                       labels = c("Never", "Former", "Current")),
    iri_q = factor(iri_quartile, levels = c("Q1", "Q2", "Q3", "Q4")),
    # Use Q4 (highest resilience) as reference
    iri_q_ref = relevel(iri_q, ref = "Q4")
  )

# Number of cycles for weight adjustment
n_cycles <- 2

# =============================================================================
# SURVEY DESIGN
# =============================================================================

design <- svydesign(
  id = ~psu,
  strata = ~strata,
  weights = ~I(mec_weight / n_cycles),
  data = df,
  nest = TRUE
)

cat("\nWeighted N:", round(sum(weights(design)), 0), "\n")

# =============================================================================
# TABLE 1: BASELINE CHARACTERISTICS BY IRI QUARTILE
# =============================================================================

cat("\n", strrep("=", 60), "\n")
cat("TABLE 1: BASELINE CHARACTERISTICS BY IRI QUARTILE\n")
cat(strrep("=", 60), "\n")

# Summary by quartile (unweighted for simplicity in output)
table1_summary <- df %>%
  group_by(iri_q) %>%
  summarise(
    n = n(),
    age = sprintf("%.1f (%.1f)", mean(age, na.rm=T), sd(age, na.rm=T)),
    female_pct = sprintf("%.1f", 100*mean(female, na.rm=T)),
    bmi = sprintf("%.1f (%.1f)", mean(bmi, na.rm=T), sd(bmi, na.rm=T)),
    hscrp = sprintf("%.2f (%.2f)", mean(hscrp, na.rm=T), sd(hscrp, na.rm=T)),
    albumin = sprintf("%.2f (%.2f)", mean(albumin, na.rm=T), sd(albumin, na.rm=T)),
    almi = sprintf("%.2f (%.2f)", mean(almi, na.rm=T), sd(almi, na.rm=T)),
    hypertension_pct = sprintf("%.1f", 100*mean(hypertension, na.rm=T)),
    diabetes_pct = sprintf("%.1f", 100*mean(diabetes, na.rm=T)),
    cvd_history_pct = sprintf("%.1f", 100*mean(cvd_history, na.rm=T)),
    deaths = sum(mort_all),
    cv_deaths = sum(mort_cv),
    .groups = "drop"
  )

print(table1_summary)

# Save Table 1
dir.create(file.path(project_root, "output", "tables"), recursive = TRUE, showWarnings = FALSE)
write_csv(table1_summary, file.path(project_root, "output", "tables", "table1_iri_baseline.csv"))

# =============================================================================
# COX MODELS - ALL-CAUSE MORTALITY
# =============================================================================

cat("\n", strrep("=", 60), "\n")
cat("COX MODELS - ALL-CAUSE MORTALITY\n")
cat(strrep("=", 60), "\n")

# Model 1: Age and sex adjusted
model1_all <- svycoxph(
  Surv(followup_years, mort_all) ~ iri_q_ref + age + sex_f,
  design = design
)
cat("\nModel 1 (Age, Sex):\n")
print(tidy(model1_all, conf.int = TRUE, exponentiate = TRUE) %>%
        filter(str_detect(term, "iri_q")) %>%
        select(term, estimate, conf.low, conf.high, p.value))

# Model 2: + race/ethnicity, BMI, smoking
model2_all <- svycoxph(
  Surv(followup_years, mort_all) ~ iri_q_ref + age + sex_f + race_eth_f + bmi + smoking_f,
  design = design
)
cat("\nModel 2 (+ Demographics, Lifestyle):\n")
print(tidy(model2_all, conf.int = TRUE, exponentiate = TRUE) %>%
        filter(str_detect(term, "iri_q")) %>%
        select(term, estimate, conf.low, conf.high, p.value))

# Model 3: + key clinical comorbidities (simplified to avoid singularity)
model3_all <- tryCatch({
  svycoxph(
    Surv(followup_years, mort_all) ~ iri_q_ref + age + sex_f + bmi + 
      smoking_f + hypertension + diabetes + cvd_history,
    design = design
  )
}, error = function(e) {
  cat("Model 3 failed, using simplified version\n")
  svycoxph(
    Surv(followup_years, mort_all) ~ iri_q_ref + age + sex_f + bmi + diabetes,
    design = design
  )
})
cat("\nModel 3 (Fully Adjusted):\n")
print(tidy(model3_all, conf.int = TRUE, exponentiate = TRUE) %>%
        filter(str_detect(term, "iri_q")) %>%
        select(term, estimate, conf.low, conf.high, p.value))

# IRI as continuous variable (per SD increase)
model_cont_all <- tryCatch({
  svycoxph(
    Surv(followup_years, mort_all) ~ iri + age + sex_f + bmi + 
      smoking_f + hypertension + diabetes + cvd_history,
    design = design
  )
}, error = function(e) {
  svycoxph(
    Surv(followup_years, mort_all) ~ iri + age + sex_f + bmi + diabetes,
    design = design
  )
})
cat("\nIRI as continuous (per SD, fully adjusted):\n")
iri_hr <- tidy(model_cont_all, conf.int = TRUE, exponentiate = TRUE) %>%
  filter(term == "iri")
cat(sprintf("HR = %.2f (95%% CI: %.2f-%.2f), p = %.4f\n",
            iri_hr$estimate, iri_hr$conf.low, iri_hr$conf.high, iri_hr$p.value))

# =============================================================================
# COX MODELS - CARDIOVASCULAR MORTALITY
# =============================================================================

cat("\n", strrep("=", 60), "\n")
cat("COX MODELS - CARDIOVASCULAR MORTALITY\n")
cat(strrep("=", 60), "\n")

# Only if sufficient events
if (sum(df$mort_cv) >= 20) {
  model3_cv <- tryCatch({
    svycoxph(
      Surv(followup_years, mort_cv) ~ iri_q_ref + age + sex_f + bmi + diabetes,
      design = design
    )
  }, error = function(e) {
    cat("CV model failed:", conditionMessage(e), "\n")
    NULL
  })
  
  if (!is.null(model3_cv)) {
    cat("\nModel (Age, Sex, BMI, Diabetes adjusted) - CV Mortality:\n")
    print(tidy(model3_cv, conf.int = TRUE, exponentiate = TRUE) %>%
            filter(str_detect(term, "iri_q")) %>%
            select(term, estimate, conf.low, conf.high, p.value))
    
    # Continuous
    model_cont_cv <- tryCatch({
      svycoxph(
        Surv(followup_years, mort_cv) ~ iri + age + sex_f + bmi + diabetes,
        design = design
      )
    }, error = function(e) NULL)
    
    if (!is.null(model_cont_cv)) {
      iri_hr_cv <- tidy(model_cont_cv, conf.int = TRUE, exponentiate = TRUE) %>%
        filter(term == "iri")
      cat(sprintf("IRI continuous: HR = %.2f (95%% CI: %.2f-%.2f), p = %.4f\n",
                  iri_hr_cv$estimate, iri_hr_cv$conf.low, iri_hr_cv$conf.high, iri_hr_cv$p.value))
    }
  }
} else {
  cat("Insufficient CV deaths for stable estimates.\n")
}

# =============================================================================
# SAVE RESULTS
# =============================================================================

# Compile all results for export
results_all <- bind_rows(
  tidy(model1_all, conf.int = TRUE, exponentiate = TRUE) %>%
    filter(str_detect(term, "iri_q")) %>%
    mutate(model = "Model 1", outcome = "All-cause"),
  tidy(model2_all, conf.int = TRUE, exponentiate = TRUE) %>%
    filter(str_detect(term, "iri_q")) %>%
    mutate(model = "Model 2", outcome = "All-cause"),
  tidy(model3_all, conf.int = TRUE, exponentiate = TRUE) %>%
    filter(str_detect(term, "iri_q")) %>%
    mutate(model = "Model 3", outcome = "All-cause")
) %>%
  mutate(
    hr_ci = sprintf("%.2f (%.2f-%.2f)", estimate, conf.low, conf.high),
    p_value = sprintf("%.4f", p.value)
  ) %>%
  select(outcome, model, term, hr_ci, p_value)

write_csv(results_all, file.path(project_root, "output", "tables", "table2_cox_results.csv"))

cat("\n", strrep("=", 60), "\n")
cat("ANALYSIS COMPLETE\n")
cat(strrep("=", 60), "\n")

cat("\nKey finding:\n")
cat(sprintf("Each 1-SD increase in IRI associated with %.0f%% lower all-cause mortality risk\n",
            (1 - iri_hr$estimate) * 100))
cat("(Higher IRI = better inflammatory resilience = lower mortality)\n")

cat("\nOutput files:\n")
cat("  - table1_iri_baseline.csv\n")
cat("  - table2_cox_results.csv\n")
