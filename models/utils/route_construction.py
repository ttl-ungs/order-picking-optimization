"""Route-construction primitives shared by opp_hc and opp_aco: shortest
paths, the best-first fallback search, the pick-to-pick construction and the
local searches on a route.

Every function takes the OPPLocationGraph explicitly. A route is the list of
stops strictly between the depot and the final node (both implicit), and it
is a simple path -- no vertex repeated -- because the exact models forbid
revisits.
"""

import heapq
import itertools
import random
import time
from typing import Dict, List, Optional, Set, Tuple

# Backtracks allowed per stitch_route construction; each costs about one
# construction step (a Dijkstra and a Tarjan pass). Going from 0 to 30 raises
# the success rate of most batches for about twice the time; going on to 200
# helps few batches and costs several times more. With both directions tried
# (stitch_route_either_way), 30 gives every measured batch a good success rate
# in at least one of them.
STITCH_MAX_BACKTRACKS = 30


def dijkstra(location_graph, source, forbidden: Set = frozenset(), targets: Optional[Set] = None) -> Tuple[Dict, Dict]:
    """
    Shortest-path distances/predecessors from `source`, never stepping on
    `forbidden` (except `source` itself). If `targets` is given, stops as
    soon as every reachable target is settled: distances are final for
    the targets (and anything settled before them), not for the whole
    graph -- enough for callers that only need paths to those targets.
    """
    dist = {source: 0.0}
    prev: Dict = {}
    visited: Set = set()
    heap = [(0.0, source)]
    weighted_neighbors = location_graph.get_weighted_neighbors
    pending = set(targets) - {source} if targets is not None else None
    if pending is not None and not pending:
        return dist, prev

    while heap:
        d, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)
        if pending is not None:
            pending.discard(u)
            if not pending:
                break

        for v, w in weighted_neighbors(u):
            if v == u or (v in forbidden and v != source):
                continue
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd, v))

    return dist, prev


def reconstruct_path(prev: Dict, source, target) -> List:
    """Rebuild the path source -> target (inclusive) from a `prev` map."""
    if target == source:
        return [source]
    path = [target]
    node = target
    while node != source:
        node = prev[node]
        path.append(node)
    path.reverse()
    return path


def multi_source_distances(location_graph, sources: Set) -> Dict:
    """
    dist_to_nearest[v]: the shortest distance from v to its closest vertex of
    `sources`, in one Dijkstra pass seeded with all of them. The tie-break of
    _best_first_search.
    """
    dist: Dict = {source: 0.0 for source in sources}
    heap = [(0.0, source) for source in sources]
    heapq.heapify(heap)
    visited: Set = set()

    while heap:
        d, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)

        for v in location_graph.get_neighbors(u):
            nd = d + location_graph.get_distance(u, v)
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                heapq.heappush(heap, (nd, v))

    return dist


def best_first_route(location_graph, required_locations: Set, max_expansions: int) -> Optional[List]:
    """
    Last-resort exhaustive route search: returns a simple depot -> final
    route (picking stops only) covering every required location, or None
    if none exists within `max_expansions`. Tries the memoized search
    first, then an un-memoized one.
    """
    if not required_locations:
        return []

    depot = location_graph.get_depot()
    final = location_graph.get_final()
    initial_remaining = frozenset(required_locations)
    dist_to_nearest_required = multi_source_distances(location_graph, set(required_locations))

    route = _best_first_search(
        location_graph, depot, final, initial_remaining, dist_to_nearest_required, max_expansions, memoize=True
    )
    if route is None:
        route = _best_first_search(
            location_graph, depot, final, initial_remaining, dist_to_nearest_required, max_expansions, memoize=False
        )
    return route


