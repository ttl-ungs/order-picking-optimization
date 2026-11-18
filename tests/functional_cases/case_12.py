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

    Whether the orders of a batch fit in the cart is not decided by the models,
    which take the batch composition as data: the vehicle capacity is validated
    before solving (models/utils/input_validation.py; see case 25d). The number
    is kept so that the cases stay numbered continuously.
    """


if __name__ == "__main__":
    unittest.main()
