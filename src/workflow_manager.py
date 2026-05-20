# workflow_manager.py

"""
Higher-level class that:

Orchestrates the Optimization Process

Provides a simplified interface to the functions in optimization_workflow.py
Manages the overall workflow from configuration to execution to analysis


Maintains State

Keeps track of the OptimizationTracker instance
Manages configuration paths and settings


Provides User-Facing Methods

Offers methods for common user operations
Abstracts away the complexity of the individual steps
"""

import os
import argparse
import pandas as pd
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import json
import time
from datetime import datetime

from .optimization_tracker import OptimizationTracker
from .optimization_workflow import (
    register_optimization_tasks,
    run_pending_optimizations,
    get_authorization_headers,
    get_optimization_response,
    build_optimization_request,
    display_optimization_response
)
from .analysis_utils import OptimizationAnalyzer
from .visualization_dashboard import OptimizationDashboard


class OptimizationWorkflowManager:
    """
    Manages the full portfolio optimization workflow from configuration to visualization.
    """
    
    def __init__(
        self,
        config_path: str = "config/optimization_parameters.yaml",
        goal_mappings_path: str = "config/goal_mappings.yaml",
        constraint_mappings_path: str = "config/constraint_mappings.yaml",
        tasks_dir: str = "tasks",
        index_path: str = "data/optimization_index.parquet",
        results_dir: str = "data/optimization_results",
        dashboard_dir: str = "dashboards"
    ):
        """
        Initialize the workflow manager.
        
        Args:
            config_path: Path to optimization parameters YAML
            goal_mappings_path: Path to goal mappings YAML
            constraint_mappings_path: Path to constraint mappings YAML
            tasks_dir: Directory to save task JSON files
            index_path: Path to the optimization index file
            results_dir: Directory to store optimization results
            dashboard_dir: Directory to save dashboard HTML files
        """
        self.config_path = config_path
        self.goal_mappings_path = goal_mappings_path
        self.constraint_mappings_path = constraint_mappings_path
        self.tasks_dir = tasks_dir
        
        # Create the tracker
        self.tracker = OptimizationTracker(
            index_path=index_path,
            results_dir=results_dir
        )
        
        # Create analyzer and dashboard
        self.analyzer = OptimizationAnalyzer(self.tracker)
        self.dashboard = OptimizationDashboard(
            tracker=self.tracker,
            output_dir=dashboard_dir
        )
    
    def register_tasks(self) -> List[str]:
        """
        Register optimization tasks from configuration.
        
        Returns:
            List of registered optimization IDs
        """
        return register_optimization_tasks(
            config_path=self.config_path,
            goal_mappings_path=self.goal_mappings_path,
            constraint_mappings_path=self.constraint_mappings_path,
            tasks_dir=self.tasks_dir,
            tracker=self.tracker
        )
    
    def run_tasks(
        self,
        status: str = 'pending',
        max_runs: int = 5,
        delay_between_runs: int = 2,
        filter_kwargs: Optional[Dict[str, Any]] = None,
        display_results=False
    ) -> List[str]:
        """
        Run pending optimization tasks.
        
        Args:
            max_runs: Maximum number of optimizations to run
            delay_between_runs: Delay between runs in seconds
            filter_kwargs: Filtering criteria for pending tasks
            display: Whether or not to display results of each run
            
        Returns:
            List of executed optimization IDs
        """

        # Get pending optimization tasks
        if status == 'pending':
            pending_tasks = self.tracker.get_pending_optimizations()
        elif status == 'FAILED':
            pending_tasks = self.tracker.get_failed_optimizations()
        else:
            raise ValueError("Invalid Status (valid optons are pending and FAILED)")
        
        ## CAN THIS BE MADE MORE EFFIEICNT ##
        # Apply filters if specified
        if filter_kwargs:
            filtered_tasks = []
            for task in pending_tasks:
                include_task = True
                for key, value in filter_kwargs.items():
                    if key in task and task[key] != value:
                        include_task = False
                        break
                if include_task:
                    filtered_tasks.append(task)
            pending_tasks = filtered_tasks
        
        # Limit the number of runs
        tasks_to_run = pending_tasks[:max_runs]
        
        executed_ids = []
        
        for task_record in tasks_to_run:
            optimization_id = task_record['optimization_id']
            task_path = task_record['task_path']
            
            print(f"Running optimization: {optimization_id}")
            
            try:
                # Load the task from the saved JSON file
                with open(task_path, 'r') as file:
                    task = json.load(file)
                
                # Build the full optimization request
                opt_request = build_optimization_request(task)
                print(opt_request)
                
                # Submit the optimization request using our enhanced method
                opt_response = get_optimization_response(
                    optimization_request=opt_request,
                    task_optimization_id=optimization_id,
                    auth_headers=get_authorization_headers(),
                    tracker=self.tracker
                )
                
                # Save the optimization results
                self.tracker.save_optimization_results(
                    optimization_id=optimization_id,
                    opt_response=opt_response
                )
                
                if display_results:
                    # Display the results
                    display_optimization_response(self.tracker, optimization_id)
                
                executed_ids.append(optimization_id)
                
                # Add delay between runs to avoid overloading the API
                if delay_between_runs > 0 and task_record != tasks_to_run[-1]:
                    time.sleep(delay_between_runs)
                    
            except Exception as e:
                print(f"Error running optimization {optimization_id}: {str(e)}")
                
                # Update status to failed
                self.tracker.update_optimization_status(
                    optimization_id=optimization_id,
                    status='FAILED',
                    error_message=str(e)
                )
        
        return executed_ids
    
    def analyze_constraints(
        self,
        constraint_name: str,
        filter_kwargs: Optional[Dict[str, Any]] = None,
        create_dashboard: bool = True,
        show_dashboard: bool = False
    ) -> pd.DataFrame:
        """
        Analyze sensitivity of goals to a constraint.
        
        Args:
            constraint_name: Name of the constraint to analyze
            filter_kwargs: Additional filtering criteria
            create_dashboard: Whether to create a dashboard
            show_dashboard: Whether to show the dashboard in browser
            
        Returns:
            DataFrame with sensitivity analysis results
        """
        # Run the analysis
        sensitivity_df = self.analyzer.constraint_sensitivity_analysis(
            constraint_name=constraint_name,
            filter_kwargs=filter_kwargs
        )
        
        if len(sensitivity_df) == 0:
            print(f"No data available for analysis of constraint '{constraint_name}'")
            return sensitivity_df
        
        # Create a dashboard if requested
        if create_dashboard:
            dashboard_path = self.dashboard.create_constraint_sensitivity_dashboard(
                constraint_name=constraint_name,
                filter_kwargs=filter_kwargs
            )
            
            if dashboard_path and show_dashboard:
                # Open the dashboard in the default web browser
                webbrowser.open(f"file://{os.path.abspath(dashboard_path)}")
        
        return sensitivity_df
    
    def analyze_efficient_frontier(
        self,
        x_goal: str,
        y_goal: str,
        filter_kwargs: Optional[Dict[str, Any]] = None,
        create_dashboard: bool = True,
        show_dashboard: bool = False
    ) -> pd.DataFrame:
        """
        Analyze the efficient frontier between two goals.
        
        Args:
            x_goal: Name of the first goal (x-axis)
            y_goal: Name of the second goal (y-axis)
            filter_kwargs: Additional filtering criteria
            create_dashboard: Whether to create a dashboard
            show_dashboard: Whether to show the dashboard in browser
            
        Returns:
            DataFrame with efficient frontier points
        """
        # Run the analysis
        frontier_df = self.analyzer.calculate_efficient_frontier(
            x_goal=x_goal,
            y_goal=y_goal,
            filter_kwargs=filter_kwargs,
            plot=False
        )
        
        if len(frontier_df) == 0:
            print(f"No data available for efficient frontier between '{x_goal}' and '{y_goal}'")
            return frontier_df
        
        # Create a dashboard if requested
        if create_dashboard:
            dashboard_path = self.dashboard.create_efficient_frontier_dashboard(
                x_goal=x_goal,
                y_goal=y_goal,
                filter_kwargs=filter_kwargs
            )
            
            if dashboard_path and show_dashboard:
                # Open the dashboard in the default web browser
                webbrowser.open(f"file://{os.path.abspath(dashboard_path)}")
        
        return frontier_df
    
    def find_optimal_constraints(
        self,
        target_goal: str,
        optimize_direction: str = 'maximize',
        filter_kwargs: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Find optimal constraint values for a specific goal.
        
        Args:
            target_goal: Name of the goal to optimize
            optimize_direction: Direction to optimize ('maximize' or 'minimize')
            filter_kwargs: Additional filtering criteria
            
        Returns:
            DataFrame with optimal constraint values
        """
        return self.analyzer.find_optimal_constraints(
            target_goal=target_goal,
            optimize_direction=optimize_direction,
            filter_kwargs=filter_kwargs
        )
    
    def compare_optimizations(
        self,
        optimization_ids: List[str],
        create_dashboard: bool = True,
        show_dashboard: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """
        Compare multiple optimization runs.
        
        Args:
            optimization_ids: List of optimization IDs to compare
            create_dashboard: Whether to create a dashboard
            show_dashboard: Whether to show the dashboard in browser
            
        Returns:
            Dictionary with different comparison DataFrames
        """
        # Run the comparisons
        goals_comparison = self.analyzer.compare_optimizations(
            optimization_ids=optimization_ids,
            comparison_type='goals'
        )
        
        constraints_comparison = self.analyzer.compare_optimizations(
            optimization_ids=optimization_ids,
            comparison_type='constraints'
        )
        
        trades_comparison = self.analyzer.compare_optimizations(
            optimization_ids=optimization_ids,
            comparison_type='trades'
        )
        
        summary_comparison = self.analyzer.compare_optimizations(
            optimization_ids=optimization_ids,
            comparison_type='summary'
        )
        
        # Create a dashboard if requested
        if create_dashboard:
            dashboard_path = self.dashboard.create_comparison_dashboard(
                optimization_ids=optimization_ids
            )
            
            if dashboard_path and show_dashboard:
                # Open the dashboard in the default web browser
                webbrowser.open(f"file://{os.path.abspath(dashboard_path)}")
        
        return {
            'goals': goals_comparison,
            'constraints': constraints_comparison,
            'trades': trades_comparison,
            'summary': summary_comparison
        }
    
    def create_summary_dashboard(
        self,
        filter_kwargs: Optional[Dict[str, Any]] = None,
        show_dashboard: bool = False
    ) -> str:
        """
        Create a summary dashboard for all optimization results.
        
        Args:
            filter_kwargs: Filtering criteria for optimizations
            show_dashboard: Whether to show the dashboard in browser
            
        Returns:
            Path to the generated dashboard
        """
        dashboard_path = self.dashboard.create_summary_dashboard(
            filter_kwargs=filter_kwargs
        )
        
        if dashboard_path and show_dashboard:
            # Open the dashboard in the default web browser
            webbrowser.open(f"file://{os.path.abspath(dashboard_path)}")
        
        return dashboard_path
    
    def generate_report(self, output_file: str = "optimization_report.html") -> str:
        """
        Generate a comprehensive report of all optimization runs.
        
        Args:
            output_file: Path to save the HTML report
            
        Returns:
            Path to the generated report
        """
        # Get successful optimizations
        successful_df = self.tracker.filter_optimizations(status='success')
        
        # Create HTML header
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Portfolio Optimization Report</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }
                .report-container {
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                    border-radius: 5px;
                }
                h1, h2, h3 {
                    color: #2c3e50;
                }
                .section {
                    margin-bottom: 30px;
                    padding: 15px;
                    background-color: white;
                    border-radius: 5px;
                    box-shadow: 0 0 5px rgba(0,0,0,0.05);
                }
                table {
                    border-collapse: collapse;
                    width: 100%;
                    margin-top: 20px;
                }
                th, td {
                    text-align: left;
                    padding: 12px;
                    border-bottom: 1px solid #ddd;
                }
                th {
                    background-color: #f2f2f2;
                }
                tr:hover {
                    background-color: #f5f5f5;
                }
                .success { color: green; }
                .failed { color: red; }
                .running { color: blue; }
                .not-run { color: gray; }
            </style>
        </head>
        <body>
            <div class="report-container">
                <h1>Portfolio Optimization Report</h1>
                <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        """
        
        # Add summary statistics
        html += f"""
                <div class="section">
                    <h2>Summary Statistics</h2>
                    <p>Total optimizations: {len(self.tracker.index_df)}</p>
                    <p>Successful optimizations: {len(successful_df)}</p>
                    <p>Failed optimizations: {len(self.tracker.filter_optimizations(status='failed'))}</p>
                    <p>Pending optimizations: {len(self.tracker.filter_optimizations(status='not_run'))}</p>
                    <p>Portfolios: {', '.join(self.tracker.index_df['portfolio'].unique())}</p>
                    <p>Benchmarks: {', '.join(self.tracker.index_df['benchmark'].unique())}</p>
                </div>
        """
        
        # Add optimization runs table
        html += """
                <div class="section">
                    <h2>Optimization Runs</h2>
                    <table>
                        <tr>
                            <th>ID</th>
                            <th>Portfolio</th>
                            <th>Benchmark</th>
                            <th>As of Date</th>
                            <th>Risk Model</th>
                            <th>Status</th>
                            <th>Timestamp</th>
                        </tr>
        """
        
        # Add rows for each optimization
        for _, row in self.tracker.index_df.iterrows():
            status_class = {
                'success': 'success',
                'failed': 'failed',
                'running': 'running',
                'not_run': 'not-run'
            }.get(row.get('status', ''), '')
            
            html += f"""
                        <tr>
                            <td>{row.get('optimization_id', '')}</td>
                            <td>{row.get('portfolio', '')}</td>
                            <td>{row.get('benchmark', '')}</td>
                            <td>{row.get('as_of_date', '')}</td>
                            <td>{row.get('risk_model', '')}</td>
                            <td class="{status_class}">{row.get('status', '')}</td>
                            <td>{row.get('run_timestamp', '')}</td>
                        </tr>
            """
        
        html += """
                    </table>
                </div>
        """
        
        # Add links to specialized dashboards
        html += """
                <div class="section">
                    <h2>Available Dashboards</h2>
                    <h3>Summary Dashboards</h3>
                    <ul>
                        <li><a href="dashboards/summary_dashboard.html" target="_blank">Overall Summary Dashboard</a></li>
                    </ul>
                    
                    <h3>Constraint Sensitivity Dashboards</h3>
                    <ul>
        """
        
        # Get all constraint columns
        constraint_columns = [col for col in self.tracker.index_df.columns 
                            if col.startswith('max_') or col.startswith('min_')]
        
        for constraint in constraint_columns:
            dashboard_path = f"dashboards/{constraint}_sensitivity_dashboard.html"
            html += f"""
                        <li><a href="{dashboard_path}" target="_blank">Sensitivity to {constraint}</a></li>
            """
        
        html += """
                    </ul>
                </div>
        """
        
        # Close HTML tags
        html += """
            </div>
        </body>
        </html>
        """
        
        # Save the report
        with open(output_file, 'w') as f:
            f.write(html)
        
        return output_file
    
    def run_workflow(
        self,
        register: bool = True,
        run: bool = True,
        status: str = 'pending',
        max_runs: int = 5,
        generate_report: bool = True,
        show_report: bool = False
    ):
        """
        Run the full optimization workflow.
        
        Args:
            register: Whether to register optimization tasks
            run: Whether to run pending optimizations
            max_runs: Maximum number of optimizations to run
            generate_report: Whether to generate a report
            show_report: Whether to show the report in browser
            
        Returns:
            Path to the generated report if applicable
        """
        # Register tasks if requested
        if register:
            print("Registering optimization tasks...")
            registered_ids = self.register_tasks()
            print(f"Registered {len(registered_ids)} optimization tasks")
        
        # Run tasks if requested
        if run:
            print("Running pending optimizations...")
            executed_ids = self.run_tasks(status=status, max_runs=max_runs)
            print(f"Executed {len(executed_ids)} optimizations")
            # print(executed_ids)
        
        # Generate report if requested
        if generate_report:
            print("Generating optimization report...")
            report_file = self.generate_report()
            print(f"Report generated at: {report_file}")
            
            if show_report:
                # Open the report in the default web browser
                webbrowser.open(f"file://{os.path.abspath(report_file)}")
            
            return report_file
        
        return None


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run Portfolio Optimization Workflow')
    
    parser.add_argument('--register', action='store_true', help='Register optimization tasks')
    parser.add_argument('--run', action='store_true', help='Run pending optimizations')
    parser.add_argument('--status', action='store_true', help='Run pending optimizations by status')
    parser.add_argument('--max-runs', type=int, default=5, help='Maximum number of optimizations to run')
    parser.add_argument('--report', action='store_true', help='Generate optimization report')
    parser.add_argument('--show', action='store_true', help='Show the report in web browser')
    
    args = parser.parse_args()
    
    # Create the workflow manager
    manager = OptimizationWorkflowManager()
    
    # Run the workflow
    manager.run_workflow(
        register=args.register,
        run=args.run,
        status=args.status,
        max_runs=args.max_runs,
        generate_report=args.report,
        show_report=args.show
    )