import os


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DAT_DIR = os.path.join(PROJECT_ROOT, "models", "dat_files")
STAGE1_ZPL_PATH = os.path.join(PROJECT_ROOT, "models", "opp_v5", "stage1_routing.zpl")
STAGE2_ZPL_PATH = os.path.join(PROJECT_ROOT, "models", "opp_v5", "stage2_scheduling.zpl")