def _best_first_search(
    location_graph, depot, final, initial_remaining: frozenset, dist_to_nearest_required: Dict,
    max_expansions: int, memoize: bool,
) -> Optional[List]:
    """
    Best-first search over states (current node, required locations left,
    path so far), ordered by (locations left, distance to the nearest
    required location, steps taken).

    A plain BFS explores states in the order they are reached, whatever
    their progress, and spends its budget on paths that still have most of
    the batch to visit. Ordering by locations left fixes most batches; the
    distance (multi_source_distances) breaks the ties between states with the
    same count, in favor of those that are actually close to finishing.
    `max_expansions` bounds the cases even this cannot rescue.
    """
    counter = itertools.count()
    start_h = dist_to_nearest_required.get(depot, 0.0) if initial_remaining else 0.0
    heap: List[Tuple[int, float, int, int, str, frozenset, List]] = [
        (len(initial_remaining), start_h, 0, next(counter), depot, initial_remaining, [depot])
    ]
    seen: Set = {(depot, initial_remaining)} if memoize else None
    expansions = 0

    while heap:
        expansions += 1
        if expansions > max_expansions:
            return None

        _, _, steps, _, node, remaining, path = heapq.heappop(heap)
        visited = set(path)

        for vertex in location_graph.get_neighbors(node):
            if vertex in visited:
                continue

            if vertex == final:
                if not remaining:
                    return path[1:]
                continue

            new_remaining = remaining - {vertex}
            if memoize:
                new_state = (vertex, new_remaining)
                if new_state in seen:
                    continue
                seen.add(new_state)
            heuristic = dist_to_nearest_required.get(vertex, 0.0) if new_remaining else 0.0
            heapq.heappush(
                heap,
                (len(new_remaining), heuristic, steps + 1, next(counter), vertex, new_remaining, path + [vertex]),
            )

    return None


def build_reversal_prefix_arrays(location_graph, route: List) -> Tuple[List[float], List[float], List[int]]:
    """
    fwd_prefix[k] / rev_prefix[k]: cumulative distance of route[0..k] walked
    forwards / in reverse. rev_broken_count[k]: how many reverse-direction
    edges among route[0..k] do not exist; a 2-opt reversal of route[i:j+1] is
    feasible only if the count is the same at both ends of the segment.
    Distances and edges are not assumed symmetric (see
    two_opt_tighten_route).
    """
    n = len(route)
    get_distance = location_graph.get_distance
    has_edge = location_graph.has_edge

    fwd_prefix = [0.0] * n
    rev_prefix = [0.0] * n
    rev_broken_count = [0] * n
    for t in range(n - 1):
        # The forward edge always exists. The reverse one may not: it is
        # counted in rev_broken_count and adds 0.0 to rev_prefix, since an inf
        # there would turn every later prefix difference into nan.
        fwd_prefix[t + 1] = fwd_prefix[t] + get_distance(route[t], route[t + 1])
        edge_ok = has_edge(route[t + 1], route[t])
        rev_prefix[t + 1] = rev_prefix[t] + (
            get_distance(route[t + 1], route[t]) if edge_ok else 0.0
        )
        rev_broken_count[t + 1] = rev_broken_count[t] + (0 if edge_ok else 1)

    return fwd_prefix, rev_prefix, rev_broken_count


def two_opt_tighten_route(location_graph, route: List) -> List:
    """
    Distance-minimizing 2-opt on `route` (topology only): applies the best
    improving reversal until none is left, in at most len(route) sweeps.

    A candidate is scored from its distance delta (the two edges at the ends
    of the reversed segment plus the segment summed in reverse) in O(1),
    after an O(n) prefix pass per sweep. The graph can be asymmetric (e.g.
    tests/shared_scenarios/functional/scenario_05.py, where L1->L2 and
    L2->L1 have different weights): reversing a segment reverses the
    direction of every edge in it, so the reverse-direction sums and missing
    edges are tracked separately from the forward ones.
    """
    if len(route) <= 1:
        return route

    depot = location_graph.get_depot()
    final = location_graph.get_final()
    get_distance = location_graph.get_distance
    has_edge = location_graph.has_edge

    current = route
    for _ in range(len(route)):
        n = len(current)
        fwd_prefix, rev_prefix, rev_broken_count = build_reversal_prefix_arrays(location_graph, current)

        best_i = best_j = None
        best_delta = -1e-9

        for i in range(n - 1):
            prev_node = current[i - 1] if i > 0 else depot
            removed_head = get_distance(prev_node, current[i])

            for j in range(i + 1, n):
                if rev_broken_count[j] - rev_broken_count[i] != 0:
                    continue  # a reverse-direction edge inside [i, j] is missing

                next_node = current[j + 1] if j + 1 < n else final

                if not has_edge(prev_node, current[j]) or not has_edge(current[i], next_node):
                    continue

                removed = removed_head + (fwd_prefix[j] - fwd_prefix[i]) + get_distance(current[j], next_node)
                added = get_distance(prev_node, current[j]) + (rev_prefix[j] - rev_prefix[i]) + get_distance(current[i], next_node)
                delta = added - removed

                if delta < best_delta:
                    best_delta = delta
                    best_i, best_j = i, j

        if best_i is None:
            break

        current = current[:best_i] + current[best_i:best_j + 1][::-1] + current[best_j + 1:]

    return current


