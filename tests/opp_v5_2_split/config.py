import os
import atexit
import shutil
import tempfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

_ORIG_STAGE1 = os.path.join(PROJECT_ROOT, "models", "opp_v5_2_split", "opp_model_v5_2_split_stage1_routing.zpl")
_ORIG_STAGE2 = os.path.join(PROJECT_ROOT, "models", "opp_v5_2_split", "opp_model_v5_2_split_stage2_scheduling.zpl")

_WORKSPACE = tempfile.mkdtemp(prefix="opp_v5_2_split_")
DAT_DIR = os.path.join(_WORKSPACE, "dat_files")
os.makedirs(DAT_DIR)

_zpl_dir = os.path.join(_WORKSPACE, "opp_v5_2_split")
os.makedirs(_zpl_dir)
shutil.copy2(_ORIG_STAGE1, _zpl_dir)
shutil.copy2(_ORIG_STAGE2, _zpl_dir)

STAGE1_ZPL_PATH = os.path.join(_zpl_dir, os.path.basename(_ORIG_STAGE1))
STAGE2_ZPL_PATH = os.path.join(_zpl_dir, os.path.basename(_ORIG_STAGE2))

atexit.register(shutil.rmtree, _WORKSPACE, True)
