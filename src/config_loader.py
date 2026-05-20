"""
Package to manage config loading and generating optimization task combinations 
for use in iteratively running optimizations with each task combination

NEED TO ADD SUPPORT OF GENERATING COMBINATIONS OF A MULTI-GOAL TASK WITH VARYING TRADE-OFFS
"""

import yaml
from pathlib import Path
import itertools
import numpy as np
from typing import Dict, List, Any



def load_optimization_config(config_path: str) -> Dict[str, Any]:
    """
    Load the optimization configuration from a YAML file.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        Dictionary containing the configuration parameters
    """
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    return config



def generate_constraint_combinations(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate all combinations of constraint values from the configuration.
    
    Args:
        config: Loaded configuration dictionary
        
    Returns:
        List of dictionaries, each representing a specific constraint combination
    """
    constraint_combinations = []
    
    # Extract constraints with discrete values
    discrete_constraints = {}
    range_constraints = {}
    
    for constraint_name, constraint_config in config['constraints'].items():
        if 'values' in constraint_config:
            # This is a discrete constraint with explicit values
            discrete_constraints[constraint_name] = constraint_config['values']
        elif all(k in constraint_config for k in ['min', 'max', 'step']):
            # This is a range constraint
            values = np.arange(
                constraint_config['min'],
                constraint_config['max'] + constraint_config['step'],
                constraint_config['step']
            )
            # Convert to list and round to avoid floating point issues
            values = [round(float(v), 6) for v in values]
            range_constraints[constraint_name] = values
    
    # Combine all constraint names and their possible values
    all_constraints = {}
    all_constraints.update(discrete_constraints)
    all_constraints.update(range_constraints)

    all_constraint_names = list(all_constraints.keys())
    all_constraint_values = [all_constraints[name] for name in all_constraint_names]
    
    # Generate all combinations of constraint values
    for constraint_values in itertools.product(*all_constraint_values):
        constraint_dict = {
            name: value for name, value in zip(all_constraint_names, constraint_values)
        }
        constraint_combinations.append(constraint_dict)
    
    return constraint_combinations


def generate_risk_model_combinations(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate all combinations of risk model options from the configuration.
    
    Args:
        config: Loaded configuration dictionary
        
    Returns:
        List of dictionaries, each representing a specific risk model configuration
    """
    # Extract risk option values
    risk_model_values = []
    risk_scaling_values = []
    risk_horizon_values = []
    
    for option in config['risk_options']:
        if 'model' in option:
            risk_model_values = option['model']
        elif 'scaling' in option:
            risk_scaling_values = option['scaling']
        elif 'horizon' in option:
            risk_horizon_values = option['horizon']
    
    # Generate all combinations of risk options
    risk_combinations = []
    for model, scaling, horizon in itertools.product(
        risk_model_values, risk_scaling_values, risk_horizon_values
    ):
        risk_config = {
            'model': model,
            'scaling': scaling,
            'horizon': horizon
        }
        risk_combinations.append(risk_config)
    
    return risk_combinations


def generate_all_parameter_combinations(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate all parameter combinations for optimization runs
    
    Args:
        config: Loaded configuration dictionary
        
    Returns:
        List of parameter sets, each representing a specific optimization run
    """

    # Generate all constraint combinations
    constraint_combinations = generate_constraint_combinations(config)
    
    # Generate all risk model combinations
    risk_model_combinations = generate_risk_model_combinations(config)
    
    # Create lists for each parameter type
    # portfolios = config['portfolios']
    # benchmarks = config['benchmarks']

    #portfolio_benchmark_pairs = config['portfolio_benchmark_pairs'] # Comment out if using √ portoflio-benchmark combinations
    
    # Use portfolio-benchmark-universe mappings
    portfolio_benchmark_universe_mappings = config.get('portfolio_benchmark_universe_mappings', [])

    as_of_dates = config['as_of_dates']
    save_to = config['saveTo']
    lookthrough = config['enableLookThrough']
    infused_cash = config['infusedCashAmount']

    # Get goals (if available in the config)
    goals = config.get('goals', [])
    # Include goals in the optimization ID
    goals_str = "_".join(goals) if goals else "no_goals"
    
    all_combinations = []
    
    # UNCOMMENT FOR MULTIPLE PORTFOLIO-BENCHMARK COMBINATIONS
    # for portfolio, benchmark, risk_config, as_of_date, constraints in itertools.product(
    #     portfolios, benchmarks, risk_model_combinations, as_of_dates, constraint_combinations
    # ):
        
    # Use itertools.product but with pre-defined portfolio-benchmark pairs
    # for pair, risk_config, as_of_date, constraints in itertools.product(
    #     portfolio_benchmark_pairs, risk_model_combinations, as_of_dates, constraint_combinations
    # ):
    
    for mapping, risk_config, as_of_date, constraints in itertools.product(
        portfolio_benchmark_universe_mappings, risk_model_combinations, as_of_dates, constraint_combinations
    ):
        portfolio = mapping['portfolio']
        benchmark = mapping['benchmark']
        universes = mapping.get('universes', [])

        # Generate a unique optimization ID
        universes_str = "_".join(universes) if universes else "no_universe"
        risk_options_str = f"{risk_config['model']}_{risk_config['scaling']}_{risk_config['horizon']}"
        opt_id = f"opt_{portfolio}_{benchmark}_{universes_str}_{as_of_date}_{risk_options_str}_{goals_str}_{hash(frozenset(constraints.items()))}"

        # risk_options_hash = hash(frozenset(risk_config.items()))
        # opt_id = f"opt_{portfolio}_{benchmark}_{as_of_date}_{risk_options_hash}_{goals_str}_{hash(frozenset(constraints.items()))}"
        
        # Create the parameter set for this run
        params = {
            'optimization_id': opt_id,
            'portfolio': portfolio,
            'benchmark': benchmark,
            'as_of_date': as_of_date,
            'risk_options': risk_config,
            'goals': goals,
            'constraints': constraints,
            'universes': universes,
            'saveTo': save_to,
            'enableLookThrough': lookthrough,
            'infusedCashAmount': infused_cash
        }
        
        all_combinations.append(params)
    
    return all_combinations