def _path_length(location_graph, path: List) -> float:
    return sum(location_graph.get_distance(path[k], path[k + 1]) for k in range(len(path) - 1))


def reroute_segments(location_graph, route: List, required_locations: Set) -> List:
    """
    Segment re-routing: for every pair of consecutive required locations a,
    b on the route (depot and final node included), replace what is walked
    between them with the shortest a -> b path that avoids every other vertex
    of the route, when it is strictly shorter. Sweeps until nothing improves.

    It complements 2-opt, which only reverses stretches and cannot swap a
    detour for a shorter corridor: here the pick order stays and only the
    corridors change. It is the "shortest paths between consecutive picks" of
    the Steiner-TSP view (Chen et al. 2013, p.79; Coruzzolo et al. 2023,
    pp.6-9), with the avoidance of the rest of the route added for the
    no-revisit rule. The route stays simple and never gets longer.
    """
    if not route:
        return route

    depot = location_graph.get_depot()
    final = location_graph.get_final()
    full = [depot] + list(route) + [final]

    for _ in range(len(required_locations) + 2):
        improved = False
        anchors = [0] + [k for k in range(1, len(full) - 1) if full[k] in required_locations] + [len(full) - 1]
        for a_idx, b_idx in zip(anchors, anchors[1:]):
            if b_idx - a_idx <= 1:
                continue
            a, b = full[a_idx], full[b_idx]
            current_length = _path_length(location_graph, full[a_idx:b_idx + 1])
            forbidden = (set(full[:a_idx]) | set(full[b_idx + 1:])) - {a, b}
            if b != final:
                forbidden.add(final)
            dist, prev = dijkstra(location_graph, a, forbidden, targets={b})
            if dist.get(b, float("inf")) < current_length - 1e-9:
                corridor = reconstruct_path(prev, a, b)
                full = full[:a_idx] + corridor + full[b_idx + 1:]
                improved = True
                break  # indices shifted; recompute anchors
        if not improved:
            break

    return full[1:-1]


def improve_route(location_graph, route: List, required_locations: Set) -> List:
    """
    Alternate two_opt_tighten_route and reroute_segments until neither
    shortens the route (each can open moves for the other).
    """
    best = list(route)
    best_length = _path_length(location_graph, [location_graph.get_depot()] + best + [location_graph.get_final()])
    for _ in range(5):
        candidate = two_opt_tighten_route(location_graph, best)
        candidate = reroute_segments(location_graph, candidate, required_locations)
        length = _path_length(location_graph, [location_graph.get_depot()] + candidate + [location_graph.get_final()])
        if length >= best_length - 1e-9:
            break
        best, best_length = candidate, length
    return best


def _corridor(location_graph, source, target, forbidden: Set) -> Optional[List]:
    """Shortest source -> target path (inclusive) avoiding `forbidden`, or None."""
    dist, prev = dijkstra(location_graph, source, forbidden, targets={target})
    if target not in dist:
        return None
    return reconstruct_path(prev, source, target)


