# =============================================================================
# IRI: KAPLAN-MEIER SURVIVAL CURVES BY IRI QUARTILE
# =============================================================================
# Shows all-cause mortality by IRI quartile
# Note: Exploratory analysis with limited deaths (N=25 in quartile subset)
# =============================================================================

library(survival)
library(survminer)
library(survey)
library(dplyr)
library(ggplot2)

# Color palette (consistent with IRI manuscript - teal gradient)
# Order: Q4 (best), Q3, Q2, Q1 (worst)
iri_colors <- c("#8FCFCF", "#5CACAC", "#2E8B8B", "#1B5E5E")

# Project paths
project_root <- normalizePath(file.path(dirname(sys.frame(1)$ofile %||% "."), ".."), mustWork = FALSE)
if (!dir.exists(project_root)) {
  project_root <- normalizePath(file.path(getwd(), ".."), mustWork = FALSE)
}

# Paths
data_path <- file.path(project_root, "data", "processed", "iri_cohort_mortality.csv")
output_dir <- file.path(project_root, "output")
manuscript_dir <- file.path(project_root, "manuscript", "figures")

cat("Loading data...\n")
df <- read.csv(data_path)

# Filter to those with IRI quartile assignment
df_km <- df %>%
  filter(iri_quartile %in% c("Q1", "Q2", "Q3", "Q4")) %>%
  mutate(
    iri_quartile = factor(iri_quartile, levels = c("Q4", "Q3", "Q2", "Q1")),  # Reference = Q4
    event = as.numeric(mort_all),
    time = followup_years
  ) %>%
  filter(!is.na(time) & !is.na(event))

cat("Analytic sample N:", nrow(df_km), "\n")
cat("Deaths:", sum(df_km$event), "\n")
cat("By quartile:\n")
print(table(df_km$iri_quartile, df_km$event))

# =============================================================================
# FIT KAPLAN-MEIER MODEL
# =============================================================================

# Unweighted fit for log-rank test and summary stats
fit <- survfit(Surv(time, event) ~ iri_quartile, data = df_km)

cat("\nSurvival summary (unweighted):\n")
print(fit)

# Survey-weighted KM curves
cat("\nComputing survey-weighted KM curves...\n")
n_cycles <- 1  # DEXA only available in 2015-2016 (single cycle)
if ("mec_weight" %in% names(df_km) & "psu" %in% names(df_km) & "strata" %in% names(df_km)) {
  km_design <- svydesign(
    id = ~psu, strata = ~strata,
    weights = ~ I(mec_weight / n_cycles),
    data = df_km %>% filter(!is.na(mec_weight), !is.na(psu), !is.na(strata)),
    nest = TRUE
  )
  use_weighted_km <- TRUE
  cat("  Using survey-weighted KM\n")
} else {
  use_weighted_km <- FALSE
  cat("  WARNING: Survey design variables missing, using unweighted KM\n")
}

# =============================================================================
# CREATE KAPLAN-MEIER PLOT
# =============================================================================

cat("\nCreating Kaplan-Meier figure...\n")

# Custom theme
km_theme <- theme_minimal(base_size = 11) +
  theme(
    text = element_text(color = "black"),
    plot.title = element_text(size = 12, face = "bold", hjust = 0),
    plot.subtitle = element_text(size = 10, color = "gray40", hjust = 0),
    plot.caption = element_text(size = 8, color = "gray50", hjust = 0),
    axis.title = element_text(size = 11, face = "bold"),
    axis.text = element_text(size = 10, color = "black"),
    legend.position = "bottom",
    legend.title = element_text(size = 10, face = "bold"),
    legend.text = element_text(size = 9),
    panel.grid.major = element_line(color = "gray90", linewidth = 0.3),
    panel.grid.minor = element_blank(),
    panel.background = element_rect(fill = "white", color = NA),
    plot.background = element_rect(fill = "white", color = NA)
  )

