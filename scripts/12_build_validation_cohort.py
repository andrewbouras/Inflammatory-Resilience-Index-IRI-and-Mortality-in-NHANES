"""
IRI Validation Study - NHANES 1999-2006 Cohort Building Script

Builds the validation cohort with IRI calculation and mortality linkage.
Uses same IRI formula as derivation cohort: IRI = (-z_hsCRP) + z_Albumin + z_ALMI

Key differences from derivation cohort building:
- Different variable names across 1999-2006 cycles
- Need to harmonize CRP, albumin, and DEXA variable names
- Longer mortality follow-up (13-20 years)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_MORTALITY = PROJECT_ROOT / "data" / "mortality"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

# =============================================================================
# CYCLE-SPECIFIC VARIABLE MAPPINGS
# =============================================================================

# CRP variable names changed across cycles
CRP_VAR_MAP = {
    "1999-2000": ("LAB11.xpt", "LBXCRP"),      # Standard CRP (mg/dL) - need to convert
    "2001-2002": ("L11_B.xpt", "LBXCRP"),
    "2003-2004": ("L11_C.xpt", "LBXCRP"),
    "2005-2006": ("CRP_D.xpt", "LBXCRP"),
}

# Albumin from biochemistry panel
ALBUMIN_VAR_MAP = {
    "1999-2000": ("LAB18.xpt", "LBXSAL"),
    "2001-2002": ("L40_B.xpt", "LBXSAL"),
    "2003-2004": ("L40_C.xpt", "LBXSAL"),
    "2005-2006": ("BIOPRO_D.xpt", "LBXSAL"),
}

# DEXA whole body - need to extract appendicular lean mass
DEXA_VAR_MAP = {
    "1999-2000": "DXX.xpt",
    "2001-2002": "DXX_B.xpt",
    "2003-2004": "DXX_C.xpt",
    "2005-2006": "DXX_D.xpt",
}

# Demographics
DEMO_VAR_MAP = {
    "1999-2000": "DEMO.xpt",
    "2001-2002": "DEMO_B.xpt",
    "2003-2004": "DEMO_C.xpt",
    "2005-2006": "DEMO_D.xpt",
}

# Mortality files
MORTALITY_FILES = {
    "1999-2000": "NHANES_1999_2000_MORT_2019_PUBLIC.dat",
    "2001-2002": "NHANES_2001_2002_MORT_2019_PUBLIC.dat",
    "2003-2004": "NHANES_2003_2004_MORT_2019_PUBLIC.dat",
    "2005-2006": "NHANES_2005_2006_MORT_2019_PUBLIC.dat",
}

# Mortality file column specifications
MORT_COLSPECS = [
    (0, 14),    # PUBLICID (padded SEQN)
    (14, 15),   # ELIGSTAT
    (15, 16),   # MORTSTAT
    (16, 19),   # UCOD_LEADING (underlying cause)
    (19, 22),   # DIABETES
    (22, 25),   # HYPERTEN
    (25, 28),   # PERMTH_INT
    (28, 31),   # PERMTH_EXM
]

MORT_NAMES = [
    'publicid', 'eligstat', 'mortstat', 'ucod_leading',
    'diabetes_mort', 'hyperten_mort', 'permth_int', 'permth_exm'
]


def load_xpt(filepath: Path) -> pd.DataFrame:
    """Load XPT file into pandas DataFrame."""
    try:
        return pd.read_sas(filepath, format='xport', encoding='latin1')
    except Exception as e:
        print(f"  Warning: Could not load {filepath.name}: {e}")
        return pd.DataFrame()


def load_mortality_file(filepath: Path) -> pd.DataFrame:
    """Load NCHS mortality file (fixed-width format)."""
    if not filepath.exists():
        print(f"  Mortality file not found: {filepath}")
        return pd.DataFrame()
    
    try:
        df = pd.read_fwf(filepath, colspecs=MORT_COLSPECS, names=MORT_NAMES, 
                         dtype=str, na_values=['.', ''])
        
        # Extract SEQN from PUBLICID
        df['SEQN'] = df['publicid'].str.strip().astype(float)
        
        # Convert numeric columns
        for col in ['eligstat', 'mortstat', 'ucod_leading', 'permth_int', 'permth_exm']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        print(f"  Loaded {len(df):,} mortality records from {filepath.name}")
        return df
        
    except Exception as e:
        print(f"  Error loading {filepath}: {e}")
        return pd.DataFrame()


def calculate_almi(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Appendicular Lean Mass Index from DEXA data.
    ALMI = (Left Arm Lean + Right Arm Lean + Left Leg Lean + Right Leg Lean) / height^2
    
    NHANES variable names:
    - DXXLLTM: Left leg lean tissue mass (excluding bone mineral)
    - DXXRLTM: Right leg lean tissue mass
    - DXXLATM: Left arm lean tissue mass  
    - DXXRATM: Right arm lean tissue mass
    
    Alternatively may use:
    - DXDLLTM, DXDRLTM, DXDLATM, DXDRATM (1999-2004 naming)
    - DXXLALE, DXXRALE, DXXLLLE, DXXRLLE (alternate naming)
    """
    # Try different variable naming conventions
    arm_leg_vars = [
        # Modern naming (2005+)
        ['DXXLATM', 'DXXRATM', 'DXXLLTM', 'DXXRLTM'],
        # Alternative naming
        ['DXDLATM', 'DXDRATM', 'DXDLLTM', 'DXDRLTM'],
        # Lean excluding BMC variants
        ['DXXLALE', 'DXXRALE', 'DXXLLLE', 'DXXRLLE'],
        # Total lean mass variants (g)
        ['DXDLALE', 'DXDRALE', 'DXDLLLE', 'DXDRLLE'],
    ]
    
    alm = pd.Series([np.nan] * len(df), index=df.index)
    
    for var_set in arm_leg_vars:
        if all(v in df.columns for v in var_set):
            # Sum lean mass in grams, convert to kg
            # Require all 4 limb values to be non-null (fillna(0) would treat
            # missing limbs as zero mass, producing falsely low ALM)
            all_present = df[var_set].notna().all(axis=1)
            alm = df[var_set].sum(axis=1)
            alm[~all_present] = np.nan
            
            # Check if values are in grams (> 1000) or kg
            if alm.median() > 1000:
                alm = alm / 1000  # Convert g to kg
            
            print(f"  Using DEXA variables: {var_set}")
            break
    else:
        # Try total lean mass columns if individual aren't available
        print("  Warning: Individual limb variables not found, checking for total appendicular")
        if 'DXDTOLE' in df.columns:
            # Use total lean and estimate appendicular as ~75%
            alm = df['DXDTOLE'] * 0.75 / 1000
            print("  Using estimated ALM from total body lean")
    
    return alm


