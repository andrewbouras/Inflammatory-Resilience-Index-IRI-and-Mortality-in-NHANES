# =============================================================================
# IRI MANUSCRIPT - UNIFIED COLOR SCHEME FIGURES
# =============================================================================
# Professional medical journal color palette: Teal/Green-based monochromatic
# All 3 figures with consistent styling
# =============================================================================

library(ggplot2)
library(dplyr)
library(tidyr)

# =============================================================================
# COLOR PALETTE: IRI STUDY (Teal/Green Monochromatic)
# =============================================================================
# Distinct from RIR (navy blue), professional for medical journals
iri_colors <- list(
  # For quartiles Q1 (worst) to Q4 (best) - gradient from dark to light
  q1 = "#1B5E5E",      # Dark teal (lowest resilience)
  q2 = "#2E8B8B",      # Medium-dark teal
  q3 = "#5CACAC",      # Medium teal
  q4 = "#8FCFCF",      # Light teal (highest resilience)
  
  # For binary significant/not
  significant = "#1B5E5E",   # Dark teal
  nonsignificant = "#9E9E9E", # Gray
  
  # Reference line
  reference = "#6B6B6B"
)

# =============================================================================
# PUBLICATION THEME
# =============================================================================
theme_iri <- function(base_size = 11) {
  theme_minimal(base_size = base_size) +
    theme(
      text = element_text(color = "black"),
      plot.title = element_text(size = base_size + 1, face = "bold", hjust = 0),
      plot.subtitle = element_text(size = base_size - 1, color = "gray40", hjust = 0),
      plot.caption = element_text(size = base_size - 2, color = "gray50", hjust = 0),
      axis.title = element_text(size = base_size, face = "bold"),
      axis.text = element_text(size = base_size - 1, color = "black"),
      axis.line = element_line(color = "black", linewidth = 0.4),
      axis.ticks = element_line(color = "black", linewidth = 0.3),
      legend.position = "bottom",
      legend.title = element_text(size = base_size - 1, face = "bold"),
      legend.text = element_text(size = base_size - 1),
      legend.background = element_blank(),
      legend.key = element_blank(),
      panel.grid.major.y = element_line(color = "gray90", linewidth = 0.3),
      panel.grid.major.x = element_blank(),
      panel.grid.minor = element_blank(),
      panel.background = element_rect(fill = "white", color = NA),
      plot.background = element_rect(fill = "white", color = NA),
      plot.margin = margin(15, 15, 15, 15),
      strip.text = element_text(face = "bold", size = base_size)
    )
}

# Output paths
output_dir <- "/Users/andrewbouras/Documents/VishrutNHANES/Inflammatory Resilience Index (IRI) and Mortality in NHANES/output"
manuscript_dir <- "/Users/andrewbouras/Documents/VishrutNHANES/Inflammatory Resilience Index (IRI) and Mortality in NHANES/manuscript/figures"
dir.create(manuscript_dir, recursive = TRUE, showWarnings = FALSE)

# ============================================================================
# FIGURE 1: FOREST PLOT - IRI AND FUNCTIONAL OUTCOMES
# ============================================================================
cat("[Figure 1: Forest Plot]\n")

results <- data.frame(
  Outcome = c("Fair/Poor Self-Rated Health", "Difficulty Walking 1/4 Mile", "Depression (PHQ-9 >=10)"),
  OR = c(2.07, 4.51, 1.40),
  CI_low = c(1.42, 1.96, 0.79),
  CI_high = c(3.01, 10.42, 2.49),
  p = c(0.0042, 0.0057, 0.1926),
  significant = c(TRUE, TRUE, FALSE)
)

results$Outcome <- factor(results$Outcome, levels = rev(results$Outcome))
results$OR_label <- sprintf("%.2f (%.2f-%.2f)", results$OR, results$CI_low, results$CI_high)

