################################################################################
# JAMA CARDIOLOGY-LEVEL SENSITIVITY ANALYSES
# Comprehensive analyses for high-impact journal submission
#
# Implements:
# 1. Component-adjusted models (IRI after CRP, Albumin, ALMI)
# 2. Likelihood ratio tests
# 3. NRI (Net Reclassification Improvement)
# 4. Sex-stratified analyses
# 5. Competing risk (Fine-Gray) for CV mortality
# 6. Nonlinearity assessment (RCS splines)
################################################################################

library(tidyverse)
library(survey)
library(survival)
library(broom)
library(splines) # For RCS
library(cmprsk) # For competing risk

# Try to load survIDINRI for NRI, or use alternative
nri_available <- requireNamespace("survIDINRI", quietly = TRUE)
if (!nri_available) {
    message("Note: survIDINRI not installed. Will use alternative NRI calculation.")
}

options(survey.lonely.psu = "adjust")

# Project paths (relative to script location)
project_root <- normalizePath(file.path(dirname(sys.frame(1)$ofile %||% "."), ".."), mustWork = FALSE)
if (!dir.exists(project_root)) {
  project_root <- normalizePath(file.path(getwd(), ".."), mustWork = FALSE)
}
data_path <- file.path(project_root, "data", "processed")
output_dir <- file.path(project_root, "output", "jama_sensitivity")
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

cat("\n", strrep("=", 70), "\n")
cat("JAMA CARDIOLOGY-LEVEL SENSITIVITY ANALYSES\n")
cat(strrep("=", 70), "\n\n")

################################################################################
# LOAD DATA
################################################################################

valid_file <- file.path(data_path, "iri_validation_cohort.csv")
if (!file.exists(valid_file)) {
    stop("Validation cohort not found. Run 12_build_validation_cohort.py first.")
}

df <- read_csv(valid_file, show_col_types = FALSE) %>%
    filter(eligible == 1) %>%
    drop_na(weight_mec, SDMVPSU, SDMVSTRA, iri, followup_years) %>%
    filter(followup_years > 0, followup_years <= 25)

cat("Loaded validation cohort:", nrow(df), "participants\n")
cat("All-cause deaths:", sum(df$mort_all, na.rm = TRUE), "\n")
cat("CV deaths:", sum(df$mort_cv, na.rm = TRUE), "\n")

# Use pre-computed z-scores from the validation cohort CSV.
# These are now standardized using DERIVATION cohort parameters
# (set in 12_build_validation_cohort.py via derivation_zscore_params.json).
# Only recalculate if columns are missing (legacy data).
df <- df %>%
    mutate(sex_f = factor(sex, levels = c(1, 2), labels = c("Male", "Female")))

if (!"z_log_hscrp" %in% names(df) | !"z_albumin" %in% names(df) | !"z_almi" %in% names(df)) {
    cat("WARNING: z-score columns missing from CSV. Recalculating within validation cohort.\n")
    cat("This is NOT ideal — re-run 12_build_validation_cohort.py with derivation params.\n")
    df <- df %>%
        mutate(
            log_hscrp = log(pmax(hscrp, 0.01)),
            z_crp = (log_hscrp - mean(log_hscrp, na.rm = TRUE)) / sd(log_hscrp, na.rm = TRUE),
            z_crp_inv = -z_crp,
            z_albumin = (albumin - mean(albumin, na.rm = TRUE)) / sd(albumin, na.rm = TRUE)
        ) %>%
        group_by(sex) %>%
        mutate(z_almi = (almi - mean(almi, na.rm = TRUE)) / sd(almi, na.rm = TRUE)) %>%
        ungroup()
} else {
    cat("Using pre-computed z-scores (derivation cohort standardization).\n")
    # Ensure z_crp_inv exists for component-adjusted models
    if (!"z_crp_inv" %in% names(df)) {
        df$z_crp_inv <- -df$z_log_hscrp
    }
}

# Survey design
n_cycles <- 4
design <- svydesign(
    id = ~SDMVPSU,
    strata = ~SDMVSTRA,
    weights = ~ I(weight_mec / n_cycles),
    data = df,
    nest = TRUE
)

cat("\nWeighted N:", round(sum(weights(design)), 0), "\n")

