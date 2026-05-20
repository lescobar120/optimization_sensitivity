# analysis_utils.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Any

from .optimization_tracker import OptimizationTracker


class OptimizationAnalyzer:
    """
    Analyzes optimization results and provides insights.
    """
    
    def __init__(self, tracker: OptimizationTracker):
        """
        Initialize the analyzer with a tracker.
        
        Args:
            tracker: OptimizationTracker instance
        """
        self.tracker = tracker

        self.custom_goal_mapper = {
            "CUSTOM_NUMBER(FIELD = 'CF_7459422178055815169')": "expected_return"
        }
        self.metadata_constraint_mapper = {
                ('weight', 'GICS Sector:All'): 'max_sector_deviation'
        }

        self.metadata_security_constraints = [
            'max_security_weight'
        ]
    
    def constraint_sensitivity_analysis(
        self, 
        constraint_name: str,
        filter_kwargs: Optional[Dict[str, Any]] = None,
        goal_metric: str = 'finalValue',
        columns_to_load: List[str] = None
    ) -> pd.DataFrame:
        """
        Analyze sensitivity of goals to changes in a constraint.
        
        Args:
            constraint_name: Name of the constraint to analyze
            filter_kwargs: Additional filtering criteria
            goal_metric: Metric to analyze for goals ('initialValue', 'finalValue', etc.)
            
        Returns:
            DataFrame with analysis results
        """
        # Get successful optimizations
        successful_df = self.tracker.filter_optimizations(status='success')
        
        # Apply additional filters if provided
        if filter_kwargs:
            for key, value in filter_kwargs.items():
                if key in successful_df.columns:
                    successful_df = successful_df[successful_df[key] == value]
        
        # Check if we have data to analyze
        if len(successful_df) == 0:
            print("No data available for analysis after filtering")
            return pd.DataFrame()
        
        # Check if constraint exists in the index
        if constraint_name not in successful_df.columns:
            print(f"Constraint '{constraint_name}' not found in the optimization index")
            return pd.DataFrame()
        
        # Get unique constraint values
        constraint_values = successful_df[constraint_name].unique()
        constraint_values = sorted([v for v in constraint_values if v is not None])
        
        if len(constraint_values) <= 1:
            print(f"Only one value ({constraint_values[0]}) found for constraint '{constraint_name}'")
            return pd.DataFrame()
        
        results = []
        
        # Analyze each optimization for the constraint values
        for constraint_value in constraint_values:
            # Get optimizations with this constraint value
            constraint_df = successful_df[successful_df[constraint_name] == constraint_value]
            
            # For each optimization, load its goal results
            for _, row in constraint_df.iterrows():
                opt_id = row['optimization_id']
                
                try:
                    # Load the results
                    opt_results = self.tracker.load_optimization_results(opt_id)
                    goals_df = opt_results['goals']
                    
                    # Analyze each goal
                    for _, goal_row in goals_df.iterrows():
                        goal_name = goal_row['fieldCode']
                        goal_value = goal_row.get(goal_metric, None)
                        
                        if goal_value is not None:
                            # Store the result
                            results.append({
                                'optimization_id': opt_id,
                                'portfolio': row['portfolio'],
                                'benchmark': row['benchmark'],
                                'as_of_date': row['as_of_date'],
                                'constraint_name': constraint_name,
                                'constraint_value': constraint_value,
                                'goal_name': goal_name,
                                'goal_metric': goal_metric,
                                'goal_value': goal_value
                            })
                
                except Exception as e:
                    print(f"Error loading results for optimization {opt_id}: {str(e)}")
        
        # Convert to DataFrame
        result_df = pd.DataFrame(results)
        
        # Pivot to make constraint values columns
        if len(result_df) > 0:
            pivot_df = result_df.pivot_table(
                index=['portfolio', 'benchmark', 'as_of_date', 'goal_name'],
                columns='constraint_value',
                values='goal_value',
                aggfunc='mean'
            )
            
            # Reset index to make it a regular DataFrame
            pivot_df = pivot_df.reset_index()
            
            return result_df, pivot_df
        
        return result_df, pd.DataFrame()
    
    ## MAKE A SIMILAR METHOD TO PLOT SCATTER OF INDIVIDUAL DATA POINTS TO SEE DISTRIBUTION
    ## OR ALSO INCLUDE A DISTRIBUTION CHART - VIOLIN CHART OR BOX PLOT

    def plot_constraint_sensitivity(
        self,
        constraint_name: str,
        goal_name: Optional[str] = None,
        filter_kwargs: Optional[Dict[str, Any]] = None,
        save_path: Optional[str] = None
    ):
        """
        Plot the sensitivity of goal metrics to a constraint.
        
        Args:
            constraint_name: Name of the constraint to analyze
            goal_name: Name of the goal to plot (if None, plots all goals)
            filter_kwargs: Additional filtering criteria
            save_path: Path to save the plot (if None, displays it)
        """
        # Get sensitivity analysis data
        df, sensitivity_df = self.constraint_sensitivity_analysis(
            constraint_name=constraint_name,
            filter_kwargs=filter_kwargs
        )
        
        if len(sensitivity_df) == 0:
            print("No data available for plotting")
            return
        
        # Extract constraint values (column names except the index columns)
        constraint_values = [col for col in sensitivity_df.columns 
                            if col not in ['portfolio', 'benchmark', 'as_of_date', 'goal_name']]
        
        if len(constraint_values) <= 1:
            print(f"Not enough constraint values to plot: {constraint_values}")
            return
        
        # Convert constraint values to numeric if possible
        constraint_values_numeric = []
        for val in constraint_values:
            try:
                constraint_values_numeric.append(float(val))
            except:
                constraint_values_numeric.append(val)
        
        # Filter by goal_name if specified
        if goal_name:
            plot_df = sensitivity_df[sensitivity_df['goal_name'] == goal_name]
            if len(plot_df) == 0:
                print(f"No data available for goal '{goal_name}'")
                return
        else:
            plot_df = sensitivity_df
        
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot each goal
        for i, (_, row) in enumerate(plot_df.iterrows()):
            goal = row['goal_name']
            portfolio = row['portfolio']
            benchmark = row['benchmark']
            label = f"{goal} ({portfolio}/{benchmark})"
            
            # Extract y values for this goal
            y_values = [row[val] for val in constraint_values]
            
            # Plot the line
            ax.plot(constraint_values_numeric, y_values, marker='o', label=label)
        
        # Set labels and title
        ax.set_xlabel(f'{constraint_name}')
        ax.set_ylabel('Goal Metric Value')
        ax.set_title(f'Sensitivity to {constraint_name}')
        
        # Add grid and legend
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.legend()
        
        # Save or show the plot
        if save_path:
            plt.savefig(save_path)
            print(f"Plot saved to {save_path}")
        else:
            plt.show()
    

    def load_goal_constraint_sensitivity_frames(
            self,
            goal: str,
            constraint_list: List[str],
            portfolio: str = None
    ):
        """
        load all goal sensitivity frames for a specified goal and constraint list
        optional: filter on portfolio

        Returns:
            Dictionary of DataFrames with comparison results with constraints as keys
        """

        sensitivity_frames = {}
        goal_check = True
        for constraint in constraint_list:
            
            sensitivity_frame, _ = self.constraint_sensitivity_analysis(
                constraint_name=constraint,
            )
            if goal_check and goal not in sensitivity_frame['goal_name'].unique():
                raise ValueError(f"{goal} does not exist as a goal")
            mask = (sensitivity_frame['goal_name'] == goal)
            if portfolio:
                mask &= (sensitivity_frame['portfolio']==portfolio)
            frame = sensitivity_frame.loc[mask].copy()

            # Nourish constraint frames with the additional constraints applied to each optimization
            # Capture all additional constraint inputs for the current constraint and enum
            additional_constraints = [c for c in constraint_list if c != constraint]
            constraints_frame = self.tracker.index_df[['optimization_id']+additional_constraints].copy()
            
            #sensitivity_frames[constraint] = frame
            sensitivity_frames[constraint] = pd.merge(frame,constraints_frame,how='left',on=['optimization_id'])

        return sensitivity_frames


    def compare_optimizations(
        self,
        optimization_ids: List[str],
        comparison_type: str = 'goals'
    ) -> pd.DataFrame:
        """
        Compare multiple optimization runs.
        
        Args:
            optimization_ids: List of optimization IDs to compare
            comparison_type: Type of comparison ('goals', 'constraints', 'trades', 'summary')
            
        Returns:
            DataFrame with comparison results
        """
        if not optimization_ids:
            return pd.DataFrame()
        
        # Verify all optimization IDs exist and have been successfully run
        for opt_id in optimization_ids:
            if opt_id not in self.tracker.index_df['optimization_id'].values:
                print(f"Optimization {opt_id} not found in index")
                return pd.DataFrame()
            
            mask = self.tracker.index_df['optimization_id'] == opt_id
            if self.tracker.index_df.loc[mask, 'status'].iloc[0] != 'success':
                print(f"Optimization {opt_id} has not been successfully run")
                return pd.DataFrame()
        
        # Load results for all optimizations
        all_results = {}
        
        for opt_id in optimization_ids:
            try:
                results = self.tracker.load_optimization_results(opt_id)
                all_results[opt_id] = results
            except Exception as e:
                print(f"Error loading results for optimization {opt_id}: {str(e)}")
                return pd.DataFrame()
        
        # Get metadata for all optimizations
        metadata = self.tracker.index_df[self.tracker.index_df['optimization_id'].isin(optimization_ids)]
        
        # Perform comparison based on type
        if comparison_type == 'goals':
            return self._compare_goals(all_results, metadata)
        elif comparison_type == 'constraints':
            return self._compare_constraints(all_results, metadata)
        elif comparison_type == 'optimization_pathways':
            return self._compare_optimization_pathways(all_results, metadata)
        elif comparison_type == 'trades':
            return self._compare_trades(all_results, metadata)
        elif comparison_type == 'summary':
            return self._compare_summary(all_results, metadata)
        else:
            print(f"Invalid comparison type: {comparison_type}")
            return pd.DataFrame()
        

    def _compare_optimization_pathways(
        self,
        all_results: Dict[str, Dict[str, pd.DataFrame]],
        metadata: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Compare goal-constraint pathways across optimizations
        Returns a dataframe of goal results and corresponding constraint levels
        """

        comparison = []

        for opt_id, results in all_results.items():
            goals_df = results['goals']
            constraints_df = results['constraints']

            # Get metadata for this optimization
            meta_row = metadata[metadata['optimization_id'] == opt_id].iloc[0]

            record = {
                'optimization_id': opt_id,
                'api_generated_id': meta_row['api_generated_id'],
                'portfolio': meta_row['portfolio'],
                'benchmark': meta_row['benchmark'],
                'as_of_date': meta_row['as_of_date'],
            }

            # Process each goal
            for _, goal_row in goals_df.iterrows():
                goal_name = goal_row['fieldCode']
                
                record[goal_name] = goal_row['finalValue']

            # Process each constraint
            for _, constraint_row in constraints_df.iterrows():
                constraint_name = constraint_row['fieldCode']
                constraint_type = constraint_row['scopeType']
                constraint_node = constraint_row['classificationNode']

                if constraint_type != 'GROUP_CLASSIFICATION' and constraint_name not in record:
                    record[constraint_name] = constraint_row['finalValue']
                if constraint_type == 'GROUP_CLASSIFICATION':
                    col = self.metadata_constraint_mapper[(constraint_name, constraint_node)]
                    record[col] = meta_row[col]

            for security_constraint in self.metadata_security_constraints:
                record[security_constraint] = meta_row[security_constraint]

            comparison.append(record)

        return pd.DataFrame(comparison)
    
    def _compare_goals(
        self,
        all_results: Dict[str, Dict[str, pd.DataFrame]],
        metadata: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Compare goals across optimizations
        Returns a dataframe of goal results and corresponding inputs
        """
        
        comparison = []
        
        for opt_id, results in all_results.items():
            goals_df = results['goals']
            
            # Get metadata for this optimization
            meta_row = metadata[metadata['optimization_id'] == opt_id].iloc[0]
            
            # Process each goal
            for _, goal_row in goals_df.iterrows():
                goal_name = goal_row['fieldCode']
                
                record = {
                    'optimization_id': opt_id,
                    'portfolio': meta_row['portfolio'],
                    'benchmark': meta_row['benchmark'],
                    'as_of_date': meta_row['as_of_date'],
                    'goal_name': goal_name,
                }
                
                # Add constraint values for context
                constraint_columns = [col for col in metadata.columns if col.startswith('max_') or col.startswith('min_')]
                for col in constraint_columns:
                    if col in meta_row and not pd.isna(meta_row[col]):
                        record[col] = meta_row[col]
                
                # Add all goal metrics
                for col in goals_df.columns:
                    if col != 'fieldCode' and not pd.isna(goal_row[col]):
                        record[f'goal_{col}'] = goal_row[col]
                
                comparison.append(record)
        
        return pd.DataFrame(comparison)
    
    def _compare_constraints(
        self,
        all_results: Dict[str, Dict[str, pd.DataFrame]],
        metadata: pd.DataFrame
    ) -> pd.DataFrame:
        """Compare constraints across optimizations."""
        
        comparison = []
        
        for opt_id, results in all_results.items():
            constraints_df = results['constraints']
            
            # Get metadata for this optimization
            meta_row = metadata[metadata['optimization_id'] == opt_id].iloc[0]
            
            # Process each constraint
            for _, constraint_row in constraints_df.iterrows():
                constraint_name = constraint_row['fieldCode']
                
                record = {
                    'optimization_id': opt_id,
                    'portfolio': meta_row['portfolio'],
                    'benchmark': meta_row['benchmark'],
                    'as_of_date': meta_row['as_of_date'],
                    'constraint_name': constraint_name,
                    'constraint_type': constraint_row.get('scopeType', 'Unknown')
                }
                
                ## SHOULD THIS INSTEAD JUST GRAB THE MIN/MAX OF THE CURRENT CONSTRAINT? ##
                # Add constraint values for context
                constraint_columns = [col for col in metadata.columns if col.startswith('max_') or col.startswith('min_')]
                for col in constraint_columns:
                    if col in meta_row and not pd.isna(meta_row[col]):
                        record[col] = meta_row[col]
                
                # Add constraint metrics
                for col in constraints_df.columns:
                    if col not in ['fieldCode', 'type'] and not pd.isna(constraint_row[col]):
                        record[f'constraint_{col}'] = constraint_row[col]
                
                comparison.append(record)
        
        return pd.DataFrame(comparison)
    
    def _compare_trades(
        self,
        all_results: Dict[str, Dict[str, pd.DataFrame]],
        metadata: pd.DataFrame
    ) -> pd.DataFrame:
        """Compare trades across optimizations."""
        
        all_trades = {}
        
        # Collect trades from all optimizations
        for opt_id, results in all_results.items():
            trades_df = results['trades']
            trades_df["changedQuantity"] = trades_df["changedQuantity"].apply(lambda x: x["value"] if isinstance(x,Dict) and "value" in x else x)
            
            # Add optimization ID to trades
            trades_df = trades_df.copy()
            trades_df['optimization_id'] = opt_id
            
            # Get metadata for this optimization
            meta_row = metadata[metadata['optimization_id'] == opt_id].iloc[0]
            
            # Add metadata columns
            for col in ['portfolio', 'benchmark', 'as_of_date']:
                trades_df[col] = meta_row[col]
            
            # Store in dictionary
            all_trades[opt_id] = trades_df
        
        # Combine all trades
        if all_trades:
            combined_trades = pd.concat(all_trades.values())
            
            # You might want to add some summary statistics here
            # For example, group by security and compare across optimizations
            
            return combined_trades
        
        return pd.DataFrame()
    
    def _compare_summary(
        self,
        all_results: Dict[str, Dict[str, pd.DataFrame]],
        metadata: pd.DataFrame
    ) -> pd.DataFrame:
        """Compare summary metrics across optimizations"""
        
        comparison = []
        
        for opt_id, results in all_results.items():
            summary_df = results['summary']
            
            # Get metadata for this optimization
            meta_row = metadata[metadata['optimization_id'] == opt_id].iloc[0]
            
            # Create a record with metadata
            record = {
                'optimization_id': opt_id,
                'portfolio': meta_row['portfolio'],
                'benchmark': meta_row['benchmark'],
                'as_of_date': meta_row['as_of_date'],
            }
            
            ## IS THIS NECESSARY ## - MAYBE
            # Add constraint values for context
            constraint_columns = [col for col in metadata.columns if col.startswith('max_') or col.startswith('min_')]
            for col in constraint_columns:
                if col in meta_row and not pd.isna(meta_row[col]):
                    record[col] = meta_row[col]
            
            # Add summary metrics
            for col in summary_df.columns:
                if not pd.isna(summary_df.iloc[0][col]):
                    record[f'summary_{col}'] = summary_df.iloc[0][col]
            
            comparison.append(record)
        
        return pd.DataFrame(comparison)
    
    def get_security_trade_stats(self, all_trades_frame, successful_optimizations_frame, portfolio):
        """
        get security trade statistics on number of times each security was a buy, sell, etc.
        """

        portfolio_trades = all_trades_frame[all_trades_frame['portfolio'] == portfolio].copy()

        # Define trade categories
        trade_categories = {
            'Buys': (portfolio_trades['changedWeight'] > 0) & (portfolio_trades['initialWeight'] > 0),
            'Sells': (portfolio_trades['changedWeight'] < 0) & (portfolio_trades['finalWeight'] > 0),
            'New Holdings': (portfolio_trades['initialWeight'] == 0) & (portfolio_trades['finalWeight'] > 0),
            'Liquidated Holdings': (portfolio_trades['finalWeight'] == 0) & (portfolio_trades['initialWeight'] > 0)
        }

        # Create a categorical column for trade type
        portfolio_trades['trade_type'] = None
        for trade_type, mask in trade_categories.items():
            portfolio_trades.loc[mask, 'trade_type'] = trade_type

        # Pivot to get counts by ticker and trade type
        trade_stats_frame = portfolio_trades.pivot_table(
            index='ticker',
            columns='trade_type',
            values='optimization_id',
            aggfunc='count',
            fill_value=0
        )

        # Ensure all trade types are present even if empty
        for trade_type in trade_categories.keys():
            if trade_type not in trade_stats_frame.columns:
                trade_stats_frame[trade_type] = 0


        successful_ids_portfolio = list(successful_optimizations_frame.loc[successful_optimizations_frame['portfolio']==portfolio,'optimization_id'])
        total_optimizations = len(successful_ids_portfolio)

        trade_stats_frame['buy_consistency'] = (trade_stats_frame['Buys'] + trade_stats_frame['New Holdings']) / total_optimizations
        trade_stats_frame['sell_consistency'] = (trade_stats_frame['Sells'] + trade_stats_frame['Liquidated Holdings']) / total_optimizations
        trade_stats_frame['new_holdings_consistency'] = trade_stats_frame['New Holdings'] / total_optimizations
        trade_stats_frame['total_actions'] = trade_stats_frame[['Buys', 'Sells', 'New Holdings', 'Liquidated Holdings']].sum(axis=1)

        return trade_stats_frame


    ## SHOULD UNPACK ACTUAL CONSTRAINT VALUES THAT WERE REALIZED AS WELL ##
    def find_optimal_constraints(
        self,
        target_goal: str,
        optimize_direction: str = 'maximize',
        filter_kwargs: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Find optimal constraint values for a specific goal 
        - filters for results of particular goal and returns a dataframe sorted with best goal result and corresponding params at the top
        
        Args:
            target_goal: Name of the goal to optimize
            optimize_direction: Direction to optimize ('maximize' or 'minimize')
            filter_kwargs: Additional filtering criteria
            
        Returns:
            DataFrame with optimal constraint values
        """
        
        # Get successful optimizations
        successful_df = self.tracker.filter_optimizations(status='success')
        
        # Apply additional filters if provided
        if filter_kwargs:
            for key, value in filter_kwargs.items():
                if key in successful_df.columns:
                    successful_df = successful_df[successful_df[key] == value]
        
        # Check if we have data to analyze
        if len(successful_df) == 0:
            print("No data available for analysis after filtering")
            return pd.DataFrame()
        
        # Get all constraint columns
        constraint_columns = [col for col in successful_df.columns 
                             if col.startswith('max_') or col.startswith('min_')]
        
        # Load goal results for each optimization
        goal_results = []
        
        for _, row in successful_df.iterrows():
            opt_id = row['optimization_id']
            
            try:
                # Load the results
                opt_results = self.tracker.load_optimization_results(opt_id)
                goals_df = opt_results['goals']
                
                # Find the target goal
                target_goal_rows = goals_df[goals_df['fieldCode'] == target_goal]
                
                if len(target_goal_rows) > 0:
                    goal_value = target_goal_rows.iloc[0].get('finalValue', None)
                    
                    if goal_value is not None:
                        # Create a record
                        record = {
                            'optimization_id': opt_id,
                            'portfolio': row['portfolio'],
                            'benchmark': row['benchmark'],
                            'as_of_date': row['as_of_date'],
                            'goal_value': goal_value
                        }
                        
                        # Add constraint values
                        for col in constraint_columns:
                            if col in row and not pd.isna(row[col]):
                                record[col] = row[col]
                        
                        goal_results.append(record)
            
            except Exception as e:
                print(f"Error loading results for optimization {opt_id}: {str(e)}")
        
        # Convert to DataFrame
        result_df = pd.DataFrame(goal_results)
        
        if len(result_df) == 0:
            print(f"No results found for goal '{target_goal}'")
            return pd.DataFrame()
        
        # Sort by goal value according to optimization direction
        if optimize_direction.lower() == 'maximize':
            result_df = result_df.sort_values('goal_value', ascending=False)
        else:
            result_df = result_df.sort_values('goal_value', ascending=True)
        
        return result_df
    
    def calculate_efficient_frontier(
        self,
        x_goal: str,
        y_goal: str,
        filter_kwargs: Optional[Dict[str, Any]] = None,
        plot: bool = False,
        save_path: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Calculate the efficient frontier between two goals.
        
        Args:
            x_goal: Name of the first goal (x-axis)
            y_goal: Name of the second goal (y-axis)
            filter_kwargs: Additional filtering criteria
            plot: Whether to plot the frontier
            save_path: Path to save the plot (if None, displays it)
            
        Returns:
            DataFrame with efficient frontier points
        """

        # Get successful optimizations
        successful_df = self.tracker.get_successful_optimizations()
        
        # Apply additional filters if provided
        if filter_kwargs:
            for key, value in filter_kwargs.items():
                if key in successful_df.columns:
                    successful_df = successful_df[successful_df[key] == value]
        
        # Check if we have data to analyze
        if len(successful_df) == 0:
            print("No data available for analysis after filtering")
            return pd.DataFrame()
        
        # Load goal results for each optimization
        frontier_points = []
        
        for _, row in successful_df.iterrows():
            opt_id = row['optimization_id']
            
            try:
                # Load the results
                opt_results = self.tracker.load_optimization_results(opt_id)
                goals_df = opt_results['goals']
                
                # Find values for both goals
                x_value = None
                y_value = None
                
                for _, goal_row in goals_df.iterrows():
                    goal_name = goal_row['fieldCode']
                    
                    if goal_name == x_goal:
                        x_value = goal_row.get('finalValue', None)
                    elif goal_name == y_goal:
                        y_value = goal_row.get('finalValue', None)
                
                if x_value is not None and y_value is not None:
                    # Create a record
                    record = {
                        'optimization_id': opt_id,
                        'portfolio': row['portfolio'],
                        'benchmark': row['benchmark'],
                        'as_of_date': row['as_of_date'],
                        'x_goal': x_goal,
                        'y_goal': y_goal,
                        'x_value': x_value,
                        'y_value': y_value
                    }
                    
                    # Add constraint values for reference
                    constraint_columns = [col for col in successful_df.columns 
                                         if col.startswith('max_') or col.startswith('min_')]
                    
                    for col in constraint_columns:
                        if col in row and not pd.isna(row[col]):
                            record[col] = row[col]
                    
                    frontier_points.append(record)
            
            except Exception as e:
                print(f"Error loading results for optimization {opt_id}: {str(e)}")
        
        # Convert to DataFrame
        frontier_df = pd.DataFrame(frontier_points)
        
        if len(frontier_df) == 0:
            print(f"No results found for goals '{x_goal}' and '{y_goal}'")
            return pd.DataFrame()
        
        # Plot if requested
        if plot:
            self._plot_frontier(frontier_df, x_goal, y_goal, save_path)
        
        return frontier_df
    
    def _plot_frontier(
        self,
        frontier_df: pd.DataFrame,
        x_goal: str,
        y_goal: str,
        save_path: Optional[str] = None
    ):
        """
        Plot the efficient frontier.
        
        Args:
            frontier_df: DataFrame with frontier points
            x_goal: Name of the x-axis goal
            y_goal: Name of the y-axis goal
            save_path: Path to save the plot (if None, displays it)
        """
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Extract data
        x_values = frontier_df['x_value']
        y_values = frontier_df['y_value']
        
        # Scatter plot
        scatter = ax.scatter(x_values, y_values, alpha=0.7)
        
        # Add labels for each point
        for i, row in frontier_df.iterrows():
            label = row['optimization_id']
            ax.annotate(
                text=f"{i}",
                xy=(row['x_value'], row['y_value']),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=8
            )
        
        # Set labels and title
        ax.set_xlabel(x_goal)
        ax.set_ylabel(y_goal)
        ax.set_title(f'Efficient Frontier: {y_goal} vs {x_goal}')
        
        # Add grid
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Save or show the plot
        if save_path:
            plt.savefig(save_path)
            print(f"Plot saved to {save_path}")
        else:
            plt.show()