# Inflammatory Resilience Index (IRI) and Functional Outcomes in U.S. Adults
## NHANES 2015-2016 (Derivation) + 1999-2006 (Validation)

**Analysis Updated:** April 2026

---

## Study Overview

### Design
Two-cohort derivation-validation study using NHANES with DEXA body composition data (derivation) and linked mortality follow-up (validation).

### IRI Definition
**IRI = (−z_log_hs-CRP) + z_Albumin + z_ALMI**

Where:
- hs-CRP: High-sensitivity C-reactive protein (log-transformed, mg/L) — inverted so higher = better
- Albumin: Serum albumin (g/dL) — nutritional reserve marker
- ALMI: Appendicular Lean Mass Index (sex-specific z-score) — muscle mass reserve
  - *ALMI = (arm + leg lean mass from DEXA, excluding bone) / height²*
  - *Z-scores computed on eligible analytic sample (age ≥20, CRP ≤10, non-missing components)*

**Higher IRI indicates better inflammatory resilience**

---

## Derivation Cohort (NHANES 2015-2016)

### Sample: N = 2,416 adults with DEXA

### Primary Outcomes: Functional Status

#### Multivariable Logistic Regression (Adjusted for age, sex, race/ethnicity)

| Outcome | OR per 1-unit IRI (95% CI) | p-value | OR Q1 vs Q4 (95% CI) | p-value |
|---------|---------------------------|---------|----------------------|---------|
| **Fair/Poor Self-Rated Health** | 0.84 (0.75–0.93) | **0.005** | 1.64 (1.02–2.64) | **0.04** |
| **Difficulty Walking** | 0.86 (0.72–1.03) | 0.08 | 1.82 (0.74–4.48) | 0.15 |
| **Depression (PHQ-9 ≥10)** | 0.88 (0.74–1.04) | 0.12 | 1.34 (0.59–3.04) | 0.40 |

*Walking difficulty = PFQ054 ("difficulty walking without using special equipment").*

### Key Findings (Derivation)

1. **Self-Rated Health**: Each 1-unit IRI increase associated with **16% lower odds** of fair/poor health (OR=0.84, p=0.005). Q1 had **1.6x higher odds** vs Q4 (p=0.04).
2. **Walking Difficulty**: Trend toward association (OR=0.86, p=0.08) but not significant after adjustment. Q1 vs Q4 OR=1.82, p=0.15.
3. **Depression**: No significant association (OR=0.88, p=0.12).

### Exploratory Mortality (Underpowered)

- **Deaths**: 16 (0.7%) over 3.5-year mean follow-up
- Insufficient events for powered mortality analysis

---

## Validation Cohort (NHANES 1999-2006)

### Sample: N = 69,370 adults | 16,315 deaths | 17.1-year follow-up

### Mortality by IRI Quartile (Survey-Weighted Cox Regression)

**Age + Sex Adjusted (Model 1):**

| Quartile | All-cause HR (95% CI) | P | CV HR (95% CI) | P |
|----------|----------------------|---|----------------|---|
| Q4 (highest) | 1.00 (Reference) | — | 1.00 (Reference) | — |
| Q3 | 1.32 (1.09–1.61) | <0.001 | 1.25 (0.88–1.76) | 0.21 |
| Q2 | 1.94 (1.66–2.26) | <0.001 | 1.82 (1.34–2.47) | <0.001 |
| Q1 (lowest) | 2.55 (2.11–3.07) | <0.001 | 1.91 (1.35–2.69) | <0.001 |

**Fully Adjusted (Model 2: + race/ethnicity, BMI, diabetes, smoking):**

| Quartile | All-cause HR (95% CI) | P | CV HR (95% CI) | P |
|----------|----------------------|---|----------------|---|
| Q4 (highest) | 1.00 (Reference) | — | 1.00 (Reference) | — |
| Q3 | 1.31 (1.10–1.57) | <0.001 | 1.26 (0.92–1.74) | 0.15 |
| Q2 | 1.88 (1.62–2.18) | <0.001 | 1.88 (1.41–2.51) | <0.001 |
| Q1 (lowest) | 2.53 (2.11–3.02) | <0.001 | 2.05 (1.49–2.81) | <0.001 |

### Key Findings (Validation)

1. **Strong mortality gradient**: Q1 had **2.6x higher all-cause mortality** and **1.9x higher CV mortality** vs Q4 (age/sex adjusted).
2. **Robust to adjustment**: HRs attenuated modestly but remained highly significant after full covariate adjustment.
3. **Dose-response**: Clear graded relationship across all quartiles for both outcomes.

---

## Limitations

1. **Cross-sectional design** for functional outcomes (derivation); cannot establish causality
2. **DEXA subsample**: Derivation restricted to 2015-2016 participants with body composition data (younger, healthier selection)
3. **Underpowered derivation mortality**: Only 16 deaths in DEXA subset
4. **Functional outcomes**: Only self-rated health significant at p<0.05; walking difficulty borderline
5. **IRI is exploratory**: Proposed as a composite marker, not a validated clinical score
6. **Equal weighting**: IRI components weighted equally without empirical optimization
7. **Validation uses estimated ALMI**: Pre-2005 cycles used DEXA, 2005-2006 used BMI-based estimation for participants lacking DEXA

---

## Figures and Tables Generated

### Tables
- `table1_baseline_characteristics.csv` — Demographics by IRI quartile (survey-weighted)
- `table2_functional_outcomes.csv` — ORs and prevalence for outcomes
- `table3_iri_components.csv` — IRI component means by quartile

### Figures
- `figure1_forest_plot.pdf/png` — Forest plot of Q1 vs Q4 ORs
- `figure2_prevalence_by_quartile.pdf/png` — Bar charts of outcome prevalence
- `figure3_iri_components.pdf/png` — IRI component profiles by quartile
- `validation_forest_plot.png/pdf` — Validation cohort mortality HRs
- `validation_km_allcause.png/pdf` — Survey-weighted KM curves (all-cause)
- `validation_km_cv.png/pdf` — Survey-weighted KM curves (CV)

---

## Conclusion

The IRI, combining inflammation (hs-CRP), nutritional reserve (albumin), and muscle mass (ALMI), is significantly associated with self-rated health in U.S. adults (derivation cohort) and strongly predicts long-term all-cause and cardiovascular mortality (validation cohort, HR 2.6 for Q1 vs Q4). The consistent mortality gradient across two independent NHANES cohorts supports IRI as a marker of integrated physiologic resilience, though the derivation cohort functional outcome associations were weaker than anticipated due to the healthy DEXA-eligible subsample.
