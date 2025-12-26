"""
IRI Study - Variable Harmonization and IRI Construction
Processes NHANES 2011-2014 and 2017-2020 data for the Inflammatory Resilience Index study

IRI = (-z_hsCRP) + z_albumin + z_grip_strength
Higher IRI = greater inflammatory resilience
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
import warnings

warnings.filterwarnings('ignore')

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_MORTALITY = PROJECT_ROOT / "data" / "mortality"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

# =============================================================================
# VARIABLE MAPPINGS ACROSS CYCLES
# =============================================================================

# Demographics
DEMO_VARS = {
    "id": "SEQN",
    "age": "RIDAGEYR",
    "sex": "RIAGENDR",           # 1=Male, 2=Female
    "race_eth": "RIDRETH3",      # 6-level race/ethnicity (2011+)
    "education": "DMDEDUC2",     # Adults 20+ education
    "marital": "DMDMARTL",       # Marital status
    "pir": "INDFMPIR",           # Poverty income ratio
    "pregnant": "RIDEXPRG",      # Pregnancy status (1=Yes, 2=No, 3=Cannot determine)
    "weight_mec": "WTMEC2YR",    # 2-year MEC weight
    "weight_interview": "WTINT2YR",
    "psu": "SDMVPSU",
    "strata": "SDMVSTRA",
}

# Pre-pandemic 2017-2020 uses different weight names
DEMO_VARS_PREPANDEMIC = {
    **DEMO_VARS,
    "weight_mec": "WTMECPRP",    # Pre-pandemic MEC weight
    "weight_interview": "WTINTPRP",
}

# Grip strength (MGX files)
GRIP_VARS = {
    "grip_max_combined": "MGXH1T1",  # Will compute max across all trials
    # Individual trials - right hand
    "grip_r1": "MGDEXSTS",           # Exam status (will need to check)
    # The actual grip readings
}

# hs-CRP (HSCRP files)
CRP_VARS = {
    "hscrp": "LBXHSCRP",         # hs-CRP (mg/L)
}

# Albumin and creatinine (BIOPRO files)
BIOPRO_VARS = {
    "albumin": "LBXSAL",         # Serum albumin (g/dL)
    "creatinine": "LBXSCR",      # Serum creatinine (mg/dL)
    "bun": "LBXSBU",             # Blood urea nitrogen
}

# Body measures
BMX_VARS = {
    "bmi": "BMXBMI",
    "weight_kg": "BMXWT",
    "height_cm": "BMXHT",
    "waist_cm": "BMXWAIST",
}

# Blood pressure examination
# Note: 2017-2020 uses oscillometric (BPXO) with different variable names
BPX_VARS_2011_2014 = {
    "sbp1": "BPXSY1",
    "sbp2": "BPXSY2",
    "sbp3": "BPXSY3",
    "sbp4": "BPXSY4",
    "dbp1": "BPXDI1",
    "dbp2": "BPXDI2",
    "dbp3": "BPXDI3",
    "dbp4": "BPXDI4",
}

BPX_VARS_2017_2020 = {
    "sbp1": "BPXOSY1",
    "sbp2": "BPXOSY2",
    "sbp3": "BPXOSY3",
    "dbp1": "BPXODI1",
    "dbp2": "BPXODI2",
    "dbp3": "BPXODI3",
}

# Blood pressure questionnaire
BPQ_VARS = {
    "htn_told": "BPQ020",        # Ever told you have high BP
    "bp_med": "BPQ040A",         # Taking prescribed BP medication
}

# Diabetes
DIQ_VARS = {
    "diabetes_told": "DIQ010",   # Doctor told you have diabetes
    "insulin_use": "DIQ050",     # Taking insulin now
    "oral_dm_med": "DIQ070",     # Taking diabetic pills
}

# HbA1c and glucose
LAB_DIABETES_VARS = {
    "hba1c": "LBXGH",            # Glycohemoglobin (%)
    "glucose_fasting": "LBXGLU", # Fasting glucose (mg/dL)
}

# Lipids
LIPID_VARS = {
    "tchol": "LBXTC",            # Total cholesterol
    "hdl": "LBDHDD",             # Direct HDL
    "trigly": "LBXTR",           # Triglycerides
}

# Smoking
SMQ_VARS = {
    "smoke_100": "SMQ020",       # Smoked at least 100 cigarettes in life
    "smoke_now": "SMQ040",       # Do you now smoke (1=every day, 2=some days, 3=not at all)
}

# Physical activity (GPAQ format for 2011+)
PAQ_VARS = {
    "vigorous_work": "PAQ605",
    "vigorous_work_days": "PAQ610",
    "vigorous_work_min": "PAD615",
    "moderate_work": "PAQ620",
    "moderate_work_days": "PAQ625",
    "moderate_work_min": "PAD630",
    "vigorous_rec": "PAQ650",
    "vigorous_rec_days": "PAQ655",
    "vigorous_rec_min": "PAD660",
    "moderate_rec": "PAQ665",
    "moderate_rec_days": "PAQ670",
    "moderate_rec_min": "PAD675",
}

# Medical conditions (CVD history)
MCQ_VARS = {
    "chf_told": "MCQ160B",       # Ever told you had CHF
    "chd_told": "MCQ160C",       # Ever told you had CHD
    "angina_told": "MCQ160D",    # Ever told you had angina
    "mi_told": "MCQ160E",        # Ever told you had heart attack
    "stroke_told": "MCQ160F",    # Ever told you had stroke
    "cancer_told": "MCQ220",     # Ever told you had cancer
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def load_xpt(filepath: Path) -> pd.DataFrame:
    """Load XPT file into pandas DataFrame."""
    try:
        return pd.read_sas(filepath, format='xport', encoding='latin1')
    except Exception as e:
        print(f"  Warning: Could not load {filepath.name}: {e}")
        return pd.DataFrame()


def find_file(cycle_dir: Path, pattern: str) -> Optional[Path]:
    """Find a file matching pattern (case-insensitive)."""
    matches = list(cycle_dir.glob(f"*{pattern}*")) + list(cycle_dir.glob(f"*{pattern.lower()}*"))
    if matches:
        return matches[0]
    return None


def compute_max_grip_strength(df: pd.DataFrame) -> pd.Series:
    """
    Compute maximum grip strength across all trials for both hands.
    MGX file contains:
    - MGDEXSTS: Exam status
    - MGXH1T1, MGXH1T2, MGXH1T3: Hand 1 trials 1-3
    - MGXH2T1, MGXH2T2, MGXH2T3: Hand 2 trials 1-3
    """
    grip_cols = ['MGXH1T1', 'MGXH1T2', 'MGXH1T3', 'MGXH2T1', 'MGXH2T2', 'MGXH2T3']
    
    # Get available columns
    available_cols = [c for c in grip_cols if c in df.columns]
    
    if not available_cols:
        print("  Warning: No grip strength columns found")
        return pd.Series([np.nan] * len(df), index=df.index)
    
    # Compute max across all available trials
    grip_values = df[available_cols].copy()
    
    # Replace invalid values (0, negative) with NaN
    grip_values = grip_values.replace(0, np.nan)
    grip_values[grip_values < 0] = np.nan
    
    return grip_values.max(axis=1)


def compute_egfr_ckdepi_2021(creatinine: pd.Series, age: pd.Series, sex: pd.Series) -> pd.Series:
    """
    Compute eGFR using CKD-EPI 2021 race-free equation.
    
    eGFR = 142 × min(Scr/κ, 1)^α × max(Scr/κ, 1)^-1.200 × 0.9938^age × (1.012 if female)
    
    Where:
    - κ = 0.7 (female) or 0.9 (male)
    - α = -0.241 (female) or -0.302 (male)
    """
    # Initialize result
    egfr = pd.Series([np.nan] * len(creatinine), index=creatinine.index)
    
    # Female (sex == 2)
    female_mask = sex == 2
    kappa_f = 0.7
    alpha_f = -0.241
    
    scr_kappa_f = creatinine[female_mask] / kappa_f
    min_term_f = np.minimum(scr_kappa_f, 1) ** alpha_f
    max_term_f = np.maximum(scr_kappa_f, 1) ** (-1.200)
    age_term_f = 0.9938 ** age[female_mask]
    egfr.loc[female_mask] = 142 * min_term_f * max_term_f * age_term_f * 1.012
    
    # Male (sex == 1)
    male_mask = sex == 1
    kappa_m = 0.9
    alpha_m = -0.302
    
    scr_kappa_m = creatinine[male_mask] / kappa_m
    min_term_m = np.minimum(scr_kappa_m, 1) ** alpha_m
    max_term_m = np.maximum(scr_kappa_m, 1) ** (-1.200)
    age_term_m = 0.9938 ** age[male_mask]
    egfr.loc[male_mask] = 142 * min_term_m * max_term_m * age_term_m
    
    return egfr


def compute_ldl_friedewald(tchol: pd.Series, hdl: pd.Series, trigly: pd.Series) -> pd.Series:
    """
    Calculate LDL using Friedewald equation: LDL = TC - HDL - (TG/5)
    Only valid when TG < 400 mg/dL.
    """
    ldl = tchol - hdl - (trigly / 5)
    ldl[trigly >= 400] = np.nan
    return ldl


def compute_mean_bp(df: pd.DataFrame, cycle: str) -> tuple:
    """Compute mean SBP and DBP from available readings."""
    if "2017" in cycle:
        sbp_cols = [c for c in ['BPXOSY1', 'BPXOSY2', 'BPXOSY3'] if c in df.columns]
        dbp_cols = [c for c in ['BPXODI1', 'BPXODI2', 'BPXODI3'] if c in df.columns]
    else:
        sbp_cols = [c for c in ['BPXSY1', 'BPXSY2', 'BPXSY3', 'BPXSY4'] if c in df.columns]
        dbp_cols = [c for c in ['BPXDI1', 'BPXDI2', 'BPXDI3', 'BPXDI4'] if c in df.columns]
    
    mean_sbp = df[sbp_cols].mean(axis=1) if sbp_cols else pd.Series([np.nan] * len(df), index=df.index)
    mean_dbp = df[dbp_cols].mean(axis=1) if dbp_cols else pd.Series([np.nan] * len(df), index=df.index)
    
    return mean_sbp, mean_dbp


def define_hypertension(df: pd.DataFrame) -> pd.Series:
    """
    Define hypertension: SBP >= 130 OR DBP >= 80 OR on BP medication.
    """
    sbp = df.get('mean_sbp', pd.Series([np.nan] * len(df)))
    dbp = df.get('mean_dbp', pd.Series([np.nan] * len(df)))
    bp_med = df.get('BPQ040A', pd.Series([np.nan] * len(df)))
    
    htn = ((sbp >= 130) | (dbp >= 80) | (bp_med == 1)).astype(float)
    htn[htn == 0] = np.where(
        sbp.isna() & dbp.isna() & bp_med.isna(),
        np.nan,
        0
    )[htn == 0]
    
    return htn


def define_diabetes(df: pd.DataFrame) -> pd.Series:
    """
    Define diabetes: HbA1c >= 6.5% OR FPG >= 126 OR told by doctor OR on meds.
    """
    hba1c = df.get('LBXGH', pd.Series([np.nan] * len(df)))
    glucose = df.get('LBXGLU', pd.Series([np.nan] * len(df)))
    told = df.get('DIQ010', pd.Series([np.nan] * len(df)))
    insulin = df.get('DIQ050', pd.Series([np.nan] * len(df)))
    oral_med = df.get('DIQ070', pd.Series([np.nan] * len(df)))
    
    dm = ((hba1c >= 6.5) | 
          (glucose >= 126) | 
          (told == 1) |
          (insulin == 1) | 
          (oral_med == 1)).astype(float)
    
    return dm


def define_smoking_status(df: pd.DataFrame) -> pd.Series:
    """
    Define smoking status: 0=Never, 1=Former, 2=Current.
    """
    smoke_100 = df.get('SMQ020', pd.Series([np.nan] * len(df)))
    smoke_now = df.get('SMQ040', pd.Series([np.nan] * len(df)))
    
    status = pd.Series([np.nan] * len(df), index=df.index)
    
    # Never: didn't smoke 100+ cigarettes (SMQ020 = 2)
    status[smoke_100 == 2] = 0
    
    # Current: smoked 100+ and currently smokes (SMQ040 = 1 or 2)
    status[(smoke_100 == 1) & smoke_now.isin([1, 2])] = 2
    
    # Former: smoked 100+ but not at all now (SMQ040 = 3)
    status[(smoke_100 == 1) & (smoke_now == 3)] = 1
    
    return status


def define_cvd_history(df: pd.DataFrame) -> pd.Series:
    """
    Define prevalent CVD: CHF, CHD, angina, MI, or stroke.
    """
    chf = df.get('MCQ160B', pd.Series([2] * len(df)))
    chd = df.get('MCQ160C', pd.Series([2] * len(df)))
    angina = df.get('MCQ160D', pd.Series([2] * len(df)))
    mi = df.get('MCQ160E', pd.Series([2] * len(df)))
    stroke = df.get('MCQ160F', pd.Series([2] * len(df)))
    
    cvd = ((chf == 1) | (chd == 1) | (angina == 1) | (mi == 1) | (stroke == 1)).astype(float)
    
    return cvd


def compute_physical_activity_met_min(df: pd.DataFrame) -> pd.Series:
    """
    Compute total MET-minutes per week from GPAQ data.
    Vigorous = 8 METs, Moderate = 4 METs
    """
    met_min = pd.Series([0.0] * len(df), index=df.index)
    
    # Vigorous work
    vig_work = df.get('PAQ605', pd.Series([2] * len(df)))
    vig_work_days = df.get('PAQ610', pd.Series([0] * len(df)))
    vig_work_min = df.get('PAD615', pd.Series([0] * len(df)))
    
    vig_work_met = np.where(vig_work == 1, 
                            8 * vig_work_days.fillna(0) * vig_work_min.fillna(0), 
                            0)
    
    # Moderate work
    mod_work = df.get('PAQ620', pd.Series([2] * len(df)))
    mod_work_days = df.get('PAQ625', pd.Series([0] * len(df)))
    mod_work_min = df.get('PAD630', pd.Series([0] * len(df)))
    
    mod_work_met = np.where(mod_work == 1,
                            4 * mod_work_days.fillna(0) * mod_work_min.fillna(0),
                            0)
    
    # Vigorous recreation
    vig_rec = df.get('PAQ650', pd.Series([2] * len(df)))
    vig_rec_days = df.get('PAQ655', pd.Series([0] * len(df)))
    vig_rec_min = df.get('PAD660', pd.Series([0] * len(df)))
    
    vig_rec_met = np.where(vig_rec == 1,
                           8 * vig_rec_days.fillna(0) * vig_rec_min.fillna(0),
                           0)
    
    # Moderate recreation
    mod_rec = df.get('PAQ665', pd.Series([2] * len(df)))
    mod_rec_days = df.get('PAQ670', pd.Series([0] * len(df)))
    mod_rec_min = df.get('PAD675', pd.Series([0] * len(df)))
    
    mod_rec_met = np.where(mod_rec == 1,
                           4 * mod_rec_days.fillna(0) * mod_rec_min.fillna(0),
                           0)
    
    met_min = vig_work_met + mod_work_met + vig_rec_met + mod_rec_met
    
    # Cap at reasonable maximum (10080 = 24h * 7days)
    met_min = np.minimum(met_min, 10080)
    
    return pd.Series(met_min, index=df.index)


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def process_cycle(cycle: str) -> pd.DataFrame:
    """Process a single NHANES cycle and return harmonized data."""
    print(f"\n{'='*60}")
    print(f"Processing {cycle}")
    print('='*60)
    
    cycle_dir = DATA_RAW / cycle
    if not cycle_dir.exists():
        print(f"  Cycle directory not found: {cycle_dir}")
        return pd.DataFrame()
    
    # Determine if pre-pandemic
    is_prepandemic = "2017" in cycle
    
    # Load demographics
    demo_file = find_file(cycle_dir, "DEMO")
    if not demo_file:
        print("  No DEMO file found")
        return pd.DataFrame()
    
    df = load_xpt(demo_file)
    print(f"  Loaded {len(df):,} participants from DEMO")
    
    # Merge all required files
    file_patterns = [
        ("MGX", "Grip strength"),
        ("HSCRP", "hs-CRP"),
        ("BIOPRO", "Biochemistry"),
        ("BMX", "Body measures"),
        ("BPX" if not is_prepandemic else "BPXO", "Blood pressure exam"),
        ("BPQ", "Blood pressure questionnaire"),
        ("DIQ", "Diabetes questionnaire"),
        ("GHB", "Glycohemoglobin"),
        ("GLU", "Glucose"),
        ("TCHOL", "Total cholesterol"),
        ("HDL", "HDL cholesterol"),
        ("TRIGLY", "Triglycerides"),
        ("SMQ", "Smoking"),
        ("PAQ", "Physical activity"),
        ("MCQ", "Medical conditions"),
    ]
    
    for pattern, description in file_patterns:
        file_path = find_file(cycle_dir, pattern)
        if file_path:
            comp_df = load_xpt(file_path)
            if 'SEQN' in comp_df.columns and len(comp_df) > 0:
                df = df.merge(comp_df, on='SEQN', how='left', suffixes=('', f'_{pattern}'))
                print(f"  Merged {description}: {len(comp_df):,} records")
        else:
            print(f"  Warning: {description} file not found")
    
    # Add cycle identifier
    df['cycle'] = cycle
    df['is_prepandemic'] = is_prepandemic
    
    return df


def construct_iri(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construct the Inflammatory Resilience Index and derived variables.
    
    IRI = (-z_hsCRP) + z_albumin + z_grip_strength (sex-specific)
    """
    print("\n" + "="*60)
    print("Constructing IRI and derived variables")
    print("="*60)
    
    # Extract core IRI components
    df['hscrp'] = df.get('LBXHSCRP', pd.Series([np.nan] * len(df)))
    df['albumin'] = df.get('LBXSAL', pd.Series([np.nan] * len(df)))
    df['grip_max'] = compute_max_grip_strength(df)
    
    # Log-transform hs-CRP
    df['log_hscrp'] = np.log(df['hscrp'].replace(0, np.nan))
    
    # Compute z-scores
    # hs-CRP: overall z-score (log-transformed)
    df['z_log_hscrp'] = (df['log_hscrp'] - df['log_hscrp'].mean()) / df['log_hscrp'].std()
    
    # Albumin: overall z-score
    df['z_albumin'] = (df['albumin'] - df['albumin'].mean()) / df['albumin'].std()
    
    # Grip strength: sex-specific z-scores
    df['z_grip'] = np.nan
    for sex in [1, 2]:  # 1=Male, 2=Female
        mask = df['RIAGENDR'] == sex
        if mask.sum() > 0:
            grip_mean = df.loc[mask, 'grip_max'].mean()
            grip_std = df.loc[mask, 'grip_max'].std()
            df.loc[mask, 'z_grip'] = (df.loc[mask, 'grip_max'] - grip_mean) / grip_std
    
    # Construct IRI
    # IRI = (-z_hsCRP) + z_albumin + z_grip
    df['iri'] = (-df['z_log_hscrp']) + df['z_albumin'] + df['z_grip']
    
    print(f"  IRI computed for {df['iri'].notna().sum():,} participants")
    print(f"  IRI mean: {df['iri'].mean():.3f}, std: {df['iri'].std():.3f}")
    
    # Create IRI quartiles
    df['iri_quartile'] = pd.qcut(df['iri'], q=4, labels=['Q1 (lowest)', 'Q2', 'Q3', 'Q4 (highest)'])
    
    # Create sensitivity flags
    df['flag_crp_high'] = (df['hscrp'] > 10).astype(int)
    df['flag_crp_very_high'] = (df['hscrp'] > 20).astype(int)
    df['flag_albumin_low'] = (df['albumin'] < 3.5).astype(int)
    df['flag_grip_low_p10'] = (df['grip_max'] < df['grip_max'].quantile(0.10)).astype(int)
    
    return df


