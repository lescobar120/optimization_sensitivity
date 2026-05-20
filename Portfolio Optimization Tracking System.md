# Portfolio Optimization Tracking System

This system provides a comprehensive workflow for managing, executing, and tracking portfolio optimization tasks. It allows you to:

1. Define optimization parameters in configuration files
2. Generate optimization tasks from these parameters
3. Execute optimizations through an API
4. Track and index all optimization runs
5. Store and retrieve optimization results
6. Generate reports and analyze results

## Project Structure

```
project/
├── config/
│   ├── optimization_parameters.yaml    # Configuration for optimization parameters
│   ├── constraint_mappings.yaml        # Mappings for constraints to templates
│   ├── goal_mappings.yaml              # Mappings for goals to templates
│   └── templates/                      # Template JSON files
│       ├── constraints/
│       └── goals/
├── data/
│   ├── optimization_index.parquet      # Master index of all optimization runs
│   └── optimization_results/           # Directory containing results
│       └── [optimization_id]/          # Subdirectory for each optimization
│           ├── api_response.json       # Raw API response
│           ├── summary.parquet         # Summary dataframe
│           ├── goals.parquet           # Goals results dataframe
│           ├── constraints.parquet     # Constraints results dataframe
│           └── trades.parquet          # Trades dataframe
├── tasks/                              # JSON task files
├── optimization_tracker.py             # Main class for tracking optimizations
├── optimization_workflow.py            # Workflow functions
├── config_loader.py                    # Load and process configuration
├── task_builder.py                     # Build optimization tasks
├── template_utils.py                   # Utility functions for templates
└── cli.py                              # Command-line interface
```

## Configuration

The system uses three main configuration files:

1. `optimization_parameters.yaml`: Defines the parameters for optimization runs
2. `constraint_mappings.yaml`: Maps constraint names to template files
3. `goal_mappings.yaml`: Maps goal names to template files

### Optimization Parameters

The `optimization_parameters.yaml` file defines:

- Portfolios to optimize
- Benchmarks to use
- Portfolio-benchmark pairs
- Risk model options
- Optimization goals
- Constraint parameters with ranges or discrete values
- As-of dates for the optimizations

Example:

```yaml
portfolios:
  - EQUITY8_US
  - EQUITY8_MID_CAP_GROWTH

benchmarks:
  - RAY
  - RDG

portfolio_benchmark_pairs:
  - portfolio: EQUITY8_US
    benchmark: RAY
  - portfolio: EQUITY8_MID_CAP_GROWTH
    benchmark: RDG

risk_options:
  - model: 
    - US_EQUITY
  - scaling: 
    - YEAR
  - horizon: 
    - ANNUAL

goals:
  - minimize_active_total_risk
  - maximize_custom_expected_return

constraints:
  turnover:
    min: 0.2
    max: 0.5
    step: 0.1
  
  maximum_positions:
    values: [200, 300]
  
  # More constraints...
```

## Usage

### Command Line Interface

The system provides a command-line interface with several commands:

#### Register Optimization Tasks

```bash
python cli.py register
```

Options:
- `--config`: Path to optimization parameters YAML (default: `config/optimization_parameters.yaml`)
- `--goal-mappings`: Path to goal mappings YAML (default: `config/goal_mappings.yaml`)
- `--constraint-mappings`: Path to constraint mappings YAML (default: `config/constraint_mappings.yaml`)
- `--tasks-dir`: Directory to save task JSON files (default: `tasks`)

#### Run Optimizations

```bash
python cli.py run
```

Options:
- `--max-runs`: Maximum number of optimizations to run (default: 5)
- `--delay`: Delay between optimization runs in seconds (default: 2)
- `--filter-portfolio`: Only run optimizations for specified portfolio
- `--filter-benchmark`: Only run optimizations for specified benchmark

#### Generate Report

```bash
python cli.py report
```

Options:
- `--output`: Output file for the report (default: `optimization_report.html`)
- `--filter-portfolio`: Filter report by portfolio
- `--filter-benchmark`: Filter report by benchmark
- `--filter-status`: Filter report by optimization status (`success`, `failed`, `running`, `not_run`)

#### List Optimizations

```bash
python cli.py list
```

Options:
- `--status`: Filter by status (`all`, `pending`, `success`, `failed`, `running`) (default: `all`)
- `--portfolio`: Filter by portfolio
- `--benchmark`: Filter by benchmark
- `--output`: Output format (`console`, `csv`, `json`) (default: `console`)
- `--output-file`: Output file path (for csv/json output)

#### View Optimization Results

```bash
python cli.py view <optimization_id>
```

Options:
- `--type`: Type of results to view (`summary`, `goals`, `constraints`, `trades`, `all`) (default: `all`)

### Using the Tracker Programmatically

```python
from optimization_tracker import OptimizationTracker
from optimization_workflow import register_optimization_tasks, run_pending_optimizations

# Create the tracker
tracker = OptimizationTracker()

# Register optimization tasks
registered_ids = register_optimization_tasks(tracker=tracker)

# Run pending optimizations
executed_ids = run_pending_optimizations(tracker=tracker, max_runs=3)

# Get results for a specific optimization
optimization_id = executed_ids[0]
results = tracker.load_optimization_results(optimization_id)
summary_df = results['summary']
goals_df = results['goals']
constraints_df = results['constraints']
trades_df = results['trades']

# Filter optimizations
filtered_df = tracker.filter_optimizations(
    portfolio='EQUITY8_US',
    benchmark='RAY',
    status='success'
)
```

## Extending the System

### Adding New Constraints

1. Add the constraint to `optimization_parameters.yaml`
2. Add a mapping for the constraint in `constraint_mappings.yaml`
3. Create a template JSON file in `config/templates/constraints/`

### Adding New Goals

1. Add the goal to `optimization_parameters.yaml`
2. Add a mapping for the goal in `goal_mappings.yaml`
3. Create a template JSON file in `config/templates/goals/`

### Customizing Result Processing

Modify the following methods in `OptimizationTracker` to customize how results are processed:

- `_extract_summary_df()`
- `_extract_goals_df()`
- `_extract_constraints_df()`
- `_extract_trades_df()`

## Notes for Implementation

- The `get_optimization_response()` function in `optimization_workflow.py` is a placeholder and should be replaced with actual API calls to your optimization service.
- The data extraction methods in `OptimizationTracker` are dummy implementations and should be updated to match the actual structure of your API responses.
- For large result sets, consider implementing pagination or filtering when loading trades data.