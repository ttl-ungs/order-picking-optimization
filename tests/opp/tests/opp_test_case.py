import time
import unittest


class OPPTestCase(unittest.TestCase):
    def setUp(self):
        self.start_time = time.time()

    def normalize_due_dates(self, orders, override=None, default=25.0):
        if override is None:
            return {n: float(default) for n in orders}
        if isinstance(override, dict):
            return override
        return {n: float(override) for n in orders}

    def apply_weight_overrides(
        self,
        w1,
        w2,
        gamma,
        delta,
        w1_override=None,
        w2_override=None,
        gamma_override=None,
        delta_override=None,
    ):
        if w1_override is not None:
            w1 = w1_override
        if w2_override is not None:
            w2 = w2_override
        if gamma_override is not None:
            gamma = gamma_override
        if delta_override is not None:
            delta = delta_override
        return w1, w2, gamma, delta

    def sum_vars_with_prefix(self, scip_model, prefix):
        total = 0.0
        for var in scip_model.getVars():
            name = var.name if hasattr(var, "name") else var.getName()
            if name.startswith(prefix):
                total += scip_model.getVal(var)
        return total
