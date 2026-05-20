# optimization_exec_summary.py

import ipywidgets as ipw
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# You'll also need to import your own classes
from .optimization_tracker import OptimizationTracker
from .analysis_utils import OptimizationAnalyzer


class OptimizationExecutiveDashboard:
    """
    Executive summary dashboard providing optimization status, metrics, and activity overview.
    """
    
    def __init__(self, tracker, analyzer=None):
        """
        Initialize the executive summary dashboard.
        
        Args:
            tracker: OptimizationTracker instance
            analyzer: OptimizationAnalyzer instance (optional)
        """
        self.tracker = tracker
        self.analyzer = analyzer
        
        # Load initial data
        self._load_data()
        
        # Build dashboard components
        self._build_components()
        
        # Create run buttons and bind callbacks
        self._create_run_buttons()
        
        # Assemble the dashboard layout
        self.dashboard_view = self._create_dashboard_layout()
    
    def _load_data(self):
        """Load and prepare the data needed for the dashboard"""

        # Status summary
        self.optimization_status_frame = self.tracker.index_df.groupby('status').count()['optimization_id'].to_frame()
        
        # Count metrics
        self.num_registered = self.tracker.index_df.shape[0]
        self.num_successful = self.tracker.get_successful_optimizations().shape[0]
        self.num_pending = len(self.tracker.get_pending_optimizations())
        self.num_failed = len(self.tracker.get_failed_optimizations())
        
        # Constraint combinations
        constraints = ['max_active_risk', 'max_positions', 'max_turnover', 'max_security_weight']
        self.constraint_combinations_frame = pd.pivot_table(
            data=self.tracker.index_df,
            index='status',
            columns=constraints,
            values='optimization_id',
            aggfunc='count',
            fill_value=0
        ).T
        
        # Failed optimizations
        self.failed_optimizations_frame = pd.DataFrame(self.tracker.get_failed_optimizations())
    
    def _build_components(self):
        """Build all dashboard components."""
        # Health status donut chart
        self.health_fig = self._build_optimization_health_fig()
        
        # Count metrics HTML components
        self.count_metrics = self._create_count_metrics()
        
        # Constraint combination accordion
        self.constraint_combo_components = self._create_constraint_combo_components()
        
        # Recent activity timeline
        self.recent_activity_plot = self._build_recent_activity_plot()
        
        # Cumulative optimizations chart
        self.cumulative_plot = self._build_cumulative_optimizations_plot()
        
        # Failed optimizations accordion
        self.failed_optimizations_accordion = self._create_failed_optimizations_accordion()
    
    def _create_count_metrics(self):
        """Create HTML components for count metrics."""
        return {
            'registered': ipw.HTML(
                f"<h3># of Registered Optimizations: {self.num_registered}</h3>",
                layout={'height': '35px'}
            ),
            'successful': ipw.HTML(
                f"<h3># of Successful Optimizations: {self.num_successful}</h3>",
                layout={'height': '35px'}
            ),
            'pending': ipw.HTML(
                f"<h3># of Pending Optimizations: {self.num_pending}</h3>",
                layout={'height': '35px'}
            ),
            'failed': ipw.HTML(
                f"<h3># of Failed Optimizations: {self.num_failed}</h3>",
                layout={'height': '35px'}
            )
        }
    
    def _create_constraint_combo_components(self):
        """Create components for constraint combinations"""

        # Header
        summary_html = ipw.HTML("<h2>Optimization Runs by Constraint Thresholds</h2>")
        
        # Create accordion items for each active risk enum
        active_risk_enums = sorted(
            self.constraint_combinations_frame.reset_index(level=0)['max_active_risk'].unique())
        
        accordion_items = []
        for active_risk in active_risk_enums:
            df = self.constraint_combinations_frame.loc[(active_risk), :]
            accordion_items.append(ipw.HTML(df.to_html()))
        
        # Create accordion
        accordion = ipw.Accordion(children=accordion_items)
        for i, active_risk in enumerate(active_risk_enums):
            accordion.set_title(i, f"Active Total Risk = {active_risk}")
        accordion.selected_index = None
        
        return {
            'summary_html': summary_html,
            'accordion': accordion
        }
    
    def _create_failed_optimizations_accordion(self):
        """Create accordion for failed optimizations"""

        if self.failed_optimizations_frame.empty:
            content = ipw.HTML("<p>No failed optimizations</p>")
        else:
            content = ipw.HTML(self.failed_optimizations_frame.to_html())
        
        accordion = ipw.Accordion(children=[content])
        accordion.set_title(0, 'Optimization Run Errors')
        accordion.selected_index = None
        
        return accordion
    
    def _create_run_buttons(self):
        """Create and bind the run buttons"""

        self.run_pending_btn = ipw.Button(
            description='Run Pending Optimizations',
            layout={'width': 'initial'},
            button_style='info'
        )
        
        self.run_failed_btn = ipw.Button(
            description='Run Failed Optimizations',
            layout={'width': 'initial'},
            button_style='warning'
        )
        
        # Bind callbacks
        self.run_pending_btn.on_click(self._run_pending_optimizations)
        self.run_failed_btn.on_click(self._run_failed_optimizations)
    
    def _run_pending_optimizations(self, _):
        """Handler for running pending optimizations"""
        # Replace with appropriate functionality
        print("Running pending optimizations...")
        # workflow_mngr.run_tasks(status='pending', max_runs=5)
        
        # Refresh dashboard after running
        self.refresh()
    
    def _run_failed_optimizations(self, _):
        """Handler for running failed optimizations"""
        # Replace with appropriate functionality
        print("Running failed optimizations...")
        # workflow_mngr.run_tasks(status='FAILED', max_runs=5)
        
        # Refresh dashboard after running
        self.refresh()
    
    def _create_dashboard_layout(self):
        """Create the main dashboard layout."""
        return ipw.VBox([
            # Top row: Health, Constraint Combinations, Cumulative Chart
            ipw.HBox([
                # Optimization Health
                self.health_fig,
                ipw.HBox(layout={'width': '40px'}),
                # Optimization Runs by Constraint Thresholds
                ipw.VBox([
                    self.constraint_combo_components['summary_html'],
                    ipw.VBox(layout={'height': '15px'}),
                    self.constraint_combo_components['accordion']
                ]),
                ipw.HBox(layout={'width': '40px'}),
                # Cumulative Optimization Runs
                self.cumulative_plot
            ], layout={
                'align_items': 'flex-start',
                'justify_content': 'space-between',
                'padding': '0px 100px 0px 0px'
            }),
            
            ipw.VBox(layout={'height': '20px'}),
            
            # Count metrics
            ipw.HBox([
                self.count_metrics['registered'],
                self.count_metrics['successful'],
                self.count_metrics['pending'],
                self.count_metrics['failed']
            ], layout={
                'justify_content': 'space-between',
                'padding': '0px 100px 0px 100px'
            }),
            
            ipw.VBox(layout={'height': '40px'}),
            
            # Recent Activity
            ipw.VBox([
                self.recent_activity_plot
            ], layout={
                'border': '1px solid lightgrey',
                'padding': '0px 100px 0px 20px'
            }),
            
            ipw.VBox(layout={'height': '20px'}),
            
            # Optimization Run Errors
            ipw.VBox([
                self.failed_optimizations_accordion
            ], layout={
                'padding': '0px 50px 0px 50px'
            }),
            
            ipw.VBox(layout={'height': '20px'}),
            
            # Optimization Run Buttons
            ipw.HBox([
                self.run_pending_btn,
                self.run_failed_btn
            ], layout={
                'padding': '0px 50px 0px 50px'
            }),
            
            ipw.VBox(layout={'height': '20px'})
        ])
    
    def refresh(self):
        """Refresh the dashboard with updated data"""

        # Reload data
        self._load_data()
        
        # Rebuild components
        self._build_components()
        
        # Update the layout
        self.dashboard_view = self._create_dashboard_layout()
    
    def get_view(self):
        """Return the dashboard view"""
        return self.dashboard_view
    
    # Placeholder methods for the visualization functions
    # These would be implemented similar to their counterparts in plot_manager.py
    
    def _build_optimization_health_fig(self):
        """Build the optimization health donut chart"""

        frame = self.optimization_status_frame
        frame['color'] = 'grey'
        frame.loc['FAILED','color'] = '#e74c3c'
        frame.loc['success','color'] = '#2ecc71'

        values = list(frame['optimization_id'])
        labels = list(frame.index)
        colors = list(frame['color'])

        # Calculate the percentage for the center
        success_percentage = frame.loc['success','optimization_id'] / sum(values) * 100

        # Create the donut chart
        fig = go.Figure(data=[go.Pie(
            values=values,
            labels=labels,
            hole=0.7,  # This makes it a donut chart (0.7 = 70% hole)
            marker_colors=colors,
            textinfo='label+percent',
            textposition='outside',
            pull=[0.02, 0]  # Slightly pull out the success segment
        )])

        # Add the number in the center
        fig.add_annotation(
            text=f"{success_percentage:.1f}%",
            x=0.5,
            y=0.5,  
            font_size=40,
            showarrow=False,
            font_color='#2c3e50'
        )

        # Add a subtitle below the percentage
        fig.add_annotation(
            text="Success Rate",
            x=0.5,
            y=0.4,
            font_size=16,
            showarrow=False,
            font_color='#7f8c8d'
        )

        # Update layout
        fig.update_layout(
            title={
                'text': 'Optimization Health Status',
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.3,
                xanchor="center",
                x=0.5
            ),
            margin=dict(t=100, b=100, l=50, r=50),
            width=500,
            height=500
        )

        fig_box = go.FigureWidget(fig)

        return fig_box
    
    def _build_recent_activity_plot(self, num_recent=10):
        """Build the recent activity timeline plot"""

        frame = self.tracker.index_df.copy()
        frame = frame.sort_values('run_timestamp',ascending=False)
        frame = frame.reset_index(drop=True)
        df = frame.iloc[:num_recent,:].copy()
        df['run_timestamp'] = pd.to_datetime(df['run_timestamp'])

        # Define colors for different statuses
        status_colors = {
            'success': '#2ecc71',  # Green
            'FAILED': '#e74c3c',   # Red
            'RUNNING': '#3498db',  # Blue
            'PENDING': '#95a5a6'   # Gray
        }

        # Create timeline visualization
        fig = go.Figure()

        # Add timeline markers
        for idx, row in df.iterrows():
            # Prepare hover text
            hover_text = f"ID: {row['optimization_id']}<br>Time: {row['run_timestamp'].strftime('%Y-%m-%d %H:%M:%S')}<br>Status: {row['status']}"
            if pd.notna(row['error_message']):
                hover_text += f"<br>Error: {row['error_message']}"
            
            # Add the marker
            fig.add_trace(go.Scatter(
                x=[row['run_timestamp']],
                y=[1],  # All markers on the same horizontal line
                mode='markers',
                marker=dict(
                    size=19,
                    color=status_colors[row['status']],
                    symbol='circle',
                    line=dict(width=2, color='white')
                ),
                name=row['status'],
                hovertext=hover_text,
                hoverinfo='text',
                showlegend=False
            ))

        # Add status legend (deduplicated)
        for status in df['status'].unique():
            fig.add_trace(go.Scatter(
                x=[None],
                y=[None],
                mode='markers',
                marker=dict(
                    size=10,
                    color=status_colors[status],
                    symbol='circle'
                ),
                name=status,
                showlegend=True
            ))

        # Update layout
        fig.update_layout(
            title='Recent Activity Timeline',
            xaxis=dict(
                title='Time',
                type='date',
                tickformat='%Y-%m-%d %H:%M:%S',
                showgrid=False,
                zeroline=False
            ),
            yaxis=dict(
                showticklabels=False,
                showgrid=False,
                zeroline=False,
                range=[0.5, 1.5]
            ),
            height=200,
            margin=dict(l=40, r=40, t=40, b=40),
            plot_bgcolor='white',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        fig_box = go.FigureWidget(fig)

        return fig_box
    
    def _build_cumulative_optimizations_plot(self):
        """Build the cumulative optimizations plot"""

        frame = self.tracker.index_df.copy()
        frame = frame.sort_values('run_timestamp', ascending=True)
        frame = frame.reset_index(drop=True)
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=frame['run_timestamp'],
                y=frame.index
            )
        )
        fig.update_layout(
            title={
                'text': 'Cumulative Optimization Runs',
                'y': 0.95,  # Move title position up (closer to top)
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            height=450,
            width=700,
            margin=dict(t=80, l=100, r=50, b=50),  # Reduce top margin
            #template='plotly_dark'
        )
        fig_box = go.FigureWidget(fig)
        
        return fig_box