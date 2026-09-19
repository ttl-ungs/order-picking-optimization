# Linear Picking Routing

## Table of Contents

- [Linear Picking Routing](#linear-picking-routing)
  - [Table of Contents](#table-of-contents)
  - [Project Purpose](#project-purpose)
  - [How the Project Was Implemented](#how-the-project-was-implemented)
    - [Current Repository Structure](#current-repository-structure)
    - [How the Observer Pattern Is Used](#how-the-observer-pattern-is-used)
    - [Optimization approach](#optimization-approach)
    - [Model parameters](#model-parameters)
  - [Requirements](#requirements)
    - [Installation](#installation)
  - [How to Run the Tests](#how-to-run-the-tests)
    - [Run the full test suite](#run-the-full-test-suite)
    - [Run a single test file](#run-a-single-test-file)
    - [What the tests cover](#what-the-tests-cover)
  - [Authors](#authors)

## Project Purpose

This repository implements a mathematical optimization model for the order picking problem in a warehouse setting.

The project focuses on the joint optimization of:

- order batching,
- batch assignment,
- mission sequencing, and
- picking routing.

In practice, the model decides how customer orders should be grouped and routed through a directed warehouse graph so that the total collection time and the penalties for earliness and tardiness are minimized.

The implementation follows the formulation described in the article mentioned in the source code comments: *A Model for the Joint Optimisation of Order Batching, Batch Assignment Sequencing and Picking Routing*.

## How the Project Was Implemented

The project is implemented in Python and uses `PySCIPOpt` as the optimization engine.

### Current Repository Structure

- `models/base/model.py` contains the abstract base model shared by all optimization approaches.
- `models/opp_v1/` contains the original OPP implementation and its related classes; later exact models are `opp_v2`..`opp_v5`, and the heuristics are `opp_hc_1`..`opp_hc_4` (Hill Climbing) and `opp_aco_1`..`opp_aco_4` (Ant Colony Optimization).
- `tests/<model>/functional/` and `tests/<model>/stress/` contain each model's tests (`test_case_NN.py`).
- `tests/shared_scenarios/` contains every reusable warehouse scenario used by the tests.
- `results/<model>/<functional|stress|stability>/` holds the CSV results produced by the test runs, read by `analysis/`.

Main components:

- `models/base/model.py` defines a base abstract model and supports an observer pattern.
- `models/opp_v1/opp_model_v1.py` contains the main OPP optimization model. It creates decision variables, defines the objective function, adds routing and timing constraints, solves the model, and returns the resulting status and output graph.
- `models/opp_v1/opp_location_graph.py` defines a lightweight directed graph structure used to represent warehouse locations, depot and final nodes, and distances between locations.
- `models/opp_v1/opp_output_builder.py` reconstructs the selected arcs from the solved model and converts them into an output graph.
- `utils/output_handler.py` acts as an observer that prints the optimization results in a readable way, including objective value, mission times, tardiness/earliness, and selected routes.
- `tests/shared_scenarios/` contains reusable warehouse layouts and parameter sets used by the tests.
- `tests/<model>/` contains the tests that validate different routing and assignment situations for each implementation.

### How the Observer Pattern Is Used

The project uses the Observer pattern to keep the optimization model independent from the way results are displayed.

The implementation works as follows:

1. `models/base/model.py` defines the abstract base class `Model`.
  This class stores a list of observers and provides `attach()`, `detach()`, and `notify()` methods.

2. `observer/observer.py` defines the abstract class `Observer`.
  Any observer must implement the `update()` method.

3. `utils/output_handler.py` implements `Observer`.
  Its `update()` method receives the solved SCIP model, the relevant sets, and the decision variables, and then prints a readable summary of the solution.

4. `models/opp_v1/opp_model_v1.py` inherits from `Model`.
  After the optimization finishes, it calls `notify(...)` with the solution data.

5. In the tests, an `OutputHandler` object is created and attached to the model before calling `solve()`.
  Because of that, every test can automatically display objective values, execution times, tardiness, earliness, and mission routes after the solver finishes.

This design has two main advantages:

- it keeps `OPPModel` focused on building and solving the mathematical model,
- it makes output handling extensible, because new observers can be added later without changing the optimization code.

### Optimization approach

The model is built as a mixed-integer optimization problem. Among other elements, it includes:

- binary routing variables to decide whether an arc is used in a mission,
- flow variables to control capacity and avoid invalid cycles,
- timing variables for mission execution and batch completion,
- tardiness and earliness variables for order service evaluation.

The objective combines:

- total collection/completion time, and
- weighted penalties for earliness and tardiness.

### Model parameters

Common parameters used by the OPP/OPP v2 models:

- `w1`: weight of completion time (sum of `v[p,b]`).
- `w2`: weight of penalty term (earliness + tardiness).
- `gamma`: weight of earliness sum.
- `delta`: weight of tardiness sum.
- `cap_n`: capacity required by each order `n`.
- `cap_vehicle`: vehicle capacity per batch.
- `a[n,i]`: 1 if order `n` must visit location `i`.
- `beta_time`: time per distance unit traveled.
- `beta_setup`: setup time per batch.
- `beta_picking`: time per unit picked (multiplies sum of `cap_n`).
- `due_date[n]`: due date for each order `n`.
- `M`: big-M constant used in timing constraints.
- `x[p,b]`: 1 if batch `b` is assigned to picker `p`.
- `y[n,b]`: 1 if order `n` is assigned to batch `b`.

Graph parameters are provided by the location graph:

- `d(i,j)`: distance between locations `i` and `j` (from the graph weights).

## Requirements

Minimum project requirements:

- Python 3
- `PySCIPOpt >= 5.6.0`

The repository currently declares the following dependency in `requirements.txt`:

```txt
pyscipopt>=5.6.0
```

### Installation

Create and activate a virtual environment if needed, then install dependencies:

```bash
pip install -r requirements.txt
```

## How to Run the Tests

The test suite is implemented with Python's built-in `unittest` framework.

### Run the full test suite

From the project root:

```bash
python -m unittest discover -s tests/opp_v1/functional -p "test_case_*.py"
```

To run any model's suite (functional or stress) with the timeout/CSV runner:

```bash
python -m tests.run_suite opp_hc_2 functional
python -m tests.run_suite opp_hc_3 stress --id 04
```

### Run a single test file

For example:

```bash
python tests/opp_v1/functional/test_case_08.py
```

### What the tests cover

The tests are based on predefined scenarios and check cases such as:

- basic two-order routing,
- routes across multiple aisles,
- alternative route selection,
- repeated picking locations,
- single-mission and multi-mission assignments.

Each test builds a warehouse graph, defines orders, missions, capacities, due dates, and assignment parameters, then solves the model and compares the generated output graph against an expected route.

## Authors

- Lucia Soria
- Ximena Ebertz
