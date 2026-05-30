"""
Execute all OPP Hill Climbing V3 tests.
"""

import sys
import os
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from tests.opp_hill_climbing.tests.normal.test_opp_hc_v3_model_1 import (
    TestOPPHillClimbingV3Model1,
)
from tests.opp_hill_climbing.tests.normal.test_opp_hc_v3_model_2 import (
    TestOPPHillClimbingV3Model2,
)
from tests.opp_hill_climbing.tests.normal.test_opp_hc_v3_model_3 import (
    TestOPPHillClimbingV3Model3,
)
from tests.opp_hill_climbing.tests.normal.test_opp_hc_v3_model_4 import (
    TestOPPHillClimbingV3Model4,
)
from tests.opp_hill_climbing.tests.normal.test_opp_hc_v3_model_5 import (
    TestOPPHillClimbingV3Model5,
)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestOPPHillClimbingV3Model1))
    suite.addTests(loader.loadTestsFromTestCase(TestOPPHillClimbingV3Model2))
    suite.addTests(loader.loadTestsFromTestCase(TestOPPHillClimbingV3Model3))
    suite.addTests(loader.loadTestsFromTestCase(TestOPPHillClimbingV3Model4))
    suite.addTests(loader.loadTestsFromTestCase(TestOPPHillClimbingV3Model5))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
