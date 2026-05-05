"""
IRI Validation Study - NHANES 1999-2006 Cohort Building Script

NHANES whole-body DEXA files for 1999-2006 contain 5 multiply imputed
records per participant. This script builds two linked validation datasets:

1. `iri_validation_cohort.*`
   One row per participant using the mean ALMI across the 5 DEXA imputations.
   This file is used for participant counts, baseline tables, and descriptive
   figures so sample sizes are not inflated.

2. `iri_validation_cohort_mi.*`
   One row per participant per DEXA imputation (`dexa_imputation` 1-5).
   This file is used for inferential mortality analyses combined with Rubin's
   rules in the downstream R scripts.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_MORTALITY = PROJECT_ROOT / "data" / "mortality"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

QUARTILE_LABELS = ["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"]

# =============================================================================
# CYCLE-SPECIFIC VARIABLE MAPPINGS
# =============================================================================

CRP_VAR_MAP = {
    "1999-2000": ("LAB11.xpt", "LBXCRP"),
    "2001-2002": ("L11_B.xpt", "LBXCRP"),
    "2003-2004": ("L11_C.xpt", "LBXCRP"),
    "2005-2006": ("CRP_D.xpt", "LBXCRP"),
}

ALBUMIN_VAR_MAP = {
    "1999-2000": ("LAB18.xpt", "LBXSAL"),
    "2001-2002": ("L40_B.xpt", "LBXSAL"),
    "2003-2004": ("L40_C.xpt", "LBXSAL"),
    "2005-2006": ("BIOPRO_D.xpt", "LBXSAL"),
}

DEXA_VAR_MAP = {
    "1999-2000": "DXX.xpt",
    "2001-2002": "DXX_B.xpt",
    "2003-2004": "DXX_C.xpt",
    "2005-2006": "DXX_D.xpt",
}

DEMO_VAR_MAP = {
    "1999-2000": "DEMO.xpt",
    "2001-2002": "DEMO_B.xpt",
    "2003-2004": "DEMO_C.xpt",
    "2005-2006": "DEMO_D.xpt",
}

MORTALITY_FILES = {
    "1999-2000": "NHANES_1999_2000_MORT_2019_PUBLIC.dat",
    "2001-2002": "NHANES_2001_2002_MORT_2019_PUBLIC.dat",
    "2003-2004": "NHANES_2003_2004_MORT_2019_PUBLIC.dat",
    "2005-2006": "NHANES_2005_2006_MORT_2019_PUBLIC.dat",
}

MORT_COLSPECS = [
    (0, 14),
    (14, 15),
    (15, 16),
    (16, 19),
    (19, 22),
    (22, 25),
    (25, 28),
    (28, 31),
]

MORT_NAMES = [
    "publicid",
    "eligstat",
    "mortstat",
    "ucod_leading",
    "diabetes_mort",
    "hyperten_mort",
    "permth_int",
    "permth_exm",
]


def load_xpt(filepath: Path) -> pd.DataFrame:
    """Load XPT file into a pandas DataFrame."""
    try:
        return pd.read_sas(filepath, format="xport", encoding="latin1")
    except Exception as exc:
        print(f"  Warning: Could not load {filepath.name}: {exc}")
        return pd.DataFrame()


def load_mortality_file(filepath: Path) -> pd.DataFrame:
    """Load NCHS mortality file (fixed-width format)."""
    if not filepath.exists():
        print(f"  Mortality file not found: {filepath}")
        return pd.DataFrame()

    try:
        df = pd.read_fwf(
            filepath,
            colspecs=MORT_COLSPECS,
            names=MORT_NAMES,
            dtype=str,
            na_values=[".", ""],
        )
        df["SEQN"] = df["publicid"].str.strip().astype(float)
        for col in ["eligstat", "mortstat", "ucod_leading", "permth_int", "permth_exm"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        print(f"  Loaded {len(df):,} mortality records from {filepath.name}")
        return df
    except Exception as exc:
        print(f"  Error loading {filepath}: {exc}")
        return pd.DataFrame()


def assert_unique(df: pd.DataFrame, keys, label: str) -> None:
    """Fail fast when a supposedly person-level merge source is duplicated."""
    if df.empty:
        return

    duplicated = df.duplicated(subset=keys, keep=False)
    if duplicated.any():
        dup_rows = int(duplicated.sum())
        unique_dups = int(df.loc[duplicated, keys].drop_duplicates().shape[0])
        raise ValueError(
            f"{label} is not unique on {keys}: {dup_rows:,} duplicated rows across "
            f"{unique_dups:,} duplicated keys."
        )


def merge_unique(
    left: pd.DataFrame,
    right: pd.DataFrame,
    label: str,
    suffixes=("", "_dup"),
) -> pd.DataFrame:
    """Merge a one-row-per-participant table and preserve unique SEQN."""
    if right.empty:
        return left

    assert_unique(right, ["SEQN"], label)
    merged = left.merge(right, on="SEQN", how="left", suffixes=suffixes)
    assert_unique(merged, ["SEQN"], f"{label} merge result")
    return merged


def save_parquet_if_available(df: pd.DataFrame, path: Path) -> bool:
    """Write parquet when an engine is installed; otherwise keep the CSV path canonical."""
    try:
        df.to_parquet(path)
        print(f"Saved: {path}")
        return True
    except ImportError as exc:
        print(f"Warning: could not save {path.name} ({exc})")
        return False


def load_body_measures(cycle_dir: Path) -> pd.DataFrame:
    """Load cycle-specific body measures needed for ALMI and covariates."""
    bmx_patterns = ["BMX.xpt", "BMX_B.xpt", "BMX_C.xpt", "BMX_D.xpt"]
    for bmx_file in bmx_patterns:
        bmx_path = cycle_dir / bmx_file
        if bmx_path.exists():
            bmx_df = load_xpt(bmx_path)
            if "SEQN" not in bmx_df.columns or len(bmx_df) == 0:
                continue

            keep_cols = [c for c in ["SEQN", "BMXHT", "BMXWT", "BMXBMI"] if c in bmx_df.columns]
            bmx_df = bmx_df[keep_cols].copy()
            assert_unique(bmx_df, ["SEQN"], f"{bmx_file} body measures")
            print(f"  Loaded body measures: {len(bmx_df):,} rows")
            return bmx_df

    print("  Warning: Body measures file not found")
    return pd.DataFrame(columns=["SEQN", "BMXHT", "BMXWT", "BMXBMI"])


def calculate_almi(df: pd.DataFrame) -> pd.Series:
    """
    Calculate appendicular lean mass from DEXA data.

    Uses the first complete set of limb lean mass variables available in the
    cycle-specific file. Mass is converted from grams to kilograms when needed.
    """
    arm_leg_vars = [
        ["DXXLATM", "DXXRATM", "DXXLLTM", "DXXRLTM"],
        ["DXDLATM", "DXDRATM", "DXDLLTM", "DXDRLTM"],
        ["DXXLALE", "DXXRALE", "DXXLLLE", "DXXRLLE"],
        ["DXDLALE", "DXDRALE", "DXDLLLE", "DXDRLLE"],
    ]

    alm = pd.Series([np.nan] * len(df), index=df.index)

    for var_set in arm_leg_vars:
        if all(v in df.columns for v in var_set):
            all_present = df[var_set].notna().all(axis=1)
            alm = df[var_set].sum(axis=1)
            alm.loc[~all_present] = np.nan
            if alm.median(skipna=True) > 1000:
                alm = alm / 1000
            print(f"  Using DEXA variables: {var_set}")
            return alm

    print("  Warning: Limb lean mass variables not found in DEXA file")
    return alm


def prepare_dexa_frames(cycle: str, cycle_dir: Path, body_df: pd.DataFrame):
    """
    Prepare both the participant-level mean DEXA summary and the
    imputation-specific DEXA long file.
    """
    dexa_path = cycle_dir / DEXA_VAR_MAP[cycle]
    if not dexa_path.exists():
        print(f"  Warning: DEXA file not found: {dexa_path}")
        return pd.DataFrame(columns=["SEQN", "alm_kg", "almi", "dexa_imputations"]), pd.DataFrame()

    dexa_df = load_xpt(dexa_path)
    if dexa_df.empty or "SEQN" not in dexa_df.columns:
        print(f"  Warning: DEXA file empty or missing SEQN: {dexa_path}")
        return pd.DataFrame(columns=["SEQN", "alm_kg", "almi", "dexa_imputations"]), pd.DataFrame()

    print(f"  DEXA columns available: {len(dexa_df.columns)}")

    if "_MULT_" in dexa_df.columns:
        dexa_df["dexa_imputation"] = pd.to_numeric(dexa_df["_MULT_"], errors="coerce").astype("Int64")
    else:
        dexa_df["dexa_imputation"] = 1

    dexa_df = dexa_df.dropna(subset=["SEQN", "dexa_imputation"]).copy()
    dexa_df["dexa_imputation"] = dexa_df["dexa_imputation"].astype(int)
    assert_unique(dexa_df[["SEQN", "dexa_imputation"]], ["SEQN", "dexa_imputation"], f"{dexa_path.name} imputation rows")

    dexa_df["alm_kg"] = calculate_almi(dexa_df)

    if not body_df.empty:
        dexa_df = dexa_df.merge(body_df, on="SEQN", how="left")
        print(f"  Attached body measures to DEXA rows: {body_df['BMXHT'].notna().sum():,} valid heights")

    if "BMXHT" in dexa_df.columns:
        height_m = dexa_df["BMXHT"] / 100
        valid_height = height_m > 0
        dexa_df["almi"] = np.nan
        dexa_df.loc[valid_height, "almi"] = dexa_df.loc[valid_height, "alm_kg"] / (height_m.loc[valid_height] ** 2)
        print(f"  ALMI median across imputed rows: {dexa_df['almi'].median(skipna=True):.2f} kg/m²")
    else:
        dexa_df["almi"] = np.nan

    counts = dexa_df.groupby("SEQN")["dexa_imputation"].nunique()
    if counts.empty or counts.min() != counts.max():
        raise ValueError(f"{cycle} DEXA imputation counts are inconsistent across participants.")

    print(
        f"  DEXA multiply imputed rows: {len(dexa_df):,} "
        f"({counts.iloc[0]} imputations per participant)"
    )

    dexa_long = dexa_df[["SEQN", "dexa_imputation", "alm_kg", "almi"]].copy()
    dexa_summary = (
        dexa_long.groupby("SEQN", as_index=False)
        .agg(alm_kg=("alm_kg", "mean"), almi=("almi", "mean"), dexa_imputations=("dexa_imputation", "nunique"))
    )
    assert_unique(dexa_summary, ["SEQN"], f"{cycle} DEXA summary")

    return dexa_summary, dexa_long


def process_cycle(cycle: str):
    """Process a single NHANES cycle and return person-level and MI data."""
    print(f"\n{'='*60}")
    print(f"Processing {cycle}")
    print("=" * 60)

    cycle_dir = DATA_RAW / cycle
    if not cycle_dir.exists():
        print(f"  Cycle directory not found: {cycle_dir}")
        return pd.DataFrame(), pd.DataFrame()

    demo_file = cycle_dir / DEMO_VAR_MAP[cycle]
    if not demo_file.exists():
        print(f"  Demographics file not found: {demo_file}")
        return pd.DataFrame(), pd.DataFrame()

    base = load_xpt(demo_file)
    if base.empty or "SEQN" not in base.columns:
        print(f"  Demographics file empty or missing SEQN: {demo_file}")
        return pd.DataFrame(), pd.DataFrame()

    assert_unique(base, ["SEQN"], f"{cycle} demographics")
    print(f"  Loaded {len(base):,} participants from demographics")

    if "RIDRETH1" in base.columns:
        base["race_eth"] = base["RIDRETH1"]
    elif "RIDRETH3" in base.columns:
        base["race_eth"] = base["RIDRETH3"]

    if "WTMEC2YR" in base.columns:
        base["weight_mec"] = base["WTMEC2YR"]
    elif "WTMEC4YR" in base.columns:
        base["weight_mec"] = base["WTMEC4YR"]
    else:
        print(f"  WARNING: No MEC weight column found for {cycle}")

    for col in ["SDMVPSU", "SDMVSTRA", "weight_mec"]:
        if col not in base.columns or base[col].isna().all():
            print(f"  ERROR: Survey design variable '{col}' missing or all NaN for {cycle}")
        else:
            print(f"  Survey variable {col}: {base[col].notna().sum():,} valid values")

    crp_file, crp_var = CRP_VAR_MAP[cycle]
    crp_path = cycle_dir / crp_file
    if crp_path.exists():
        crp_df = load_xpt(crp_path)
        if crp_var in crp_df.columns:
            crp_df = crp_df[["SEQN", crp_var]].copy()
            assert_unique(crp_df, ["SEQN"], f"{crp_file} CRP")
            crp_df["hscrp"] = crp_df[crp_var]
            if cycle in ["1999-2000", "2001-2002", "2003-2004", "2005-2006"]:
                pre_median = crp_df["hscrp"].median(skipna=True)
                crp_df["hscrp"] = crp_df["hscrp"] * 10
                print(
                    f"  Converted CRP from mg/dL to mg/L "
                    f"(pre-conversion median: {pre_median:.3f} mg/dL)"
                )
            base = merge_unique(base, crp_df[["SEQN", "hscrp"]], f"{cycle} CRP")
            print(f"  Merged CRP: {crp_df['hscrp'].notna().sum():,} valid values")
    else:
        print(f"  Warning: CRP file not found: {crp_path}")

    alb_file, alb_var = ALBUMIN_VAR_MAP[cycle]
    alb_path = cycle_dir / alb_file
    if alb_path.exists():
        alb_df = load_xpt(alb_path)
        if alb_var in alb_df.columns:
            alb_df = alb_df[["SEQN", alb_var]].copy()
            assert_unique(alb_df, ["SEQN"], f"{alb_file} albumin")
            alb_df["albumin"] = alb_df[alb_var]
            base = merge_unique(base, alb_df[["SEQN", "albumin"]], f"{cycle} albumin")
            print(f"  Merged albumin: {alb_df['albumin'].notna().sum():,} valid values")
    else:
        print(f"  Warning: Albumin file not found: {alb_path}")

    body_df = load_body_measures(cycle_dir)
    if not body_df.empty:
        base = merge_unique(base, body_df, f"{cycle} body measures")

    covariate_files = [
        ("DIQ", "Diabetes"),
        ("SMQ", "Smoking"),
        ("MCQ", "Medical conditions"),
        ("HUQ", "Health status"),
        ("PFQ", "Physical functioning"),
    ]

    for prefix, description in covariate_files:
        for ext in ["", "_B", "_C", "_D"]:
            cov_path = cycle_dir / f"{prefix}{ext}.xpt"
            if cov_path.exists():
                cov_df = load_xpt(cov_path)
                if "SEQN" in cov_df.columns and len(cov_df) > 0:
                    assert_unique(cov_df, ["SEQN"], f"{cov_path.name} {description}")
                    base = base.merge(cov_df, on="SEQN", how="left", suffixes=("", f"_{prefix}"))
                    assert_unique(base, ["SEQN"], f"{cycle} {description} merge result")
                    print(f"  Merged {description}: {len(cov_df):,} records")
                break

    base["cycle"] = cycle
    base["cohort"] = "validation"

    dexa_summary, dexa_long = prepare_dexa_frames(cycle, cycle_dir, body_df)
    person_df = merge_unique(base, dexa_summary, f"{cycle} DEXA summary")

    if dexa_long.empty:
        mi_df = pd.DataFrame(columns=list(base.columns) + ["dexa_imputation", "alm_kg", "almi"])
    else:
        mi_df = base.merge(dexa_long, on="SEQN", how="inner")
        mi_df["cycle"] = cycle
        mi_df["cohort"] = "validation"
        assert_unique(mi_df, ["SEQN", "dexa_imputation"], f"{cycle} MI cohort")

    return person_df, mi_df


def construct_iri_validation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construct IRI for the validation cohort.

    IRI = (-z_hsCRP) + z_Albumin + z_ALMI (sex-specific for ALMI)
    """
    print("\n" + "=" * 60)
    print("Constructing IRI for validation cohort")
    print("=" * 60)

    df = df.copy()

    required = ["hscrp", "albumin", "almi"]
    for var in required:
        if var in df.columns:
            print(f"  {var}: {df[var].notna().sum():,} valid values")
        else:
            print(f"  WARNING: {var} not found in dataframe")

    params_path = DATA_PROCESSED / "derivation_zscore_params.json"
    if params_path.exists():
        with open(params_path, "r") as f:
            params = json.load(f)
        print("  Using DERIVATION cohort z-score parameters (proper external validation)")
        use_derivation_params = True
    else:
        print("  WARNING: derivation_zscore_params.json not found!")
        print("  Run 02_build_cohort.py first to generate derivation parameters.")
        print("  Falling back to validation-cohort standardization (NOT ideal).")
        use_derivation_params = False

    df["log_hscrp"] = np.log(df["hscrp"].replace(0, np.nan))

    if use_derivation_params:
        df["z_log_hscrp"] = (df["log_hscrp"] - params["log_crp"]["mean"]) / params["log_crp"]["std"]
        df["z_albumin"] = (df["albumin"] - params["albumin"]["mean"]) / params["albumin"]["std"]

        df["z_almi"] = np.nan
        for sex, key in [(1, "almi_male"), (2, "almi_female")]:
            mask = df["RIAGENDR"] == sex
            if mask.sum() > 0 and params[key]["std"] > 0:
                df.loc[mask, "z_almi"] = (df.loc[mask, "almi"] - params[key]["mean"]) / params[key]["std"]
    else:
        df["z_log_hscrp"] = (df["log_hscrp"] - df["log_hscrp"].mean()) / df["log_hscrp"].std()
        df["z_albumin"] = (df["albumin"] - df["albumin"].mean()) / df["albumin"].std()

        df["z_almi"] = np.nan
        for sex in [1, 2]:
            mask = df["RIAGENDR"] == sex
            if mask.sum() > 0:
                almi_mean = df.loc[mask, "almi"].mean()
                almi_std = df.loc[mask, "almi"].std()
                if almi_std > 0:
                    df.loc[mask, "z_almi"] = (df.loc[mask, "almi"] - almi_mean) / almi_std

    df["iri"] = (-df["z_log_hscrp"]) + df["z_albumin"] + df["z_almi"]
    df["iri_quartile"] = np.nan

    print(f"\n  IRI computed for {df['iri'].notna().sum():,} rows")
    if df["iri"].notna().sum() > 0:
        print(f"  IRI mean: {df['iri'].mean():.3f}, std: {df['iri'].std():.3f}")
        print(f"  IRI range: [{df['iri'].min():.3f}, {df['iri'].max():.3f}]")

    return df