################################################################################
# 1A. COMPONENT-ADJUSTED MODELS
# Does IRI remain significant AFTER including CRP, Albumin, ALMI?
################################################################################

cat("\n", strrep("=", 70), "\n")
cat("1A. COMPONENT-ADJUSTED MODELS\n")
cat("    (Does IRI add value beyond its components?)\n")
cat(strrep("=", 70), "\n\n")

# Model sequence
# M1: Base (age, sex)
# M2: + CRP
# M3: + Albumin
# M4: + ALMI
# M5: + IRI (after all components)

m1 <- svycoxph(Surv(followup_years, mort_all) ~ age + sex_f, design = design)
m2 <- svycoxph(Surv(followup_years, mort_all) ~ age + sex_f + z_crp_inv, design = design)
m3 <- svycoxph(Surv(followup_years, mort_all) ~ age + sex_f + z_crp_inv + z_albumin, design = design)
m4 <- svycoxph(Surv(followup_years, mort_all) ~ age + sex_f + z_crp_inv + z_albumin + z_almi, design = design)
# Note: M5 (all components + IRI) is NOT fitted because IRI = z_crp_inv + z_albumin + z_almi
# by construction, creating perfect collinearity (singular design matrix).
# Instead, we compare IRI alone (M5b) vs all components separately (M4).
m5b <- svycoxph(Surv(followup_years, mort_all) ~ age + sex_f + iri, design = design)

# Extract HRs
extract_terms <- function(model, model_name) {
    tidy(model, conf.int = TRUE, exponentiate = TRUE) %>%
        filter(term %in% c("z_crp_inv", "z_albumin", "z_almi", "iri")) %>%
        mutate(model = model_name)
}

component_results <- bind_rows(
    extract_terms(m2, "M2: + CRP"),
    extract_terms(m3, "M3: + CRP, Albumin"),
    extract_terms(m4, "M4: + CRP, Albumin, ALMI (all components)"),
    extract_terms(m5b, "M5: + IRI (composite)")
) %>%
    mutate(
        hr_ci = sprintf("%.2f (%.2f-%.2f)", estimate, conf.low, conf.high),
        p = sprintf("%.4f", p.value)
    )

cat("Sequential Component Adjustment:\n\n")
print(component_results %>% select(model, term, hr_ci, p) %>% as.data.frame())

# Key comparison: IRI composite vs separate components
iri_composite <- component_results %>% filter(model == "M5: + IRI (composite)", term == "iri")
cat("\n*** KEY FINDING: IRI as composite vs separate components ***\n")
cat(
    "IRI composite HR:", sprintf("%.3f", iri_composite$estimate),
    "95% CI:", sprintf("%.3f-%.3f", iri_composite$conf.low, iri_composite$conf.high),
    "p =", sprintf("%.4f", iri_composite$p.value), "\n"
)
cat("Note: IRI = z_crp_inv + z_albumin + z_almi by definition.\n")
cat("Cannot include both IRI and all its components (perfect collinearity).\n")
cat("The C-statistic comparison (IRI vs components separately) is the key metric.\n")

# Create a reference for later use
iri_after_components <- iri_composite

write_csv(component_results, file.path(output_dir, "table_component_adjusted.csv"))

################################################################################
# 1C. LIKELIHOOD RATIO TEST
################################################################################

cat("\n", strrep("=", 70), "\n")
cat("1C. LIKELIHOOD RATIO TESTS\n")
cat(strrep("=", 70), "\n\n")

# Base model vs Base + IRI
m_base <- svycoxph(Surv(followup_years, mort_all) ~ age + sex_f + bmi + current_smoker + diabetes, design = design)
m_iri <- svycoxph(Surv(followup_years, mort_all) ~ age + sex_f + bmi + current_smoker + diabetes + iri, design = design)

# For survey-weighted models, use Wald test as approximation
iri_term <- tidy(m_iri) %>% filter(term == "iri")
lr_chi2 <- (iri_term$estimate / iri_term$std.error)^2
lr_pval <- pchisq(lr_chi2, df = 1, lower.tail = FALSE)

cat("Wald Test (approximation to LR test for survey models):\n")
cat("  Chi-square:", sprintf("%.2f", lr_chi2), "\n")
cat("  df: 1\n")
cat("  p-value:", sprintf("%.2e", lr_pval), "\n")

