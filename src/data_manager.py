# visualization/portfolio_viz/data_manager.py
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
import pandas as pd
import os
from .optimization_tracker import OptimizationTracker

# @dataclass
# class VisualizationRanges:
#     """Stores the valid ranges for visualization parameters"""
#     positions: Tuple[float, float]
#     risk: Tuple[float, float]
#     turnover: Tuple[float, float]
#     expected_return: Tuple[float, float]
#     max_sector_deviation: Optional[Tuple[float, float]] = None
    
#     @classmethod
#     def from_dataframe(cls, df: pd.DataFrame, padding: float = 0.1):
#         """Creates ranges from a dataframe with appropriate padding"""
#         pos_pad = 50  # Integer padding for positions
#         return cls(
#             positions=(df['maximum_positions'].min() - pos_pad, df['maximum_positions'].max() + pos_pad),
#             risk=(df['active_total_risk'].min() * 0.9, df['active_total_risk'].max() * 1.1),
#             turnover=(max(df['turnover'].min() - 0.5,0), min(df['turnover'].max() + 0.5,1)),
#             expected_return=(df['expected_return'].min() * 0.9, df['expected_return'].max() * 1.1),
#             max_sector_deviation=(df['max_sector_deviation'].min() * 0.9, df['max_sector_deviation'].max() * 1.1) if 'max_sector_deviation' in df.columns else None
#         )


@dataclass
class VisualizationRanges:
    """Stores the valid ranges for visualization parameters"""
    # Required ranges
    positions: Tuple[float, float]
    risk: Tuple[float, float]
    turnover: Tuple[float, float]
    expected_return: Tuple[float, float]
    
    # Optional ranges stored in a dictionary
    optional_ranges: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    
    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, padding: float = 0.1):
        """Creates ranges from a dataframe with appropriate padding"""
        pos_pad = 30  # Integer padding for positions
        
        # Define mapping of column names to configuration parameters
        column_configs = {
            'maximum_positions': {
                'attr_name': 'positions',
                'min_adjustment': lambda x: x - pos_pad,
                'max_adjustment': lambda x: x + pos_pad,
                'required': True
            },
            'active_total_risk': {
                'attr_name': 'risk',
                'min_adjustment': lambda x: x * 0.9,
                'max_adjustment': lambda x: x * 1.1,
                'required': True
            },
            'turnover': {
                'attr_name': 'turnover',
                'min_adjustment': lambda x: max(x - 0.5, 0),
                'max_adjustment': lambda x: min(x + 0.5, 1),
                'required': True
            },
            'expected_return': {
                'attr_name': 'expected_return',
                'min_adjustment': lambda x: x * 0.9,
                'max_adjustment': lambda x: x * 1.1,
                'required': True
            },
            # Optional columns
            'max_sector_deviation': {
                'attr_name': 'max_sector_deviation',
                'min_adjustment': lambda x: max(x - 0.02,0),
                'max_adjustment': lambda x: min(x + 0.02,1),
                'required': False
            },
            # Add more optional columns here as needed
        }
        
        # Initialize required parameters
        params = {}
        optional_ranges = {}
        
        # Process each column configuration
        for col_name, config in column_configs.items():
            if col_name in df.columns:
                min_val = config['min_adjustment'](df[col_name].min())
                max_val = config['max_adjustment'](df[col_name].max())
                
                if config['required']:
                    params[config['attr_name']] = (min_val, max_val)
                else:
                    optional_ranges[config['attr_name']] = (min_val, max_val)
            elif config['required']:
                raise ValueError(f"Required column '{col_name}' not found in dataframe")
        
        # Create the instance with required and optional parameters
        instance = cls(**params)
        instance.optional_ranges = optional_ranges
        return instance
    
    def get_range(self, name: str) -> Optional[Tuple[float, float]]:
        """Get a range by name, checking both required and optional ranges"""
        if hasattr(self, name):
            return getattr(self, name)
        return self.optional_ranges.get(name)
    
    def has_range(self, name: str) -> bool:
        """Check if a range exists by name"""
        return hasattr(self, name) or name in self.optional_ranges

