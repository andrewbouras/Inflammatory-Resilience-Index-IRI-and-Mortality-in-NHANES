"""
Modified IRI Study - Mortality Linkage

Links the IRI cohort with NCHS mortality data.
Defines outcomes: all-cause, cardiovascular, and heart failure mortality.
"""

import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_MORTALITY = PROJECT_ROOT / "data" / "mortality"

# Mortality file column specifications (fixed-width format)
# Based on NCHS documentation for public-use linked mortality files
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


def load_mortality_file(filepath: Path) -> pd.DataFrame:
    """Load NCHS mortality file (fixed-width format)."""
    if not filepath.exists():
        print(f"  File not found: {filepath}")
        return pd.DataFrame()
    
    try:
        # Read fixed-width file
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


def define_cause_specific_mortality(df: pd.DataFrame) -> pd.DataFrame:
    """
    Define cause-specific mortality outcomes based on UCOD_LEADING.
    
    UCOD_LEADING codes (ICD-10 groups):
    1 = Heart disease (I00-I09, I11, I13, I20-I51)
    2 = Cancer
    3 = Chronic lower respiratory disease
    4 = Accidents
    5 = Cerebrovascular disease (stroke)
    6 = Alzheimer's disease
    7 = Diabetes
    8 = Influenza/pneumonia
    9 = Kidney disease
    10 = All other causes
    """
    # Cardiovascular mortality (heart disease + cerebrovascular)
    df['mort_cv'] = ((df['mortstat'] == 1) & 
                     (df['ucod_leading'].isin([1, 5]))).astype(int)
    
    # Heart disease mortality only
    df['mort_heart'] = ((df['mortstat'] == 1) & 
                        (df['ucod_leading'] == 1)).astype(int)
    
    # All-cause mortality
    df['mort_all'] = (df['mortstat'] == 1).astype(int)
    
    # Cancer mortality
    df['mort_cancer'] = ((df['mortstat'] == 1) & 
                         (df['ucod_leading'] == 2)).astype(int)
    
    return df


def main():
    print("\n" + "="*60)
    print("MODIFIED IRI STUDY - MORTALITY LINKAGE")
    print("="*60)
    
    # Load harmonized cohort
    cohort_path = DATA_PROCESSED / "iri_cohort.parquet"
    if not cohort_path.exists():
        print("Error: Cohort file not found. Run 02_build_cohort.py first.")
        return
    
    df = pd.read_parquet(cohort_path)
    print(f"Loaded IRI cohort: {len(df):,} participants")
    
    # Load mortality files
    print("\nLoading mortality files...")
    mort_files = list(DATA_MORTALITY.glob("*.dat"))
    
    if not mort_files:
        print("No mortality files found. Attempting download...")
        # Try alternative: use the mortality data from RIR project if available
        alt_mort = Path("/Users/andrewbouras/Documents/VishrutNHANES/Residual Inflammatory Risk (RIR) in Statin-Treated Adults: NHANES Analysis/data/mortality")
        if alt_mort.exists():
            mort_files = list(alt_mort.glob("*.dat"))
    
    all_mort = []
    for mort_file in mort_files:
        mort_df = load_mortality_file(mort_file)
        if len(mort_df) > 0:
            all_mort.append(mort_df)
    
    if not all_mort:
        print("\nNo mortality data loaded. Creating placeholder mortality variables...")
        # Create placeholder - analysis will need actual mortality data
        df['mortstat'] = np.nan
        df['mort_all'] = np.nan
        df['mort_cv'] = np.nan
        df['mort_heart'] = np.nan
        df['followup_years'] = np.nan
    else:
        # Combine mortality data
        combined_mort = pd.concat(all_mort, ignore_index=True)
        combined_mort = combined_mort.drop_duplicates(subset=['SEQN'])
        combined_mort = define_cause_specific_mortality(combined_mort)
        
        print(f"\nCombined mortality data: {len(combined_mort):,} records")
        
        # Merge with cohort
        mort_vars = ['SEQN', 'mortstat', 'permth_exm', 'mort_all', 'mort_cv', 'mort_heart', 'mort_cancer']
        df = df.merge(combined_mort[mort_vars], on='SEQN', how='left')
        
        # Fill NaN mortality (not linked = assumed alive through follow-up)
        df['mortstat'] = df['mortstat'].fillna(0).astype(int)
        df['mort_all'] = df['mort_all'].fillna(0).astype(int)
        df['mort_cv'] = df['mort_cv'].fillna(0).astype(int)
        df['mort_heart'] = df['mort_heart'].fillna(0).astype(int)
        df['mort_cancer'] = df['mort_cancer'].fillna(0).astype(int)
        
        # Calculate follow-up time
        df['followup_years'] = df['permth_exm'] / 12
        # For those not in mortality file, use approximate follow-up
        # 2015-2016 to 2019 = ~3-4 years; 2017-2018 to 2019 = ~1-2 years
        df.loc[df['followup_years'].isna() & (df['cycle'] == '2015-2016'), 'followup_years'] = 3.5
        df.loc[df['followup_years'].isna() & (df['cycle'] == '2017-2020'), 'followup_years'] = 2.0
    
    # Save linked dataset
    output_path = DATA_PROCESSED / "iri_cohort_mortality.parquet"
    df.to_parquet(output_path)
    print(f"\nSaved: {output_path}")
    
    csv_path = DATA_PROCESSED / "iri_cohort_mortality.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved: {csv_path}")
    
    # Summary
    eligible = df[df['eligible'] == 1]
    print("\n" + "="*60)
    print("MORTALITY LINKAGE SUMMARY")
    print("="*60)
    print(f"Eligible participants: {len(eligible):,}")
    print(f"Deaths (all-cause): {eligible['mort_all'].sum():,.0f}")
    print(f"CV deaths: {eligible['mort_cv'].sum():,.0f}")
    print(f"Heart disease deaths: {eligible['mort_heart'].sum():,.0f}")
    print(f"Mean follow-up: {eligible['followup_years'].mean():.1f} years")
    
    print("\nMortality by IRI quartile:")
    mort_by_q = eligible.groupby('iri_quartile').agg({
        'mort_all': ['sum', 'mean'],
        'mort_cv': ['sum', 'mean'],
        'followup_years': 'mean'
    }).round(3)
    print(mort_by_q)


if __name__ == "__main__":
    main()
