import os
from dotenv import load_dotenv

# Cargamos el archivo .env una sola vez
load_dotenv()

# Variables para los tests (Skip/Run)
RUN_LARGE_TESTS = os.environ.get("RUN_LARGE_TESTS") == "1"

# Variables para los Executors
TEST_TIMEOUT_MINUTES = int(os.environ.get("TEST_TIMEOUT_MINUTES", "25"))
STRESS_TEST_TIMEOUT_MINUTES = int(
    os.environ.get("STRESS_TEST_TIMEOUT_MINUTES", str(TEST_TIMEOUT_MINUTES))
)

WRITE_RESULTS_CSV = os.environ.get("WRITE_RESULTS_CSV", "").strip().lower() in (
    "1",
    "true",
    "yes",
)
