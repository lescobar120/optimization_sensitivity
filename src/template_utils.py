# template_utils.py

"""
This package containts utility functions for managing optimization task components 
and injecting config values into template placeholders for scaling of constraint generation.
In particular, this package is helpful for an optimization iteration or efficient fronteir analysis workflow,
whereby a common task template would iterate over combinations of gradually relaxing constraints and goals/trade-offs

NEED TO ADD SUPPORT FOR ITERATING ON GOAL TRADE-OFF COMBINATIONS
"""

import json
import yaml
import os
from pathlib import Path
from typing import Dict, List, Any, Union

def load_template(template_path: str, templates_dir: str = "config/templates") -> str:
    """
    Load a template file as a string.
    
    Args:
        template_path: Relative path to the template within templates_dir
        templates_dir: Base directory for templates
        
    Returns:
        Template content as a string
    """
    full_path = Path(templates_dir) / template_path
    with open(full_path, 'r') as file:
        return file.read()

def load_constraint_mappings(mappings_path: str) -> Dict[str, Any]:
    """
    Load constraint mappings from a YAML file.
    
    Args:
        mappings_path: Path to the mappings YAML file
        
    Returns:
        Dictionary containing the constraint mappings
    """
    with open(mappings_path, 'r') as file:
        mappings = yaml.safe_load(file)
    return mappings['constraints']

def load_goal_mappings(mappings_path: str) -> Dict[str, Any]:
    """
    Load goal mappings from a YAML file.
    
    Args:
        mappings_path: Path to the mappings YAML file
        
    Returns:
        Dictionary containing the goal mappings
    """
    with open(mappings_path, 'r') as file:
        mappings = yaml.safe_load(file)
    return mappings['goals']


def load_trade_universe_mappings(mappings_path: str) -> Dict[str, Any]:
    """
    Load trade universe mappings from a YAML file.
    
    Args:
        mappings_path: Path to the mappings YAML file
        
    Returns:
        Dictionary containing the trade universe mappings
    """
    with open(mappings_path, 'r') as file:
        mappings = yaml.safe_load(file)
    return mappings['trade_universes']


def load_custom_instrument_list(list_path: str) -> List[Dict[str, str]]:
    """
    Load a list of custom instruments from a JSON file.
    
    Args:
        list_path: Path to the instrument list JSON file
        
    Returns:
        List of instrument dictionaries
    """
    with open(list_path, 'r') as file:
        instrument_list = json.load(file)
    return instrument_list


def map_constraint_to_params(constraint_name: str, constraint_value: Any, 
                            mappings: Dict[str, Any]) -> Dict[str, str]:
    """
    Map a constraint value to template parameters based on mappings.
    
    Args:
        constraint_name: Name of the constraint
        constraint_value: Value of the constraint
        mappings: Dictionary of constraint mappings
        
    Returns:
        Dictionary of template parameters
    """
    if constraint_name not in mappings:
        raise ValueError(f"No mapping found for constraint: {constraint_name}")
    
    mapping = mappings[constraint_name]
    params = {}
    
    # Handle different parameter mapping styles
    if "param_key" in mapping:
        # Simple 1:1 mapping
        params[mapping["param_key"]] = constraint_value
    elif "param_keys" in mapping:
        # Complex mapping for constraints with min/max values
        if isinstance(constraint_value, dict):
            for key, param_key in mapping["param_keys"].items():
                if key in constraint_value:
                    params[param_key] = constraint_value[key]
        else:
            # Handle case where we have param_keys but value is not a dict
            raise ValueError(f"Expected dict value for constraint {constraint_name}")
    
    return params


def map_trade_univ_to_params(config_params: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Map a trade universe to template parameters based on mappings.
    
    Args:
        config_params: Dictionary of optimization configuration parameters
        mapping: Dictionary of trade universe mapping
        
    Returns:
        Dictionary of template parameters
    """

    # Prepare template parameters
    template_params = {
        "portfolioId": config_params['portfolio'],
        "benchmarkId": config_params['benchmark']
        }
    
    # For custom universes, load the instrument list
    if "instrument_list" in mapping:
        _instruments = load_custom_instrument_list(f"config/instruments/{mapping['instrument_list']}")
        instruments = [{"instrumentUniqueId":_id059} for _id059 in _instruments]
        template_params["customUniverse"] = instruments

    return template_params


def populate_template(template_str: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Replace placeholders in template with actual values, handling negative expressions.
    
    Args:
        template_str: Template string with placeholders
        params: Dictionary of parameter values to substitute
        
    Returns:
        Populated template as a Python dictionary
    """
    # Start with the template as a string
    populated = template_str
    
    # Replace each placeholder with its value
    for key, value in params.items():
        placeholder = f"${{{key}}}"

        # Handle different data types
        if isinstance(value, (list, dict)):
            # For lists and dictionaries, convert to JSON string representation 
            # WITHOUT surrounding quotes (they're already in the JSON)
            json_value = json.dumps(value)
            
            # Handle the placeholder pattern differently for lists/dicts
            # We need to handle both "${key}" and ${key} formats
            quoted_pattern = f'"{placeholder}"'
            if quoted_pattern in populated:
                # Replace "${key}" with the raw JSON without extra quotes
                populated = populated.replace(quoted_pattern, json_value)
            elif placeholder in populated:
                # Replace ${key} with the raw JSON
                populated = populated.replace(placeholder, json_value)
        
        # Handle different data types
        elif isinstance(value, (int, float, bool)):
            # For numeric types and booleans, convert to JSON representation
            json_value = json.dumps(value)
            
            # Pattern for negative value inside quotes: "-${key}"
            quoted_neg_pattern = f'"-{placeholder}"'
            if quoted_neg_pattern in populated:
                neg_json_value = json.dumps(-value)
                populated = populated.replace(quoted_neg_pattern, neg_json_value)
            
            # Pattern for direct negative placeholder: -${key}
            direct_neg_pattern = f'-{placeholder}'
            if direct_neg_pattern in populated:
                neg_json_value = json.dumps(-value)
                populated = populated.replace(direct_neg_pattern, neg_json_value)
            
            # Finally replace standard placeholders
            # First quoted placeholders: "${key}"
            quoted_pattern = f'"{placeholder}"'
            if quoted_pattern in populated:
                populated = populated.replace(quoted_pattern, json_value)
            
            # Then direct placeholders: ${key}
            if placeholder in populated:
                populated = populated.replace(placeholder, json_value)

        else:
            # For strings, keep the regular replacement
            populated = populated.replace(placeholder, str(value))
    
    # Debug output
    #print(f"Final populated JSON: {populated}")
    
    # Convert back to Python dictionary
    try:
        return json.loads(populated)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        print(f"Problematic JSON: {populated}")
        raise