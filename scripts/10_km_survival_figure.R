# =============================================================================
# IRI: KAPLAN-MEIER SURVIVAL CURVES BY IRI QUARTILE
# =============================================================================
# Shows all-cause mortality by IRI quartile
# Note: Exploratory analysis with limited deaths (N=25 in quartile subset)
# =============================================================================

library(survival)
library(survminer)
library(dplyr)
library(ggplot2)

# Color palette (consistent with IRI manuscript - teal gradient)
# Order: Q4 (best), Q3, Q2, Q1 (worst)
iri_colors <- c("#8FCFCF", "#5CACAC", "#2E8B8B", "#1B5E5E")

# Paths
data_path <- "/Users/andrewbouras/Documents/VishrutNHANES/Inflammatory Resilience Index (IRI) and Mortality in NHANES/data/processed/iri_cohort_mortality.csv"
output_dir <- "/Users/andrewbouras/Documents/VishrutNHANES/Inflammatory Resilience Index (IRI) and Mortality in NHANES/output"
manuscript_dir <- "/Users/andrewbouras/Documents/VishrutNHANES/Inflammatory Resilience Index (IRI) and Mortality in NHANES/manuscript/figures"

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

fit <- survfit(Surv(time, event) ~ iri_quartile, data = df_km)

cat("\nSurvival summary:\n")
print(fit)

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

# Use ggsurvplot for publication-quality KM curves
p_km <- ggsurvplot(
  fit,
  data = df_km,
  palette = iri_colors,  # Q4 light to Q1 dark
  conf.int = TRUE,
  conf.int.alpha = 0.15,
  pval = TRUE,
  pval.coord = c(0.5, 0.85),
  pval.size = 4,
  risk.table = TRUE,
  risk.table.col = "strata",
  risk.table.height = 0.25,
  risk.table.y.text = FALSE,
  ncensor.plot = FALSE,
  legend.title = "IRI Quartile",
  legend.labs = c("Q4 (Highest)", "Q3", "Q2", "Q1 (Lowest)"),
  xlab = "Follow-up Time (Years)",
  ylab = "Survival Probability",
  title = "All-Cause Mortality by IRI Quartile",
  subtitle = "NHANES 2015-2018 with mortality follow-up through 2019",
  ggtheme = km_theme,
  surv.median.line = "none"
)

# Add caption
p_km$plot <- p_km$plot +
  labs(caption = "Lower IRI quartiles (worse resilience) show higher mortality. Log-rank test p-value shown.\nNote: Exploratory analysis with limited events (25 deaths); interpret with caution.")

# Save
ggsave(file.path(output_dir, "figure5_km_survival.png"), 
       print(p_km), width = 8, height = 7, dpi = 300, bg = "white")
ggsave(file.path(output_dir, "figure5_km_survival.pdf"), 
       print(p_km), width = 8, height = 7, bg = "white")
ggsave(file.path(manuscript_dir, "figure5_km_survival.png"), 
       print(p_km), width = 8, height = 7, dpi = 300, bg = "white")
ggsave(file.path(manuscript_dir, "figure5_km_survival.pdf"), 
       print(p_km), width = 8, height = 7, bg = "white")

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

