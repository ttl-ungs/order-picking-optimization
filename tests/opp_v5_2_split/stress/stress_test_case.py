from tests.opp_v5_2_split.opp_test_case_v5_2_split import OPPTestCaseSplit


class OPPSplitStressTestCase(OPPTestCaseSplit):
    def assert_stress_pipeline(self, scenario):
        stage1_values, route_times, stage2_status, stage2_values = self.run_pipeline(scenario)
        self.assertIn(stage2_status, ("optimal", "feasible"))
        self.assert_routes_cover_requirements(stage1_values, scenario)
        self.assertEqual(set(self.assignments(stage2_values, scenario["P"], scenario["B"])), scenario["B"])
        self.assert_no_overlap(stage2_values, scenario, route_times)