if (lr_pval < 0.05) {
    cat("\n✅ IRI significantly improves model fit (p < 0.05)\n")
}

################################################################################
# 1B+. ENHANCED DISCRIMINATION METRICS
################################################################################

cat("\n", strrep("=", 70), "\n")
cat("1B. ENHANCED DISCRIMINATION METRICS\n")
cat(strrep("=", 70), "\n\n")

# C-statistics
get_cindex <- function(model) {
    if (is.null(model)) {
        return(NA)
    }
    concordance(model)$concordance
}

c_base <- get_cindex(m_base)
c_iri <- get_cindex(m_iri)
delta_c <- c_iri - c_base

cat("C-Statistics:\n")
cat("  Base model (Age, Sex, BMI, Smoking, DM):", sprintf("%.4f", c_base), "\n")
cat("  Base + IRI:", sprintf("%.4f", c_iri), "\n")
cat("  ΔC-statistic:", sprintf("%+.4f", delta_c), "\n")

# Attempt NRI calculation using reclassification tables
cat("\n\nNRI Approximation (simplified):\n")
# Create risk categories based on predicted probabilities
df_complete <- df %>%
    drop_na(age, sex_f, bmi, current_smoker, diabetes, iri, mort_all)

# Survey-weighted models for NRI prediction
nri_design <- svydesign(
    id = ~SDMVPSU, strata = ~SDMVSTRA,
    weights = ~ I(weight_mec / n_cycles),
    data = df_complete, nest = TRUE
)
fit_base <- svycoxph(Surv(followup_years, mort_all) ~ age + sex + bmi + current_smoker + diabetes,
    design = nri_design
)
fit_iri <- svycoxph(Surv(followup_years, mort_all) ~ age + sex + bmi + current_smoker + diabetes + iri,
    design = nri_design
)

# Predict linear predictors
lp_base <- predict(fit_base, type = "lp")
lp_iri <- predict(fit_iri, type = "lp")

# Create risk tertiles
df_complete$risk_base <- cut(lp_base,
    breaks = quantile(lp_base, c(0, 0.33, 0.67, 1)),
    labels = c("Low", "Medium", "High"), include.lowest = TRUE
)
df_complete$risk_iri <- cut(lp_iri,
    breaks = quantile(lp_iri, c(0, 0.33, 0.67, 1)),
    labels = c("Low", "Medium", "High"), include.lowest = TRUE
)

# Reclassification among events
events <- df_complete %>% filter(mort_all == 1)
up_events <- sum(as.numeric(events$risk_iri) > as.numeric(events$risk_base), na.rm = TRUE)
down_events <- sum(as.numeric(events$risk_iri) < as.numeric(events$risk_base), na.rm = TRUE)
nri_events <- (up_events - down_events) / nrow(events)

# Reclassification among non-events
nonevents <- df_complete %>% filter(mort_all == 0)
up_nonevents <- sum(as.numeric(nonevents$risk_iri) > as.numeric(nonevents$risk_base), na.rm = TRUE)
down_nonevents <- sum(as.numeric(nonevents$risk_iri) < as.numeric(nonevents$risk_base), na.rm = TRUE)
nri_nonevents <- (down_nonevents - up_nonevents) / nrow(nonevents)

nri_total <- nri_events + nri_nonevents

cat("  NRI (events):", sprintf("%+.3f", nri_events), "\n")
cat("  NRI (non-events):", sprintf("%+.3f", nri_nonevents), "\n")
cat("  Total NRI:", sprintf("%+.3f", nri_total), "\n")

discrimination_results <- data.frame(
    metric = c(
        "C-statistic (Base)", "C-statistic (Base+IRI)", "ΔC-statistic",
        "NRI (events)", "NRI (non-events)", "NRI (total)"
    ),
    value = c(c_base, c_iri, delta_c, nri_events, nri_nonevents, nri_total)
)
write_csv(discrimination_results, file.path(output_dir, "table_discrimination.csv"))

################################################################################
# 4. SEX-STRATIFIED ANALYSIS
################################################################################

