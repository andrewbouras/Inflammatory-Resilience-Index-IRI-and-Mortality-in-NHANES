"""
Modified IRI Study - NHANES Data Download Script

Modified IRI = (-z_CRP) + z_Albumin + z_ALM (Appendicular Lean Mass)

Available cycles: 2015-2016, 2017-2020
(Only cycles with both hs-CRP and DEXA whole body scans)
"""

import os
import requests
from pathlib import Path
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_MORTALITY = PROJECT_ROOT / "data" / "mortality"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': '*/*',
}

BASE_URL = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public"

# =============================================================================
# FILE DEFINITIONS - 2015-2016 and 2017-2020
# =============================================================================

FILES_2015_2016 = {
    # Demographics
    "DEMO_I.xpt": f"{BASE_URL}/2015/DataFiles/DEMO_I.xpt",
    
    # IRI Components
    "HSCRP_I.xpt": f"{BASE_URL}/2015/DataFiles/HSCRP_I.xpt",          # hs-CRP
    "BIOPRO_I.xpt": f"{BASE_URL}/2015/DataFiles/BIOPRO_I.xpt",        # Albumin + Creatinine
    "DXX_I.xpt": f"{BASE_URL}/2015/DataFiles/DXX_I.xpt",              # DEXA Whole Body (ALM)
    
    # Covariates
    "BMX_I.xpt": f"{BASE_URL}/2015/DataFiles/BMX_I.xpt",              # Body measures
    "BPX_I.xpt": f"{BASE_URL}/2015/DataFiles/BPX_I.xpt",              # Blood pressure
    "BPQ_I.xpt": f"{BASE_URL}/2015/DataFiles/BPQ_I.xpt",              # BP questionnaire
    "DIQ_I.xpt": f"{BASE_URL}/2015/DataFiles/DIQ_I.xpt",              # Diabetes
    "GHB_I.xpt": f"{BASE_URL}/2015/DataFiles/GHB_I.xpt",              # HbA1c
    "GLU_I.xpt": f"{BASE_URL}/2015/DataFiles/GLU_I.xpt",              # Glucose
    "TCHOL_I.xpt": f"{BASE_URL}/2015/DataFiles/TCHOL_I.xpt",          # Total cholesterol
    "HDL_I.xpt": f"{BASE_URL}/2015/DataFiles/HDL_I.xpt",              # HDL
    "TRIGLY_I.xpt": f"{BASE_URL}/2015/DataFiles/TRIGLY_I.xpt",        # Triglycerides
    "SMQ_I.xpt": f"{BASE_URL}/2015/DataFiles/SMQ_I.xpt",              # Smoking
    "MCQ_I.xpt": f"{BASE_URL}/2015/DataFiles/MCQ_I.xpt",              # Medical conditions
    "KIQ_U_I.xpt": f"{BASE_URL}/2015/DataFiles/KIQ_U_I.xpt",          # Kidney questionnaire
    "ALB_CR_I.xpt": f"{BASE_URL}/2015/DataFiles/ALB_CR_I.xpt",        # Urine albumin/creatinine
}

FILES_2017_2020 = {
    # Demographics
    "P_DEMO.xpt": f"{BASE_URL}/2017/DataFiles/P_DEMO.xpt",
    
    # IRI Components
    "P_HSCRP.xpt": f"{BASE_URL}/2017/DataFiles/P_HSCRP.xpt",
    "P_BIOPRO.xpt": f"{BASE_URL}/2017/DataFiles/P_BIOPRO.xpt",
    "P_DXX.xpt": f"{BASE_URL}/2017/DataFiles/P_DXX.xpt",
    
    # Covariates
    "P_BMX.xpt": f"{BASE_URL}/2017/DataFiles/P_BMX.xpt",
    "P_BPXO.xpt": f"{BASE_URL}/2017/DataFiles/P_BPXO.xpt",
    "P_BPQ.xpt": f"{BASE_URL}/2017/DataFiles/P_BPQ.xpt",
    "P_DIQ.xpt": f"{BASE_URL}/2017/DataFiles/P_DIQ.xpt",
    "P_GHB.xpt": f"{BASE_URL}/2017/DataFiles/P_GHB.xpt",
    "P_GLU.xpt": f"{BASE_URL}/2017/DataFiles/P_GLU.xpt",
    "P_TCHOL.xpt": f"{BASE_URL}/2017/DataFiles/P_TCHOL.xpt",
    "P_HDL.xpt": f"{BASE_URL}/2017/DataFiles/P_HDL.xpt",
    "P_TRIGLY.xpt": f"{BASE_URL}/2017/DataFiles/P_TRIGLY.xpt",
    "P_SMQ.xpt": f"{BASE_URL}/2017/DataFiles/P_SMQ.xpt",
    "P_MCQ.xpt": f"{BASE_URL}/2017/DataFiles/P_MCQ.xpt",
    "P_KIQ_U.xpt": f"{BASE_URL}/2017/DataFiles/P_KIQ_U.xpt",
    "P_ALB_CR.xpt": f"{BASE_URL}/2017/DataFiles/P_ALB_CR.xpt",
}

# Mortality linkage files
MORTALITY_FILES = {
    "2015-2016": "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2015_2016_MORT_2019_PUBLIC.dat",
    "2017-2018": "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2017_2018_MORT_2019_PUBLIC.dat",
}


def download_file(url: str, dest_path: Path, min_size: int = 1000) -> bool:
    """Download a file with validation."""
    try:
        if dest_path.exists() and dest_path.stat().st_size > min_size:
            print(f"  [EXISTS] {dest_path.name}")
            return True
            
        print(f"  [DOWNLOADING] {dest_path.name}...")
        response = requests.get(url, headers=HEADERS, verify=False, timeout=120)
        
        if response.status_code == 200 and len(response.content) > min_size:
            with open(dest_path, 'wb') as f:
                f.write(response.content)
            print(f"  [SUCCESS] {dest_path.name} ({len(response.content):,} bytes)")
            return True
        else:
            print(f"  [FAILED] {dest_path.name} - Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  [ERROR] {dest_path.name}: {e}")
        return False


def download_cycle(cycle_name: str, files: dict):
    """Download all files for a cycle."""
    print(f"\n{'='*60}")
    print(f"CYCLE: {cycle_name}")
    print('='*60)
    
    cycle_dir = DATA_RAW / cycle_name
    cycle_dir.mkdir(parents=True, exist_ok=True)
    
    success = 0
    for filename, url in files.items():
        if download_file(url, cycle_dir / filename):
            success += 1
    
    print(f"\n  Downloaded {success}/{len(files)} files")


def download_mortality():
    """Download mortality linkage files."""
    print(f"\n{'='*60}")
    print("MORTALITY LINKAGE FILES")
    print('='*60)
    
    DATA_MORTALITY.mkdir(parents=True, exist_ok=True)
    
    for cycle, url in MORTALITY_FILES.items():
        filename = url.split('/')[-1]
        download_file(url, DATA_MORTALITY / filename, min_size=100)


def main():
    print("\n" + "="*60)
    print("MODIFIED IRI STUDY - NHANES DATA DOWNLOAD")
    print("Cycles: 2015-2016, 2017-2020")
    print("Components: hs-CRP + Albumin + DEXA (ALM)")
    print("="*60)
    
    download_cycle("2015-2016", FILES_2015_2016)
    download_cycle("2017-2020", FILES_2017_2020)
    download_mortality()
    
    print("\n" + "="*60)
    print("DOWNLOAD COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
