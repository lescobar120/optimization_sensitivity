# task_builder.py

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Union
from .template_utils import (
    load_template, populate_template, 
    load_custom_instrument_list, load_goal_mappings, load_constraint_mappings, 
    map_trade_univ_to_params, map_constraint_to_params
)

def build_task(config_params: Dict[str, Any], 
               trade_universe_mappings: Dict[str, Any],
               goal_mappings: List[str], 
               constraint_mappings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build optimization task for one parameter set using mappings from config.
    
    Args:
        config_params: Dictionary of configuration parameters
        mappings: Dictionary of constraint mappings
        
    Returns:
        Complete optimization task structure
    """
    task = {
        "optimizationId": config_params["optimization_id"],
        "portfolioId": config_params["portfolio"],
        "benchmarkId": config_params["benchmark"],
        "tradeUniverse": [],
        "asOfDate": config_params["as_of_date"],
        "riskOptions": {
            "riskModel": config_params["risk_options"]["model"],
            "riskModelScaling": config_params["risk_options"]["scaling"],
            "riskModelHorizon": config_params["risk_options"]["horizon"]
        },
        "goals": [],
        "portfolioConstraints": [],
        "instrumentConstraints": [],
        "options": {
            "longPositionOnly": True,
            "benchmarkCrossOver": True,
            "longShortCrossOver": True,
            "tradeLevel": "SECURITY",
            "liquidateNonUniverseInstruments": True,
            "enforceRoundLots": True
        },
        "saveTo": config_params["saveTo"],
        "enableLookThrough": config_params["enableLookThrough"],
        "infusedCashAmount": config_params["infusedCashAmount"]
    }

    # Process trade universes
    for universe_name in config_params.get('universes', []):
        if universe_name in trade_universe_mappings:
            mapping = trade_universe_mappings[universe_name]
            template_path = mapping["template_path"]
            
            try:
                # Load template
                template = load_template(template_path)
                
                # Prepare template parameters
                template_params = map_trade_univ_to_params(config_params, mapping)
                
                # Populate template
                universe = populate_template(template, template_params)
                
                # Add to trade universe in task
                task["tradeUniverse"].append(universe)
            except Exception as e:
                print(f"Error processing trade universe {universe_name}: {e}")

    # Process each goal in the configuration
    for goal_name in config_params['goals']:
        if goal_name in goal_mappings:
            mapping = goal_mappings[goal_name]
            template_path = mapping["template_path"]
            try:
                # Load template string
                template = load_template(template_path)
                
                # Add to goals in task
                task["goals"].append(json.loads(template))
            except Exception as e:
                print(f"Error processing goal {goal_name}: {e}")
    
    
    # Process each constraint in the configuration
    for constraint_name, constraint_value in config_params["constraints"].items():
        if constraint_name in constraint_mappings:
            mapping = constraint_mappings[constraint_name]
            template_path = mapping["template_path"]
            category = mapping["category"]
            
            try:
                # Load template
                template = load_template(template_path)
                
                # Map the constraint value to template parameters
                template_params = map_constraint_to_params(
                    constraint_name, constraint_value, constraint_mappings
                )
                
                # Populate template
                constraint = populate_template(template, template_params)
                
                # Add to appropriate category in task
                task[category].append(constraint)
            except Exception as e:
                print(f"Error processing constraint {constraint_name}: {e}")
    
    return task