def process_cycle(cycle: str) -> pd.DataFrame:
    """Process a single NHANES cycle and return harmonized data."""
    print(f"\n{'='*60}")
    print(f"Processing {cycle}")
    print('='*60)
    
    cycle_dir = DATA_RAW / cycle
    if not cycle_dir.exists():
        print(f"  Cycle directory not found: {cycle_dir}")
        return pd.DataFrame()
    
    # Load demographics
    demo_file = cycle_dir / DEMO_VAR_MAP[cycle]
    if not demo_file.exists():
        print(f"  Demographics file not found: {demo_file}")
        return pd.DataFrame()
    
    df = load_xpt(demo_file)
    print(f"  Loaded {len(df):,} participants from demographics")
    
    # Extract key demographic variables
    # Race/ethnicity variable name changed
    if 'RIDRETH1' in df.columns:
        df['race_eth'] = df['RIDRETH1']  # 5-level for 1999-2006
    elif 'RIDRETH3' in df.columns:
        df['race_eth'] = df['RIDRETH3']
    
    # Weight variable - use MEC weight
    if 'WTMEC2YR' in df.columns:
        df['weight_mec'] = df['WTMEC2YR']
    elif 'WTMEC4YR' in df.columns:
        df['weight_mec'] = df['WTMEC4YR']
    
    # Load CRP
    crp_file, crp_var = CRP_VAR_MAP[cycle]
    crp_path = cycle_dir / crp_file
    if crp_path.exists():
        crp_df = load_xpt(crp_path)
        if crp_var in crp_df.columns:
            crp_df['hscrp'] = crp_df[crp_var]
            # NHANES 1999-2004 LBXCRP is in mg/dL (typical median ~0.2-0.3)
            # NHANES 2005+ LBXHSCRP is in mg/L (typical median ~1.5-3.0)
            # Convert mg/dL to mg/L: multiply by 10
            if crp_df['hscrp'].median() < 1.0 and cycle in ['1999-2000', '2001-2002', '2003-2004', '2005-2006']:
                crp_df['hscrp'] = crp_df['hscrp'] * 10  # Convert mg/dL to mg/L
                print(f"  Converted CRP from mg/dL to mg/L (median was {crp_df['hscrp'].median()/10:.2f} mg/dL)")
            df = df.merge(crp_df[['SEQN', 'hscrp']], on='SEQN', how='left')
            print(f"  Merged CRP: {crp_df['hscrp'].notna().sum():,} valid values")
    else:
        print(f"  Warning: CRP file not found: {crp_path}")
    
    # Load Albumin
    alb_file, alb_var = ALBUMIN_VAR_MAP[cycle]
    alb_path = cycle_dir / alb_file
    if alb_path.exists():
        alb_df = load_xpt(alb_path)
        if alb_var in alb_df.columns:
            alb_df['albumin'] = alb_df[alb_var]
            df = df.merge(alb_df[['SEQN', 'albumin']], on='SEQN', how='left')
            print(f"  Merged albumin: {alb_df['albumin'].notna().sum():,} valid values")
    else:
        print(f"  Warning: Albumin file not found: {alb_path}")
    
    # Load DEXA
    dexa_file = DEXA_VAR_MAP[cycle]
    dexa_path = cycle_dir / dexa_file
    if dexa_path.exists():
        dexa_df = load_xpt(dexa_path)
        print(f"  DEXA columns available: {len(dexa_df.columns)}")
        
        # Calculate ALM
        dexa_df['alm_kg'] = calculate_almi(dexa_df)
        
        # Get height from body measures for ALMI calculation
        bmx_patterns = ['BMX.xpt', 'BMX_B.xpt', 'BMX_C.xpt', 'BMX_D.xpt']
        for bmx_file in bmx_patterns:
            bmx_path = cycle_dir / bmx_file
            if bmx_path.exists():
                bmx_df = load_xpt(bmx_path)
                if 'BMXHT' in bmx_df.columns:
                    dexa_df = dexa_df.merge(bmx_df[['SEQN', 'BMXHT', 'BMXWT', 'BMXBMI']], 
                                            on='SEQN', how='left')
                    print(f"  Merged body measures: {bmx_df['BMXHT'].notna().sum():,} valid heights")
                break
        
        # Calculate ALMI = ALM / height^2
        if 'BMXHT' in dexa_df.columns and 'alm_kg' in dexa_df.columns:
            height_m = dexa_df['BMXHT'] / 100
            dexa_df['almi'] = dexa_df['alm_kg'] / (height_m ** 2)
            print(f"  ALMI median: {dexa_df['almi'].median():.2f} kg/m²")
        
        # Merge DEXA with main dataframe
        dexa_cols = ['SEQN', 'alm_kg', 'almi'] + [c for c in ['BMXHT', 'BMXWT', 'BMXBMI'] if c in dexa_df.columns]
        df = df.merge(dexa_df[[c for c in dexa_cols if c in dexa_df.columns]], 
                      on='SEQN', how='left')
    else:
        print(f"  Warning: DEXA file not found: {dexa_path}")
    
    # Load additional covariates
    covariate_files = [
        ('DIQ', 'Diabetes'),
        ('SMQ', 'Smoking'),
        ('MCQ', 'Medical conditions'),
        ('HUQ', 'Health status'),
        ('PFQ', 'Physical functioning'),
    ]
    
    for prefix, description in covariate_files:
        for ext in ['', '_B', '_C', '_D']:
            cov_path = cycle_dir / f"{prefix}{ext}.xpt"
            if cov_path.exists():
                cov_df = load_xpt(cov_path)
                if 'SEQN' in cov_df.columns and len(cov_df) > 0:
                    df = df.merge(cov_df, on='SEQN', how='left', suffixes=('', f'_{prefix}'))
                    print(f"  Merged {description}: {len(cov_df):,} records")
                break
    
    # Add cycle identifier
    df['cycle'] = cycle
    df['cohort'] = 'validation'
    
    return df


