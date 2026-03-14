import pyscipopt

from models.opp.opp_location_graph import OPPLocationGraph
from observer.observer import Observer


class OutputHandler(Observer):

    def update(
        self,
        model: pyscipopt.Model,
        N: set,
        V: set,
        H: set,
        P: set,
        K: set,
        ta: dict,
        ea: dict,
        t_exec: dict,
        v: dict,
        z: dict,
        depot_vertex,
        final_vertex,
    ):
        print("\n" + "=" * 50)
        print(" OPTIMIZATION RESULTS")
        print("=" * 50)

        if model.getStatus() == "optimal":
            objval = model.getObjVal()
            print(f"Optimal Objective Function Value: {objval:.4f}")
            print("-" * 50)

            print("Mission Execution Times (t_exec_h):")
            for h in H:
                val_t_exec = model.getVal(t_exec[h])
                print(f"  t_exec_{h} (Mission {h}): {val_t_exec:.4f}")
            print("-" * 50)

            print("Batch Completion Times (v_pk):")
            for p in P:
                for k in K:
                    val_v = model.getVal(v[p, k])
                    print(f"  v_{p}_{k} (Picker {p}, Position {k}): {val_v:.4f}")
            print("-" * 50)

            print("Tardiness and Earliness per Order (ta_n, ea_n):")
            total_tardiness = 0
            total_earliness = 0
            for n in N:
                val_ta = model.getVal(ta[n])
                val_ea = model.getVal(ea[n])
                print(
                    f"  Order {n}: Tardiness (ta_{n})={val_ta:.4f}, Earliness (ea_{n})={val_ea:.4f}"
                )
                total_tardiness += val_ta
                total_earliness += val_ea

            print(f"  Total Tardiness Sum: {total_tardiness:.4f}")
            print(f"  Total Earliness Sum: {total_earliness:.4f}")
            print("-" * 50)

            print("Mission Routes (z_ijh Arcs > 0.5):")
            for h in H:
                mission_route_arcs = []
                for i in V:
                    for j in V:
                        try:
                            val_z = model.getVal(z[i, j, h])
                            if val_z > 0.5:
                                mission_route_arcs.append((i, j))
                        except KeyError:
                            continue

                if mission_route_arcs:
                    ordered_route = self._reconstruct_route(
                        mission_route_arcs,
                        depot_vertex,
                        final_vertex,
                    )

                    print(
                        f"  Mission {h}: Route: {' -> '.join(map(str, ordered_route))}"
                    )
                else:
                    print(f"  Mission {h}: Not assigned or trivial/not found route")
            print("-" * 50)

        else:
            print(f"SCIP finished with status: {model.getStatus()}")

        print("=" * 50 + "\n")

    def _reconstruct_route(self, active_arcs, depot, final):

        if not active_arcs:
            return [depot, final] if depot != final else [depot]

        arc_dict = {origin: destination for origin, destination in active_arcs}

        route = [depot]
        current = depot

        while current != final and current in arc_dict:
            next_node = arc_dict[current]
            route.append(next_node)
            current = next_node

        return route