def relocate_picks(location_graph, route: List, required_locations: Set, deadline: Optional[float] = None) -> List:
    """
    Or-opt relocation on the pick order (Or 1976): take one required location
    p out of the sequence, joining its neighbors by the shortest corridor
    that avoids the rest of the route, and reinsert it between another pair
    of consecutive picks. First-improvement, until no relocation shortens
    the route.

    Neither 2-opt (which reverses a stretch) nor reroute_segments (which
    keeps the pick order) can make this move. With O(k^2) candidates of
    three Dijkstras each for k picks it is expensive: meant for elite routes
    only. The route stays simple and never gets longer.
    """
    if not route:
        return route

    depot = location_graph.get_depot()
    final = location_graph.get_final()
    full = [depot] + list(route) + [final]
    best_length = _path_length(location_graph, full)

    for _ in range(len(required_locations) * 2 + 2):
        improved = False
        anchors = [0] + [k for k in range(1, len(full) - 1) if full[k] in required_locations] + [len(full) - 1]

        for i in range(1, len(anchors) - 1):
            if _past(deadline):
                return full[1:-1]
            a_idx, p_idx, b_idx = anchors[i - 1], anchors[i], anchors[i + 1]
            a, p, b = full[a_idx], full[p_idx], full[b_idx]

            # 1) Remove p: join a -> b avoiding the rest of the route.
            outside = set(full[:a_idx]) | set(full[b_idx + 1:])
            forbidden = outside - {a, b}
            if b != final:
                forbidden.add(final)
            join = _corridor(location_graph, a, b, forbidden)
            if join is None:
                continue
            reduced = full[:a_idx] + join + full[b_idx + 1:]
            if p in join:
                # The shortcut still passes through p: keep it if shorter.
                length = _path_length(location_graph, reduced)
                if length < best_length - 1e-9:
                    full, best_length, improved = reduced, length, True
                    break
                continue

            # 2) Reinsert p between each other pair of consecutive picks.
            reduced_anchors = [0] + [
                k for k in range(1, len(reduced) - 1) if reduced[k] in required_locations
            ] + [len(reduced) - 1]
            for c_idx, d_idx in zip(reduced_anchors, reduced_anchors[1:]):
                c, d = reduced[c_idx], reduced[d_idx]
                if (c, d) == (a, b):
                    continue  # where p came from
                keep = set(reduced[:c_idx]) | set(reduced[d_idx + 1:])
                forbidden_cp = (keep | {d, final}) - {c}
                leg1 = _corridor(location_graph, c, p, forbidden_cp)
                if leg1 is None:
                    continue
                forbidden_pd = (keep | set(leg1)) - {p, d}
                if d != final:
                    forbidden_pd.add(final)
                leg2 = _corridor(location_graph, p, d, forbidden_pd)
                if leg2 is None:
                    continue
                candidate = reduced[:c_idx] + leg1 + leg2[1:] + reduced[d_idx + 1:]
                if len(candidate) != len(set(candidate)):
                    continue
                length = _path_length(location_graph, candidate)
                if length < best_length - 1e-9:
                    full, best_length, improved = candidate, length, True
                    break
            if improved:
                break

        if not improved:
            break

    return full[1:-1]


def _past(deadline: Optional[float]) -> bool:
    return deadline is not None and time.time() > deadline


def _realize_pick_order(location_graph, prefix: List, picks: List, suffix: List, required_locations: Set) -> Optional[List]:
    """
    Connect prefix[-1] -> picks[0] -> ... -> picks[-1] -> suffix[0] with
    successive shortest corridors, each avoiding every vertex already used
    (and `final` unless it is the target). A pick an earlier corridor walked
    through is skipped. Returns the full vertex list, or None if some
    corridor does not exist.
    """
    final = location_graph.get_final()
    used = set(prefix) | set(suffix)
    path = list(prefix)
    for target in list(picks) + [suffix[0]]:
        if target in path:
            continue
        forbidden = (used | set(path)) - {path[-1], target}
        if target != final:
            forbidden.add(final)
        leg = _corridor(location_graph, path[-1], target, forbidden)
        if leg is None:
            return None
        path.extend(leg[1:])
    return path + list(suffix[1:])


def reverse_pick_segments(
    location_graph, route: List, required_locations: Set, max_segment: int = 8, deadline: Optional[float] = None,
) -> List:
    """
    2-opt on the pick order (Croes 1958; Lin 1965): reverse the order of the
    picks p_i..p_j (at most `max_segment` of them) and redraw the corridors
    between them with _realize_pick_order. First-improvement, until no
    reversal shortens the route.

    Reversing raw vertex stretches (two_opt_tighten_route) almost never
    closes on a grid, where the two new junctions would have to be adjacent
    cells; reversing picks and redrawing corridors does. Expensive, like
    relocate_picks: meant for elite routes only. The route stays simple and
    never gets longer.
    """
    if not route:
        return route

    depot = location_graph.get_depot()
    final = location_graph.get_final()
    full = [depot] + list(route) + [final]
    best_length = _path_length(location_graph, full)

    for _ in range(len(required_locations) * 2 + 2):
        improved = False
        anchors = [0] + [k for k in range(1, len(full) - 1) if full[k] in required_locations] + [len(full) - 1]
        for i in range(1, len(anchors) - 2):
            if _past(deadline):
                return full[1:-1]
            for j in range(i + 1, min(i + max_segment, len(anchors) - 1)):
                prefix = full[:anchors[i - 1] + 1]
                suffix = full[anchors[j + 1]:]
                picks = [full[anchors[k]] for k in range(j, i - 1, -1)]
                candidate = _realize_pick_order(location_graph, prefix, picks, suffix, required_locations)
                if candidate is None or len(candidate) != len(set(candidate)):
                    continue
                length = _path_length(location_graph, candidate)
                if length < best_length - 1e-9:
                    full, best_length, improved = candidate, length, True
                    break
            if improved:
                break
        if not improved:
            break

    return full[1:-1]