def create_derived_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Create all derived clinical variables."""
    print("\n" + "="*60)
    print("Creating derived clinical variables")
    print("="*60)
    
    # Demographics
    df['age'] = df['RIDAGEYR']
    df['sex'] = df['RIAGENDR']  # 1=Male, 2=Female
    df['female'] = (df['sex'] == 2).astype(int)
    
    # Race/ethnicity (RIDRETH3 for 2011+)
    # 1=Mexican American, 2=Other Hispanic, 3=NH White, 4=NH Black, 6=NH Asian, 7=Other/Multi
    df['race_eth'] = df['RIDRETH3']
    
    # Education (DMDEDUC2 for adults 20+)
    # 1=Less than 9th grade, 2=9-11th grade, 3=HS grad/GED, 4=Some college, 5=College grad+
    df['education'] = df['DMDEDUC2']
    df['college_grad'] = (df['education'] >= 5).astype(int)
    
    # Poverty income ratio
    df['pir'] = df['INDFMPIR']
    df['poverty'] = (df['pir'] < 1.0).astype(int)
    
    # BMI categories
    df['bmi'] = df['BMXBMI']
    df['bmi_cat'] = pd.cut(df['bmi'], 
                           bins=[0, 18.5, 25, 30, 100],
                           labels=['Underweight', 'Normal', 'Overweight', 'Obese'])
    df['obesity'] = (df['bmi'] >= 30).astype(int)
    
    # eGFR (CKD-EPI 2021)
    df['creatinine'] = df['LBXSCR']
    df['egfr'] = compute_egfr_ckdepi_2021(df['creatinine'], df['age'], df['sex'])
    df['ckd_stage'] = pd.cut(df['egfr'],
                             bins=[0, 15, 30, 45, 60, 90, 200],
                             labels=['G5', 'G4', 'G3b', 'G3a', 'G2', 'G1'])
    df['egfr_lt60'] = (df['egfr'] < 60).astype(int)
    df['flag_severe_ckd'] = (df['egfr'] < 30).astype(int)
    
    # Blood pressure
    df['mean_sbp'], df['mean_dbp'] = zip(*df.groupby('cycle').apply(
        lambda g: pd.DataFrame({'sbp': compute_mean_bp(g, g.name)[0], 
                                 'dbp': compute_mean_bp(g, g.name)[1]}).values.T.tolist()
    ).explode().apply(lambda x: (x[0], x[1]) if isinstance(x, list) else (np.nan, np.nan)))
    
    # Simpler approach for BP
    sbp_cols = [c for c in df.columns if 'BPXSY' in c or 'BPXOSY' in c]
    dbp_cols = [c for c in df.columns if 'BPXDI' in c or 'BPXODI' in c]
    df['mean_sbp'] = df[sbp_cols].mean(axis=1) if sbp_cols else np.nan
    df['mean_dbp'] = df[dbp_cols].mean(axis=1) if dbp_cols else np.nan
    
    # Hypertension
    df['hypertension'] = define_hypertension(df)
    
    # Diabetes
    df['diabetes'] = define_diabetes(df)
    df['hba1c'] = df['LBXGH']
    
    # Lipids
    df['tchol'] = df['LBXTC']
    df['hdl'] = df.get('LBDHDD', df.get('LBXHDD', pd.Series([np.nan] * len(df))))
    df['trigly'] = df['LBXTR']
    df['ldl'] = compute_ldl_friedewald(df['tchol'], df['hdl'], df['trigly'])
    df['dyslipidemia'] = ((df['tchol'] >= 200) | (df['ldl'] >= 130) | 
                          (df['hdl'] < 40) | (df['trigly'] >= 150)).astype(int)
    
    # Smoking
    df['smoking_status'] = define_smoking_status(df)
    df['current_smoker'] = (df['smoking_status'] == 2).astype(int)
    
    # Physical activity
    df['met_min_week'] = compute_physical_activity_met_min(df)
    df['meets_pa_guidelines'] = (df['met_min_week'] >= 600).astype(int)  # 150 min moderate or 75 min vigorous
    
    # CVD history
    df['cvd_history'] = define_cvd_history(df)
    df['chf_history'] = (df.get('MCQ160B', pd.Series([2] * len(df))) == 1).astype(int)
    df['cancer_history'] = (df.get('MCQ220', pd.Series([2] * len(df))) == 1).astype(int)
    df['flag_cancer'] = df['cancer_history']
    
    # Pregnancy exclusion flag
    df['pregnant'] = (df.get('RIDEXPRG', pd.Series([2] * len(df))) == 1).astype(int)
    
    print(f"  Created derived variables for {len(df):,} participants")
    
    return df


def apply_eligibility_criteria(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply study eligibility criteria and create analytic flags.
    
    Hard exclusions:
    - Age < 18
    - Pregnant
    - Missing all 3 IRI components
    
    Soft flags for sensitivity analyses:
    - hs-CRP > 10 mg/L
    - Prevalent cancer
    - Severe CKD (eGFR < 30)
    """
    print("\n" + "="*60)
    print("Applying eligibility criteria")
    print("="*60)
    
    n_start = len(df)
    
    # Create eligibility flag (not excluding yet)
    df['eligible'] = 1
    
    # Age >= 18
    df.loc[df['age'] < 18, 'eligible'] = 0
    n_age = (df['age'] >= 18).sum()
    print(f"  Age >= 18: {n_age:,} ({100*n_age/n_start:.1f}%)")
    
    # Not pregnant
    df.loc[df['pregnant'] == 1, 'eligible'] = 0
    n_preg = ((df['age'] >= 18) & (df['pregnant'] != 1)).sum()
    print(f"  Not pregnant: {n_preg:,}")
    
    # Has at least some IRI data
    has_crp = df['hscrp'].notna()
    has_alb = df['albumin'].notna()
    has_grip = df['grip_max'].notna()
    df['has_iri_components'] = (has_crp & has_alb & has_grip).astype(int)
    df.loc[df['has_iri_components'] == 0, 'eligible'] = 0
    
    n_iri = df['has_iri_components'].sum()
    print(f"  Has all IRI components: {n_iri:,}")
    
    # Has mortality linkage eligibility (non-missing SEQN is sufficient for public data)
    df['has_mortality_eligible'] = 1  # Will update after merging mortality
    
    # Final eligible count
    n_eligible = df['eligible'].sum()
    print(f"\n  Total eligible: {n_eligible:,} ({100*n_eligible/n_start:.1f}%)")
    
    # Create primary analysis flag (eligible AND hs-CRP <= 10)
    df['primary_analysis'] = ((df['eligible'] == 1) & (df['hscrp'] <= 10)).astype(int)
    n_primary = df['primary_analysis'].sum()
    print(f"  Primary analysis (CRP <= 10): {n_primary:,}")
    
    return df