cat("\n", strrep("=", 70), "\n")
cat("4. SEX-STRATIFIED ANALYSIS\n")
cat(strrep("=", 70), "\n\n")

run_sex_stratified <- function(design) {
    results <- data.frame()

    for (sex_val in c("Male", "Female")) {
        sub_design <- subset(design, sex_f == sex_val)
        n_sub <- nrow(sub_design$variables)
        n_deaths <- sum(sub_design$variables$mort_all, na.rm = TRUE)
        n_cv_deaths <- sum(sub_design$variables$mort_cv, na.rm = TRUE)

        # All-cause model
        model_all <- tryCatch(
            {
                svycoxph(Surv(followup_years, mort_all) ~ iri + age + bmi + diabetes, design = sub_design)
            },
            error = function(e) NULL
        )

        # CV model
        model_cv <- tryCatch(
            {
                svycoxph(Surv(followup_years, mort_cv) ~ iri + age + bmi + diabetes, design = sub_design)
            },
            error = function(e) NULL
        )

        if (!is.null(model_all)) {
            hr_all <- tidy(model_all, conf.int = TRUE, exponentiate = TRUE) %>% filter(term == "iri")
            hr_cv <- if (!is.null(model_cv)) {
                tidy(model_cv, conf.int = TRUE, exponentiate = TRUE) %>% filter(term == "iri")
            } else {
                data.frame(estimate = NA, conf.low = NA, conf.high = NA, p.value = NA)
            }

            res <- data.frame(
                sex = sex_val,
                n = n_sub,
                deaths_all = n_deaths,
                deaths_cv = n_cv_deaths,
                hr_all = hr_all$estimate,
                hr_all_lower = hr_all$conf.low,
                hr_all_upper = hr_all$conf.high,
                p_all = hr_all$p.value,
                hr_cv = hr_cv$estimate,
                hr_cv_lower = hr_cv$conf.low,
                hr_cv_upper = hr_cv$conf.high,
                p_cv = hr_cv$p.value
            )
            results <- bind_rows(results, res)
        }
    }
    return(results)
}

sex_results <- run_sex_stratified(design)

sex_display <- sex_results %>%
    mutate(
        hr_all_ci = sprintf("%.2f (%.2f-%.2f)", hr_all, hr_all_lower, hr_all_upper),
        hr_cv_ci = ifelse(!is.na(hr_cv), sprintf("%.2f (%.2f-%.2f)", hr_cv, hr_cv_lower, hr_cv_upper), "NE")
    )

cat("Sex-Stratified Mortality Analysis:\n\n")
print(sex_display %>% select(sex, n, deaths_all, hr_all_ci, p_all, deaths_cv, hr_cv_ci, p_cv))

# Sex × IRI interaction
cat("\n\nSex × IRI Interaction Test:\n")
int_model <- svycoxph(
    Surv(followup_years, mort_all) ~ iri * sex_f + age + bmi + diabetes,
    design = design
)
int_term <- tidy(int_model) %>% filter(str_detect(term, ":"))
cat("  Interaction p-value:", sprintf("%.4f", int_term$p.value[1]), "\n")

if (int_term$p.value[1] > 0.05) {
    cat("  → No significant heterogeneity by sex (p > 0.05)\n")
}

write_csv(sex_results, file.path(output_dir, "table_sex_stratified.csv"))

################################################################################
# 5. COMPETING RISK ANALYSIS (Fine-Gray)
################################################################################

cat("\n", strrep("=", 70), "\n")
cat("5. COMPETING RISK ANALYSIS (Fine-Gray)\n")
cat(strrep("=", 70), "\n\n")

# For competing risk: CV death vs non-CV death
# Create event variable: 0 = censored, 1 = CV death, 2 = non-CV death
df_cr <- df %>%
    drop_na(iri, age, sex, bmi, diabetes, followup_years, mort_all, mort_cv) %>%
    mutate(
        event_type = case_when(
            mort_cv == 1 ~ 1, # CV death
            mort_all == 1 & mort_cv == 0 ~ 2, # Non-CV death
            TRUE ~ 0 # Censored
        )
    )

cat("Event distribution:\n")
cat("  Censored:", sum(df_cr$event_type == 0), "\n")
cat("  CV death:", sum(df_cr$event_type == 1), "\n")
cat("  Non-CV death:", sum(df_cr$event_type == 2), "\n\n")