class OptimizationDataManager:
    """Manages optimization result data and provides filtered views"""
    
    def __init__(self, results_frame: pd.DataFrame, tracker: Optional['OptimizationTracker'] = None):
        self.frame = results_frame.sort_values(['expected_return'], ascending=False)
        self.ranges = VisualizationRanges.from_dataframe(self.frame)
        # Create tracker if not provided
        if tracker is None:
            self.tracker = OptimizationTracker()
        else:
            self.tracker = tracker
    
    def filter_results(self, **kwargs) -> pd.DataFrame:
        """
        Returns filtered results based on provided ranges
        
        Example:
            filter_results(
                positions=(100, 200),
                risk=(0.01, 0.02),
                turnover=(0.1, 0.5),
                max_sector_deviation=(0.05, 0.15)  # Optional
            )
        """
        # Start with all rows
        mask = pd.Series(True, index=self.frame.index)
        
        # Column name mapping (parameter name -> dataframe column)
        column_mapping = {
            'positions': 'maximum_positions',
            'risk': 'active_total_risk',
            'turnover': 'turnover',
            'expected_return': 'expected_return',
            'max_sector_deviation': 'max_sector_deviation',
            # Add more mappings as needed
        }
        
        # Apply filters for each provided range
        for param_name, range_value in kwargs.items():
            if param_name in column_mapping:
                col_name = column_mapping[param_name]
                if col_name in self.frame.columns:
                    mask &= self.frame[col_name].between(*range_value)
        
        return self.frame.loc[mask]
    
        
    def get_trades_for_task(self, task_id: str) -> pd.DataFrame:
        """Retrieves trades data for a specific task"""
        # Strip any additional information from task_id (like expected return)
        task_id = task_id.split(' ')[0]
        opt_id = self.tracker.filter_optimizations(api_generated_id=task_id)["optimization_id"].values[0]
        results = self.tracker.load_optimization_results(opt_id)
        
        trades_df = results['trades']
        trades_df["changedQuantity"] = trades_df["changedQuantity"].apply(lambda x: x["value"] if isinstance(x,Dict) and "value" in x else x)

        return trades_df

# class OptimizationDataManager:
#     """Manages optimization result data and provides filtered views"""
    
#     def __init__(self, results_frame: pd.DataFrame, tracker: Optional[OptimizationTracker] = None):
#         self.frame = results_frame.sort_values(['expected_return'], ascending=False)
#         self.ranges = VisualizationRanges.from_dataframe(self.frame)
#         # Create tracker if not provided
#         if tracker is None:
#             self.tracker = OptimizationTracker()
#         else:
#             self.tracker = tracker
        
#     def filter_results(self, pos_range: Tuple[float, float], 
#                       risk_range: Tuple[float, float], 
#                       turnover_range: Tuple[float, float]) -> pd.DataFrame:
#         """Returns filtered results based on slider ranges"""
#         mask = (
#             self.frame['maximum_positions'].between(*pos_range) &
#             self.frame['active_total_risk'].between(*risk_range) &
#             self.frame['turnover'].between(*turnover_range)
#         )
#         return self.frame.loc[mask]
    
#     def get_trades_for_task(self, task_id: str) -> pd.DataFrame:
#         """Retrieves trades data for a specific task"""
#         # Strip any additional information from task_id (like expected return)
#         task_id = task_id.split(' ')[0]
#         opt_id = self.tracker.filter_optimizations(api_generated_id=task_id)["optimization_id"].values[0]
#         results = self.tracker.load_optimization_results(opt_id)
        
#         trades_df = results['trades']
#         trades_df["changedQuantity"] = trades_df["changedQuantity"].apply(lambda x: x["value"] if isinstance(x,Dict) and "value" in x else x)

#         return trades_df
    

