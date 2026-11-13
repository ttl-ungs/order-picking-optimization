import os
from dotenv import load_dotenv

# Cargamos el archivo .env una sola vez
load_dotenv()

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

# Keep each heuristic solution (instance + solution, JSON) next to the CSV so
# verification/ can re-check it against opp_mono without re-running the
# suite. Only models that attach a SolutionRecordDTO (opp_hc, opp_aco)
# produce one; for the rest this flag is a no-op.
WRITE_SOLUTIONS = os.environ.get("WRITE_SOLUTIONS", "").strip().lower() in (
    "1",
    "true",
    "yes",
)
