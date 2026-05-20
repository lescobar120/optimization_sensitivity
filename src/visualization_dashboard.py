# visualization_dashboard.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Any
import os
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import base64
from io import BytesIO

from .optimization_tracker import OptimizationTracker
from .analysis_utils import OptimizationAnalyzer


class OptimizationDashboard:
    """
    Creates interactive dashboards for optimization results.
    """
    
    def __init__(
        self, 
        tracker: OptimizationTracker,
        output_dir: str = "dashboards"
    ):
        """
        Initialize the dashboard with a tracker.
        
        Args:
            tracker: OptimizationTracker instance
            output_dir: Directory to save dashboard HTML files
        """
        self.tracker = tracker
        self.analyzer = OptimizationAnalyzer(tracker)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_summary_dashboard(
        self,
        filter_kwargs: Optional[Dict[str, Any]] = None,
        output_file: str = "summary_dashboard.html"
    ) -> str:
        """
        Create a summary dashboard for optimization results.
        
        Args:
            filter_kwargs: Additional filtering criteria
            output_file: Output file name
            
        Returns:
            Path to the generated dashboard
        """
        # Get successful optimizations
        successful_df = self.tracker.filter_optimizations(status='success')
        
        # Apply additional filters if provided
        if filter_kwargs:
            for key, value in filter_kwargs.items():
                if key in successful_df.columns:
                    successful_df = successful_df[successful_df[key] == value]
        
        # Check if we have data
        if len(successful_df) == 0:
            print("No successful optimizations found with the specified filters")
            return ""
        
        # Generate HTML content
        html_content = self._generate_summary_html(successful_df)
        
        # Save the HTML file
        output_path = self.output_dir / output_file
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        return str(output_path)
    
    def _generate_summary_html(self, df: pd.DataFrame) -> str:
        """
        Generate HTML content for the summary dashboard.
        
        Args:
            df: DataFrame with optimization metadata
            
        Returns:
            HTML content as a string
        """
        # Create HTML header
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Portfolio Optimization Summary Dashboard</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <script src="https://d3js.org/d3.v7.min.js"></script>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }
                .dashboard-container {
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
                .chart-container {
                    margin-bottom: 30px;
                    padding: 15px;
                    background-color: white;
                    border-radius: 5px;
                    box-shadow: 0 0 5px rgba(0,0,0,0.05);
                }
                .filters {
                    margin-bottom: 20px;
                    padding: 15px;
                    background-color: #f9f9f9;
                    border-radius: 5px;
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
            <div class="dashboard-container">
                <h1>Portfolio Optimization Summary Dashboard</h1>
        """
        
        # Add summary statistics
        html += f"""
                <div class="chart-container">
                    <h2>Summary Statistics</h2>
                    <p>Total optimizations: {len(df)}</p>
                    <p>Portfolios: {', '.join(df['portfolio'].unique())}</p>
                    <p>Benchmarks: {', '.join(df['benchmark'].unique())}</p>
                    <p>As of dates: {', '.join(df['as_of_date'].unique())}</p>
                </div>
        """
        
        # Add optimization runs table
        html += """
                <div class="chart-container">
                    <h2>Optimization Runs</h2>
                    <table>
                        <tr>
                            <th>ID</th>
                            <th>Portfolio</th>
                            <th>Benchmark</th>
                            <th>As of Date</th>
                            <th>Risk Model</th>
                            <th>Max Active Risk</th>
                            <th>Max Positions</th>
                            <th>Max Turnover</th>
                            <th>Status</th>
                            <th>Timestamp</th>
                        </tr>
        """
        
        # Add rows for each optimization
        for _, row in df.iterrows():
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
                            <td>{row.get('max_active_risk', '')}</td>
                            <td>{row.get('max_positions', '')}</td>
                            <td>{row.get('max_turnover', '')}</td>
                            <td class="{status_class}">{row.get('status', '')}</td>
                            <td>{row.get('run_timestamp', '')}</td>
                        </tr>
            """
        
        html += """
                    </table>
                </div>
        """
        
        # Add constraint distribution visualization (if possible)
        constraint_columns = [col for col in df.columns 
                             if col.startswith('max_') or col.startswith('min_')]
        
        if constraint_columns:
            # Generate bar charts for each constraint
            for constraint in constraint_columns:
                if constraint in df.columns:
                    # Skip if all values are None/NaN
                    if df[constraint].isna().all():
                        continue
                    
                    # Calculate frequency of each value
                    value_counts = df[constraint].value_counts().reset_index()
                    value_counts.columns = ['value', 'count']
                    
                    # Create a plotly bar chart
                    fig = go.Figure(data=[
                        go.Bar(
                            x=value_counts['value'],
                            y=value_counts['count'],
                            text=value_counts['count'],
                            textposition='auto'
                        )
                    ])
                    
                    fig.update_layout(
                        title=f'Distribution of {constraint}',
                        xaxis_title=constraint,
                        yaxis_title='Count',
                        height=400
                    )
                    
                    plot_div = fig.to_html(full_html=False, include_plotlyjs=False)
                    
                    html += f"""
                    <div class="chart-container">
                        <h2>Distribution of {constraint}</h2>
                        {plot_div}
                    </div>
                    """
        
        # Close HTML tags
        html += """
            </div>
            <script>
                // Add any JavaScript here for interactivity
            </script>
        </body>
        </html>
        """
        
        return html
    
    def create_constraint_sensitivity_dashboard(
        self,
        constraint_name: str,
        filter_kwargs: Optional[Dict[str, Any]] = None,
        output_file: Optional[str] = None
    ) -> str:
        """
        Create a dashboard visualizing the sensitivity to a constraint.
        
        Args:
            constraint_name: Name of the constraint to analyze
            filter_kwargs: Additional filtering criteria
            output_file: Output file name (if None, uses constraint name)
            
        Returns:
            Path to the generated dashboard
        """
        # Use constraint name for output file if not specified
        if output_file is None:
            output_file = f"{constraint_name}_sensitivity_dashboard.html"
        
        # Get sensitivity analysis data
        sensitivity_df = self.analyzer.constraint_sensitivity_analysis(
            constraint_name=constraint_name,
            filter_kwargs=filter_kwargs
        )
        
        if len(sensitivity_df) == 0:
            print("No data available for sensitivity analysis")
            return ""
        
        # Generate HTML content
        html_content = self._generate_sensitivity_html(sensitivity_df, constraint_name)
        
        # Save the HTML file
        output_path = self.output_dir / output_file
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        return str(output_path)
    
    def _generate_sensitivity_html(
        self,
        sensitivity_df: pd.DataFrame,
        constraint_name: str
    ) -> str:
        """
        Generate HTML content for the sensitivity dashboard.
        
        Args:
            sensitivity_df: DataFrame with sensitivity analysis results
            constraint_name: Name of the constraint being analyzed
            
        Returns:
            HTML content as a string
        """
        # Create HTML header
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Constraint Sensitivity Dashboard</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }
                .dashboard-container {
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
                .chart-container {
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
            </style>
        </head>
        <body>
            <div class="dashboard-container">
                <h1>Sensitivity to {constraint_name}</h1>
        """
        
        # Extract constraint values (column names except the index columns)
        constraint_values = [col for col in sensitivity_df.columns 
                            if col not in ['portfolio', 'benchmark', 'as_of_date', 'goal_name']]
        
        # Convert constraint values to numeric if possible
        constraint_values_numeric = []
        for val in constraint_values:
            try:
                constraint_values_numeric.append(float(val))
            except:
                constraint_values_numeric.append(val)
        
        # Create a line chart for each goal
        for i, (_, row) in enumerate(sensitivity_df.iterrows()):
            goal = row['goal_name']
            portfolio = row['portfolio']
            benchmark = row['benchmark']
            title = f"{goal} ({portfolio}/{benchmark})"
            
            # Extract y values for this goal
            y_values = [row[val] for val in constraint_values]
            
            # Create a plotly line chart
            fig = go.Figure(data=[
                go.Scatter(
                    x=constraint_values,
                    y=y_values,
                    mode='lines+markers',
                    name=title
                )
            ])
            
            fig.update_layout(
                title=title,
                xaxis_title=constraint_name,
                yaxis_title='Goal Value',
                height=400
            )
            
            plot_div = fig.to_html(full_html=False, include_plotlyjs=False)
            
            html += f"""
                <div class="chart-container">
                    <h2>{title}</h2>
                    {plot_div}
                </div>
            """
        
        # Add raw data table
        html += """
                <div class="chart-container">
                    <h2>Raw Data</h2>
                    <table>
                        <tr>
                            <th>Portfolio</th>
                            <th>Benchmark</th>
                            <th>Goal</th>
        """
        
        # Add column headers for constraint values
        for val in constraint_values:
            html += f"""
                            <th>{val}</th>
            """
        
        html += """
                        </tr>
        """
        
        # Add rows for each goal
        for _, row in sensitivity_df.iterrows():
            html += f"""
                        <tr>
                            <td>{row['portfolio']}</td>
                            <td>{row['benchmark']}</td>
                            <td>{row['goal_name']}</td>
            """
            
            # Add cells for constraint values
            for val in constraint_values:
                cell_value = row[val] if pd.notna(row[val]) else ""
                html += f"""
                            <td>{cell_value}</td>
                """
            
            html += """
                        </tr>
            """
        
        html += """
                    </table>
                </div>
        """
        
        # Close HTML tags
        html += """
            </div>
            <script>
                // Add any JavaScript here for interactivity
            </script>
        </body>
        </html>
        """
        
        return html
    
    def create_efficient_frontier_dashboard(
        self,
        x_goal: str,
        y_goal: str,
        filter_kwargs: Optional[Dict[str, Any]] = None,
        output_file: Optional[str] = None
    ) -> str:
        """
        Create a dashboard visualizing the efficient frontier.
        
        Args:
            x_goal: Name of the first goal (x-axis)
            y_goal: Name of the second goal (y-axis)
            filter_kwargs: Additional filtering criteria
            output_file: Output file name (if None, generates based on goals)
            
        Returns:
            Path to the generated dashboard
        """
        # Generate output file name if not specified
        if output_file is None:
            output_file = f"efficient_frontier_{x_goal}_{y_goal}.html"
        
        # Get efficient frontier data
        frontier_df = self.analyzer.calculate_efficient_frontier(
            x_goal=x_goal,
            y_goal=y_goal,
            filter_kwargs=filter_kwargs,
            plot=False
        )
        
        if len(frontier_df) == 0:
            print(f"No data available for efficient frontier between {x_goal} and {y_goal}")
            return ""
        
        # Generate HTML content
        html_content = self._generate_frontier_html(frontier_df, x_goal, y_goal)
        
        # Save the HTML file
        output_path = self.output_dir / output_file
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        return str(output_path)
    
    def _generate_frontier_html(
        self,
        frontier_df: pd.DataFrame,
        x_goal: str,
        y_goal: str
    ) -> str:
        """
        Generate HTML content for the efficient frontier dashboard.
        
        Args:
            frontier_df: DataFrame with frontier points
            x_goal: Name of the x-axis goal
            y_goal: Name of the y-axis goal
            
        Returns:
            HTML content as a string
        """
        # Create HTML header
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Efficient Frontier Dashboard</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }
                .dashboard-container {
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
                .chart-container {
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
                .selected {
                    background-color: #e3f2fd;
                }
            </style>
        </head>
        <body>
            <div class="dashboard-container">
                <h1>Efficient Frontier: {y_goal} vs {x_goal}</h1>
        """
        
        # Create a scatter plot for the frontier
        fig = go.Figure()
        
        # Add data points
        fig.add_trace(go.Scatter(
            x=frontier_df['x_value'],
            y=frontier_df['y_value'],
            mode='markers',
            marker=dict(
                size=10,
                color='royalblue',
                line=dict(width=2, color='darkblue')
            ),
            text=[f"ID: {id}<br>Portfolio: {port}<br>Benchmark: {bench}" 
                  for id, port, bench in zip(
                      frontier_df['optimization_id'], 
                      frontier_df['portfolio'], 
                      frontier_df['benchmark']
                  )],
            hoverinfo='text',
            customdata=frontier_df.index  # Store row indices for interactivity
        ))
        
        # Customize the layout
        fig.update_layout(
            title=f"Efficient Frontier: {y_goal} vs {x_goal}",
            xaxis_title=x_goal,
            yaxis_title=y_goal,
            hovermode='closest',
            height=600,
            showlegend=False
        )
        
        # Convert to HTML
        plot_div = fig.to_html(
            full_html=False, 
            include_plotlyjs=False,
            config={'responsive': True}
        )
        
        # Add the plot to HTML
        html += f"""
            <div class="chart-container">
                <h2>Efficient Frontier</h2>
                {plot_div}
                <p>Click on points to view details below.</p>
            </div>
        """
        
        # Add table with frontier points
        html += """
            <div class="chart-container">
                <h2>Frontier Points</h2>
                <table id="frontierTable">
                    <thead>
                        <tr>
                            <th>Optimization ID</th>
                            <th>Portfolio</th>
                            <th>Benchmark</th>
                            <th>As of Date</th>
                            <th>X Goal</th>
                            <th>Y Goal</th>
                            <th>X Value</th>
                            <th>Y Value</th>
        """
        
        # Add constraint columns to table header
        constraint_columns = [col for col in frontier_df.columns 
                             if col.startswith('max_') or col.startswith('min_')]
        
        for col in constraint_columns:
            html += f"""
                            <th>{col}</th>
            """
        
        html += """
                        </tr>
                    </thead>
                    <tbody>
        """
        
        # Add rows for each point
        for i, row in frontier_df.iterrows():
            html += f"""
                        <tr id="row-{i}" data-index="{i}">
                            <td>{row['optimization_id']}</td>
                            <td>{row['portfolio']}</td>
                            <td>{row['benchmark']}</td>
                            <td>{row['as_of_date']}</td>
                            <td>{row['x_goal']}</td>
                            <td>{row['y_goal']}</td>
                            <td>{row['x_value']}</td>
                            <td>{row['y_value']}</td>
            """
            
            # Add constraint values
            for col in constraint_columns:
                cell_value = row[col] if col in row and pd.notna(row[col]) else ""
                html += f"""
                            <td>{cell_value}</td>
                """
            
            html += """
                        </tr>
            """
        
        html += """
                    </tbody>
                </table>
            </div>
        """
        
        # Add JavaScript for interactivity
        html += """
            <script>
                // Add interactivity - highlight rows when clicking on points
                var plot = document.querySelector('.js-plotly-plot');
                
                if (plot) {
                    plot.on('plotly_click', function(data) {
                        // Get the point index from customdata
                        var pointIndex = data.points[0].customdata;
                        
                        // Remove highlighting from all rows
                        var allRows = document.querySelectorAll('#frontierTable tbody tr');
                        allRows.forEach(row => row.classList.remove('selected'));
                        
                        // Highlight the selected row
                        var selectedRow = document.querySelector('#row-' + pointIndex);
                        if (selectedRow) {
                            selectedRow.classList.add('selected');
                            // Scroll to the selected row
                            selectedRow.scrollIntoView({behavior: 'smooth', block: 'center'});
                        }
                    });
                }
                
                // Also allow clicking on table rows to highlight
                var tableRows = document.querySelectorAll('#frontierTable tbody tr');
                tableRows.forEach(row => {
                    row.addEventListener('click', function() {
                        // Remove highlighting from all rows
                        tableRows.forEach(r => r.classList.remove('selected'));
                        
                        // Highlight the clicked row
                        this.classList.add('selected');
                    });
                });
            </script>
        """
        
        # Close HTML tags
        html += """
            </div>
        </body>
        </html>
        """
        
        return html
    
    def create_comparison_dashboard(
        self,
        optimization_ids: List[str],
        output_file: Optional[str] = None
    ) -> str:
        """
        Create a dashboard comparing multiple optimization runs.
        
        Args:
            optimization_ids: List of optimization IDs to compare
            output_file: Output file name (if None, generates based on IDs)
            
        Returns:
            Path to the generated dashboard
        """
        # Generate output file name if not specified
        if output_file is None:
            # Use a shortened version of the first few IDs
            id_str = "_".join([opt_id[:8] for opt_id in optimization_ids[:3]])
            if len(optimization_ids) > 3:
                id_str += f"_and_{len(optimization_ids) - 3}_more"
            output_file = f"comparison_{id_str}.html"
        
        # Get comparison data for different aspects
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
        
        # Get metadata for these optimizations
        metadata = self.tracker.index_df[
            self.tracker.index_df['optimization_id'].isin(optimization_ids)
        ]
        
        # Generate HTML content
        html_content = self._generate_comparison_html(
            metadata=metadata,
            goals_comparison=goals_comparison,
            constraints_comparison=constraints_comparison,
            trades_comparison=trades_comparison
        )
        
        # Save the HTML file
        output_path = self.output_dir / output_file
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        return str(output_path)
    
    def _generate_comparison_html(
        self,
        metadata: pd.DataFrame,
        goals_comparison: pd.DataFrame,
        constraints_comparison: pd.DataFrame,
        trades_comparison: pd.DataFrame
    ) -> str:
        """
        Generate HTML content for the comparison dashboard.
        
        Args:
            metadata: DataFrame with optimization metadata
            goals_comparison: DataFrame with goals comparison
            constraints_comparison: DataFrame with constraints comparison
            trades_comparison: DataFrame with trades comparison
            
        Returns:
            HTML content as a string
        """
        # Create HTML header
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Optimization Comparison Dashboard</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }
                .dashboard-container {
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
                .chart-container {
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
                .tab {
                    overflow: hidden;
                    border: 1px solid #ccc;
                    background-color: #f1f1f1;
                    border-radius: 5px 5px 0 0;
                }
                .tab button {
                    background-color: inherit;
                    float: left;
                    border: none;
                    outline: none;
                    cursor: pointer;
                    padding: 14px 16px;
                    transition: 0.3s;
                    font-size: 16px;
                }
                .tab button:hover {
                    background-color: #ddd;
                }
                .tab button.active {
                    background-color: #ccc;
                }
                .tabcontent {
                    display: none;
                    padding: 6px 12px;
                    border: 1px solid #ccc;
                    border-top: none;
                    border-radius: 0 0 5px 5px;
                    animation: fadeEffect 1s;
                }
                @keyframes fadeEffect {
                    from {opacity: 0;}
                    to {opacity: 1;}
                }
            </style>
        </head>
        <body>
            <div class="dashboard-container">
                <h1>Optimization Comparison Dashboard</h1>
        """
        
        # Add summary of optimizations being compared
        html += """
                <div class="chart-container">
                    <h2>Optimizations Being Compared</h2>
                    <table>
                        <tr>
                            <th>Optimization ID</th>
                            <th>Portfolio</th>
                            <th>Benchmark</th>
                            <th>As of Date</th>
                            <th>Risk Model</th>
        """
        
        # Add constraint columns to header
        constraint_columns = [col for col in metadata.columns 
                             if col.startswith('max_') or col.startswith('min_')]
        
        for col in constraint_columns:
            html += f"""
                            <th>{col}</th>
            """
        
        html += """
                        </tr>
        """
        
        # Add rows for each optimization
        for _, row in metadata.iterrows():
            html += f"""
                        <tr>
                            <td>{row['optimization_id']}</td>
                            <td>{row['portfolio']}</td>
                            <td>{row['benchmark']}</td>
                            <td>{row['as_of_date']}</td>
                            <td>{row['risk_model']}</td>
            """
            
            # Add constraint values
            for col in constraint_columns:
                cell_value = row[col] if col in row and pd.notna(row[col]) else ""
                html += f"""
                            <td>{cell_value}</td>
                """
            
            html += """
                        </tr>
            """
        
        html += """
                    </table>
                </div>
        """
        
        # Add tabs for different comparisons
        html += """
                <div class="tab">
                    <button class="tablinks active" onclick="openTab(event, 'GoalsTab')">Goals</button>
                    <button class="tablinks" onclick="openTab(event, 'ConstraintsTab')">Constraints</button>
                    <button class="tablinks" onclick="openTab(event, 'TradesTab')">Trades</button>
                </div>
        """
        
        # Add Goals tab content
        html += """
                <div id="GoalsTab" class="tabcontent" style="display: block;">
                    <h2>Goals Comparison</h2>
        """
        
        # Add goals comparison chart if data exists
        if len(goals_comparison) > 0:
            # Create a grouped bar chart for goals
            fig = go.Figure()
            
            # Extract unique goal names
            goal_names = goals_comparison['goal_name'].unique()
            
            # Add bars for each optimization
            for opt_id in metadata['optimization_id']:
                opt_data = goals_comparison[goals_comparison['optimization_id'] == opt_id]
                
                # Skip if no data for this optimization
                if len(opt_data) == 0:
                    continue
                
                # Add a trace for this optimization
                fig.add_trace(go.Bar(
                    name=opt_id,
                    x=opt_data['goal_name'],
                    y=opt_data['goal_value'],
                    text=opt_data['goal_value'],
                    textposition='auto'
                ))
            
            # Customize layout
            fig.update_layout(
                title='Goal Values by Optimization',
                xaxis_title='Goal',
                yaxis_title='Value',
                barmode='group',
                height=500
            )
            
            # Convert to HTML
            plot_div = fig.to_html(
                full_html=False, 
                include_plotlyjs=False,
                config={'responsive': True}
            )
            
            # Add the plot to HTML
            html += f"""
                <div class="chart-container">
                    {plot_div}
                </div>
            """
            
            # Add table with detailed data
            html += """
                <h3>Goal Details</h3>
                <table>
                    <tr>
                        <th>Optimization ID</th>
                        <th>Goal</th>
                        <th>Value</th>
                        <th>Achievement (%)</th>
                    </tr>
            """
            
            # Add rows for each goal
            for _, row in goals_comparison.iterrows():
                html += f"""
                    <tr>
                        <td>{row['optimization_id']}</td>
                        <td>{row['goal_name']}</td>
                        <td>{row['goal_value']}</td>
                        <td>{row.get('goal_achievement', '')}</td>
                    </tr>
                """
            
            html += """
                </table>
            """
        else:
            html += """
                <p>No goals comparison data available.</p>
            """
        
        html += """
                </div>
        """
        
        # Add Constraints tab content
        html += """
                <div id="ConstraintsTab" class="tabcontent">
                    <h2>Constraints Comparison</h2>
        """
        
        # Add constraints comparison chart if data exists
        if len(constraints_comparison) > 0:
            # Create a grouped bar chart for constraints
            fig = go.Figure()
            
            # Extract unique constraint names
            constraint_names = constraints_comparison['constraint_name'].unique()
            
            # Add bars for each optimization
            for opt_id in metadata['optimization_id']:
                opt_data = constraints_comparison[constraints_comparison['optimization_id'] == opt_id]
                
                # Skip if no data for this optimization
                if len(opt_data) == 0:
                    continue
                
                # Add a trace for this optimization
                fig.add_trace(go.Bar(
                    name=opt_id,
                    x=opt_data['constraint_name'],
                    y=opt_data['constraint_achieved'],
                    text=opt_data['constraint_achieved'],
                    textposition='auto'
                ))
            
            # Customize layout
            fig.update_layout(
                title='Constraint Achievement by Optimization',
                xaxis_title='Constraint',
                yaxis_title='Achieved Value',
                barmode='group',
                height=500
            )
            
            # Convert to HTML
            plot_div = fig.to_html(
                full_html=False, 
                include_plotlyjs=False,
                config={'responsive': True}
            )
            
            # Add the plot to HTML
            html += f"""
                <div class="chart-container">
                    {plot_div}
                </div>
            """
            
            # Add table with detailed data
            html += """
                <h3>Constraint Details</h3>
                <table>
                    <tr>
                        <th>Optimization ID</th>
                        <th>Constraint</th>
                        <th>Type</th>
                        <th>Target</th>
                        <th>Achieved</th>
                        <th>Binding</th>
                    </tr>
            """
            
            # Add rows for each constraint
            for _, row in constraints_comparison.iterrows():
                binding = row.get('constraint_binding', '')
                binding_text = 'Yes' if binding == True else 'No' if binding == False else ''
                
                html += f"""
                    <tr>
                        <td>{row['optimization_id']}</td>
                        <td>{row['constraint_name']}</td>
                        <td>{row['constraint_type']}</td>
                        <td>{row.get('constraint_target', '')}</td>
                        <td>{row.get('constraint_achieved', '')}</td>
                        <td>{binding_text}</td>
                    </tr>
                """
            
            html += """
                </table>
            """
        else:
            html += """
                <p>No constraints comparison data available.</p>
            """
        
        html += """
                </div>
        """
        
        # Add Trades tab content
        html += """
                <div id="TradesTab" class="tabcontent">
                    <h2>Trades Comparison</h2>
        """
        
        # Add trades comparison if data exists
        if len(trades_comparison) > 0:
            # Create a treemap for trade weights by security
            fig = px.treemap(
                trades_comparison,
                path=['optimization_id', 'security_id'],
                values='trade_value',
                color='trade_weight',
                color_continuous_scale='RdBu',
                color_continuous_midpoint=0,
                title='Trade Values by Security and Optimization'
            )
            
            # Customize layout
            fig.update_layout(
                height=600,
                margin=dict(t=50, l=25, r=25, b=25)
            )
            
            # Convert to HTML
            plot_div = fig.to_html(
                full_html=False, 
                include_plotlyjs=False,
                config={'responsive': True}
            )
            
            # Add the plot to HTML
            html += f"""
                <div class="chart-container">
                    {plot_div}
                </div>
            """
            
            # Add table with top trades
            html += """
                <h3>Top Trades by Absolute Value</h3>
                <table>
                    <tr>
                        <th>Optimization ID</th>
                        <th>Security ID</th>
                        <th>Security Name</th>
                        <th>Current Weight</th>
                        <th>Target Weight</th>
                        <th>Trade Weight</th>
                        <th>Trade Value</th>
                    </tr>
            """
            
            # Sort trades by absolute value and take top 20
            top_trades = trades_comparison.copy()
            top_trades['abs_trade_value'] = top_trades['trade_value'].abs()
            top_trades = top_trades.sort_values('abs_trade_value', ascending=False).head(20)
            
            # Add rows for each trade
            for _, row in top_trades.iterrows():
                html += f"""
                    <tr>
                        <td>{row['optimization_id']}</td>
                        <td>{row['security_id']}</td>
                        <td>{row['security_name']}</td>
                        <td>{row['current_weight']}</td>
                        <td>{row['target_weight']}</td>
                        <td>{row['trade_weight']}</td>
                        <td>{row['trade_value']}</td>
                    </tr>
                """
            
            html += """
                </table>
            """
        else:
            html += """
                <p>No trades comparison data available.</p>
            """
        
        html += """
                </div>
        """
        
        # Add JavaScript for tab functionality
        html += """
            <script>
                function openTab(evt, tabName) {
                    var i, tabcontent, tablinks;
                    
                    // Hide all tab content
                    tabcontent = document.getElementsByClassName("tabcontent");
                    for (i = 0; i < tabcontent.length; i++) {
                        tabcontent[i].style.display = "none";
                    }
                    
                    // Remove active class from all tab buttons
                    tablinks = document.getElementsByClassName("tablinks");
                    for (i = 0; i < tablinks.length; i++) {
                        tablinks[i].className = tablinks[i].className.replace(" active", "");
                    }
                    
                    // Show current tab and set button as active
                    document.getElementById(tabName).style.display = "block";
                    evt.currentTarget.className += " active";
                }
            </script>
        """
        
        # Close HTML tags
        html += """
            </div>
        </body>
        </html>
        """
        
        return html