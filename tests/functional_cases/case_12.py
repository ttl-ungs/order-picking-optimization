import unittest
import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
)

from tests.infra.cases.exact_model_case import ExactModelTestCase


class Case12(ExactModelTestCase):
    """
    Case 12 has no active tests.

    It checked that the orders of a batch fit in the cart (12 orders, 6 missions,
    3 pickers, two missions per picker and two orders per mission), but the
    models take the batch composition as data and no longer evaluate the cart
    capacity, so the check no longer applies. The vehicle capacity is validated
    before solving instead (models/utils/input_validation.py; see case 25d).
    """


if __name__ == "__main__":
    unittest.main()