def construct_iri_validation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construct IRI for validation cohort.
    IRI = (-z_hsCRP) + z_Albumin + z_ALMI (sex-specific for ALMI)

    Uses derivation cohort z-score parameters for proper external validation.
    Falls back to validation-cohort standardization if params file not found.
    """
    import json

    print("\n" + "="*60)
    print("Constructing IRI for validation cohort")
    print("="*60)

    # Check for required components
    required = ['hscrp', 'albumin', 'almi']
    for var in required:
        if var in df.columns:
            print(f"  {var}: {df[var].notna().sum():,} valid values")
        else:
            print(f"  WARNING: {var} not found in dataframe")

    # Load derivation cohort z-score parameters for proper external validation
    params_path = DATA_PROCESSED / "derivation_zscore_params.json"
    if params_path.exists():
        with open(params_path, 'r') as f:
            params = json.load(f)
        print("  Using DERIVATION cohort z-score parameters (proper external validation)")
        use_derivation_params = True
    else:
        print("  WARNING: derivation_zscore_params.json not found!")
        print("  Run 02_build_cohort.py first to generate derivation parameters.")
        print("  Falling back to validation-cohort standardization (NOT ideal).")
        use_derivation_params = False

    # Log-transform hs-CRP
    df['log_hscrp'] = np.log(df['hscrp'].replace(0, np.nan))

    if use_derivation_params:
        # Apply derivation cohort means/SDs for z-score calculation
        df['z_log_hscrp'] = (df['log_hscrp'] - params['log_crp']['mean']) / params['log_crp']['std']
        df['z_albumin'] = (df['albumin'] - params['albumin']['mean']) / params['albumin']['std']

        df['z_almi'] = np.nan
        for sex, key in [(1, 'almi_male'), (2, 'almi_female')]:
            mask = df['RIAGENDR'] == sex
            if mask.sum() > 0 and params[key]['std'] > 0:
                df.loc[mask, 'z_almi'] = (df.loc[mask, 'almi'] - params[key]['mean']) / params[key]['std']
    else:
        # Fallback: standardize within validation cohort
        df['z_log_hscrp'] = (df['log_hscrp'] - df['log_hscrp'].mean()) / df['log_hscrp'].std()
        df['z_albumin'] = (df['albumin'] - df['albumin'].mean()) / df['albumin'].std()

        df['z_almi'] = np.nan
        for sex in [1, 2]:
            mask = df['RIAGENDR'] == sex
            if mask.sum() > 0:
                almi_mean = df.loc[mask, 'almi'].mean()
                almi_std = df.loc[mask, 'almi'].std()
                if almi_std > 0:
                    df.loc[mask, 'z_almi'] = (df.loc[mask, 'almi'] - almi_mean) / almi_std

    # Construct IRI: IRI = (-z_hsCRP) + z_albumin + z_ALMI
    df['iri'] = (-df['z_log_hscrp']) + df['z_albumin'] + df['z_almi']
    
    print(f"\n  IRI computed for {df['iri'].notna().sum():,} participants")
    if df['iri'].notna().sum() > 0:
        print(f"  IRI mean: {df['iri'].mean():.3f}, std: {df['iri'].std():.3f}")
        print(f"  IRI range: [{df['iri'].min():.3f}, {df['iri'].max():.3f}]")
    
    # Create IRI quartiles
    df['iri_quartile'] = pd.qcut(df['iri'].dropna(), q=4, labels=['Q1', 'Q2', 'Q3', 'Q4'])
    df['iri_quartile'] = df['iri_quartile'].cat.rename_categories({
        'Q1': 'Q1 (lowest)', 'Q2': 'Q2', 'Q3': 'Q3', 'Q4': 'Q4 (highest)'
    })
    
    return df


def link_mortality(df: pd.DataFrame) -> pd.DataFrame:
    """Link validation cohort with mortality data through 2019."""
    print("\n" + "="*60)
    print("Linking mortality data")
    print("="*60)
    
    all_mort = []
    for cycle, mort_file in MORTALITY_FILES.items():
        mort_path = DATA_MORTALITY / mort_file
        if mort_path.exists():
            mort_df = load_mortality_file(mort_path)
            if len(mort_df) > 0:
                mort_df['mort_cycle'] = cycle
                all_mort.append(mort_df)
    
    if not all_mort:
        print("  No mortality data loaded!")
        return df
    
    combined_mort = pd.concat(all_mort, ignore_index=True)
    combined_mort = combined_mort.drop_duplicates(subset=['SEQN'])
    print(f"  Combined mortality records: {len(combined_mort):,}")
    
    # Define mortality outcomes
    # All-cause mortality
    combined_mort['mort_all'] = (combined_mort['mortstat'] == 1).astype(int)
    
    # Cardiovascular mortality (UCOD_LEADING: 1=Heart disease, 5=Cerebrovascular)
    combined_mort['mort_cv'] = ((combined_mort['mortstat'] == 1) & 
                                 (combined_mort['ucod_leading'].isin([1, 5]))).astype(int)
    
    # Heart disease mortality
    combined_mort['mort_heart'] = ((combined_mort['mortstat'] == 1) & 
                                    (combined_mort['ucod_leading'] == 1)).astype(int)
    
    # Stroke/cerebrovascular mortality
    combined_mort['mort_stroke'] = ((combined_mort['mortstat'] == 1) & 
                                     (combined_mort['ucod_leading'] == 5)).astype(int)
    
    # Cancer mortality
    combined_mort['mort_cancer'] = ((combined_mort['mortstat'] == 1) & 
                                     (combined_mort['ucod_leading'] == 2)).astype(int)
    
    # Calculate follow-up time
    combined_mort['followup_months'] = combined_mort['permth_exm']
    combined_mort['followup_years'] = combined_mort['followup_months'] / 12
    
    # Merge with main dataframe
    mort_vars = ['SEQN', 'mortstat', 'mort_all', 'mort_cv', 'mort_heart', 'mort_stroke', 'mort_cancer', 
                 'followup_months', 'followup_years', 'ucod_leading', 'eligstat']
    df = df.merge(combined_mort[mort_vars], on='SEQN', how='left')
    
    # Fill missing (assume alive if not linked, which is conservative)
    # Only for those with eligstat = 1 (eligible for linkage)
    df['mort_all'] = df['mort_all'].fillna(0).astype(int)
    df['mort_cv'] = df['mort_cv'].fillna(0).astype(int)
    df['mort_heart'] = df['mort_heart'].fillna(0).astype(int)
    df['mort_stroke'] = df['mort_stroke'].fillna(0).astype(int)
    df['mort_cancer'] = df['mort_cancer'].fillna(0).astype(int)
    
    # For those without follow-up time, estimate based on cycle
    cycle_to_followup = {
        '1999-2000': 20,  # ~20 years to 2019
        '2001-2002': 18,
        '2003-2004': 16,
        '2005-2006': 14,
    }
    for cycle, fu_years in cycle_to_followup.items():
        mask = (df['cycle'] == cycle) & (df['followup_years'].isna())
        df.loc[mask, 'followup_years'] = fu_years
    
    print(f"\n  Mortality linkage complete:")
    print(f"  Total deaths (all-cause): {df['mort_all'].sum():,}")
    print(f"  CV deaths: {df['mort_cv'].sum():,}")
    print(f"  Heart disease deaths: {df['mort_heart'].sum():,}")
    print(f"  Mean follow-up: {df['followup_years'].mean():.1f} years")
    
    return df


def apply_eligibility_criteria(df: pd.DataFrame) -> pd.DataFrame:
    """Apply study eligibility criteria matching derivation cohort."""
    print("\n" + "="*60)
    print("Applying eligibility criteria")
    print("="*60)
    
    n_start = len(df)
    
    df['eligible'] = 1
    
    # Age >= 20 (to match derivation cohort)
    df.loc[df['RIDAGEYR'] < 20, 'eligible'] = 0
    n_age = (df['RIDAGEYR'] >= 20).sum()
    print(f"  Age >= 20: {n_age:,}")
    
    # Not pregnant
    if 'RIDEXPRG' in df.columns:
        df.loc[df['RIDEXPRG'] == 1, 'eligible'] = 0
    
    # Has all IRI components
    has_hscrp = df['hscrp'].notna() if 'hscrp' in df.columns else pd.Series([False] * len(df))
    has_albumin = df['albumin'].notna() if 'albumin' in df.columns else pd.Series([False] * len(df))
    has_almi = df['almi'].notna() if 'almi' in df.columns else pd.Series([False] * len(df))
    
    df['has_iri_components'] = (has_hscrp & has_albumin & has_almi).astype(int)
    df.loc[df['has_iri_components'] == 0, 'eligible'] = 0
    
    n_iri = df['has_iri_components'].sum()
    print(f"  Has all IRI components: {n_iri:,}")
    
    # CRP <= 10 for primary analysis (exclude acute inflammation)
    df['crp_valid'] = (df['hscrp'] <= 10).astype(int) if 'hscrp' in df.columns else 0
    df.loc[df['crp_valid'] == 0, 'eligible'] = 0
    
    n_crp = ((df['has_iri_components'] == 1) & (df['crp_valid'] == 1)).sum()
    print(f"  CRP <= 10 mg/L: {n_crp:,}")
    
    # Final eligible
    n_eligible = df['eligible'].sum()
    print(f"\n  Total eligible for analysis: {n_eligible:,} ({100*n_eligible/n_start:.1f}%)")
    
    return df


def create_derived_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Create additional clinical variables for analysis."""
    
    # Demographics
    df['age'] = df['RIDAGEYR']
    df['sex'] = df['RIAGENDR']
    df['female'] = (df['sex'] == 2).astype(int)
    
    # Socioeconomic variables (for sensitivity analyses)
    # Education: DMDEDUC2 for adults 20+ (same coding as derivation cohort)
    # Note: In 1999-2006, may also be DMDEDUC or DMDEDUC3
    edu_var = None
    for var in ['DMDEDUC2', 'DMDEDUC', 'DMDEDUC3']:
        if var in df.columns:
            edu_var = var
            break
    if edu_var:
        df['education'] = df[edu_var]
        df.loc[df['education'] > 5, 'education'] = np.nan  # 7=Refused, 9=Don't know
        df['edu_less_than_hs'] = (df['education'].isin([1, 2])).astype(float)
        df.loc[df['education'].isna(), 'edu_less_than_hs'] = np.nan
        print(f"  Education available: {df['education'].notna().sum():,}")
    
    # Poverty-Income Ratio
    if 'INDFMPIR' in df.columns:
        df['pir'] = df['INDFMPIR']
        df['below_poverty'] = (df['pir'] < 1).astype(float)
        df.loc[df['pir'].isna(), 'below_poverty'] = np.nan
        print(f"  PIR available: {df['pir'].notna().sum():,}")
    
    # BMI
    if 'BMXBMI' in df.columns:
        df['bmi'] = df['BMXBMI']
    
    # Diabetes
    if 'DIQ010' in df.columns:
        df['diabetes'] = (df['DIQ010'] == 1).astype(int)
    
    # Hypertension
    # Check for BP medication or elevated BP
    if 'BPQ040A' in df.columns:
        df['hypertension'] = (df['BPQ040A'] == 1).astype(int)
    
    # Smoking
    if 'SMQ020' in df.columns and 'SMQ040' in df.columns:
        df['current_smoker'] = ((df['SMQ020'] == 1) & (df['SMQ040'].isin([1, 2]))).astype(int)
    
    # CVD history
    cvd_vars = ['MCQ160B', 'MCQ160C', 'MCQ160D', 'MCQ160E', 'MCQ160F']
    available_cvd = [v for v in cvd_vars if v in df.columns]
    if available_cvd:
        df['cvd_history'] = (df[available_cvd].eq(1).any(axis=1)).astype(int)
    
    # Self-rated health
    if 'HUQ010' in df.columns:
        df['fair_poor_health'] = (df['HUQ010'].isin([4, 5])).astype(int)
    
    # Walking difficulty
    if 'PFQ061B' in df.columns:
        df['walking_difficulty'] = (df['PFQ061B'].isin([2, 3, 4])).astype(int)
    
    return df


