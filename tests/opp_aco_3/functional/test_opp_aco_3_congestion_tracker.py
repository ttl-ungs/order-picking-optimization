import unittest

import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
)

from models.utils.congestion import CongestionTracker


class TestCongestionTracker(unittest.TestCase):
    """
    Deterministic unit tests for the shared CongestionTracker (models/utils/congestion.py),
    isolated from ACO's randomness, so the congestion mechanism itself is
    verified independently of the metaheuristic's search behaviour.
    """

    def test_no_conflict_when_only_one_owner_uses_a_resource(self):
        tracker = CongestionTracker()
        start, wait = tracker.reserve(("N", "L1"), requested_start=5.0, duration=2.0, owner="P1")
        self.assertEqual(start, 5.0)
        self.assertEqual(wait, 0.0)

    def test_second_owner_waits_for_first_owner_to_free_the_resource(self):
        tracker = CongestionTracker()
        tracker.reserve(("N", "L1"), requested_start=0.0, duration=5.0, owner="P1")  # busy [0,5)

        start, wait = tracker.reserve(("N", "L1"), requested_start=2.0, duration=1.0, owner="P2")
        self.assertEqual(start, 5.0)
        self.assertEqual(wait, 3.0)

    def test_same_owner_does_not_conflict_with_its_own_reservations(self):
        tracker = CongestionTracker()
        tracker.reserve(("N", "L1"), requested_start=0.0, duration=5.0, owner="P1")

        start, wait = tracker.reserve(("N", "L1"), requested_start=2.0, duration=1.0, owner="P1")
        self.assertEqual(start, 2.0)
        self.assertEqual(wait, 0.0)

    def test_reservation_cascades_through_multiple_conflicting_intervals(self):
        tracker = CongestionTracker()
        tracker.reserve(("N", "L1"), requested_start=0.0, duration=5.0, owner="P1")  # [0,5)
        tracker.reserve(("N", "L1"), requested_start=5.0, duration=5.0, owner="P2")  # [5,10)

        # A third picker arriving at t=1 must wait past BOTH existing intervals.
        start, wait = tracker.reserve(("N", "L1"), requested_start=1.0, duration=1.0, owner="P3")
        self.assertEqual(start, 10.0)
        self.assertEqual(wait, 9.0)

    def test_peek_wait_does_not_mutate_state(self):
        tracker = CongestionTracker()
        tracker.reserve(("N", "L1"), requested_start=0.0, duration=5.0, owner="P1")

        wait_before = tracker.peek_wait(("N", "L1"), requested_start=1.0, duration=1.0, owner="P2")
        wait_after = tracker.peek_wait(("N", "L1"), requested_start=1.0, duration=1.0, owner="P2")
        self.assertEqual(wait_before, wait_after)
        self.assertEqual(wait_before, 4.0)

    def test_edge_and_node_keys_do_not_collide(self):
        node_key = CongestionTracker.node_key("L1")
        edge_key = CongestionTracker.edge_key("L1", "L2")
        self.assertNotEqual(node_key, edge_key)

    def test_edge_key_is_direction_agnostic(self):
        self.assertEqual(
            CongestionTracker.edge_key("L1", "L2"),
            CongestionTracker.edge_key("L2", "L1"),
        )

    def test_dwell_uses_min_dwell_floor(self):
        tracker = CongestionTracker(min_dwell=2.0)
        self.assertEqual(tracker.dwell(service_time=0.0), 2.0)
        self.assertEqual(tracker.dwell(service_time=5.0), 5.0)


if __name__ == "__main__":
    unittest.main()
