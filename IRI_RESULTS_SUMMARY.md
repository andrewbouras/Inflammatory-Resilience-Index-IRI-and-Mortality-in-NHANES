# Inflammatory Resilience Index (IRI) and Functional Outcomes in U.S. Adults
## NHANES 2015-2020 Analysis Results

**Analysis Completed:** December 2025

---

## Study Overview

### Design
Cross-sectional analysis of NHANES 2015-2020 with DEXA body composition data

### IRI Definition
**IRI = (−z_hs-CRP) + z_Albumin + z_ALMI**

Where:
- hs-CRP: High-sensitivity C-reactive protein (mg/L) — inverted so higher = better
- Albumin: Serum albumin (g/dL) — nutritional reserve marker
- ALMI: Appendicular Lean Mass Index (z-score) — muscle mass reserve
  - *Note: ALMI = (arm + leg lean mass from DEXA, excluding bone) / height²*
  - *Values shown are standardized z-scores, not raw kg/m²*

**Higher IRI indicates better inflammatory resilience**

---

## Sample Characteristics

| Characteristic | Q1 (Lowest) | Q2 | Q3 | Q4 (Highest) | p-value |
|---------------|-------------|-----|-----|--------------|---------|
| **N** | 652 | 757 | 743 | 577 | - |
| **Age, years** | 42.3 ± 11.2 | 41.4 ± 11.4 | 39.6 ± 10.9 | 34.3 ± 10.7 | <0.001 |
| **Female, %** | 68.6 | 57.5 | 40.6 | 25.1 | <0.001 |
| **BMI, kg/m²** | 29.5 ± 7.0 | 29.2 ± 6.2 | 29.2 ± 6.7 | 27.4 ± 6.3 | <0.001 |
| **hs-CRP, mg/L** | 4.08 ± 2.62 | 2.62 ± 2.07 | 1.77 ± 1.75 | 0.77 ± 1.12 | <0.001 |
| **Albumin, g/dL** | 4.12 ± 0.28 | 4.32 ± 0.24 | 4.47 ± 0.22 | 4.70 ± 0.23 | <0.001 |
| **ALMI z-score** | -0.40 ± 1.09 | 0.22 ± 0.83 | 0.49 ± 0.77 | 0.53 ± 0.81 | <0.001 |
| **Diabetes, %** | 15.6 | 11.8 | 9.6 | 5.7 | <0.001 |
| **Hypertension, %** | 41.0 | 40.3 | 39.4 | 33.1 | 0.20 |
| **CVD history, %** | 5.4 | 3.0 | 3.8 | 2.3 | 0.12 |
| **Current smoker, %** | 25.8 | 18.7 | 21.9 | 16.5 | 0.03 |

---

## Primary Outcomes: Functional Status

### Prevalence by IRI Quartile (Survey-Weighted)

| Outcome | Q1 (Lowest) | Q2 | Q3 | Q4 (Highest) |
|---------|-------------|-----|-----|--------------|
| **Fair/Poor Self-Rated Health** | 19.2% | 17.5% | 13.8% | 9.2% |
| **Difficulty Walking ¼ Mile** | 12.4% | 8.7% | 7.8% | 2.5% |
| **Depression (PHQ-9 ≥10)** | 8.5% | 7.0% | 6.6% | 5.3% |

### Multivariable Logistic Regression (Adjusted for age, sex, race/ethnicity)

| Outcome | OR per 1-unit IRI (95% CI) | p-value | OR Q1 vs Q4 (95% CI) | p-value |
|---------|---------------------------|---------|----------------------|---------|
| **Fair/Poor Self-Rated Health** | 0.81 (0.74–0.89) | **<0.001** | 2.07 (1.42–3.01) | **0.004** |
| **Difficulty Walking ¼ Mile** | 0.78 (0.67–0.91) | **0.005** | 4.51 (1.96–10.42) | **0.006** |
| **Depression (PHQ-9 ≥10)** | 0.90 (0.77–1.05) | 0.14 | 1.40 (0.79–2.49) | 0.19 |

---

## Key Findings

1. **Self-Rated Health**: Each 1-unit increase in IRI associated with **19% lower odds** of fair/poor health (OR=0.81, p<0.001). Lowest quartile had **2.1x higher odds** of poor health vs highest quartile.

2. **Mobility Limitations**: Each 1-unit IRI increase associated with **22% lower odds** of difficulty walking (OR=0.78, p=0.005). Lowest quartile had **4.5x higher odds** of walking difficulty.

3. **Depression**: Trend toward association with IRI (OR=0.90) but not statistically significant (p=0.14).

4. **Gradient Effect**: Clear dose-response relationship across quartiles for both self-rated health and mobility.

---

## Exploratory: Mortality (Underpowered)

- **Sample**: 2,729 participants with DEXA
- **Deaths**: 20 (0.7%)
- **Mean follow-up**: 3.5 years
- **Finding**: Insufficient events for powered mortality analysis
- **Note**: Effect estimates may appear large due to short follow-up; this is exploratory only

---

## Limitations

1. **Cross-sectional design**: Cannot establish causality for IRI-outcome associations
2. **DEXA subsample**: Restricted to participants with body composition data (younger, healthier)
3. **Short mortality follow-up**: Only 20 deaths; mortality analysis is exploratory
4. **IRI is exploratory**: This index is proposed as an exploratory composite, not a validated clinical score
5. **ALM from DEXA**: Sum of arm + leg lean mass from DEXA, excluding bone, divided by height²

---

## Figures and Tables Generated

### Tables
- `table1_baseline_characteristics.csv` — Demographics by IRI quartile
- `table2_functional_outcomes.csv` — ORs and prevalence for outcomes
- `table3_iri_components.csv` — IRI component means by quartile

### Figures
- `figure1_forest_plot.pdf/png` — Forest plot of Q1 vs Q4 ORs
- `figure2_prevalence_by_quartile.pdf/png` — Bar charts of outcome prevalence
- `figure3_iri_components.pdf/png` — IRI component profiles by quartile

---

## Conclusion

The Inflammatory Resilience Index (IRI), combining inflammation (hs-CRP), nutritional reserve (albumin), and muscle mass (ALMI from DEXA), is significantly associated with self-rated health and mobility limitations in U.S. adults. Adults in the lowest IRI quartile have 2-4.5× higher odds of poor functional outcomes compared to those in the highest quartile. These findings support IRI as a marker of integrated physiologic resilience, though validation in prospective cohorts with adequate mortality events is needed.