def polish_route(location_graph, route: List, required_locations: Set, deadline: Optional[float] = None) -> List:
    """
    Expensive improvement for elite routes: alternate reverse_pick_segments,
    relocate_picks and improve_route until none shortens the route.

    After `deadline` (an absolute time.time(), optional) it stops and returns
    the best route so far, never worse than the input. On the 100x100 grid
    one call takes tens of seconds.
    """
    best = list(route)
    best_length = _path_length(location_graph, [location_graph.get_depot()] + best + [location_graph.get_final()])
    for _ in range(5):
        if _past(deadline):
            break
        candidate = reverse_pick_segments(location_graph, best, required_locations, deadline=deadline)
        candidate = relocate_picks(location_graph, candidate, required_locations, deadline=deadline)
        candidate = improve_route(location_graph, candidate, required_locations)
        length = _path_length(location_graph, [location_graph.get_depot()] + candidate + [location_graph.get_final()])
        if length >= best_length - 1e-9:
            break
        best, best_length = candidate, length
    return best


def undirected_adjacency(location_graph) -> Dict:
    """Underlying undirected adjacency (out- and in-neighbors) of every vertex, as sets."""
    adjacency: Dict = {v: set() for v in location_graph.get_vertices()}
    for u in location_graph.get_vertices():
        for v in location_graph.get_neighbors(u):
            if v != u:
                adjacency[u].add(v)
                adjacency.setdefault(v, set()).add(u)
    return adjacency


def roulette(weights: Dict, rng=random):
    """Random-proportional choice over `weights` (uniform if they're all 0)."""
    total = sum(weights.values())
    if total <= 0:
        return rng.choice(list(weights))
    rand_val = rng.uniform(0, total)
    cumulative = 0.0
    chosen = None
    for key, weight in weights.items():
        chosen = key
        cumulative += weight
        if rand_val <= cumulative:
            break
    return chosen


def keeps_route_completable(undirected: Dict, pick, visited: Set, remaining: Set, final) -> bool:
    """
    Necessary condition for a simple route to still exist after walking to
    `pick`: the rest of the route is a simple path pick -> final that avoids
    `visited`, so every location still required must lie on some simple
    pick -> final path of the graph without `visited`.

    A vertex v lies on a simple s-t path iff, after adding a virtual edge
    (s, t), v is in the biconnected component of that edge: one Tarjan pass
    (simple_path_component). Besides a graph cut in two, this rejects the
    "pocket" a connectivity check misses: a required location at the end of
    a dead-end corridor is connected but can only be entered and left
    through the same vertex.

    It is not sufficient: two required locations can each be on some simple
    path but not on the same one. On a directed graph it runs on the
    underlying undirected graph (`undirected`), where it is still necessary,
    since a directed simple path is also an undirected one.
    """
    if final in visited:
        return False
    left = remaining - visited
    blocked = visited - {pick}
    component = simple_path_component(undirected, pick, final, blocked)
    return bool(component) and left <= component


