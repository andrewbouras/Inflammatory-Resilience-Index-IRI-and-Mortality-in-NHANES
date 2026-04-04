"""
IRI Validation Study - NHANES 1999-2006 Data Download Script

Downloads data for external validation cohort with long-term mortality follow-up.
Cycles: 1999-2000, 2001-2002, 2003-2004, 2005-2006
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
# FILE DEFINITIONS - NHANES 1999-2006 (Validation Cohort)
# =============================================================================

FILES_1999_2000 = {
    # Demographics
    "DEMO.xpt": f"{BASE_URL}/1999/DataFiles/DEMO.xpt",
    
    # IRI Components
    "LAB11.xpt": f"{BASE_URL}/1999/DataFiles/LAB11.xpt",      # CRP
    "LAB18.xpt": f"{BASE_URL}/1999/DataFiles/LAB18.xpt",      # Biochemistry (Albumin)
    "DXX.xpt": f"{BASE_URL}/1999/DataFiles/DXX.xpt",          # DEXA Whole Body
    
    # Covariates
    "BMX.xpt": f"{BASE_URL}/1999/DataFiles/BMX.xpt",          # Body measures
    "BPX.xpt": f"{BASE_URL}/1999/DataFiles/BPX.xpt",          # Blood pressure
    "DIQ.xpt": f"{BASE_URL}/1999/DataFiles/DIQ.xpt",          # Diabetes
    "LAB10AM.xpt": f"{BASE_URL}/1999/DataFiles/LAB10AM.xpt",  # HbA1c
    "LAB13.xpt": f"{BASE_URL}/1999/DataFiles/LAB13.xpt",      # Total cholesterol, HDL
    "LAB13AM.xpt": f"{BASE_URL}/1999/DataFiles/LAB13AM.xpt",  # Triglycerides
    "SMQ.xpt": f"{BASE_URL}/1999/DataFiles/SMQ.xpt",          # Smoking
    "MCQ.xpt": f"{BASE_URL}/1999/DataFiles/MCQ.xpt",          # Medical conditions
    "HUQ.xpt": f"{BASE_URL}/1999/DataFiles/HUQ.xpt",          # Health status
    "PFQ.xpt": f"{BASE_URL}/1999/DataFiles/PFQ.xpt",          # Physical functioning
    "PAQ.xpt": f"{BASE_URL}/1999/DataFiles/PAQ.xpt",          # Physical activity
}

FILES_2001_2002 = {
    # Demographics
    "DEMO_B.xpt": f"{BASE_URL}/2001/DataFiles/DEMO_B.xpt",
    
    # IRI Components
    "L11_B.xpt": f"{BASE_URL}/2001/DataFiles/L11_B.xpt",      # CRP
    "L40_B.xpt": f"{BASE_URL}/2001/DataFiles/L40_B.xpt",      # Biochemistry (Albumin)
    "DXX_B.xpt": f"{BASE_URL}/2001/DataFiles/DXX_B.xpt",      # DEXA Whole Body
    
    # Covariates
    "BMX_B.xpt": f"{BASE_URL}/2001/DataFiles/BMX_B.xpt",
    "BPX_B.xpt": f"{BASE_URL}/2001/DataFiles/BPX_B.xpt",
    "DIQ_B.xpt": f"{BASE_URL}/2001/DataFiles/DIQ_B.xpt",
    "L10AM_B.xpt": f"{BASE_URL}/2001/DataFiles/L10AM_B.xpt",  # HbA1c
    "L13_B.xpt": f"{BASE_URL}/2001/DataFiles/L13_B.xpt",      # Cholesterol
    "L13AM_B.xpt": f"{BASE_URL}/2001/DataFiles/L13AM_B.xpt",  # Triglycerides
    "SMQ_B.xpt": f"{BASE_URL}/2001/DataFiles/SMQ_B.xpt",
    "MCQ_B.xpt": f"{BASE_URL}/2001/DataFiles/MCQ_B.xpt",
    "HUQ_B.xpt": f"{BASE_URL}/2001/DataFiles/HUQ_B.xpt",
    "PFQ_B.xpt": f"{BASE_URL}/2001/DataFiles/PFQ_B.xpt",
    "PAQ_B.xpt": f"{BASE_URL}/2001/DataFiles/PAQ_B.xpt",      # Physical activity
}

FILES_2003_2004 = {
    # Demographics
    "DEMO_C.xpt": f"{BASE_URL}/2003/DataFiles/DEMO_C.xpt",
    
    # IRI Components
    "L11_C.xpt": f"{BASE_URL}/2003/DataFiles/L11_C.xpt",      # CRP
    "L40_C.xpt": f"{BASE_URL}/2003/DataFiles/L40_C.xpt",      # Biochemistry (Albumin)
    "DXX_C.xpt": f"{BASE_URL}/2003/DataFiles/DXX_C.xpt",      # DEXA Whole Body
    
    # Covariates
    "BMX_C.xpt": f"{BASE_URL}/2003/DataFiles/BMX_C.xpt",
    "BPX_C.xpt": f"{BASE_URL}/2003/DataFiles/BPX_C.xpt",
    "DIQ_C.xpt": f"{BASE_URL}/2003/DataFiles/DIQ_C.xpt",
    "L10AM_C.xpt": f"{BASE_URL}/2003/DataFiles/L10AM_C.xpt",
    "L13_C.xpt": f"{BASE_URL}/2003/DataFiles/L13_C.xpt",
    "L13AM_C.xpt": f"{BASE_URL}/2003/DataFiles/L13AM_C.xpt",
    "SMQ_C.xpt": f"{BASE_URL}/2003/DataFiles/SMQ_C.xpt",
    "MCQ_C.xpt": f"{BASE_URL}/2003/DataFiles/MCQ_C.xpt",
    "HUQ_C.xpt": f"{BASE_URL}/2003/DataFiles/HUQ_C.xpt",
    "PFQ_C.xpt": f"{BASE_URL}/2003/DataFiles/PFQ_C.xpt",
    "PAQ_C.xpt": f"{BASE_URL}/2003/DataFiles/PAQ_C.xpt",      # Physical activity
}

FILES_2005_2006 = {
    # Demographics
    "DEMO_D.xpt": f"{BASE_URL}/2005/DataFiles/DEMO_D.xpt",
    
    # IRI Components
    "CRP_D.xpt": f"{BASE_URL}/2005/DataFiles/CRP_D.xpt",      # CRP
    "BIOPRO_D.xpt": f"{BASE_URL}/2005/DataFiles/BIOPRO_D.xpt", # Biochemistry (Albumin)
    "DXX_D.xpt": f"{BASE_URL}/2005/DataFiles/DXX_D.xpt",      # DEXA Whole Body
    
    # Covariates
    "BMX_D.xpt": f"{BASE_URL}/2005/DataFiles/BMX_D.xpt",
    "BPX_D.xpt": f"{BASE_URL}/2005/DataFiles/BPX_D.xpt",
    "DIQ_D.xpt": f"{BASE_URL}/2005/DataFiles/DIQ_D.xpt",
    "GHB_D.xpt": f"{BASE_URL}/2005/DataFiles/GHB_D.xpt",
    "TCHOL_D.xpt": f"{BASE_URL}/2005/DataFiles/TCHOL_D.xpt",
    "TRIGLY_D.xpt": f"{BASE_URL}/2005/DataFiles/TRIGLY_D.xpt",
    "HDL_D.xpt": f"{BASE_URL}/2005/DataFiles/HDL_D.xpt",
    "SMQ_D.xpt": f"{BASE_URL}/2005/DataFiles/SMQ_D.xpt",
    "MCQ_D.xpt": f"{BASE_URL}/2005/DataFiles/MCQ_D.xpt",
    "HUQ_D.xpt": f"{BASE_URL}/2005/DataFiles/HUQ_D.xpt",
    "PFQ_D.xpt": f"{BASE_URL}/2005/DataFiles/PFQ_D.xpt",
    "PAQ_D.xpt": f"{BASE_URL}/2005/DataFiles/PAQ_D.xpt",      # Physical activity
}

# Mortality linkage files for 1999-2006 cycles
MORTALITY_FILES_VALIDATION = {
    "1999-2000": "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_1999_2000_MORT_2019_PUBLIC.dat",
    "2001-2002": "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2001_2002_MORT_2019_PUBLIC.dat",
    "2003-2004": "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2003_2004_MORT_2019_PUBLIC.dat",
    "2005-2006": "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2005_2006_MORT_2019_PUBLIC.dat",
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
    return success


def download_mortality_validation():
    """Download mortality linkage files for 1999-2006."""
    print(f"\n{'='*60}")
    print("MORTALITY LINKAGE FILES (Validation Cohort)")
    print('='*60)
    
    DATA_MORTALITY.mkdir(parents=True, exist_ok=True)
    
    for cycle, url in MORTALITY_FILES_VALIDATION.items():
        filename = url.split('/')[-1]
        download_file(url, DATA_MORTALITY / filename, min_size=100)


def main():
    print("\n" + "="*60)
    print("IRI VALIDATION STUDY - NHANES 1999-2006 DATA DOWNLOAD")
    print("Cycles: 1999-2000, 2001-2002, 2003-2004, 2005-2006")
    print("Components: CRP + Albumin + DEXA (ALM)")
    print("="*60)
    
    total_success = 0
    total_success += download_cycle("1999-2000", FILES_1999_2000)
    total_success += download_cycle("2001-2002", FILES_2001_2002)
    total_success += download_cycle("2003-2004", FILES_2003_2004)
    total_success += download_cycle("2005-2006", FILES_2005_2006)
    
    download_mortality_validation()
    
    print("\n" + "="*60)
    print(f"DOWNLOAD COMPLETE: {total_success} files downloaded")
    print("="*60)


if __name__ == "__main__":
    main()
