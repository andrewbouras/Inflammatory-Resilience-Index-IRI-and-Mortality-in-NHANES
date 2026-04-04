"""
Modified IRI Study - Cohort Construction

Modified IRI = (-z_log_CRP) + z_Albumin + z_ALM

Where:
- z_log_CRP: z-score of log-transformed hs-CRP (inverted so higher = less inflammation)
- z_Albumin: z-score of serum albumin (higher = better nutritional status)
- z_ALM: z-score of appendicular lean mass, height-adjusted, sex-specific

Higher IRI = better inflammatory resilience
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"


def load_xpt(filepath: Path) -> pd.DataFrame:
    """Load XPT file."""
    try:
        return pd.read_sas(filepath, format='xport', encoding='latin1')
    except Exception as e:
        print(f"  Warning: Could not load {filepath.name}: {e}")
        return pd.DataFrame()


def find_file(cycle_dir: Path, pattern: str) -> Path:
    """Find file matching pattern."""
    matches = list(cycle_dir.glob(f"*{pattern}*"))
    return matches[0] if matches else None


def calculate_egfr_ckdepi2021(scr: pd.Series, age: pd.Series, sex: pd.Series) -> pd.Series:
    """
    Calculate eGFR using CKD-EPI 2021 equation (race-free).
    scr: serum creatinine in mg/dL
    age: age in years
    sex: 1=Male, 2=Female
    """
    kappa = np.where(sex == 2, 0.7, 0.9)
    alpha = np.where(sex == 2, -0.241, -0.302)
    female_mult = np.where(sex == 2, 1.012, 1.0)
    
    scr_kappa = scr / kappa
    term1 = 142 * (np.minimum(scr_kappa, 1) ** alpha)
    term2 = np.maximum(scr_kappa, 1) ** (-1.200)
    term3 = 0.9938 ** age
    
    return term1 * term2 * term3 * female_mult


def process_cycle(cycle: str, cycle_dir: Path) -> pd.DataFrame:
    """Process a single NHANES cycle."""
    print(f"\n{'='*60}")
    print(f"Processing {cycle}")
    print('='*60)
    
    if not cycle_dir.exists():
        print(f"  Directory not found")
        return pd.DataFrame()
    
    # Load demographics
    demo_file = find_file(cycle_dir, "DEMO")
    if not demo_file:
        return pd.DataFrame()
    
    df = load_xpt(demo_file)
    print(f"  Loaded {len(df):,} participants from DEMO")
    
    # Merge components
    components = [
        ("HSCRP", "hs-CRP"),
        ("BIOPRO", "Biochemistry (albumin/creatinine)"),
        ("DXX", "DEXA Whole Body"),
        ("BMX", "Body measures"),
        ("BPX", "Blood pressure"),
        ("BPXO", "Blood pressure (oscillometric)"),
        ("BPQ", "BP questionnaire"),
        ("DIQ", "Diabetes"),
        ("GHB", "HbA1c"),
        ("GLU", "Glucose"),
        ("TCHOL", "Total cholesterol"),
        ("HDL", "HDL"),
        ("TRIGLY", "Triglycerides"),
        ("SMQ", "Smoking"),
        ("MCQ", "Medical conditions"),
        # Functional outcomes
        ("HUQ", "Health status (self-rated)"),
        ("PFQ", "Physical functioning"),
        ("DPQ", "Depression (PHQ-9)"),
    ]
    
    for pattern, desc in components:
        file_path = find_file(cycle_dir, pattern)
        if file_path:
            comp_df = load_xpt(file_path)
            if 'SEQN' in comp_df.columns and len(comp_df) > 0:
                df = df.merge(comp_df, on='SEQN', how='left', suffixes=('', f'_{pattern}'))
                print(f"  Merged {desc}: {len(comp_df):,}")
    
    df['cycle'] = cycle
    return df


def calculate_alm(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Appendicular Lean Mass (ALM) from DEXA components.
    ALM = Left Arm + Right Arm + Left Leg + Right Leg lean mass (excluding BMC)
    
    Variables:
    - DXDLALE: Left arm lean (excl BMC)
    - DXDRALE: Right arm lean (excl BMC)
    - DXDLLLE: Left leg lean (excl BMC)
    - DXDRLLE: Right leg lean (excl BMC)
    """
    alm_cols = ['DXDLALE', 'DXDRALE', 'DXDLLLE', 'DXDRLLE']
    
    # Check which columns exist
    available = [c for c in alm_cols if c in df.columns]
    
    if len(available) == 4:
        # Sum in grams, convert to kg (require all 4 limbs to be non-null)
        alm_g = df[available].sum(axis=1, min_count=4)
        alm_kg = alm_g / 1000
        return alm_kg
    else:
        print(f"  Warning: Missing ALM columns. Have: {available}")
        return pd.Series([np.nan] * len(df), index=df.index)