def simple_path_component(undirected: Dict, s, t, blocked: Set) -> Set:
    """
    Vertices of the biconnected component of edge (s, t) -- virtual if the
    graph does not have it -- in the undirected graph without `blocked`:
    exactly the vertices on some simple s -> t path. Empty if t cannot be
    reached from s. Iterative Tarjan (Hopcroft & Tarjan 1973) over an edge
    stack, stopping at the first component that contains both s and t (there
    is only one, since two components share at most one vertex).
    """
    # The virtual edge is spliced into the neighbor lists of s and t only;
    # other vertices iterate their cached adjacency and filter `blocked`
    # inline. This runs about 20 times per ant route.
    if t in undirected[s]:
        extra = {}
    else:
        extra = {s: (t,), t: (s,)}

    def neighbors_of(u):
        if u in extra:
            return itertools.chain(undirected[u], extra[u])
        return iter(undirected[u])

    disc = {s: 0}
    low = {s: 0}
    timer = 0
    edge_stack: List[Tuple[str, str]] = []
    stack = [(s, None, neighbors_of(s))]

    while stack:
        u, parent, neighbors = stack[-1]
        descended = False
        disc_u = disc[u]
        for v in neighbors:
            if v == parent or v in blocked:
                continue
            disc_v = disc.get(v)
            if disc_v is None:
                timer += 1
                disc[v] = low[v] = timer
                edge_stack.append((u, v))
                stack.append((v, u, neighbors_of(v)))
                descended = True
                break
            if disc_v < disc_u:
                if disc_v < low[u]:
                    low[u] = disc_v
                edge_stack.append((u, v))
        if descended:
            continue

        stack.pop()
        if parent is None:
            continue
        if low[u] < low[parent]:
            low[parent] = low[u]
        if low[u] >= disc[parent]:
            component: Set[str] = set()
            while edge_stack:
                edge = edge_stack.pop()
                component.update(edge)
                if edge == (parent, u):
                    break
            if s in component and t in component:
                return component

    return set()



def stitch_route(
    location_graph, required_locations: Set, weight, undirected: Dict, rng=random,
    max_backtracks: int = STITCH_MAX_BACKTRACKS,
) -> Optional[List]:
    """
    Randomized pick-to-pick construction of a route (the full depot ... final
    vertex list, a simple path), or None if it cannot finish within
    `max_backtracks`. From the current pick, every required location r still
    reachable without a revisit gets weight(current, r, d), with d the
    shortest non-revisiting distance, and one is drawn by roulette among
    those that pass keeps_route_completable (checked lazily: draw, check,
    drop and redraw). The shortest path to it is appended; required locations
    on the way count as picked.

    The pick-to-pick view and the random-proportional rule are those of Chen
    et al. (2013), p.79 and Eq. 2. opp_aco passes weight = tau^alpha *
    (1/d)^beta (see its _build_batch_route); opp_hc passes (1/d)^beta, as a
    randomized multi-start construction.

    When no candidate passes the check, the last pick and its corridor are
    undone and another candidate is drawn at that step: a randomized
    depth-first search pruned by keeps_route_completable and bounded by
    `max_backtracks`. The check is necessary but not sufficient, and without
    backtracking some batches almost never finish. A candidate tried at a
    step stays removed, so no branch is repeated.
    """
    depot = location_graph.get_depot()
    final = location_graph.get_final()

    route = [depot]
    visited = {depot}
    remaining = set(required_locations)

    def open_step(current):
        dist, prev = dijkstra(location_graph, current, forbidden=(visited | {final}) - {current}, targets=remaining)
        weights = {}
        # sorted(): the roulette walks `weights` in insertion order, and a set
        # of str iterates in an order that depends on PYTHONHASHSEED. With a
        # fixed order the result depends on Seed alone.
        for r in sorted(remaining):
            if r in dist:
                weights[r] = weight(current, r, dist[r] if dist[r] > 0 else 0.01)
        return {"current": current, "prev": prev, "weights": weights}

    committed = []  # stack of (step, corridor, picks it covered)
    step = open_step(depot) if remaining else None
    backtracks = 0

    while remaining:
        weights = step["weights"]
        advanced = False
        while weights:
            r = roulette(weights, rng)
            del weights[r]  # tried: not drawn again at this step
            corridor = reconstruct_path(step["prev"], step["current"], r)[1:]
            if keeps_route_completable(undirected, r, visited.union(corridor), remaining, final):
                picked = remaining.intersection(corridor)
                committed.append((step, corridor, picked))
                route.extend(corridor)
                visited.update(corridor)
                remaining -= picked
                advanced = True
                break
        if advanced:
            if remaining:
                step = open_step(route[-1])
            continue

        if not committed or backtracks >= max_backtracks:
            return None
        backtracks += 1
        step, corridor, picked = committed.pop()
        del route[len(route) - len(corridor):]
        visited.difference_update(corridor)
        remaining |= picked

    dist, prev = dijkstra(location_graph, route[-1], forbidden=visited - {route[-1]}, targets={final})
    if final not in dist:
        return None
    route.extend(reconstruct_path(prev, route[-1], final)[1:])
    return route