def main():
    """Main processing function."""
    print("\n" + "="*60)
    print("IRI STUDY - DATA HARMONIZATION")
    print("="*60)
    
    # Process each cycle
    cycles = ["2011-2012", "2013-2014", "2017-2020"]
    all_data = []
    
    for cycle in cycles:
        df = process_cycle(cycle)
        if len(df) > 0:
            all_data.append(df)
    
    if not all_data:
        print("\nNo data loaded. Run 01_download_data.py first.")
        return
    
    # Combine cycles
    combined = pd.concat(all_data, ignore_index=True)
    print(f"\nCombined: {len(combined):,} participants across all cycles")
    
    # Construct IRI
    combined = construct_iri(combined)
    
    # Create derived variables
    combined = create_derived_variables(combined)
    
    # Apply eligibility criteria
    combined = apply_eligibility_criteria(combined)
    
    # Select and order key variables for export
    key_vars = [
        # Identifiers
        'SEQN', 'cycle', 'is_prepandemic',
        
        # Survey design
        'WTMEC2YR', 'WTMECPRP', 'SDMVPSU', 'SDMVSTRA',
        
        # IRI components and composite
        'hscrp', 'log_hscrp', 'z_log_hscrp',
        'albumin', 'z_albumin',
        'grip_max', 'z_grip',
        'iri', 'iri_quartile',
        
        # Demographics
        'age', 'sex', 'female', 'race_eth', 'education', 'college_grad', 'pir', 'poverty',
        
        # Cardiometabolic
        'bmi', 'bmi_cat', 'obesity',
        'mean_sbp', 'mean_dbp', 'hypertension',
        'hba1c', 'diabetes',
        'tchol', 'hdl', 'ldl', 'trigly', 'dyslipidemia',
        
        # Kidney
        'creatinine', 'egfr', 'ckd_stage', 'egfr_lt60',
        
        # Lifestyle
        'smoking_status', 'current_smoker',
        'met_min_week', 'meets_pa_guidelines',
        
        # Medical history
        'cvd_history', 'chf_history', 'cancer_history',
        
        # Eligibility and flags
        'eligible', 'primary_analysis', 'has_iri_components',
        'pregnant',
        'flag_crp_high', 'flag_crp_very_high',
        'flag_albumin_low', 'flag_grip_low_p10',
        'flag_severe_ckd', 'flag_cancer',
    ]
    
    # Keep only variables that exist
    export_vars = [v for v in key_vars if v in combined.columns]
    
    # Save processed data
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    output_path = DATA_PROCESSED / "iri_cohort_harmonized.parquet"
    combined[export_vars].to_parquet(output_path)
    print(f"\nSaved: {output_path}")
    
    # Also save as CSV for R import
    csv_path = DATA_PROCESSED / "iri_cohort_harmonized.csv"
    combined[export_vars].to_csv(csv_path, index=False)
    print(f"Saved: {csv_path}")
    
    # Summary statistics
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total participants: {len(combined):,}")
    print(f"Eligible for analysis: {combined['eligible'].sum():,}")
    print(f"Primary analysis cohort: {combined['primary_analysis'].sum():,}")
    print(f"\nBy cycle:")
    print(combined.groupby('cycle')['eligible'].agg(['count', 'sum']))
    print(f"\nIRI distribution (eligible):")
    eligible = combined[combined['eligible'] == 1]
    print(f"  Mean: {eligible['iri'].mean():.3f}")
    print(f"  SD: {eligible['iri'].std():.3f}")
    print(f"  Range: [{eligible['iri'].min():.3f}, {eligible['iri'].max():.3f}]")
    print(f"\nIRI quartile counts:")
    print(eligible['iri_quartile'].value_counts().sort_index())


if __name__ == "__main__":
    main()

