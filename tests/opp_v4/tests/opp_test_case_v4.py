import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from tests.opp.tests.opp_test_case import OPPTestCase

class OPPTestCaseV4(OPPTestCase):
    def assert_workload_balance(self, var_values, P, B, max_difference=1):
        picker_workload = {p: 0 for p in P}
        for key, val in var_values.items():
            if key.lower().startswith("x_pb") and val > 0.5:
                for p in P:
                    if p in key: picker_workload[p] += 1
        workloads = list(picker_workload.values())
        if workloads:
            self.assertLessEqual(max(workloads) - min(workloads), max_difference, "Desbalanceo de carga")

    def assert_no_time_overlap(self, var_values, P, B):
        x_pb, v_pb, u_pb = {}, {}, {}
        for key, val in var_values.items():
            k = key.lower()
            p_match = [p for p in P if p in key]
            b_match = [b for b in B if b in key]
            if p_match and b_match:
                p, b = p_match[0], b_match[0]
                if k.startswith("x_pb"): x_pb[(p, b)] = val
                elif k.startswith("v_pb"): v_pb[(p, b)] = val
                elif k.startswith("u_pb"): u_pb[(p, b)] = val
        for p in P:
            tasks = sorted([(v_pb.get((p, b), 0)-u_pb.get((p, b), 0), v_pb.get((p, b), 0), b) for b in B if x_pb.get((p, b), 0) > 0.5])
            # if len(tasks) > 1:
            #     print(f"DEBUG picker {p} tasks (start, end, batch): {tasks}")
            #     batches_on_p = [b for b in B if x_pb.get((p, b), 0) > 0.5]
            #     for key, val in sorted(var_values.items()):
            #         kl = key.lower()
            #         if kl.startswith("z_bk") and any(b in key for b in batches_on_p):
            #             print(f"DEBUG {key} = {val}")
            #     for b in batches_on_p:
            #         print(f"DEBUG t_exec_b[{b}] = {var_values.get(f't_exec_b${b}', var_values.get(f't_exec_b[{b}]'))}")
            for i in range(len(tasks) - 1):
                self.assertGreaterEqual(tasks[i+1][0], tasks[i][1] - 1e-4, f"Solapamiento temporal en {p}")
