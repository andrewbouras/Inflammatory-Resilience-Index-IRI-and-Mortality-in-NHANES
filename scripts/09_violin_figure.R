# =============================================================================
# IRI: VIOLIN PLOTS - IRI Distribution by Functional Outcomes
# =============================================================================
# Shows full distribution of IRI scores by each functional outcome
# More informative than bar chart means
# =============================================================================

library(ggplot2)
library(dplyr)
library(tidyr)

# Color palette (consistent with IRI manuscript - teal)
iri_colors <- list(
  primary = "#1B5E5E",
  secondary = "#2E8B8B",
  light = "#5CACAC",
  lighter = "#8FCFCF",
  accent = "#C44E52",
  gray = "#7F7F7F"
)

# Paths
data_path <- "/Users/andrewbouras/Documents/VishrutNHANES/Inflammatory Resilience Index (IRI) and Mortality in NHANES/data/processed/iri_functional_cohort.csv"
output_dir <- "/Users/andrewbouras/Documents/VishrutNHANES/Inflammatory Resilience Index (IRI) and Mortality in NHANES/output"
manuscript_dir <- "/Users/andrewbouras/Documents/VishrutNHANES/Inflammatory Resilience Index (IRI) and Mortality in NHANES/manuscript/figures"

cat("Loading data...\n")
df <- read.csv(data_path)

cat("Total N:", nrow(df), "\n")

# =============================================================================
# Prepare outcome variables
# =============================================================================

# Check what outcome variables exist
cat("\nAvailable columns:\n")
print(names(df))

# Create outcome indicators based on actual data coding
df <- df %>%
  mutate(
    # Self-rated health: use existing poor_health if present, else create
    health_status = case_when(
      !is.na(poor_health) & poor_health == 1 ~ "Fair/Poor",
      !is.na(poor_health) & poor_health == 0 ~ "Good/Excellent",
      !is.na(self_rated_health) & self_rated_health >= 4 ~ "Fair/Poor",
      !is.na(self_rated_health) ~ "Good/Excellent",
      TRUE ~ NA_character_
    ),
    
    # Difficulty walking: 0=No difficulty, 1=Difficulty
    walk_status = case_when(
      !is.na(difficulty_walking) & difficulty_walking == 1 ~ "Yes",
      !is.na(difficulty_walking) & difficulty_walking == 0 ~ "No",
      TRUE ~ NA_character_
    ),
    
    # Depression: use existing depression if present, else from PHQ-9
    depression_status = case_when(
      !is.na(depression) & depression == 1 ~ "Yes",
      !is.na(depression) & depression == 0 ~ "No",
      !is.na(phq9_score) & phq9_score >= 10 ~ "Yes",
      !is.na(phq9_score) ~ "No",
      TRUE ~ NA_character_
    )
  )

# Check distributions
cat("\nOutcome distributions:\n")
cat("Health status:\n"); print(table(df$health_status, useNA = "ifany"))
cat("Walk status:\n"); print(table(df$walk_status, useNA = "ifany"))
cat("Depression status:\n"); print(table(df$depression_status, useNA = "ifany"))

# Check IRI score exists
if (!"iri_score" %in% names(df)) {
  # Calculate IRI if not present (standardized sum of components)
  cat("\nCalculating IRI score from components...\n")
  df <- df %>%
    mutate(
      z_crp = -scale(log(hscrp + 0.1)),  # Inverted: lower CRP = higher resilience
      z_alb = scale(albumin),
      z_almi = scale(z_almi),
      iri_score = z_crp + z_alb + z_almi
    )
}

cat("IRI score range:", range(df$iri_score, na.rm = TRUE), "\n")

# =============================================================================
# Theme
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
      legend.position = "bottom",
      panel.grid.major.y = element_line(color = "gray90", linewidth = 0.3),
      panel.grid.major.x = element_blank(),
      panel.grid.minor = element_blank(),
      panel.background = element_rect(fill = "white", color = NA),
      plot.background = element_rect(fill = "white", color = NA),
      plot.margin = margin(15, 15, 15, 15),
      strip.text = element_text(face = "bold", size = base_size)
    )
}