def insertion_route(location_graph, required_locations: Set, rng=None) -> Optional[List]:
    """
    Route from a pick order built by farthest insertion (Rosenkrantz, Stearns
    & Lewis 1977, "An analysis of several heuristics for the traveling
    salesman problem"): start from depot -> final and repeatedly insert the
    pick farthest from the current sequence where it adds the least distance.
    Distances between picks are plain shortest paths; the order is then
    realized with no-revisit corridors by _realize_pick_order. With `rng`
    the insertion order is random instead, for multi-start diversity.
    Returns the full depot ... final route, or None if the corridors cannot
    be realized.

    stitch_route's greedy choice leaves far picks for last, and a route can
    cross a grid column early and cut off the picks left on it, many steps
    before the dead end, where backtracking does not reach. Insertion places
    every pick in a globally coherent order from the start.
    """
    depot = location_graph.get_depot()
    final = location_graph.get_final()
    picks = list(required_locations)
    if not picks:
        return [depot, final]

    nodes = [depot] + picks
    targets = set(picks) | {final}
    dist = {}
    for u in nodes:
        d, _ = dijkstra(location_graph, u, frozenset(), targets=targets)
        for v in targets:
            dist[(u, v)] = d.get(v, float("inf"))

    sequence = [depot, final]
    left = set(picks)

    def gap(a, b):
        return dist.get((a, b), float("inf"))

    while left:
        if rng is None:
            chosen = max(
                sorted(left),
                key=lambda p: min(gap(s, p) for s in sequence if s != final),
            )
        else:
            chosen = rng.choice(sorted(left))
        best_pos, best_delta = None, float("inf")
        for k in range(len(sequence) - 1):
            a, b = sequence[k], sequence[k + 1]
            delta = gap(a, chosen) + gap(chosen, b) - gap(a, b)
            if delta < best_delta:
                best_pos, best_delta = k + 1, delta
        if best_pos is None:
            return None  # `chosen` cannot be connected to the sequence: no route
        sequence.insert(best_pos, chosen)
        left.discard(chosen)

    return _realize_pick_order(location_graph, [depot], sequence[1:-1], [final], required_locations)


def reversed_graph(location_graph):
    """
    The same warehouse with every edge reversed and depot and final node
    swapped: a depot ... final route of it, read backwards, is a route of
    the original graph with the same length. It lets any construction run
    from the final node backwards (see stitch_route_either_way).
    """
    from models.base.opp_location_graph import OPPLocationGraph

    depot = location_graph.get_depot()
    final = location_graph.get_final()
    reverse = OPPLocationGraph(depot_node=final, final_node=depot)
    for v in location_graph.get_vertices():
        if v not in (depot, final):
            reverse.add_vertex(v, "picking")
    for u in location_graph.get_vertices():
        for v in location_graph.get_neighbors(u):
            reverse.add_edge(v, u, location_graph.get_distance(u, v))
    return reverse


def stitch_route_either_way(
    location_graph, reverse_graph, required_locations: Set, weight, undirected: Dict,
    backwards: bool, rng=random, max_backtracks: int = STITCH_MAX_BACKTRACKS,
) -> Optional[List]:
    """
    stitch_route from the depot forwards or, with backwards=True, from the
    final node backwards over `reverse_graph`; the result is always in the
    depot ... final direction. `weight(current, r, d)` receives the pair in
    the direction the construction moves (current -> r on the reversed graph
    is r -> current on the original).

    stitch_route leaves the picks far from where it starts for last, and
    some batches have a cluster of those that an early move cuts off:
    building from the other end, next to them, finishes most of the time.
    Other batches show the opposite pattern, so callers alternate. The
    closest precedent is Lesch et al. (2023), Applied Intelligence
    53:18605-18629, who also evaluate every pick route reversed (p.18617);
    they reverse a finished route, while this builds it from the other end.
    """
    if not backwards:
        return stitch_route(location_graph, required_locations, weight, undirected, rng, max_backtracks)
    route = stitch_route(reverse_graph, required_locations, weight, undirected, rng, max_backtracks)
    return route[::-1] if route is not None else None