def create_derived_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Create additional clinical variables for analysis."""
    df = df.copy()
    df["age"] = df["RIDAGEYR"]
    df["sex"] = df["RIAGENDR"]
    df["female"] = (df["sex"] == 2).astype(int)

    edu_var = None
    for var in ["DMDEDUC2", "DMDEDUC", "DMDEDUC3"]:
        if var in df.columns:
            edu_var = var
            break
    if edu_var:
        df["education"] = df[edu_var]
        df.loc[df["education"] > 5, "education"] = np.nan
        df["edu_less_than_hs"] = (df["education"].isin([1, 2])).astype(float)
        df.loc[df["education"].isna(), "edu_less_than_hs"] = np.nan
        print(f"  Education available: {df['education'].notna().sum():,}")

    if "INDFMPIR" in df.columns:
        df["pir"] = df["INDFMPIR"]
        df["below_poverty"] = (df["pir"] < 1).astype(float)
        df.loc[df["pir"].isna(), "below_poverty"] = np.nan
        print(f"  PIR available: {df['pir'].notna().sum():,}")

    if "BMXBMI" in df.columns:
        df["bmi"] = df["BMXBMI"]

    if "DIQ010" in df.columns:
        df["diabetes"] = (df["DIQ010"] == 1).astype(int)

    if "BPQ040A" in df.columns:
        df["hypertension"] = (df["BPQ040A"] == 1).astype(int)

    if "SMQ020" in df.columns and "SMQ040" in df.columns:
        df["current_smoker"] = ((df["SMQ020"] == 1) & (df["SMQ040"].isin([1, 2]))).astype(int)

    cvd_vars = ["MCQ160B", "MCQ160C", "MCQ160D", "MCQ160E", "MCQ160F"]
    available_cvd = [v for v in cvd_vars if v in df.columns]
    if available_cvd:
        df["cvd_history"] = (df[available_cvd].eq(1).any(axis=1)).astype(int)

    if "HUQ010" in df.columns:
        df["fair_poor_health"] = (df["HUQ010"].isin([4, 5])).astype(int)

    if "PFQ061B" in df.columns:
        df["walking_difficulty"] = (df["PFQ061B"].isin([2, 3, 4])).astype(int)

    return df


def apply_eligibility_criteria(df: pd.DataFrame, summary_keys=None, label: str = "participants") -> pd.DataFrame:
    """Apply the main validation-cohort eligibility criteria."""
    df = df.copy()
    print("\n" + "=" * 60)
    print("Applying eligibility criteria")
    print("=" * 60)

    summary_df = df.drop_duplicates(subset=summary_keys) if summary_keys else df
    n_start = len(summary_df)

    df["eligible"] = 1
    df.loc[df["RIDAGEYR"] < 20, "eligible"] = 0

    if "RIDEXPRG" in df.columns:
        df.loc[df["RIDEXPRG"] == 1, "eligible"] = 0

    has_hscrp = df["hscrp"].notna() if "hscrp" in df.columns else pd.Series([False] * len(df))
    has_albumin = df["albumin"].notna() if "albumin" in df.columns else pd.Series([False] * len(df))
    has_almi = df["almi"].notna() if "almi" in df.columns else pd.Series([False] * len(df))

    df["has_iri_components"] = (has_hscrp & has_albumin & has_almi).astype(int)
    df.loc[df["has_iri_components"] == 0, "eligible"] = 0

    df["crp_valid"] = (df["hscrp"] <= 10).astype(int) if "hscrp" in df.columns else 0
    df.loc[df["crp_valid"] == 0, "eligible"] = 0

    summary_df = df.drop_duplicates(subset=summary_keys) if summary_keys else df
    n_age = int((summary_df["RIDAGEYR"] >= 20).sum())
    n_iri = int(summary_df["has_iri_components"].sum())
    n_crp = int(((summary_df["has_iri_components"] == 1) & (summary_df["crp_valid"] == 1)).sum())
    n_eligible = int(summary_df["eligible"].sum())

    print(f"  Age >= 20: {n_age:,} {label}")
    print(f"  Has all IRI components: {n_iri:,} {label}")
    print(f"  CRP <= 10 mg/L: {n_crp:,} {label}")
    print(f"\n  Total eligible for analysis: {n_eligible:,} ({100 * n_eligible / n_start:.1f}% of {label})")

    return df


def compute_quartile_bins(df: pd.DataFrame) -> list:
    """Compute fixed quartile bins from the participant-level analytic cohort."""
    elig_iri = df.loc[(df["eligible"] == 1) & df["iri"].notna(), "iri"]
    if len(elig_iri) == 0:
        raise ValueError("Cannot compute IRI quartiles: no eligible rows with non-missing IRI.")

    _, bins = pd.qcut(elig_iri, q=4, retbins=True, duplicates="drop")
    if len(bins) != 5:
        raise ValueError(f"Expected 4 IRI quartile bins, found {len(bins) - 1}.")

    bins[0] = -np.inf
    bins[-1] = np.inf
    print(f"  IRI quartile bins computed from {len(elig_iri):,} eligible participants")
    print(f"  Quartile cutpoints: {', '.join(f'{b:.3f}' for b in bins[1:-1])}")
    return bins.tolist()


def assign_iri_quartiles(df: pd.DataFrame, quartile_bins) -> pd.DataFrame:
    """Assign fixed IRI quartiles to eligible rows."""
    mask = (df["eligible"] == 1) & df["iri"].notna()
    df["iri_quartile"] = pd.Series([pd.NA] * len(df), dtype="object")
    df.loc[mask, "iri_quartile"] = pd.cut(
        df.loc[mask, "iri"],
        bins=quartile_bins,
        labels=QUARTILE_LABELS,
        include_lowest=True,
        ordered=True,
    ).astype(str)
    df.loc[~mask, "iri_quartile"] = pd.NA
    df["iri_quartile"] = pd.Categorical(df["iri_quartile"], categories=QUARTILE_LABELS, ordered=True)
    return df


def link_mortality(df: pd.DataFrame, summary_keys=None, label: str = "participants") -> pd.DataFrame:
    """Link validation cohort with mortality data through 2019."""
    df = df.copy()
    print("\n" + "=" * 60)
    print("Linking mortality data")
    print("=" * 60)

    all_mort = []
    for cycle, mort_file in MORTALITY_FILES.items():
        mort_path = DATA_MORTALITY / mort_file
        if mort_path.exists():
            mort_df = load_mortality_file(mort_path)
            if len(mort_df) > 0:
                mort_df["mort_cycle"] = cycle
                all_mort.append(mort_df)

    if not all_mort:
        print("  No mortality data loaded!")
        return df

    combined_mort = pd.concat(all_mort, ignore_index=True)
    combined_mort = combined_mort.drop_duplicates(subset=["SEQN"])
    print(f"  Combined mortality records: {len(combined_mort):,}")

    combined_mort["mort_all"] = (combined_mort["mortstat"] == 1).astype(int)
    combined_mort["mort_cv"] = ((combined_mort["mortstat"] == 1) & (combined_mort["ucod_leading"].isin([1, 5]))).astype(int)
    combined_mort["mort_heart"] = ((combined_mort["mortstat"] == 1) & (combined_mort["ucod_leading"] == 1)).astype(int)
    combined_mort["mort_stroke"] = ((combined_mort["mortstat"] == 1) & (combined_mort["ucod_leading"] == 5)).astype(int)
    combined_mort["mort_cancer"] = ((combined_mort["mortstat"] == 1) & (combined_mort["ucod_leading"] == 2)).astype(int)
    combined_mort["followup_months"] = combined_mort["permth_exm"]
    combined_mort["followup_years"] = combined_mort["followup_months"] / 12

    mort_vars = [
        "SEQN",
        "mortstat",
        "mort_all",
        "mort_cv",
        "mort_heart",
        "mort_stroke",
        "mort_cancer",
        "followup_months",
        "followup_years",
        "ucod_leading",
        "eligstat",
    ]
    df = df.merge(combined_mort[mort_vars], on="SEQN", how="left")

    linkage_eligible = df["eligstat"] == 1
    for col in ["mort_all", "mort_cv", "mort_heart", "mort_stroke", "mort_cancer"]:
        df.loc[linkage_eligible & df[col].isna(), col] = 0
        df[col] = df[col].astype("Int64")

    cycle_to_followup = {
        "1999-2000": 20,
        "2001-2002": 18,
        "2003-2004": 16,
        "2005-2006": 14,
    }
    for cycle, fu_years in cycle_to_followup.items():
        mask = (df["cycle"] == cycle) & (df["followup_years"].isna())
        df.loc[mask, "followup_years"] = fu_years

    summary_df = df.drop_duplicates(subset=summary_keys) if summary_keys else df
    print(f"\n  Mortality linkage complete ({label}):")
    print(f"  Total deaths (all-cause): {summary_df['mort_all'].sum():,}")
    print(f"  CV deaths: {summary_df['mort_cv'].sum():,}")
    print(f"  Heart disease deaths: {summary_df['mort_heart'].sum():,}")
    print(f"  Mean follow-up: {summary_df['followup_years'].mean():.1f} years")

    return df


def validate_outputs(person_df: pd.DataFrame, mi_df: pd.DataFrame) -> None:
    """Check that the saved cohorts obey the intended person vs MI structure."""
    assert_unique(person_df, ["SEQN"], "participant-level validation cohort")

    mi_nonmissing = mi_df.dropna(subset=["dexa_imputation"]).copy()
    assert_unique(mi_nonmissing, ["SEQN", "dexa_imputation"], "MI validation cohort")

    eligible_person = person_df.loc[person_df["eligible"] == 1, "SEQN"].astype(float)
    eligible_mi = mi_nonmissing.loc[mi_nonmissing["eligible"] == 1].copy()
    mi_counts = eligible_mi.groupby("SEQN")["dexa_imputation"].nunique()

    if mi_counts.empty:
        raise ValueError("MI validation cohort has no eligible rows after filtering.")

    if mi_counts.min() != 5 or mi_counts.max() != 5:
        bad = int((mi_counts != 5).sum())
        raise ValueError(f"Eligible MI validation cohort must have 5 imputations per participant; found {bad:,} inconsistent participants.")

    person_set = set(eligible_person.tolist())
    mi_set = set(mi_counts.index.astype(float).tolist())
    if person_set != mi_set:
        raise ValueError(
            "Eligible participant IDs do not match between the person-level and MI validation cohorts."
        )

    per_imp_counts = eligible_mi.groupby("dexa_imputation")["SEQN"].nunique()
    if per_imp_counts.nunique() != 1:
        raise ValueError("Eligible participant counts differ across DEXA imputations.")

    invalid_followup = person_df.loc[(person_df["eligible"] == 1) & (person_df["followup_years"] <= 0)]
    if len(invalid_followup) > 0:
        raise ValueError(f"Found {len(invalid_followup):,} eligible participants with nonpositive follow-up.")

    print("\nIntegrity checks passed:")
    print(f"  Participant-level cohort rows: {len(person_df):,}")
    print(f"  Eligible participant count: {len(person_set):,}")
    print(f"  MI cohort rows: {len(mi_nonmissing):,}")
    print(f"  Eligible participants per imputation: {int(per_imp_counts.iloc[0]):,}")


def save_quartile_bins(quartile_bins: list) -> Path:
    """Persist the fixed quartile cutpoints used across person and MI datasets."""
    out_path = DATA_PROCESSED / "iri_validation_quartile_bins.json"
    with open(out_path, "w") as f:
        json.dump({"quartile_bins": quartile_bins, "labels": QUARTILE_LABELS}, f, indent=2)
    return out_path


def main():
    """Build the validation cohort."""
    print("\n" + "=" * 60)
    print("IRI VALIDATION STUDY - COHORT BUILDING")
    print("NHANES 1999-2006")
    print("=" * 60)

    cycles = ["1999-2000", "2001-2002", "2003-2004", "2005-2006"]
    person_frames = []
    mi_frames = []

    for cycle in cycles:
        person_df, mi_df = process_cycle(cycle)
        if len(person_df) > 0:
            person_frames.append(person_df)
        if len(mi_df) > 0:
            mi_frames.append(mi_df)

    if not person_frames:
        print("\nNo data loaded. Run 11_download_validation_data.py first.")
        return

    combined = pd.concat(person_frames, ignore_index=True)
    assert_unique(combined, ["SEQN"], "combined participant-level validation cohort")
    print(f"\nCombined participant-level cohort: {len(combined):,} unique participants across all cycles")

    combined = construct_iri_validation(combined)
    combined = create_derived_variables(combined)
    combined = apply_eligibility_criteria(combined, summary_keys=["SEQN"])
    quartile_bins = compute_quartile_bins(combined)
    combined = assign_iri_quartiles(combined, quartile_bins)
    combined = link_mortality(combined, summary_keys=["SEQN"])

    combined_mi = pd.concat(mi_frames, ignore_index=True)
    combined_mi = construct_iri_validation(combined_mi)
    combined_mi = create_derived_variables(combined_mi)
    combined_mi = apply_eligibility_criteria(combined_mi, summary_keys=["SEQN"], label="unique participants")
    combined_mi = assign_iri_quartiles(combined_mi, quartile_bins)
    combined_mi = link_mortality(combined_mi, summary_keys=["SEQN"], label="unique participants")

    validate_outputs(combined, combined_mi)

    print("\n" + "=" * 60)
    print("MORTALITY BY IRI QUARTILE")
    print("=" * 60)
    eligible = combined[combined["eligible"] == 1].copy()
    if "iri_quartile" in eligible.columns:
        mort_summary = (
            eligible.groupby("iri_quartile", observed=False)
            .agg(
                N=("SEQN", "count"),
                Deaths=("mort_all", "sum"),
                Mortality_Rate=("mort_all", "mean"),
                CV_Deaths=("mort_cv", "sum"),
                CV_Mortality_Rate=("mort_cv", "mean"),
                Followup_Years=("followup_years", "mean"),
            )
            .round(3)
        )
        print(mort_summary)

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    person_parquet = DATA_PROCESSED / "iri_validation_cohort.parquet"
    person_csv = DATA_PROCESSED / "iri_validation_cohort.csv"
    eligible_csv = DATA_PROCESSED / "iri_validation_eligible.csv"
    eligible_parquet = DATA_PROCESSED / "iri_validation_eligible.parquet"

    mi_parquet = DATA_PROCESSED / "iri_validation_cohort_mi.parquet"
    mi_csv = DATA_PROCESSED / "iri_validation_cohort_mi.csv"
    mi_eligible_csv = DATA_PROCESSED / "iri_validation_eligible_mi.csv"
    mi_eligible_parquet = DATA_PROCESSED / "iri_validation_eligible_mi.parquet"

    combined.to_csv(person_csv, index=False)
    eligible.to_csv(eligible_csv, index=False)

    combined_mi.to_csv(mi_csv, index=False)
    combined_mi.loc[combined_mi["eligible"] == 1].to_csv(mi_eligible_csv, index=False)

    person_parquet_saved <- save_parquet_if_available(combined, person_parquet)
    eligible_parquet_saved <- save_parquet_if_available(eligible, eligible_parquet)
    mi_parquet_saved <- save_parquet_if_available(combined_mi, mi_parquet)
    mi_eligible_parquet_saved <- save_parquet_if_available(
        combined_mi.loc[combined_mi["eligible"] == 1],
        mi_eligible_parquet,
    )

    quartile_path = save_quartile_bins(quartile_bins)

    print(f"Saved: {person_csv}")
    print(f"Saved: {eligible_csv}")
    print(f"Saved: {mi_csv}")
    print(f"Saved: {mi_eligible_csv}")
    if person_parquet_saved:
        print(f"Saved: {person_parquet}")
    if eligible_parquet_saved:
        print(f"Saved: {eligible_parquet}")
    if mi_parquet_saved:
        print(f"Saved: {mi_parquet}")
    if mi_eligible_parquet_saved:
        print(f"Saved: {mi_eligible_parquet}")
    print(f"Saved: {quartile_path}")

    print("\n" + "=" * 60)
    print("VALIDATION COHORT SUMMARY")
    print("=" * 60)
    print(f"Total unique participants: {len(combined):,}")
    print(f"Eligible participants: {combined['eligible'].sum():,}")
    print(f"All-cause deaths: {eligible['mort_all'].sum():,}")
    print(f"CV deaths: {eligible['mort_cv'].sum():,}")
    print(f"Mean follow-up: {eligible['followup_years'].mean():.1f} years")

    if "iri" in eligible.columns and eligible["iri"].notna().sum() > 0:
        print(f"\nIRI distribution (eligible participants):")
        print(f"  Mean: {eligible['iri'].mean():.3f}")
        print(f"  SD: {eligible['iri'].std():.3f}")
        print(f"  Range: [{eligible['iri'].min():.3f}, {eligible['iri'].max():.3f}]")


if __name__ == "__main__":
    main()