def build_iri_cohort(df: pd.DataFrame) -> pd.DataFrame:
    """Build the Modified IRI cohort with all derived variables."""
    print("\n" + "="*60)
    print("Building Modified IRI Cohort")
    print("="*60)
    
    # Demographics
    df['age'] = df['RIDAGEYR']
    df['sex'] = df['RIAGENDR']  # 1=Male, 2=Female
    df['female'] = (df['sex'] == 2).astype(int)
    df['race_eth'] = df.get('RIDRETH3', pd.Series([np.nan] * len(df), index=df.index))
    
    # Socioeconomic variables (for sensitivity analyses)
    # Education: 1=<9th, 2=9-11th, 3=HS/GED, 4=Some college/AA, 5=College+
    df['education'] = df.get('DMDEDUC2', pd.Series([np.nan] * len(df), index=df.index))
    df.loc[df['education'] > 5, 'education'] = np.nan  # 7=Refused, 9=Don't know
    # Binary: Less than HS vs HS or higher
    df['edu_less_than_hs'] = (df['education'].isin([1, 2])).astype(float)
    df.loc[df['education'].isna(), 'edu_less_than_hs'] = np.nan
    print(f"  Education available: {df['education'].notna().sum():,}")
    
    # Poverty-Income Ratio: 0-5 (top-coded at 5)
    df['pir'] = df.get('INDFMPIR', pd.Series([np.nan] * len(df), index=df.index))
    # Binary: Below poverty (<1) vs at/above poverty (>=1)
    df['below_poverty'] = (df['pir'] < 1).astype(float)
    df.loc[df['pir'].isna(), 'below_poverty'] = np.nan
    print(f"  PIR available: {df['pir'].notna().sum():,}")
    
    # Survey design
    df['mec_weight'] = df.get('WTMEC2YR', df.get('WTMECPRP', pd.Series([np.nan] * len(df), index=df.index)))
    df['psu'] = df['SDMVPSU']
    df['strata'] = df['SDMVSTRA']
    
    # ==========================================================================
    # IRI COMPONENTS
    # ==========================================================================
    
    # 1. hs-CRP (mg/L)
    df['hscrp'] = df.get('LBXHSCRP', pd.Series([np.nan] * len(df), index=df.index))
    print(f"  hs-CRP available: {df['hscrp'].notna().sum():,}")
    
    # 2. Serum Albumin (g/dL)
    df['albumin'] = df.get('LBXSAL', pd.Series([np.nan] * len(df), index=df.index))
    print(f"  Albumin available: {df['albumin'].notna().sum():,}")
    
    # 3. Appendicular Lean Mass
    df['alm_kg'] = calculate_alm(df)
    print(f"  ALM available: {df['alm_kg'].notna().sum():,}")
    
    # Height for ALM adjustment
    df['height_m'] = df.get('BMXHT', pd.Series([np.nan] * len(df), index=df.index)) / 100
    
    # ALM index (ALM / height^2) - similar to SMI (skeletal muscle index)
    # Treat ALM=0 as missing (DEXA not performed, not true zero)
    df['alm_kg'] = df['alm_kg'].replace(0, np.nan)
    df['almi'] = df['alm_kg'] / (df['height_m'] ** 2)
    
    # ==========================================================================
    # Z-SCORE CALCULATIONS
    # ==========================================================================
    
    print("\n  Calculating z-scores...")

    # Preliminary eligibility mask: compute z-score means/SDs on the analytic
    # sample only (age >= 20, CRP <= 10, non-missing components and weights).
    # This prevents pediatric participants and acute inflammation (CRP > 10)
    # from influencing the standardization parameters.
    eligible_for_zscore = (
        (df['age'] >= 20) &
        (df['hscrp'] <= 10) &
        df['hscrp'].notna() &
        df['albumin'].notna() &
        df['almi'].notna() &
        df['mec_weight'].notna()
    )
    print(f"  Eligible for z-score computation: {eligible_for_zscore.sum():,}")

    # z_log_CRP (inverted: multiply by -1 so higher = less inflammation)
    df['log_hscrp'] = np.log(df['hscrp'].replace(0, np.nan))
    mean_log_crp = df.loc[eligible_for_zscore, 'log_hscrp'].mean()
    std_log_crp = df.loc[eligible_for_zscore, 'log_hscrp'].std()
    df['z_crp'] = (df['log_hscrp'] - mean_log_crp) / std_log_crp
    df['z_crp_inv'] = df['z_crp'] * -1  # Inverted

    # z_Albumin
    mean_alb = df.loc[eligible_for_zscore, 'albumin'].mean()
    std_alb = df.loc[eligible_for_zscore, 'albumin'].std()
    df['z_albumin'] = (df['albumin'] - mean_alb) / std_alb

    # z_ALMI (sex-specific)
    df['z_almi'] = np.nan
    almi_params = {}
    for sex_val in [1, 2]:
        mask = (df['sex'] == sex_val) & eligible_for_zscore
        subset = df.loc[mask, 'almi']
        mean_almi = subset.mean()
        std_almi = subset.std()
        almi_params[sex_val] = {'mean': mean_almi, 'std': std_almi}
        if std_almi > 0:
            # Apply z-scores to ALL participants of this sex (using eligible means/SDs)
            sex_mask = df['sex'] == sex_val
            df.loc[sex_mask, 'z_almi'] = (df.loc[sex_mask, 'almi'] - mean_almi) / std_almi

    # Save derivation cohort standardization parameters for validation use
    import json
    zscore_params = {
        'log_crp': {'mean': float(mean_log_crp), 'std': float(std_log_crp)},
        'albumin': {'mean': float(mean_alb), 'std': float(std_alb)},
        'almi_male': {'mean': float(almi_params[1]['mean']), 'std': float(almi_params[1]['std'])},
        'almi_female': {'mean': float(almi_params[2]['mean']), 'std': float(almi_params[2]['std'])},
    }
    params_path = DATA_PROCESSED / "derivation_zscore_params.json"
    with open(params_path, 'w') as f:
        json.dump(zscore_params, f, indent=2)
    print(f"  Saved z-score standardization parameters to {params_path}")
    
    # ==========================================================================
    # MODIFIED IRI CONSTRUCTION
    # ==========================================================================
    
    df['iri'] = df['z_crp_inv'] + df['z_albumin'] + df['z_almi']
    print(f"  IRI calculated for: {df['iri'].notna().sum():,}")
    
    # IRI quartiles (computed on eligible subset only, so quartile boundaries
    # reflect the analytic population, not those who will be excluded)
    df['iri_quartile'] = np.nan
    elig_iri = df.loc[eligible_for_zscore & df['iri'].notna(), 'iri']
    df.loc[elig_iri.index, 'iri_quartile'] = pd.qcut(
        elig_iri, q=4, labels=['Q1', 'Q2', 'Q3', 'Q4']
    )
    
    # ==========================================================================
    # COVARIATES
    # ==========================================================================
    
    # BMI
    df['bmi'] = df.get('BMXBMI', pd.Series([np.nan] * len(df), index=df.index))
    df['obesity'] = (df['bmi'] >= 30).astype(int)
    
    # Blood pressure
    sbp_cols = [c for c in df.columns if 'BPXSY' in c or 'BPXOSY' in c]
    dbp_cols = [c for c in df.columns if 'BPXDI' in c or 'BPXODI' in c]
    df['mean_sbp'] = df[sbp_cols].mean(axis=1) if sbp_cols else np.nan
    df['mean_dbp'] = df[dbp_cols].mean(axis=1) if dbp_cols else np.nan
    
    bp_med = df.get('BPQ040A', pd.Series([np.nan] * len(df), index=df.index))
    df['hypertension'] = ((df['mean_sbp'] >= 130) | (df['mean_dbp'] >= 80) | (bp_med == 1)).astype(float)
    
    # Diabetes
    hba1c = df.get('LBXGH', pd.Series([np.nan] * len(df), index=df.index))
    glucose = df.get('LBXGLU', pd.Series([np.nan] * len(df), index=df.index))
    dm_told = df.get('DIQ010', pd.Series([np.nan] * len(df), index=df.index))
    df['hba1c'] = hba1c
    df['diabetes'] = ((hba1c >= 6.5) | (glucose >= 126) | (dm_told == 1)).astype(float)
    
    # Smoking
    smoke_100 = df.get('SMQ020', pd.Series([np.nan] * len(df), index=df.index))
    smoke_now = df.get('SMQ040', pd.Series([np.nan] * len(df), index=df.index))
    df['smoking_status'] = np.nan
    df.loc[smoke_100 == 2, 'smoking_status'] = 0  # Never
    df.loc[(smoke_100 == 1) & smoke_now.isin([1, 2]), 'smoking_status'] = 2  # Current
    df.loc[(smoke_100 == 1) & (smoke_now == 3), 'smoking_status'] = 1  # Former
    df['current_smoker'] = (df['smoking_status'] == 2).astype(int)
    
    # eGFR
    scr = df.get('LBXSCR', pd.Series([np.nan] * len(df), index=df.index))
    df['egfr'] = calculate_egfr_ckdepi2021(scr, df['age'], df['sex'])
    df['ckd'] = (df['egfr'] < 60).astype(int)
    
    # CVD history
    chd = df.get('MCQ160C', pd.Series([2] * len(df), index=df.index))
    mi = df.get('MCQ160E', pd.Series([2] * len(df), index=df.index))
    stroke = df.get('MCQ160F', pd.Series([2] * len(df), index=df.index))
    angina = df.get('MCQ160D', pd.Series([2] * len(df), index=df.index))
    chf = df.get('MCQ160B', pd.Series([2] * len(df), index=df.index))
    df['cvd_history'] = ((chd == 1) | (mi == 1) | (stroke == 1) | (angina == 1) | (chf == 1)).astype(float)
    
    # Cancer
    cancer = df.get('MCQ220', pd.Series([2] * len(df), index=df.index))
    df['cancer_history'] = (cancer == 1).astype(int)
    
    # ==========================================================================
    # FUNCTIONAL OUTCOMES
    # ==========================================================================
    
    # Self-rated health (HUQ010): 1=Excellent, 2=Very good, 3=Good, 4=Fair, 5=Poor
    df['self_rated_health'] = df.get('HUQ010', pd.Series([np.nan] * len(df), index=df.index))
    df.loc[df['self_rated_health'] > 5, 'self_rated_health'] = np.nan  # 7,9 = refused/don't know
    # Binary: Fair/Poor vs Excellent/Very good/Good
    df['poor_health'] = (df['self_rated_health'] >= 4).astype(float)
    df.loc[df['self_rated_health'].isna(), 'poor_health'] = np.nan
    
    # Mobility limitations (PFQ054): Difficulty walking without special equipment
    # "Because of a health problem, do you have difficulty walking without
    #  using any special equipment?"
    # 1 = Yes (has difficulty), 2 = No, 7 = Refused, 9 = Don't know
    pfq054 = df.get('PFQ054', pd.Series([np.nan] * len(df), index=df.index))
    df['difficulty_walking'] = (pfq054 == 1).astype(float)
    df.loc[pfq054.isna() | (pfq054 > 2), 'difficulty_walking'] = np.nan
    
    # Note: difficulty_stairs removed — was duplicate of difficulty_walking (both PFQ054)
    
    # PHQ-9 Depression score (DPQ010-DPQ090, each 0-3)
    phq_items = ['DPQ010', 'DPQ020', 'DPQ030', 'DPQ040', 'DPQ050', 
                 'DPQ060', 'DPQ070', 'DPQ080', 'DPQ090']
    phq_cols = [c for c in phq_items if c in df.columns]
    if phq_cols:
        # Replace 7,9 with NaN
        for col in phq_cols:
            df.loc[df[col] > 3, col] = np.nan
        df['phq9_score'] = df[phq_cols].sum(axis=1, min_count=9)  # require all 9
        # Depression: PHQ-9 >= 10 (moderate-severe)
        df['depression'] = (df['phq9_score'] >= 10).astype(float)
        df.loc[df['phq9_score'].isna(), 'depression'] = np.nan
    else:
        df['phq9_score'] = np.nan
        df['depression'] = np.nan
    
    print(f"  Self-rated health available: {df['self_rated_health'].notna().sum():,}")
    print(f"  Mobility limitation data: {df['difficulty_walking'].notna().sum():,}")
    print(f"  PHQ-9 available: {df['phq9_score'].notna().sum():,}")
    
    # ==========================================================================
    # ELIGIBILITY
    # ==========================================================================
    
    print("\n  Applying eligibility criteria...")
    
    df['age_eligible'] = (df['age'] >= 20).astype(int)
    df['iri_available'] = df['iri'].notna().astype(int)
    df['crp_valid'] = (df['hscrp'] <= 10).astype(int)  # Exclude acute inflammation
    
    df['eligible'] = (
        df['age_eligible'] & 
        df['iri_available'] & 
        df['crp_valid'] &
        df['mec_weight'].notna()
    ).astype(int)
    
    print(f"  Age ≥20: {df['age_eligible'].sum():,}")
    print(f"  IRI available: {df['iri_available'].sum():,}")
    print(f"  hs-CRP ≤10: {df['crp_valid'].sum():,}")
    print(f"  Final eligible: {df['eligible'].sum():,}")
    
    return df


