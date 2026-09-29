from observer.observer import Observer


class OutputHandler(Observer):
    """
    Output handler for opp_aco_4 (picker-speed and cold-chain-aware Ant
    Colony Optimization, no congestion). Same format as opp_aco_2's
    OutputHandler, plus the picker speeds and cold-chain limit used for
    this run.
    """

    def update(
        self,
        solution_info: dict,
    ):
        """
        Display solution information from the Ant Colony Optimization algorithm.

        Args:
            solution_info: Dictionary containing:
                - status: "optimal" or "infeasible"
                - objective_value: float
                - batch_times: dict {batch: execution_time}
                - batch_completions: dict {batch: completion_time}
                - picker_assignments: dict {batch: picker}
                - tardiness: dict {order: tardiness}
                - earliness: dict {order: earliness}
                - routes: dict {batch: route_list}
                - V_p: dict {picker: speed}
                - T_frio_max: float
        """
        print("\n" + "=" * 50)
        print(" OPTIMIZATION RESULTS (ACO v4 - picker speed & cold chain)")
        print("=" * 50)

        status = solution_info.get("status", "unknown")

        if status == "optimal" or status == "feasible":
            objval = solution_info.get("objective_value", 0)
            print(f"Status: {status.upper()}")
            print(f"Objective Function Value: {objval:.4f}")
            print("-" * 50)

            V_p = solution_info.get("V_p", {})
            T_frio_max = solution_info.get("T_frio_max")
            if V_p:
                print("Picker Speeds (V_p):")
                for picker, speed in sorted(V_p.items()):
                    print(f"  {picker}: {speed}")
            if T_frio_max is not None:
                print(f"Cold Chain Limit (T_frio_max): {T_frio_max}")
            if V_p or T_frio_max is not None:
                print("-" * 50)

            picker_assignments = solution_info.get("picker_assignments", {})
            if picker_assignments:
                print("Picker Assignments (x_pb):")
                for picker in sorted(set(picker_assignments.values())):
                    batches = sorted(b for b, p in picker_assignments.items() if p == picker)
                    print(f"  {picker}: {', '.join(batches) if batches else '(idle)'}")
                print("-" * 50)

            batch_times = solution_info.get("batch_times", {})
            if batch_times:
                print("Batch Execution Times (t_exec_pb):")
                for batch, t_exec_val in sorted(batch_times.items()):
                    print(f"  t_exec_{batch} (Batch {batch}): {t_exec_val:.4f}")
                print("-" * 50)

            batch_completions = solution_info.get("batch_completions", {})
            if batch_completions:
                print("Batch Completion Times (c_b):")
                for batch, completion_time in sorted(batch_completions.items()):
                    print(f"  v_{batch} (Batch {batch}): {completion_time:.4f}")
                print("-" * 50)

            tardiness = solution_info.get("tardiness", {})
            earliness = solution_info.get("earliness", {})
            if tardiness or earliness:
                print("Tardiness and Earliness per Order (ta_n, ea_n):")
                total_tardiness = 0
                total_earliness = 0
                all_orders = set(tardiness.keys()) | set(earliness.keys())
                for order in sorted(all_orders):
                    ta = tardiness.get(order, 0)
                    ea = earliness.get(order, 0)
                    print(
                        f"  Order {order}: Tardiness (ta_{order})={ta:.4f}, Earliness (ea_{order})={ea:.4f}"
                    )
                    total_tardiness += ta
                    total_earliness += ea

                print(f"  Total Tardiness Sum: {total_tardiness:.4f}")
                print(f"  Total Earliness Sum: {total_earliness:.4f}")
                print("-" * 50)

            routes = solution_info.get("routes", {})
            if routes:
                print("Batch Routes:")
                for batch in sorted(routes.keys()):
                    route = routes[batch]
                    if route:
                        route_str = " -> ".join(map(str, route))
                        print(f"  Batch {batch}: Route: {route_str}")
                    else:
                        print(f"  Batch {batch}: Not assigned or empty route")
                print("-" * 50)

        else:
            print(f"Ant Colony Optimization finished with status: {status}")

        print("=" * 50 + "\n")
