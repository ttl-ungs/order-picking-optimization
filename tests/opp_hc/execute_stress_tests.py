import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.test_runner import TestRunner
from tests.test_config import STRESS_TEST_TIMEOUT_MINUTES, WRITE_RESULTS_CSV

if __name__ == "__main__":
    # 1. Por defecto busca todos los tests, pero si le pasamos un parámetro, busca ese específico
    test_pattern = "test_*.py"
    if len(sys.argv) > 1:
        numero_test = sys.argv[1]
        test_pattern = f"test_opp_hc_model_{numero_test}.py"
        print(f"Modo individual: Buscando el test {test_pattern}")

    runner = TestRunner(
        timeout_minutes=STRESS_TEST_TIMEOUT_MINUTES,
        write_csv=WRITE_RESULTS_CSV,
        model_name="opp_hc",
        test_type="stress",
    )

    suite = unittest.TestLoader().discover(
        start_dir=os.path.join(os.path.dirname(__file__), "tests", "stress"),
        pattern=test_pattern,
    )
    test_ids = TestRunner.collect_test_ids(suite)

    results = runner.run(test_ids)

    # Agregamos el pattern al resumen para saber qué consola corrió qué test
    runner.print_summary(results, f"STRESS TESTS ({test_pattern})")

    sys.exit(0 if runner.succeeded(results) else 1)
