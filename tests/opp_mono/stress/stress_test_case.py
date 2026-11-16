from tests.opp_mono.opp_mono_test_case import OPPTestCaseMono


class OPPMonoStressTestCase(OPPTestCaseMono):
    def assert_stress_pipeline(self, scenario):
        values, route_times, status, _ = self.run_pipeline(scenario)
        self.assertIn(status, ("optimal", "feasible"))
        self.assert_routes_cover_requirements(values, scenario)
        self.assertEqual(set(self.assignments(values, scenario["P"], scenario["B"])), scenario["B"])
        self.assert_no_overlap(values, scenario, route_times)
