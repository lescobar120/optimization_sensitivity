# optimization_tracker.py
import os
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union


class OptimizationTracker:
    """
    Tracks and manages portfolio optimization runs and their results
    """

    ###########################################################################################################################
    #############  Incorporate method to cache risk report data that aligns with Optimization ID and path caching #############
    ###########################################################################################################################

    def __init__(
        self, 
        index_path: str = "data/optimization_index.parquet",
        results_dir: str = "data/optimization_results",
        risk_report_dir: str = "data/risk_reports"
    ):
        """
        Initialize the optimization tracker.
        
        Args:
            index_path: Path to the master index file
            results_dir: Base directory to store optimization results
        """
        self.index_path = Path(index_path)
        self.results_dir = Path(results_dir)
        self.risk_report_dir = Path(risk_report_dir)
        
        # Create directories if they don't exist
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.risk_report_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or create the index DataFrame
        if self.index_path.exists():
            self.index_df = pd.read_parquet(self.index_path)
        else:
            self.index_df = self._create_empty_index()
            self._save_index()
    
    def _create_empty_index(self) -> pd.DataFrame:
        """
        Create an empty index DataFrame with required columns.
        
        Returns:
            Empty DataFrame with appropriate columns
        """
        columns = [
            # Identifiers
            'optimization_id',
            'fs_id',
            'api_generated_id',
            'portfolio',
            'benchmark',
            'as_of_date',
            
            # Risk options
            'risk_model',
            'risk_scaling',
            'risk_horizon',
            
            # Trade Universe
            #'trade_universes', ## Incorporate at some point - will need to parse accordingly

            # Goals
            'goals_summary',
            
            # Constraints
            'max_active_risk',
            'min_positions',
            'max_positions',
            'min_turnover',
            'max_turnover',
            'min_sector_deviation',  # Added min deviation
            'max_sector_deviation',  # Renamed to be clearer
            'min_security_weight',   # Added min security weight
            'max_security_weight',
            
            # File paths
            'task_path',
            'results_path',
            'summary_path',
            'goals_path',
            'constraints_path',
            'trades_path',
            'exceptions_path',
            'risk_report_path',
            
            # Status information
            'status',
            'error_message',
            'run_timestamp',
            'session_id'
        ]
        
        return pd.DataFrame(columns=columns)


    def _format_goals_summary(self, goals: List[Dict[str, Any]]) -> str:
        """
        Format goals into a structured string summary.
        
        Args:
            goals: List of goal dictionaries
            
        Returns:
            Formatted string representing goals
        """
        if not goals:
            return ""
        
        formatted_goals = []
        
        for goal in goals:
            # Extract field code/name and action
            field_code = goal.get('fieldCode', '')
            action = goal.get('action', '')
            tradeoff = goal.get('tradeoff', 1.0)
            
            # Format each goal as field:action:tradeoff
            formatted_goal = f"{field_code}:{action}:{tradeoff}"
            formatted_goals.append(formatted_goal)
        
        # Join all formatted goals with semicolons
        return ";".join(formatted_goals)

    def _extract_constraints_from_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract constraint values from task structure.
        
        Args:
            task: The optimization task dictionary
            
        Returns:
            Dictionary of constraint values
        """
        constraints = {}
        
        # Extract portfolio constraints
        for constraint in task.get('portfolioConstraints', []):
            field_code = constraint.get('fieldCode', '')
            
            if field_code == 'maximum_positions':
                constraints['min_positions'] = constraint.get('minThreshold')
                constraints['max_positions'] = constraint.get('maxThreshold')
            
            elif field_code == 'turnover':
                constraints['min_turnover'] = constraint.get('minThreshold', 0)
                constraints['max_turnover'] = constraint.get('maxThreshold')
            
            elif field_code == 'active_total_risk':
                constraints['max_active_risk'] = constraint.get('maxThreshold')
            
            elif field_code == 'weight' and 'classificationNode' in constraint:
                # Sector weight constraint
                if (constraint.get('classificationNode', {}).get('classificationName') == 'GICS Sector' and
                    constraint.get('relativeTo') == 'BENCHMARK'):
                    constraints['min_sector_deviation'] = constraint.get('minThreshold')
                    constraints['max_sector_deviation'] = constraint.get('maxThreshold')
        
        # Extract instrument constraints
        for constraint in task.get('instrumentConstraints', []):
            # Look for MAX_WEIGHT field
            for field in constraint.get('fields', []):
                if field.get('fieldCode') == 'MAX_WEIGHT':
                    value = field.get('valueOrField', {}).get('value')
                    if value is not None:
                        constraints['max_security_weight'] = value
                
                elif field.get('fieldCode') == 'MIN_WEIGHT':
                    value = field.get('valueOrField', {}).get('value')
                    if value is not None:
                        constraints['min_security_weight'] = value
        
        return constraints


    def register_optimization_task(self, task: Dict[str, Any], task_path: str) -> str:
        """
        Register a new optimization task to the index.
        
        Args:
            task: The optimization task dictionary
            task_path: Path to the saved task JSON file
            
        Returns:
            optimization_id for the registered task
        """
        optimization_id = task.get('optimizationId')
        
        # Check if this optimization has already been registered
        if optimization_id in self.index_df['optimization_id'].values:
            #print(f"Optimization {optimization_id} already registered. Skipping registration.")
            return optimization_id
        
        # Create the results directory for this optimization
        # results_path = self.results_dir / optimization_id
        # results_path.mkdir(parents=True, exist_ok=True)

        # risk_report_path = self.risk_report_dir / optimization_id
        # risk_report_path.mkdir(parents=True, exist_ok=True)

        # Create a filesystem-friendly ID for directory names
        import hashlib
        fs_friendly_id = hashlib.md5(optimization_id.encode()).hexdigest()
        
        # Create directories using the shortened ID
        results_path = self.results_dir / fs_friendly_id
        results_path.mkdir(parents=True, exist_ok=True)

        risk_report_path = self.risk_report_dir / fs_friendly_id
        risk_report_path.mkdir(parents=True, exist_ok=True)
        
        # Format goals summary
        goals_summary = self._format_goals_summary(task.get('goals', []))
        
        # Extract constraint values using the new method
        constraints = self._extract_constraints_from_task(task)
        
        # Prepare the record for the index
        record = {
            'optimization_id': optimization_id,
            'fs_id': fs_friendly_id, # Filesystem-friendly ID
            'api_generated_id': None,  # Will be updated after API call
            'portfolio': task.get('portfolioId'),
            'benchmark': task.get('benchmarkId'),
            'as_of_date': task.get('asOfDate'),
            
            # Risk options
            'risk_model': task.get('riskOptions', {}).get('riskModel'),
            'risk_scaling': task.get('riskOptions', {}).get('riskModelScaling'),
            'risk_horizon': task.get('riskOptions', {}).get('riskModelHorizon'),
            
            # Goals summary
            'goals_summary': goals_summary,
            
            # Constraints (with default None for all)
            'max_active_risk': constraints.get('max_active_risk'),
            'min_positions': constraints.get('min_positions'),
            'max_positions': constraints.get('max_positions'),
            'min_turnover': constraints.get('min_turnover'),
            'max_turnover': constraints.get('max_turnover'),
            'min_sector_deviation': constraints.get('min_sector_deviation'),
            'max_sector_deviation': constraints.get('max_sector_deviation'),
            'min_security_weight': constraints.get('min_security_weight'),
            'max_security_weight': constraints.get('max_security_weight'),
            
            # File paths
            'task_path': task_path,
            'results_path': str(results_path),
            'summary_path': str(results_path / 'summary.parquet'),
            'goals_path': str(results_path / 'goals.parquet'),
            'constraints_path': str(results_path / 'constraints.parquet'),
            'trades_path': str(results_path / 'trades.parquet'),
            'exceptions_path': str(results_path / 'exceptions.parquet'),
            'risk_report_path': str(risk_report_path / 'risk_report.parquet'),
            
            # Status information
            'status': 'not_run',
            'error_message': None,
            'run_timestamp': None,
            'session_id': None
        }
        
        # Append to the index DataFrame
        # FIX FOR CONCAT WARNING: Create a new row with proper dtypes
        # Get current dtypes from the index DataFrame
        if len(self.index_df) > 0:
            # Create a new row with the same structure as the existing DataFrame
            new_row = pd.DataFrame([record], columns=self.index_df.columns)
            
            # Ensure each column has the correct dtype
            for col in self.index_df.columns:
                if col in new_row.columns:
                    try:
                        new_row[col] = new_row[col].astype(self.index_df[col].dtype)
                    except:
                        # If conversion fails, keep the original dtype
                        pass
            
            # Concatenate with proper dtypes
            self.index_df = pd.concat([self.index_df, new_row], ignore_index=True)
        else:
            # If index is empty, just create a new DataFrame
            self.index_df = pd.DataFrame([record])
        
        self._save_index()
        
        return optimization_id
    
    def _save_index(self):
        """Save the index DataFrame to the parquet file."""
        self.index_df.to_parquet(self.index_path, index=False)

    def update_optimization_status(
        self, 
        optimization_id: str, 
        api_generated_id: Optional[str] = None,
        session_id: Optional[str] = None,  # Added session_id parameter
        status: str = 'success',
        error_message: Optional[str] = None
    ):
        """
        Update the status of an optimization run in the index.
        
        Args:
            optimization_id: The optimization ID to update
            api_generated_id: ID generated by the API for this optimization
            session_id: Session ID from the API response
            status: Status of the optimization (success, failure, running)
            error_message: Error message if the optimization failed
        """
        if optimization_id not in self.index_df['optimization_id'].values:
            raise ValueError(f"Optimization {optimization_id} not found in index")
        
        # Update the status and relevant fields
        mask = self.index_df['optimization_id'] == optimization_id
        if api_generated_id:
            self.index_df.loc[mask, 'api_generated_id'] = api_generated_id
        
        if session_id:
            self.index_df.loc[mask, 'session_id'] = session_id
        
        self.index_df.loc[mask, 'status'] = status
        
        if error_message:
            self.index_df.loc[mask, 'error_message'] = error_message
        
        self.index_df.loc[mask, 'run_timestamp'] = datetime.now().isoformat()
        
        # Save the index
        self._save_index()


    def save_optimization_results(
        self,
        optimization_id: str,
        opt_response: Dict[str, Any]
    ):
        """
        Save optimization results to parquet files.
        
        Args:
            optimization_id: The optimization ID
            opt_response: Optimization response from the API
        """

        # If Optimization Error: status_code = {400, 401, 404, 500}
        if 'error' in opt_response:
            # Update status in index
            self.update_optimization_status(
                optimization_id, 
                status='FAILED',
                error_message = f"{opt_response['error']}: {opt_response['errorDescription']}"
            )


        elif optimization_id not in self.index_df['optimization_id'].values:
            raise ValueError(f"Optimization {optimization_id} not found in index")
        
        else:
            # Get paths from the index
            mask = self.index_df['optimization_id'] == optimization_id
            results_path = Path(self.index_df.loc[mask, 'results_path'].iloc[0])
            summary_path = Path(self.index_df.loc[mask, 'summary_path'].iloc[0])
            goals_path = Path(self.index_df.loc[mask, 'goals_path'].iloc[0])
            constraints_path = Path(self.index_df.loc[mask, 'constraints_path'].iloc[0])
            trades_path = Path(self.index_df.loc[mask, 'trades_path'].iloc[0])
            exceptions_path = Path(self.index_df.loc[mask, 'exceptions_path'].iloc[0])
            
            # Save API response as JSON for reference
            with open(results_path / 'api_response.json', 'w') as f:
                json.dump(opt_response, f, indent=2)
            
            # Extract and save data frames
            summary_df = self._extract_summary_df(opt_response)
            goals_df = self._extract_goals_df(opt_response)
            constraints_df = self._extract_constraints_df(opt_response)
            trades_df = self._extract_trades_df(opt_response)
            exceptions_df = self._extract_exceptions_df(opt_response)
            
            # Save dataframes
            summary_df.to_parquet(summary_path)
            goals_df.to_parquet(goals_path)
            constraints_df.to_parquet(constraints_path)
            trades_df.to_parquet(trades_path)
            exceptions_df.to_parquet(exceptions_path)
            
            # Update status in index
            self.update_optimization_status(
                optimization_id, 
                api_generated_id=opt_response.get('optimizationId', None),
                session_id=opt_response.get('sessionId', None),
                status=opt_response.get('statusCode', 'success') # default to status of success (lowercase differentiates from true SUCCESS)
            )
    
    def get_pending_optimizations(self) -> List[Dict[str, Any]]:
        """
        Get list of optimization tasks that haven't been run yet.
        
        Returns:
            List of optimization task records that have 'not_run' status
        """
        pending_df = self.index_df[self.index_df['status'] == 'not_run']
        return pending_df.to_dict('records')
    
    def get_failed_optimizations(self) -> List[Dict[str, Any]]:
        """
        Get list of optimization tasks that haven't been run yet.
        
        Returns:
            List of optimization task records that have 'not_run' status
        """
        failed_df = self.index_df[self.index_df['status'] == 'FAILED']
        return failed_df.to_dict('records')
    
    def get_successful_optimizations(self) -> pd.DataFrame:
        """
        Get all successful optimization runs.
        
        Returns:
            DataFrame of successful optimization records
        """
        return self.index_df[self.index_df['status'].apply(lambda x: x.upper()) == 'SUCCESS']
    
    def load_optimization_results(self, optimization_id: str) -> Dict[str, pd.DataFrame]:
        """
        Load the results for a specific optimization.
        
        Args:
            optimization_id: The optimization ID to load
            
        Returns:
            Dictionary containing the various result dataframes
        """
        if optimization_id not in self.index_df['optimization_id'].values:
            raise ValueError(f"Optimization {optimization_id} not found in index")
        
        mask = self.index_df['optimization_id'] == optimization_id
        
        if self.index_df.loc[mask, 'status'].iloc[0].upper() != 'SUCCESS':
            raise ValueError(f"Optimization {optimization_id} has not been successfully run")
        
        summary_path = self.index_df.loc[mask, 'summary_path'].iloc[0]
        goals_path = self.index_df.loc[mask, 'goals_path'].iloc[0]
        constraints_path = self.index_df.loc[mask, 'constraints_path'].iloc[0]
        trades_path = self.index_df.loc[mask, 'trades_path'].iloc[0]
        exceptions_path = self.index_df.loc[mask, 'exceptions_path'].iloc[0]
        
        return {
            'summary': pd.read_parquet(summary_path),
            'goals': pd.read_parquet(goals_path),
            'constraints': pd.read_parquet(constraints_path),
            'trades': pd.read_parquet(trades_path),
            'exceptions': pd.read_parquet(exceptions_path)
        }
    
    def filter_optimizations(self, **kwargs) -> pd.DataFrame:
        """
        Filter optimizations based on various criteria.
        
        Args:
            **kwargs: Key-value pairs for filtering (column_name=value)
            
        Returns:
            Filtered DataFrame of optimization records
        """
        result_df = self.index_df.copy()
        
        for key, value in kwargs.items():
            if key in result_df.columns:
                result_df = result_df[result_df[key] == value]
        
        return result_df
    

    def parse_goals_summary(self, goals_summary: str) -> List[Dict[str, Any]]:
        """
        Parse a goals summary string back into a structured format.
        
        Args:
            goals_summary: Formatted string representing goals
            
        Returns:
            List of dictionaries with goal details
        """
        if not goals_summary:
            return []
        
        goals = []
        goal_strings = goals_summary.split(';')
        
        for goal_str in goal_strings:
            parts = goal_str.split(':')
            
            if len(parts) >= 2:
                goal = {
                    'fieldCode': parts[0],
                    'action': parts[1]
                }
                
                # Add tradeoff if available
                if len(parts) >= 3:
                    try:
                        goal['tradeoff'] = float(parts[2])
                    except ValueError:
                        goal['tradeoff'] = 1.0
                
                goals.append(goal)
        
        return goals

    def filter_by_goal(self, field_code: str = None, action: str = None) -> pd.DataFrame:
        """
        Filter optimizations by goal field code and/or action.
        
        Args:
            field_code: Goal field code to filter by (optional)
            action: Goal action to filter by (optional)
            
        Returns:
            Filtered DataFrame of optimization records
        """
        # Start with all records
        result_df = self.index_df.copy()
        
        # Apply filtering if criteria are provided
        if field_code or action:
            filtered_indices = []
            
            for i, row in result_df.iterrows():
                goals_summary = row.get('goals_summary', '')
                goals = self.parse_goals_summary(goals_summary)
                
                include_row = False
                for goal in goals:
                    goal_field = goal.get('fieldCode', '')
                    goal_action = goal.get('action', '')
                    
                    field_match = not field_code or field_code in goal_field
                    action_match = not action or action == goal_action
                    
                    if field_match and action_match:
                        include_row = True
                        break
                
                if include_row:
                    filtered_indices.append(i)
            
            # Filter to include only matched rows
            result_df = result_df.loc[filtered_indices]
        
        return result_df
    

    def _extract_summary_df(self, opt_response: Dict[str, Any]) -> pd.DataFrame:
        """
        Extract summary data from optimization response.
        
        Args:
            opt_response: Optimization response from API
            
        Returns:
            DataFrame containing summary information
        """
        # Get the summary data
        summary_data = opt_response.get('summary', {})
        
        if not summary_data:
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=[
                'turnoverRate', 'tradesValue', 'buyNumber', 'buyAmount', 'buyCost',
                'sellNumber', 'sellAmount', 'sellCost'
                ])
        
        # Handle case where summary is already a dict
        if isinstance(summary_data, dict):
            return pd.DataFrame([summary_data])
        
        # Handle case where summary is a list
        if isinstance(summary_data, list):
            return pd.DataFrame(summary_data)
        
        # Fallback for unexpected format
        return pd.DataFrame([{'optimization_id': opt_response.get('optimizationId', '')}])

    def _extract_goals_df(self, opt_response: Dict[str, Any]) -> pd.DataFrame:
        """
        Extract goals results from optimization response.
        
        Args:
            opt_response: Optimization response from API
            
        Returns:
            DataFrame containing goals data
        """
        # Get the goals data
        goals_data = opt_response.get('goals', [])
        
        if not goals_data:
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=['fieldCode', 'initialValue', 'finalValue'])
        
        # Convert to DataFrame
        goals_df = pd.DataFrame(goals_data)
        
        return goals_df

    def _extract_constraints_df(self, opt_response: Dict[str, Any]) -> pd.DataFrame:
        """
        Extract constraints results from optimization response.
        
        Args:
            opt_response: Optimization response from API
            
        Returns:
            DataFrame containing constraints data
        """
        # Get the constraints data
        constraints_data = opt_response.get('constraints', [])
        
        if not constraints_data:
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=['fieldCode', 'scopeType', 'initialValue', 'finalValue', 'classificationNode'])
        
        # Convert to DataFrame
        constraints_df = pd.DataFrame(constraints_data)
        
        # If classificationNode exists, handle it
        if 'classificationNode' in constraints_df.columns:
            # Function to unpack classification node
            def unpack_classification_node(node_dict):
                if not isinstance(node_dict, dict):
                    return ''
                name = node_dict.get('classificationName', '') + ':'
                levels = ''.join(node_dict.get('levels', ['']))
                return name + levels
            
            constraints_df['classificationNode'] = constraints_df['classificationNode'].apply(unpack_classification_node)
        
        return constraints_df

    def _extract_trades_df(self, opt_response: Dict[str, Any]) -> pd.DataFrame:
        """
        Extract trades from optimization response.
        
        Args:
            opt_response: Optimization response from API
            
        Returns:
            DataFrame containing trades data
        """
        # Get the proposed trades data
        trades_data = opt_response.get('proposedTrades', [])
        
        if not trades_data:
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=[
                'instrumentUniqueId', 'ticker', 'instrumentName', 'initialWeight',
                'finalWeight', 'changedWeight', 'changedQuantity', 'changedAmount', 'transactionCost'
            ])
        
        # Convert to DataFrame
        trades_df = pd.DataFrame(trades_data)
        
        # Sort by changed weight (descending)
        if 'changedWeight' in trades_df.columns:
            trades_df = trades_df.sort_values(by='changedWeight', ascending=False)
        
        return trades_df

    def _extract_exceptions_df(self, opt_response: Dict[str, Any]) -> pd.DataFrame:
        """
        Extract exceptions from optimization response.
        
        Args:
            opt_response: Optimization response from API
            
        Returns:
            DataFrame containing exceptions data
        """
        # Get the exceptions data
        exceptions_data = opt_response.get('exceptions', [])
        
        if not exceptions_data:
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=['instrumentUniqueId', 'ticker', 'instrumentName','portfolioName','reason'])
        
        # Convert to DataFrame
        exceptions_df = pd.DataFrame(exceptions_data)
        
        return exceptions_df



