import os
from dotenv import load_dotenv

# Settings of the test runner, read from the environment (.env is loaded once).
load_dotenv()

TEST_TIMEOUT_MINUTES = int(os.environ.get("TEST_TIMEOUT_MINUTES", "25"))
STRESS_TEST_TIMEOUT_MINUTES = int(
    os.environ.get("STRESS_TEST_TIMEOUT_MINUTES", str(TEST_TIMEOUT_MINUTES))
)

WRITE_RESULTS_CSV = os.environ.get("WRITE_RESULTS_CSV", "").strip().lower() in (
    "1",
    "true",
    "yes",
)

# Print the full result of every OPP-HC and OPP-ACO solve through the model's
# OutputHandler (the Observer). The exact models have no handler.
PRINT_RESULTS = os.environ.get("PRINT_RESULTS", "").strip().lower() in (
    "1",
    "true",
    "yes",
)

# Keep each solution (instance + solution, JSON) next to the CSV, so that
# verification/ can re-check it without running the suite again.
WRITE_SOLUTIONS = os.environ.get("WRITE_SOLUTIONS", "").strip().lower() in (
    "1",
    "true",
    "yes",
)
