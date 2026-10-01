from observer.observer import Observer


class OutputHandler(Observer):
    """
    Output handler for OPP Hill Climbing model.
    Displays solution information in a similar format to OPPModelV3 OutputHandler.
    """

    def update(
        self,
        solution_info: dict,
    ):
        """
        Display solution information from Hill Climbing algorithm.

        Args:
            solution_info: Dictionary containing:
                - status: "optimal" or "infeasible"
                - objective_value: float
                - batch_times: dict {batch: execution_time}
                - batch_completions: dict {batch: completion_time}
                - tardiness: dict {order: tardiness}
                - earliness: dict {order: earliness}
                - routes: dict {batch: route_list}
        """
        print("\n" + "=" * 50)
        print(" OPTIMIZATION RESULTS (Hill Climbing)")
        print("=" * 50)

        status = solution_info.get("status", "unknown")

        if status == "optimal" or status == "feasible":
            objval = solution_info.get("objective_value", 0)
            print(f"Status: {status.upper()}")
            print(f"Objective Function Value: {objval:.4f}")
            print("-" * 50)

            # Batch execution times
            batch_times = solution_info.get("batch_times", {})
            if batch_times:
                print("Batch Execution Times (d_h):")
                for batch, t_exec_val in sorted(batch_times.items()):
                    print(f"  t_exec_{batch} (Batch {batch}): {t_exec_val:.4f}")
                print("-" * 50)

            # Batch completion times
            batch_completions = solution_info.get("batch_completions", {})
            if batch_completions:
                print("Batch Completion Times (c_pk):")
                for batch, completion_time in sorted(batch_completions.items()):
                    print(f"  v_{batch} (Batch {batch}): {completion_time:.4f}")
                print("-" * 50)

            # Tardiness and Earliness
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
                    print(f"  Order {order}: Tardiness (ta_{order})={ta:.4f}, Earliness (ea_{order})={ea:.4f}")
                    total_tardiness += ta
                    total_earliness += ea

                print(f"  Total Tardiness Sum: {total_tardiness:.4f}")
                print(f"  Total Earliness Sum: {total_earliness:.4f}")
                print("-" * 50)

            # Routes
            routes = solution_info.get("routes", {})
            if routes:
                print("Batch Routes:")
                for batch in sorted(routes.keys()):
                    route = routes[batch]
                    if route:
                        route_str = ' -> '.join(map(str, route))
                        print(f"  Batch {batch}: Route: {route_str}")
                    else:
                        print(f"  Batch {batch}: Not assigned or empty route")
                print("-" * 50)

        else:
            print(f"Hill Climbing finished with status: {status}")

        print("=" * 50 + "\n")