p1 <- ggplot(results, aes(x = OR, y = Outcome)) +
  geom_vline(xintercept = 1, linetype = "dashed", color = iri_colors$reference, linewidth = 0.6) +
  geom_errorbarh(aes(xmin = CI_low, xmax = CI_high), height = 0.15, linewidth = 0.8, color = "gray30") +
  geom_point(aes(color = significant), size = 4.5) +
  geom_text(aes(label = OR_label, x = CI_high + 0.8), hjust = 0, size = 3.2) +
  scale_color_manual(values = c("TRUE" = iri_colors$significant, "FALSE" = iri_colors$nonsignificant), 
                     guide = "none") +
  scale_x_log10(breaks = c(0.5, 1, 2, 4, 8, 12), limits = c(0.5, 18)) +
  labs(
    title = "Lowest IRI Quartile (Q1) vs Highest (Q4) and Functional Outcomes",
    subtitle = "NHANES 2015-2020 | Adjusted for age, sex, and race/ethnicity",
    x = "Odds Ratio (95% CI)",
    y = ""
  ) +
  theme_iri() +
  theme(
    panel.grid.major.y = element_blank(),
    axis.text.y = element_text(size = 11)
  )

ggsave(file.path(output_dir, "figure1_forest_plot.png"), p1, width = 9, height = 4, dpi = 300, bg = "white")
ggsave(file.path(output_dir, "figure1_forest_plot.pdf"), p1, width = 9, height = 4, bg = "white")
ggsave(file.path(manuscript_dir, "figure1_forest_plot.png"), p1, width = 9, height = 4, dpi = 300, bg = "white")
ggsave(file.path(manuscript_dir, "figure1_forest_plot.pdf"), p1, width = 9, height = 4, bg = "white")
cat("  Saved Figure 1\n")

# ============================================================================
# FIGURE 2: PREVALENCE BY IRI QUARTILE
# ============================================================================
cat("\n[Figure 2: Prevalence by Quartile]\n")

prev_data <- data.frame(
  Quartile = rep(c("Q1\n(Lowest)", "Q2", "Q3", "Q4\n(Highest)"), 3),
  Outcome = rep(c("Fair/Poor Health", "Difficulty Walking", "Depression"), each = 4),
  Prevalence = c(
    19.2, 17.5, 13.8, 9.2,
    12.4, 8.7, 7.8, 2.5,
    8.5, 7.0, 6.6, 5.3
  ),
  SE = c(
    2.0, 1.6, 1.9, 1.0,
    1.7, 1.4, 1.3, 0.6,
    0.9, 1.3, 0.9, 0.6
  )
)

prev_data$Quartile <- factor(prev_data$Quartile, levels = c("Q1\n(Lowest)", "Q2", "Q3", "Q4\n(Highest)"))
prev_data$Outcome <- factor(prev_data$Outcome, levels = c("Fair/Poor Health", "Difficulty Walking", "Depression"))

# Map quartile to color
quartile_colors <- c("Q1\n(Lowest)" = iri_colors$q1, "Q2" = iri_colors$q2, 
                     "Q3" = iri_colors$q3, "Q4\n(Highest)" = iri_colors$q4)

p2 <- ggplot(prev_data, aes(x = Quartile, y = Prevalence, fill = Quartile)) +
  geom_bar(stat = "identity", width = 0.7) +
  geom_errorbar(aes(ymin = pmax(0, Prevalence - 1.96*SE), ymax = Prevalence + 1.96*SE), 
                width = 0.2, linewidth = 0.5) +
  facet_wrap(~Outcome, scales = "free_y", ncol = 3) +
  scale_fill_manual(values = quartile_colors, guide = "none") +
  labs(
    title = "Functional Outcome Prevalence by IRI Quartile",
    subtitle = "Survey-weighted estimates | NHANES 2015-2020",
    x = "IRI Quartile",
    y = "Prevalence (%)",
    caption = "Error bars represent 95% CI. Lower quartiles indicate lower inflammatory resilience."
  ) +
  theme_iri()