# Survey-weighted KM curves using svykm() + manual ggplot2
# (ggsurvplot doesn't support survey-weighted survival objects)
if (use_weighted_km) {
  quartiles <- levels(df_km$iri_quartile)
  km_list <- list()
  for (q in quartiles) {
    sub_design <- subset(km_design, iri_quartile == q)
    km_fit_q <- svykm(Surv(time, event) ~ 1, design = sub_design, se = FALSE)
    km_list[[q]] <- data.frame(
      time = km_fit_q$time,
      surv = km_fit_q$surv,
      quartile = q
    )
  }
  km_weighted <- do.call(rbind, km_list)
  km_weighted$quartile <- factor(km_weighted$quartile, levels = quartiles)

  # Log-rank p-value from unweighted fit (for annotation)
  lr_test <- survdiff(Surv(time, event) ~ iri_quartile, data = df_km)
  lr_pval <- 1 - pchisq(lr_test$chisq, length(lr_test$n) - 1)
  pval_label <- if (lr_pval < 0.001) "p < 0.001" else sprintf("p = %.3f", lr_pval)

  p_km <- ggplot(km_weighted, aes(x = time, y = surv, color = quartile)) +
    geom_step(linewidth = 0.8) +
    scale_color_manual(
      values = setNames(iri_colors, quartiles),
      name = "IRI Quartile",
      labels = c("Q4 (Highest)", "Q3", "Q2", "Q1 (Lowest)")
    ) +
    scale_y_continuous(limits = c(0.85, 1), labels = scales::percent) +
    labs(
      title = "All-Cause Mortality by IRI Quartile (Survey-Weighted)",
      subtitle = "NHANES 2015-2018 with mortality follow-up through 2019",
      x = "Follow-up Time (Years)",
      y = "Survival Probability",
      caption = paste0(
        "Survey-weighted Kaplan-Meier curves. Log-rank test ", pval_label, ".\n",
        "Note: Exploratory analysis with limited events (", sum(df_km$event),
        " deaths); interpret with caution."
      )
    ) +
    annotate("text", x = 0.5, y = 0.86, label = pval_label, size = 4, hjust = 0) +
    km_theme
} else {
  # Fallback: unweighted KM via ggsurvplot
  p_km <- ggsurvplot(
    fit, data = df_km, palette = iri_colors,
    conf.int = TRUE, conf.int.alpha = 0.15,
    pval = TRUE, pval.coord = c(0.5, 0.85), pval.size = 4,
    risk.table = TRUE, risk.table.col = "strata", risk.table.height = 0.25,
    risk.table.y.text = FALSE, ncensor.plot = FALSE,
    legend.title = "IRI Quartile",
    legend.labs = c("Q4 (Highest)", "Q3", "Q2", "Q1 (Lowest)"),
    xlab = "Follow-up Time (Years)", ylab = "Survival Probability",
    title = "All-Cause Mortality by IRI Quartile",
    subtitle = "NHANES 2015-2018 with mortality follow-up through 2019",
    ggtheme = km_theme, surv.median.line = "none"
  )
  p_km$plot <- p_km$plot +
    labs(caption = "Lower IRI quartiles (worse resilience) show higher mortality.\nNote: Exploratory analysis with limited events; interpret with caution.")
}

# Save
ggsave(file.path(output_dir, "figure5_km_survival.png"),
       p_km, width = 8, height = 7, dpi = 300, bg = "white")
ggsave(file.path(output_dir, "figure5_km_survival.pdf"),
       p_km, width = 8, height = 7, bg = "white")
ggsave(file.path(manuscript_dir, "figure5_km_survival.png"),
       p_km, width = 8, height = 7, dpi = 300, bg = "white")
ggsave(file.path(manuscript_dir, "figure5_km_survival.pdf"),
       p_km, width = 8, height = 7, bg = "white")

cat("\n✅ Saved: figure5_km_survival.png/pdf\n")

# =============================================================================
# SUMMARY STATISTICS
# =============================================================================

cat("\n--- Mortality Summary by IRI Quartile ---\n")
df_km %>%
  group_by(iri_quartile) %>%
  summarise(
    N = n(),
    Deaths = sum(event),
    Rate_per_100 = Deaths / N * 100,
    Mean_FU_years = mean(time, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  arrange(desc(iri_quartile)) %>%
  print()

# Log-rank test
cat("\nLog-rank test:\n")
print(survdiff(Surv(time, event) ~ iri_quartile, data = df_km))