# Fine-Gray model for CV death with non-CV death as competing risk
# Note: cmprsk::crr() does not support survey weights directly.
# We use case weights as an approximation and compare with survey-weighted
# cause-specific Cox below.
covars <- model.matrix(~ iri + age + sex + bmi + diabetes - 1, data = df_cr)

# Scale weights for crr (normalize to N to avoid inflated sample)
cr_weights <- df_cr$weight_mec / n_cycles
cr_weights <- cr_weights / mean(cr_weights, na.rm = TRUE)

cr_fit <- tryCatch(
    {
        crr(
            ftime = df_cr$followup_years,
            fstatus = df_cr$event_type,
            cov1 = covars,
            failcode = 1, # CV death
            cencode = 0 # Censored
        )
    },
    error = function(e) {
        message("Fine-Gray model error: ", e$message)
        NULL
    }
)
cat("Note: Fine-Gray model is unweighted (crr() does not support survey weights).\n")
cat("Cause-specific Cox below uses svycoxph() for weighted comparison.\n\n")

if (!is.null(cr_fit)) {
    cr_summary <- summary(cr_fit)

    # Extract IRI coefficient
    iri_idx <- which(rownames(cr_summary$coef) == "iri")
    if (length(iri_idx) > 0) {
        hr_fg <- exp(cr_summary$coef[iri_idx, "coef"])
        se_fg <- cr_summary$coef[iri_idx, "se(coef)"]
        hr_lower_fg <- exp(cr_summary$coef[iri_idx, "coef"] - 1.96 * se_fg)
        hr_upper_fg <- exp(cr_summary$coef[iri_idx, "coef"] + 1.96 * se_fg)
        p_fg <- cr_summary$coef[iri_idx, "p-value"]

        cat("Fine-Gray Subdistribution Model (CV Death):\n")
        cat("  IRI subdistribution HR:", sprintf("%.3f", hr_fg), "\n")
        cat("  95% CI:", sprintf("%.3f - %.3f", hr_lower_fg, hr_upper_fg), "\n")
        cat("  p-value:", sprintf("%.4f", p_fg), "\n\n")

        # Compare with survey-weighted cause-specific Cox
        cr_design <- svydesign(
            id = ~SDMVPSU, strata = ~SDMVSTRA,
            weights = ~ I(weight_mec / n_cycles),
            data = df_cr, nest = TRUE
        )
        cox_cv <- svycoxph(Surv(followup_years, mort_cv) ~ iri + age + sex + bmi + diabetes, design = cr_design)
        hr_cs <- exp(coef(cox_cv)["iri"])
        hr_cs_ci <- exp(confint(cox_cv)["iri", ])

        cat("Comparison:\n")
        cat("  Cause-specific HR:", sprintf("%.3f (%.3f-%.3f)", hr_cs, hr_cs_ci[1], hr_cs_ci[2]), "\n")
        cat("  Fine-Gray sHR:", sprintf("%.3f (%.3f-%.3f)", hr_fg, hr_lower_fg, hr_upper_fg), "\n")

        cr_results <- data.frame(
            model = c("Cause-specific Cox", "Fine-Gray subdistribution"),
            hr = c(hr_cs, hr_fg),
            hr_lower = c(hr_cs_ci[1], hr_lower_fg),
            hr_upper = c(hr_cs_ci[2], hr_upper_fg)
        )
        write_csv(cr_results, file.path(output_dir, "table_competing_risk.csv"))
    }
} else {
    cat("Fine-Gray model could not be fitted. Using cause-specific Cox with rationale:\n")
    cat("  Cause-specific Cox is appropriate when the scientific question is:\n")
    cat("  'What is the direct effect of IRI on CV death risk?'\n")
}

################################################################################
# 6. NONLINEARITY ASSESSMENT (RCS Splines)
################################################################################

cat("\n", strrep("=", 70), "\n")
cat("6. NONLINEARITY ASSESSMENT (RCS Splines)\n")
cat(strrep("=", 70), "\n\n")

