"""Route-construction primitives shared by opp_hc and opp_aco.

Moved verbatim (behavior unchanged) out of models/opp_hc/opp_hc.py so
that opp_aco's pick-to-pick route construction (see its
_build_batch_route) can reuse the exact same shortest-path, best-first
fallback and 2-opt code that opp_hc already validated, instead of a
second copy drifting apart.

Every function takes the OPPLocationGraph explicitly. Routes follow
opp_hc's convention: a list of the picking stops strictly between depot
and final (depot/final themselves are implicit), and a route is a SIMPLE
path -- no vertex repeated -- because the exact models forbid revisits.
"""

import heapq
import itertools
import random
import time
from typing import Dict, List, Optional, Set, Tuple

# Backtracks allowed per stitch_route construction (see its docstring):
# each costs about one construction step (a Dijkstra + a Tarjan pass).
# Measured 2026-09-27 on realistic_crew_scenario(13) and (16), 20
# constructions per batch per setting: 0 -> 30 backtracks raised most
# batches' success rate noticeably (e.g. 13x13 B1 forwards 55% -> 80%)
# for ~2x the time per construction; 30 -> 200 helped a few batches
# further (13x13 B5 forwards 10% -> 50%) but cost another ~3x and left
# others flat or lower (16x16 B6 forwards 50% -> 20%, within noise).
# With both directions tried (stitch_route_either_way), 30 already gives
# every measured batch >= 45% success in at least one direction, so the
# extra time is better spent on the other direction than on deeper
# backtracking.
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
    Single Dijkstra pass, seeded at distance 0 from EVERY vertex in
    `sources` at once, giving dist_to_nearest[v] = shortest distance
    from v to its closest source, for every v reachable from any of
    them. O((V+E) log V) total (same cost as one ordinary Dijkstra),
    used by _best_first_search as a distance-aware tie-break -- see its
    docstring for why "how many locations are still required" alone
    isn't always enough to steer the search away from a required set
    that's numerically small but geometrically spread out.
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
    Best-first search over states (current_node, remaining_required,
    path_so_far), ordered by (locations still required, distance from
    `node` to the closest ORIGINAL required location, steps taken so
    far) instead of plain FIFO BFS.

    2026-09-26 audit finding: a WAREHOUSE-GRID batch needing ~20 required
    locations on a 49-node grid genuinely exists a valid route (the exact
    solver finds one), but plain BFS -- which explores states in the
    order they were first reached, oblivious to how close any of them
    is to actually finishing the route -- needed ~3.7M expansions and
    ~3GB to find it, because it burns almost all of that budget on
    partial paths that still have most of the batch left to visit,
    before ever getting to the few that are nearly done. Ordering the
    frontier by "fewest locations left" first fixed most batches
    outright, but a "few locations left, all of them far away" state
    can still rank ahead of a "few locations left, all of them nearby"
    one on that key alone -- dist_to_nearest_required (from
    multi_source_distances) breaks that tie by real graph distance,
    not path length, so the search drains the states that are actually
    close to finishing, not just those reached in fewer hops.
    `max_expansions` remains the hard safety valve below for whatever
    pathological cases even this can't rescue.
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
    fwd_prefix[k]/rev_prefix[k]: cumulative distance of route[0..k]
    traversed forward / in reverse. rev_broken_count[k]: how many of
    the reverse-direction edges among route[0..k] don't exist -- a
    2-opt reversal of route[i:j+1] is only feasible if this is the
    same at both ends of the segment (i.e. zero reverse edges are
    missing inside it). Shared by two_opt_tighten_route and opp_hc's
    _generate_route_neighbor -- see two_opt_tighten_route's docstring for
    why get_distance/has_edge are NOT assumed symmetric here.
    """
    n = len(route)
    get_distance = location_graph.get_distance
    has_edge = location_graph.has_edge

    fwd_prefix = [0.0] * n
    rev_prefix = [0.0] * n
    rev_broken_count = [0] * n
    for t in range(n - 1):
        # route[t] -> route[t + 1] is one of the route's own edges,
        # which is always feasible for a route this is called on
        # (topology-valid, or the current sweep state in
        # two_opt_tighten_route), so get_distance here is always
        # finite. The reverse direction may not exist at all
        # (get_distance returns float("inf")): rev_broken_count
        # tracks that separately (used to reject any candidate whose
        # reversed segment would need this edge) so a 0.0 placeholder
        # is used for rev_prefix's running sum instead -- letting an
        # "inf" into the cumulative sum would poison every later
        # prefix value (inf - inf = nan), including for ranges that
        # never touch this broken edge.
        fwd_prefix[t + 1] = fwd_prefix[t] + get_distance(route[t], route[t + 1])
        edge_ok = has_edge(route[t + 1], route[t])
        rev_prefix[t + 1] = rev_prefix[t] + (
            get_distance(route[t + 1], route[t]) if edge_ok else 0.0
        )
        rev_broken_count[t + 1] = rev_broken_count[t] + (0 if edge_ok else 1)

    return fwd_prefix, rev_prefix, rev_broken_count


def two_opt_tighten_route(location_graph, route: List) -> List:
    """
    Standalone distance-minimizing 2-opt local search over `route`
    (topology only -- no picker, no cold chain): repeatedly applies the
    best improving reversal until none is left. Bounded to len(route)
    sweeps as a safety valve -- in practice 2-opt converges in far fewer.

    Each candidate reversal is scored via a distance DELTA (the 2 edges
    leaving/entering the reversed segment, plus the segment's own
    distance re-summed in reverse) instead of rebuilding the whole
    candidate route and re-validating/re-summing it from scratch --
    O(1) per candidate (after an O(n) prefix pass per sweep) instead of
    O(n). This graph can be directed/asymmetric (see e.g.
    tests/shared_scenarios/functional/scenario_05.py, where L1->L2
    and L2->L1 have different weights), so get_distance/has_edge are
    NOT assumed symmetric: reversing route[i:j+1] also reverses the
    direction every edge inside it is traversed in, so the reverse-
    direction prefix sums/broken-edge counts below are tracked
    separately from the forward ones, not derived by just negating or
    reusing them.
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
    Segment re-routing local search: for every pair of consecutive
    required locations (depot and final included as the route's ends) a
    -> ... -> b, replace the vertices walked between them with the
    shortest a -> b path that avoids every OTHER vertex of the route,
    whenever that is strictly shorter. Sweeps until no segment improves
    (bounded by the number of segments, as a safety valve).

    Complements two_opt_tighten_route: 2-opt only reverses stretches of the
    route, so it can't replace a detour through non-required vertices with
    a different, shorter corridor; this move keeps the pick order and only
    changes the corridors between picks. It is the order-picking "route
    improvement by shortest paths between consecutive picks" idea behind
    the Steiner-TSP view of Chen et al. (2013) p.79 and Coruzzolo et al.
    (2023) pp.6-9 (distances between picks = shortest paths), applied
    under the no-revisit constraint -- the avoidance of the rest of the
    route is our addition for that constraint.

    Keeps the route simple (the new corridor avoids every other route
    vertex) and never increases its length. Takes/returns picking stops
    only (depot/final implicit), like the rest of this module.
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
    shortens the route (each can open moves for the other). Bounded to a
    few rounds as a safety valve; in practice 1-2 suffice.
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
    Or-opt style relocation over the pick ORDER (Or 1976; the classic
    TSP "move one node elsewhere in the tour" neighborhood): take one
    required location p out of the sequence -- joining its two neighbor
    picks a, b by the shortest corridor avoiding the rest of the route --
    and reinsert it between another pair of consecutive picks c, d
    (corridors c -> p -> d, again avoiding the rest of the route).
    First-improvement, repeated until no relocation shortens the route
    (bounded as a safety valve).

    2-opt and reroute_segments can't express this move: 2-opt only
    reverses a contiguous stretch, reroute_segments keeps the pick order.
    Measured 2026-09-26 on realistic_crew_scenario(7): after both, one
    batch still stayed at 76 route-time units vs 74 for the Split's exact Stage 1.

    O(k^2) candidate moves of 3 Dijkstras each for k picks, so it's much
    more expensive than improve_route -- meant for elite routes only (see
    opp_aco's _recombine_shortest_routes), not every ant. Keeps the
    route simple and never lengthens it. Picking stops only in/out.
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
                # The shortcut itself still passes through p: plain win if shorter.
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
                    continue  # that's where p came from
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
    Connect prefix[-1] -> picks[0] -> ... -> picks[-1] -> suffix[0] by
    successive shortest corridors, each avoiding every vertex already
    used (prefix, suffix, earlier corridors) and `final` unless it is the
    target. A pick already walked through by an earlier corridor is
    skipped (it's visited). Returns the full vertex list, or None if some
    corridor doesn't exist.
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
    2-opt over the PICK ORDER (Croes 1958 / Lin 1965's 2-opt, applied to
    the sequence of required locations rather than to raw vertices):
    reverse the order of picks p_i..p_j (at most `max_segment` of them)
    and re-realize the corridors between them with shortest paths that
    avoid the rest of the route (_realize_pick_order). First-improvement,
    repeated until no reversal shortens the route (bounded).

    two_opt_tighten_route reverses raw vertex stretches, which on a grid
    almost never closes (the two new junctions must be adjacent cells);
    reversing picks and re-drawing corridors does. Measured 2026-09-26 on
    realistic_crew_scenario(7): the only non-optimal elite route left
    (76 vs the Split's 74) needed exactly this move -- the middle picks visited
    in reverse, through different corridors.

    O(k * max_segment) candidates, each re-realizing up to max_segment + 1
    corridors: meant for elite routes only, like relocate_picks. Keeps the
    route simple, never lengthens it. Picking stops only in/out.
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
    Expensive route improvement for ELITE routes: alternate pick-level
    2-opt (reverse_pick_segments), or-opt relocation (relocate_picks) and
    the cheap improve_route until none shortens the route (bounded).

    `deadline` (absolute time.time(), optional): stop improving once it
    passes and return the best route so far -- never worse than the input.
    Needed because one call scales with graph size: measured 2026-09-27 on
    the 100x100 grid (10,000 nodes), ~34 s per call, 30 calls =
    1007 s of a 1141 s opp_aco run whose Max_time was 1 s.
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
    Necessary condition for a simple route to still exist after
    walking to `pick` (with `visited` now including that path): the
    rest of the route is a simple path pick -> final that avoids
    `visited`, so every still-required location must lie on SOME
    simple pick -> final path in the graph minus `visited`.

    Exact test for "v lies on some simple s-t path" (standard graph
    theory result, e.g. via block-cut trees): add a virtual edge
    (s, t); v lies on a simple s-t path iff v belongs to the
    biconnected component containing that edge. One Tarjan pass
    (simple_path_component). This rejects both a graph cut in two and
    the subtler "pocket" case a plain connectivity BFS misses -- a
    required location at the end of a one-wide dead-end corridor is
    connected, but can only be entered and left through the same
    vertex (measured 2026-09-26 on realistic_crew_scenario(7): with
    connectivity alone, ~85% of constructions still fell back to the
    exhaustive search, every time because of such a pocket).

    Our own addition (not from Chen et al., whose routes may revisit
    aisles, so they never hit this). Still not sufficient -- two
    required locations can each be on some simple path but not on the
    same one. On a directed graph it runs on the underlying undirected
    graph (`undirected`, from undirected_adjacency), where it is still a valid
    necessary condition -- a directed simple path is also an undirected
    one -- just a weaker filter. (A first version followed
    get_neighbors, i.e. out-edges only, and wrongly rejected every pick
    on directed test graphs such as test_case_pre_check_uses_tightened_
    route's -- caught by the functional suite, 2026-09-26.)
    """
    if final in visited:
        return False
    left = remaining - visited
    blocked = visited - {pick}
    component = simple_path_component(undirected, pick, final, blocked)
    return bool(component) and left <= component


def simple_path_component(undirected: Dict, s, t, blocked: Set) -> Set:
    """
    Vertices of the biconnected component containing edge (s, t) --
    added as a virtual edge if the graph doesn't have it -- in the
    undirected graph minus `blocked`, i.e. exactly the vertices lying on some
    simple s -> t path (see keeps_route_completable). Empty set if t
    is unreachable from s. Iterative Tarjan (Hopcroft & Tarjan 1973)
    over an edge stack, stopping at the first component that contains
    both s and t (two biconnected components share at most one vertex,
    so there is only one such component).
    """
    # Virtual s-t edge (if not already an edge): spliced into s's and
    # t's neighbor lists only; every other vertex iterates its cached
    # adjacency set directly, filtering `blocked` inline, instead of
    # materializing a filtered list per visit (this runs ~20x per ant
    # route -- 2026-09-26 profiling put it at ~40% of ACO runtime).
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
    Randomized pick-to-pick route construction (full depot ... final
    vertex list, a simple path), or None if it can't finish within
    `max_backtracks`. From the current pick, every still-required
    location r reachable without revisiting gets weight(current, r, d) --
    d the shortest non-revisiting distance -- and one is drawn by roulette
    among those passing keeps_route_completable (lazy rejection: draw,
    check, drop and redraw on failure -- the same distribution restricted
    to the picks that pass, at one Tarjan pass per draw instead of one
    per candidate). The shortest non-revisiting path to it is appended;
    required locations passed on the way count as picked.

    The pick-to-pick (Steiner-TSP) view and the random-proportional rule
    are Chen et al. (2013), A-TOP, p.79 and Eq. 2 -- opp_aco passes
    weight = tau^alpha * (1/d)^beta; see its _build_batch_route for the
    full rationale and the deviations (no revisits, the completability
    check). opp_hc uses it with weight = (1/d)^beta as a randomized
    multi-start construction.

    Backtracking (our own addition, not from the papers): when no
    candidate passes the check, undo the last pick (its whole corridor)
    and draw another candidate at that step instead of giving up --
    a randomized depth-first search with keeps_route_completable as the
    pruning rule, bounded by `max_backtracks`. keeps_route_completable is
    necessary but not sufficient, so without this some batches almost
    never finished: measured 2026-09-27 on realistic_crew_scenario(13),
    batch B6 succeeded in 0/100 constructions (B5 in 15/100), which made
    opp_hc report "infeasible" and left opp_aco with only the long
    best-first fallback route -- too long for T_cold = 280 in
    realistic_crew_cold_chain, so no ant ever came out compliant.
    Candidates already tried at a step stay removed after backtracking
    to it, so the search never repeats a branch.
    """
    depot = location_graph.get_depot()
    final = location_graph.get_final()

    route = [depot]
    visited = {depot}
    remaining = set(required_locations)

    def open_step(current):
        dist, prev = dijkstra(location_graph, current, forbidden=(visited | {final}) - {current}, targets=remaining)
        weights = {}
        # sorted(): roulette walks `weights` in insertion order, and a set of
        # str iterates in an order that changes with PYTHONHASHSEED, so the
        # same Seed used to pick different locations in different processes
        # (measured 2026-10-14: up to 0.5% objective spread on stress 03, and
        # stress 11 infeasible in 2 of 7 processes). Same probabilities, fixed
        # order -- results now depend on Seed alone.
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
            del weights[r]  # tried: never redrawn at this step, even after a backtrack
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
    Pick order by farthest insertion (Rosenkrantz, Stearns & Lewis 1977,
    "An analysis of several heuristics for the traveling salesman
    problem"): start from depot -> final, repeatedly take the pick
    farthest from the current sequence and insert it where it adds the
    least distance. Distances between picks are plain shortest paths
    (the Steiner-TSP distances of Chen et al. 2013, p.79 / Coruzzolo et
    al. 2023, pp.6-9), ignoring the no-revisit rule; the order is then
    realized with no-revisit corridors by _realize_pick_order. With `rng`,
    the insertion order is randomized instead (random insertion), for
    multi-start diversity. Returns the full depot ... final route or None
    if the corridors can't be realized.

    Why (our own use of it, measured 2026-09-27): stitch_route's
    distance-greedy choice leaves far picks for last, and on
    realistic_crew_scenario(13)'s B6 the route crossed the grid's right
    column early and cut off the three picks left on it -- 0/100
    constructions finished, even with 200 backtracks, because the fatal
    move is many steps before the dead end. Insertion places every pick
    in a globally coherent order from the start.
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
            return None  # `chosen` unreachable from/to the sequence: no route at all
        sequence.insert(best_pos, chosen)
        left.discard(chosen)

    return _realize_pick_order(location_graph, [depot], sequence[1:-1], [final], required_locations)


def reversed_graph(location_graph):
    """
    The same warehouse with every edge reversed and depot/final swapped:
    a depot ... final route of it, read backwards, is a depot ... final
    route of the original graph with the same length (edge weights are
    carried over per direction). Lets any construction here run "from
    the final node backwards" unchanged -- see stitch_route_either_way.
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
    stitch_route from the depot forwards, or (backwards=True) from the
    final node backwards over `reverse_graph` (see reversed_graph),
    returned in the original depot ... final direction either way.
    `weight(current, r, d)` always receives the pair in the direction the
    construction moves (current -> r in the reversed graph means r ->
    current in the original).

    Our own addition. Closest precedent: Lesch et al. (2023), Applied
    Intelligence 53:18605-18629, also evaluate every ACO pick route
    reversed ("the reverse pick route is calculated by reversing the
    market sequence", p.18617) and run their S-shape baseline on reversed
    routes too (p.18620) -- but they reverse a finished route, while this
    BUILDS the route from the other end, which changes which picks the
    greedy choice leaves for last. Why (measured 2026-09-27):
    stitch_route's distance-greedy choice leaves the picks far from where
    it STARTS for last, and some batches have a cluster of those that an
    early move cuts off -- realistic_crew_scenario(13)'s B6 has three
    picks on the grid's right column near the final node, and forward
    construction finished 0-5% of the time even with backtracking;
    backwards (starting next to them) it finished 75%. Other batches
    show the opposite pattern (16x16's B4: forwards ~0-15%, backwards
    100%), so callers alternate between the two directions.
    """
    if not backwards:
        return stitch_route(location_graph, required_locations, weight, undirected, rng, max_backtracks)
    route = stitch_route(reverse_graph, required_locations, weight, undirected, rng, max_backtracks)
    return route[::-1] if route is not None else None