def main():
    print("\n" + "="*60)
    print("MODIFIED IRI STUDY - COHORT CONSTRUCTION")
    print("IRI = (-z_CRP) + z_Albumin + z_ALM")
    print("="*60)
    
    # Only 2015-2016 has whole-body DEXA (required for ALMI component of IRI).
    # 2017-2020 lacks DEXA data, so all participants would be ineligible.
    cycles = [
        ("2015-2016", DATA_RAW / "2015-2016"),
    ]
    
    all_data = []
    for cycle_name, cycle_dir in cycles:
        df = process_cycle(cycle_name, cycle_dir)
        if len(df) > 0:
            all_data.append(df)
    
    if not all_data:
        print("\nNo data loaded. Run 01_download_data.py first.")
        return
    
    combined = pd.concat(all_data, ignore_index=True)
    print(f"\nCombined: {len(combined):,} participants")
    
    combined = build_iri_cohort(combined)
    
    # Export key variables
    export_vars = [
        'SEQN', 'cycle',
        'mec_weight', 'psu', 'strata',
        'age', 'sex', 'female', 'race_eth',
        'education', 'edu_less_than_hs', 'pir', 'below_poverty',
        'hscrp', 'albumin', 'alm_kg', 'almi',
        'z_crp_inv', 'z_albumin', 'z_almi',
        'iri', 'iri_quartile',
        'bmi', 'obesity', 'height_m',
        'mean_sbp', 'mean_dbp', 'hypertension',
        'hba1c', 'diabetes',
        'smoking_status', 'current_smoker',
        'egfr', 'ckd',
        'cvd_history', 'cancer_history',
        # Functional outcomes
        'self_rated_health', 'poor_health',
        'difficulty_walking',
        'phq9_score', 'depression',
        'eligible',
    ]
    
    export_vars = [v for v in export_vars if v in combined.columns]
    
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    
    output_path = DATA_PROCESSED / "iri_cohort.parquet"
    combined[export_vars].to_parquet(output_path)
    print(f"\nSaved: {output_path}")
    
    csv_path = DATA_PROCESSED / "iri_cohort.csv"
    combined[export_vars].to_csv(csv_path, index=False)
    print(f"Saved: {csv_path}")
    
    # Save eligible-only subset for functional analysis scripts (05, 06, 07, 09)
    eligible = combined[combined['eligible'] == 1]
    functional_path = DATA_PROCESSED / "iri_functional_cohort.csv"
    eligible[export_vars].to_csv(functional_path, index=False)
    print(f"Saved: {functional_path} (N={len(eligible):,} eligible)")

    # Summary
    print("\n" + "="*60)
    print("COHORT SUMMARY")
    print("="*60)
    print(f"Total participants: {len(combined):,}")
    print(f"Eligible for analysis: {len(eligible):,}")
    print(f"\nIRI distribution (eligible):")
    print(eligible['iri'].describe())
    print(f"\nIRI by quartile:")
    print(eligible.groupby('iri_quartile')['iri'].agg(['count', 'mean', 'min', 'max']))


if __name__ == "__main__":
    main()