ggsave(file.path(output_dir, "figure2_prevalence_by_quartile.png"), p2, width = 10, height = 4.5, dpi = 300, bg = "white")
ggsave(file.path(output_dir, "figure2_prevalence_by_quartile.pdf"), p2, width = 10, height = 4.5, bg = "white")
ggsave(file.path(manuscript_dir, "figure2_prevalence_by_quartile.png"), p2, width = 10, height = 4.5, dpi = 300, bg = "white")
ggsave(file.path(manuscript_dir, "figure2_prevalence_by_quartile.pdf"), p2, width = 10, height = 4.5, bg = "white")
cat("  Saved Figure 2\n")

# ============================================================================
# FIGURE 3: IRI COMPONENTS BY QUARTILE
# ============================================================================
cat("\n[Figure 3: IRI Components]\n")

data_path <- "/Users/andrewbouras/Documents/VishrutNHANES/Inflammatory Resilience Index (IRI) and Mortality in NHANES/data/processed/iri_functional_cohort.csv"
dat <- read.csv(data_path)

component_summary <- dat %>%
  group_by(iri_quartile) %>%
  summarise(
    CRP = mean(hscrp, na.rm = TRUE),
    Albumin = mean(albumin, na.rm = TRUE),
    ALMI_z = mean(z_almi, na.rm = TRUE),
    .groups = "drop"
  )

comp_long <- pivot_longer(component_summary, cols = c(CRP, Albumin, ALMI_z), 
                          names_to = "Component", values_to = "Value") %>%
  mutate(
    Component = factor(Component, levels = c("CRP", "Albumin", "ALMI_z"),
                       labels = c("hs-CRP (mg/L)", "Albumin (g/dL)", "ALMI (z-score)"))
  )

# Map quartile to color (Q1-Q4)
comp_long$iri_quartile <- factor(comp_long$iri_quartile, levels = c("Q1", "Q2", "Q3", "Q4"))
quartile_colors_short <- c("Q1" = iri_colors$q1, "Q2" = iri_colors$q2, 
                           "Q3" = iri_colors$q3, "Q4" = iri_colors$q4)

p3 <- ggplot(comp_long, aes(x = iri_quartile, y = Value, fill = iri_quartile)) +
  geom_bar(stat = "identity", width = 0.7) +
  facet_wrap(~Component, scales = "free_y", ncol = 3) +
  scale_fill_manual(values = quartile_colors_short, name = "IRI Quartile") +
  labs(
    title = "IRI Component Values by Quartile",
    subtitle = "Lower hs-CRP, higher albumin, and higher ALMI indicate better resilience",
    x = "IRI Quartile",
    y = "Mean Value",
    caption = "Q1 = lowest resilience (highest inflammation, lowest muscle mass); Q4 = highest resilience"
  ) +
  theme_iri() +
  theme(legend.position = "none")

ggsave(file.path(output_dir, "figure3_iri_components.png"), p3, width = 10, height = 4.5, dpi = 300, bg = "white")
ggsave(file.path(output_dir, "figure3_iri_components.pdf"), p3, width = 10, height = 4.5, bg = "white")
ggsave(file.path(manuscript_dir, "figure3_iri_components.png"), p3, width = 10, height = 4.5, dpi = 300, bg = "white")
ggsave(file.path(manuscript_dir, "figure3_iri_components.pdf"), p3, width = 10, height = 4.5, bg = "white")
cat("  Saved Figure 3\n")

# ============================================================================
# COMPLETE
# ============================================================================
cat("\n", strrep("=", 60), "\n")
cat("IRI FIGURES COMPLETE - UNIFIED TEAL COLOR SCHEME\n")
cat(strrep("=", 60), "\n")
cat("\nColor palette:\n")
cat("  Q1 (dark):  ", iri_colors$q1, "\n")
cat("  Q2:         ", iri_colors$q2, "\n")
cat("  Q3:         ", iri_colors$q3, "\n")
cat("  Q4 (light): ", iri_colors$q4, "\n")
cat("\nAll 3 figures saved to:", output_dir, "\n")
cat("Also copied to:", manuscript_dir, "\n")