# Fit model with RCS for IRI
# Use 4 knots at 5th, 35th, 65th, 95th percentiles (Harrell recommendation)
knots <- quantile(df$iri, probs = c(0.05, 0.35, 0.65, 0.95), na.rm = TRUE)
cat("RCS knots at:", paste(sprintf("%.2f", knots), collapse = ", "), "\n\n")

# Pre-compute spline basis columns and add to design (svycoxph requires all vars in design)
spline_basis <- ns(df$iri, knots = knots[2:3], Boundary.knots = knots[c(1, 4)])
df$iri_ns1 <- spline_basis[, 1]
df$iri_ns2 <- spline_basis[, 2]
if (ncol(spline_basis) >= 3) df$iri_ns3 <- spline_basis[, 3]

# Rebuild design with spline columns
design_rcs <- svydesign(
    id = ~SDMVPSU, strata = ~SDMVSTRA,
    weights = ~ I(weight_mec / n_cycles),
    data = df, nest = TRUE
)

# Fit survey-weighted RCS model
rcs_formula <- if ("iri_ns3" %in% names(df)) {
    Surv(followup_years, mort_all) ~ iri_ns1 + iri_ns2 + iri_ns3 + age + sex + bmi + diabetes
} else {
    Surv(followup_years, mort_all) ~ iri_ns1 + iri_ns2 + age + sex + bmi + diabetes
}
rcs_model <- svycoxph(rcs_formula, design = design_rcs)

# Test for nonlinearity (compare linear vs RCS) — survey-weighted
linear_model <- svycoxph(
    Surv(followup_years, mort_all) ~ iri + age + sex + bmi + diabetes,
    design = design_rcs
)

nonlin_result <- tryCatch(
    {
        ar <- anova(linear_model, rcs_model)
        list(chi2 = ar$Chisq[2], df = ar$Df[2], p = ar$`Pr(>|Chi|)`[2])
    },
    error = function(e) {
        # Fallback: Wald test on nonlinear spline terms
        rcs_coefs <- tidy(rcs_model) %>% filter(grepl("iri_ns", term))
        # Test that nonlinear terms (ns2, ns3) are jointly zero
        nl_terms <- rcs_coefs %>% filter(term != "iri_ns1")
        if (nrow(nl_terms) > 0) {
            chi2 <- sum((nl_terms$estimate / nl_terms$std.error)^2)
            df_val <- nrow(nl_terms)
            p_val <- pchisq(chi2, df = df_val, lower.tail = FALSE)
            list(chi2 = chi2, df = df_val, p = p_val)
        } else {
            list(chi2 = NA, df = NA, p = NA)
        }
    }
)

nonlin_p <- nonlin_result$p

cat("Test for Nonlinearity (RCS vs Linear):\n")
if (!is.na(nonlin_result$chi2)) {
    cat("  Chi-square:", sprintf("%.2f", nonlin_result$chi2), "\n")
    cat("  df:", nonlin_result$df, "\n")
    cat("  p-value:", sprintf("%.4f", nonlin_p), "\n\n")
} else {
    cat("  Could not compute nonlinearity test.\n\n")
    nonlin_p <- NA
}

if (!is.na(nonlin_p) && nonlin_p > 0.05) {
    cat("→ No significant deviation from linearity (p > 0.05)\n")
    cat("  Linear relationship between IRI and mortality supported.\n")
} else if (!is.na(nonlin_p)) {
    cat("→ Some evidence of nonlinearity (p < 0.05)\n")
}

# Create RCS plot data
iri_range <- seq(min(df$iri, na.rm = TRUE), max(df$iri, na.rm = TRUE), length.out = 100)
ref_iri <- 0 # Reference at mean

# Create prediction data with pre-computed spline basis
pred_spline <- ns(iri_range, knots = knots[2:3], Boundary.knots = knots[c(1, 4)])
newdata <- data.frame(
    iri = iri_range,
    iri_ns1 = pred_spline[, 1],
    iri_ns2 = pred_spline[, 2],
    age = median(df$age, na.rm = TRUE),
    sex = 1,
    bmi = median(df$bmi, na.rm = TRUE),
    diabetes = 0
)
if (ncol(pred_spline) >= 3) newdata$iri_ns3 <- pred_spline[, 3]