def main():
    """Build the validation cohort."""
    print("\n" + "="*60)
    print("IRI VALIDATION STUDY - COHORT BUILDING")
    print("NHANES 1999-2006")
    print("="*60)
    
    # Process each cycle
    cycles = ["1999-2000", "2001-2002", "2003-2004", "2005-2006"]
    all_data = []
    
    for cycle in cycles:
        df = process_cycle(cycle)
        if len(df) > 0:
            all_data.append(df)
    
    if not all_data:
        print("\nNo data loaded. Run 11_download_validation_data.py first.")
        return
    
    # Combine cycles
    combined = pd.concat(all_data, ignore_index=True)
    print(f"\nCombined: {len(combined):,} participants across all cycles")
    
    # Construct IRI
    combined = construct_iri_validation(combined)
    
    # Create derived variables
    combined = create_derived_variables(combined)
    
    # Apply eligibility criteria
    combined = apply_eligibility_criteria(combined)
    
    # Link mortality
    combined = link_mortality(combined)
    
    # Summary by IRI quartile
    print("\n" + "="*60)
    print("MORTALITY BY IRI QUARTILE")
    print("="*60)
    
    eligible = combined[combined['eligible'] == 1].copy()
    if 'iri_quartile' in eligible.columns:
        mort_summary = eligible.groupby('iri_quartile').agg({
            'SEQN': 'count',
            'mort_all': ['sum', 'mean'],
            'mort_cv': ['sum', 'mean'],
            'followup_years': 'mean'
        }).round(3)
        print(mort_summary)
    
    # Save
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    
    # Save full cohort
    output_path = DATA_PROCESSED / "iri_validation_cohort.parquet"
    combined.to_parquet(output_path)
    print(f"\nSaved: {output_path}")
    
    # Save CSV for R
    csv_path = DATA_PROCESSED / "iri_validation_cohort.csv"
    combined.to_csv(csv_path, index=False)
    print(f"Saved: {csv_path}")
    
    # Save eligible-only subset
    eligible_path = DATA_PROCESSED / "iri_validation_eligible.parquet"
    eligible.to_parquet(eligible_path)
    print(f"Saved: {eligible_path}")
    
    # Final summary
    print("\n" + "="*60)
    print("VALIDATION COHORT SUMMARY")
    print("="*60)
    print(f"Total participants: {len(combined):,}")
    print(f"Eligible for analysis: {combined['eligible'].sum():,}")
    print(f"All-cause deaths: {eligible['mort_all'].sum():,}")
    print(f"CV deaths: {eligible['mort_cv'].sum():,}")
    print(f"Mean follow-up: {eligible['followup_years'].mean():.1f} years")
    
    if 'iri' in eligible.columns and eligible['iri'].notna().sum() > 0:
        print(f"\nIRI distribution (eligible):")
        print(f"  Mean: {eligible['iri'].mean():.3f}")
        print(f"  SD: {eligible['iri'].std():.3f}")
        print(f"  Range: [{eligible['iri'].min():.3f}, {eligible['iri'].max():.3f}]")


if __name__ == "__main__":
    main()
