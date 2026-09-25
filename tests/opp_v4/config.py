import os
import atexit
import shutil
import tempfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

_ORIG_ZPL = os.path.join(PROJECT_ROOT, "models", "opp_v4", "opp_model_v4.zpl")

_WORKSPACE = tempfile.mkdtemp(prefix="opp_v4_")
DAT_DIR = os.path.join(_WORKSPACE, "dat_files")
os.makedirs(DAT_DIR)

_zpl_dir = os.path.join(_WORKSPACE, "opp_v4")
os.makedirs(_zpl_dir)
shutil.copy2(_ORIG_ZPL, _zpl_dir)

ZPL_PATH = os.path.join(_zpl_dir, os.path.basename(_ORIG_ZPL))

atexit.register(shutil.rmtree, _WORKSPACE, True)