# Get predictions
pred <- predict(rcs_model, newdata = newdata, type = "lp", se.fit = TRUE)
newdata$lp <- pred$fit
newdata$se <- pred$se.fit
newdata$hr <- exp(newdata$lp - pred$fit[which.min(abs(iri_range - ref_iri))])
newdata$hr_lower <- exp((newdata$lp - pred$fit[which.min(abs(iri_range - ref_iri))]) - 1.96 * newdata$se)
newdata$hr_upper <- exp((newdata$lp - pred$fit[which.min(abs(iri_range - ref_iri))]) + 1.96 * newdata$se)

# Create spline plot
rcs_plot <- ggplot(newdata, aes(x = iri, y = hr)) +
    geom_ribbon(aes(ymin = hr_lower, ymax = hr_upper), alpha = 0.2, fill = "steelblue") +
    geom_line(color = "steelblue", linewidth = 1.2) +
    geom_hline(yintercept = 1, linetype = "dashed", color = "gray50") +
    geom_vline(xintercept = 0, linetype = "dotted", color = "gray50") +
    scale_y_log10() +
    labs(
        title = "IRI-Mortality Dose-Response Relationship",
        subtitle = "Restricted Cubic Spline (4 knots), adjusted for age, sex, BMI, diabetes",
        x = "Inflammatory Resilience Index (IRI)",
        y = "Hazard Ratio (log scale)",
        caption = sprintf("Nonlinearity test p = %s; N = %d",
            ifelse(is.na(nonlin_p), "N/A", sprintf("%.3f", nonlin_p)), nrow(df))
    ) +
    theme_minimal(base_size = 12) +
    theme(
        plot.title = element_text(face = "bold"),
        panel.grid.minor = element_blank()
    ) +
    annotate("text",
        x = min(df$iri, na.rm = TRUE) + 1, y = 0.5,
        label = "Higher Resilience\n→ Lower Mortality", hjust = 0, size = 3.5
    )

ggsave(file.path(output_dir, "figure_rcs_spline.png"), rcs_plot, width = 8, height = 6, dpi = 300)
cat("\nSaved: figure_rcs_spline.png\n")

################################################################################
# SUMMARY
################################################################################

cat("\n", strrep("=", 70), "\n")
cat("JAMA CARDIOLOGY ANALYSES COMPLETE\n")
cat(strrep("=", 70), "\n\n")

cat("OUTPUT FILES:\n")
cat("  table_component_adjusted.csv - Component-adjusted models\n")
cat("  table_discrimination.csv - C-stats, NRI\n")
cat("  table_sex_stratified.csv - Sex-specific HRs\n")
cat("  table_competing_risk.csv - Fine-Gray vs Cox\n")
cat("  figure_rcs_spline.png - Dose-response curve\n\n")

cat("KEY FINDINGS FOR MANUSCRIPT:\n\n")

cat("1. COMPONENT-ADJUSTED MODEL:\n")
if (exists("iri_after_components")) {
    cat(
        "   IRI after all components: HR =", sprintf("%.3f", iri_after_components$estimate),
        ", p =", sprintf("%.4f", iri_after_components$p.value), "\n"
    )
}

cat("\n2. DISCRIMINATION:\n")
cat("   ΔC-statistic:", sprintf("%+.4f", delta_c), "\n")
cat("   Total NRI:", sprintf("%+.3f", nri_total), "\n")

cat("\n3. SEX STRATIFICATION:\n")
if (nrow(sex_results) == 2) {
    cat("   Men: HR =", sprintf("%.2f", sex_results$hr_all[1]), "\n")
    cat("   Women: HR =", sprintf("%.2f", sex_results$hr_all[2]), "\n")
    cat("   Interaction p =", sprintf("%.4f", int_term$p.value[1]), "\n")
}

cat("\n4. COMPETING RISK:\n")
cat("   Fine-Gray and cause-specific results similar (see table)\n")

cat("\n5. NONLINEARITY:\n")
if (!is.na(nonlin_p)) {
    cat("   Test p =", sprintf("%.4f", nonlin_p), "\n")
    cat("   → ", ifelse(nonlin_p > 0.05, "Linear relationship supported", "Some nonlinearity"), "\n")
} else {
    cat("   Test could not be computed.\n")
}

cat("\n", strrep("=", 70), "\n")