# =============================================================================
# Create violin plot for each outcome
# =============================================================================

cat("\nCreating violin plots...\n")

# Function to create individual violin
make_violin <- function(data, outcome_col, outcome_label, yes_label = "Yes", no_label = "No") {
  plot_data <- data %>%
    filter(!is.na(.data[[outcome_col]]) & !is.na(iri_score)) %>%
    mutate(Outcome = factor(.data[[outcome_col]], levels = c(no_label, yes_label)))
  
  # Calculate means for annotation
  means <- plot_data %>%
    group_by(Outcome) %>%
    summarise(mean_iri = mean(iri_score, na.rm = TRUE), .groups = "drop")
  
  ggplot(plot_data, aes(x = Outcome, y = iri_score, fill = Outcome)) +
    geom_violin(alpha = 0.7, color = "gray30", linewidth = 0.3) +
    geom_boxplot(width = 0.15, fill = "white", alpha = 0.8, outlier.size = 0.5) +
    geom_point(data = means, aes(x = Outcome, y = mean_iri), 
               color = iri_colors$accent, size = 3, shape = 18) +
    scale_fill_manual(values = c(iri_colors$lighter, iri_colors$primary), guide = "none") +
    labs(title = outcome_label, x = "", y = "IRI Score") +
    theme_iri() +
    theme(plot.title = element_text(size = 11, hjust = 0.5))
}

# Create three violin plots
p1 <- make_violin(df, "health_status", "Self-Rated Health", "Fair/Poor", "Good/Excellent")
p2 <- make_violin(df, "walk_status", "Difficulty Walking 1/4 Mile", "Yes", "No")
p3 <- make_violin(df, "depression_status", "Depression (PHQ-9 >=10)", "Yes", "No")

# Combine using patchwork
library(patchwork)

combined <- p1 + p2 + p3 +
  plot_layout(ncol = 3) +
  plot_annotation(
    title = "IRI Score Distribution by Functional Outcome Status",
    subtitle = "NHANES 2015-2020 | Lower IRI indicates lower inflammatory resilience",
    caption = "Violin plots show full distribution; box plots show median and IQR; red diamonds indicate means.\nParticipants with adverse outcomes have lower IRI scores (worse resilience).",
    theme = theme(
      plot.title = element_text(size = 13, face = "bold"),
      plot.subtitle = element_text(size = 10, color = "gray40"),
      plot.caption = element_text(size = 8, color = "gray50", hjust = 0)
    )
  )

# Save
ggsave(file.path(output_dir, "figure4_violin_iri.png"), combined, 
       width = 11, height = 5, dpi = 300, bg = "white")
ggsave(file.path(output_dir, "figure4_violin_iri.pdf"), combined, 
       width = 11, height = 5, bg = "white")
ggsave(file.path(manuscript_dir, "figure4_violin_iri.png"), combined, 
       width = 11, height = 5, dpi = 300, bg = "white")
ggsave(file.path(manuscript_dir, "figure4_violin_iri.pdf"), combined, 
       width = 11, height = 5, bg = "white")

cat("\n✅ Saved: figure4_violin_iri.png/pdf\n")

# =============================================================================
# Print summary statistics
# =============================================================================

cat("\n--- IRI by Outcome Status ---\n")

summarize_iri <- function(data, outcome_col, label) {
  data %>%
    filter(!is.na(.data[[outcome_col]]) & !is.na(iri_score)) %>%
    group_by(.data[[outcome_col]]) %>%
    summarise(
      N = n(),
      Mean = mean(iri_score, na.rm = TRUE),
      SD = sd(iri_score, na.rm = TRUE),
      Median = median(iri_score, na.rm = TRUE),
      .groups = "drop"
    ) %>%
    mutate(Outcome = label) %>%
    relocate(Outcome)
}

bind_rows(
  summarize_iri(df, "health_status", "Self-Rated Health"),
  summarize_iri(df, "walk_status", "Walking Difficulty"),
  summarize_iri(df, "depression_status", "Depression")
) %>% print()

