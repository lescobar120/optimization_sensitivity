# visualization/portfolio_viz/gui.py
import pandas as pd
import ipywidgets as ipw
import plotly.graph_objects as go
from typing import Callable, Optional

#from oos.xml.base import *
from .data_manager import OptimizationDataManager#, OrderManager
from .plot_manager import ParallelCoordinatesPlotter

class PortfolioOptimizationGUI:
    """
    Main GUI class for portfolio optimization visualization and trade management.
    Provides an interface for:
    - Visualizing optimization results through parallel coordinates
    - Filtering results using interactive sliders
    - Viewing and staging trades for selected optimization tasks
    """
    
    def __init__(self, data_manager: OptimizationDataManager):
        """
        Initialize the GUI with a data manager instance.
        
        Args:
            data_manager: Instance of OptimizationDataManager containing the optimization results
        """
        self.data_manager = data_manager
        self.plotter = ParallelCoordinatesPlotter()
        #self.order_manager = OrderManager()
        
        # Build the interface components
        self._build_sliders()
        self._build_controls()
        self._build_view()
        
        # Update the task dropdown with initial options
        self._update_task_dropdown(self.data_manager.frame)

    def _build_sliders(self):
        """Creates and configures all slider controls for filtering"""
        ranges = self.data_manager.ranges
        
        # Position slider
        self.pos_slider = self._create_range_slider(
            value=ranges.positions,
            min_val=ranges.positions[0],
            max_val=ranges.positions[1],
            step=1,
            description='# of Positions:',
            readout_format='d'
        )
        
        # Risk slider
        self.risk_slider = self._create_range_slider(
            value=ranges.risk,
            min_val=ranges.risk[0],
            max_val=ranges.risk[1],
            step=0.001,
            description='Active Total Risk:',
            readout_format='.3f'
        )

        # Sector Deviation slider
        self.sector_dev_slider = self._create_range_slider(
            value=ranges.optional_ranges['max_sector_deviation'],
            min_val=ranges.optional_ranges['max_sector_deviation'][0],
            max_val=ranges.optional_ranges['max_sector_deviation'][1],
            step=0.01,
            description='Sector Deviation:',
            readout_format='.2f'
        )
        
        # Turnover slider
        self.turnover_slider = self._create_range_slider(
            value=ranges.turnover,
            min_val=ranges.turnover[0],
            max_val=ranges.turnover[1],
            step=0.05,
            description='Turnover:',
            readout_format='.2f'
        )
        
        # Connect slider events
        for slider in (self.pos_slider, self.risk_slider, self.turnover_slider, self.sector_dev_slider):
            slider.observe(self._handle_slider_change, names='value')

    def _build_controls(self):
        """Creates control elements with proper initial states"""
        # Task selection dropdown
        self.task_dd = ipw.Dropdown(
            description='Optimization Task',
            style={'description_width': 'initial'},
            layout={'width': 'max-content'}
        )
        
        # Create buttons
        self.view_trades_btn = ipw.Button(
            description='View Trades',
            layout={'width': 'auto', 'margin': '0px 10px 0px 0px'}
        )
        
        # Container for trades display - initialize empty
        self.trades_display = ipw.HTML(
            layout={'height': '500px', 'display': 'none'}
        )
        
        # Status output for messages
        self.status_output = ipw.HTML(
            layout={'width': 'auto', 'margin': '10px 0px'}
        )
        
        # Create button container for layout organization
        self.button_container = ipw.HBox([
            ipw.VBox([
                # Action buttons
                ipw.HBox([self.view_trades_btn]),
                # Status message area
                self.status_output
            ])
        ])
        
        # Connect button handlers
        self.task_dd.observe(self._handle_task_selection, names='value')
        self.view_trades_btn.on_click(self._handle_view_trades)

    def _build_view(self):
        """Constructs the main view layout"""
        filtered_data = self.data_manager.filter_results(
            positions=self.pos_slider.value,
            risk=self.risk_slider.value,
            turnover=self.turnover_slider.value,
            max_sector_deviation=self.sector_dev_slider.value
        )
        
        # Create plot with filtered indices
        fig = self.plotter.create_plot(
            results_df=self.data_manager.frame,
            selected_indices=filtered_data.index,
            ranges=self.data_manager.ranges
        )
        fig_widget = go.FigureWidget(fig)
        
        # Create main view with consistent button visibility
        self.view = ipw.VBox([
            # Top section: Data exploration
            ipw.VBox([
                self.turnover_slider,
                self.risk_slider,
                self.sector_dev_slider,
                self.pos_slider,
                
                fig_widget,
            ], layout={'border': '1px solid #ddd', 'padding': '10px', 'margin': '5px'}),
            
            # Bottom section: Task selection and actions
            ipw.VBox([
                self.task_dd,
                self.button_container,
                self.trades_display
            ], layout={'border': '1px solid #ddd', 'padding': '10px', 'margin': '5px'})
        ])

    def _create_range_slider(self, value, min_val, max_val, step, description, readout_format) -> ipw.FloatRangeSlider:
        """Helper method to create standardized range sliders"""
        return ipw.FloatRangeSlider(
            value=value,
            min=min_val,
            max=max_val,
            step=step,
            description=description,
            disabled=False,
            continuous_update=False,
            layout={'width': '600px'},
            style={'description_width':'initial'},
            readout=True,
            readout_format=readout_format
        )

    def _handle_slider_change(self, change):
        """Handles changes in slider values"""
        filtered_data = self.data_manager.filter_results(
            positions=self.pos_slider.value,
            risk=self.risk_slider.value,
            turnover=self.turnover_slider.value,
            max_sector_deviation=self.sector_dev_slider.value
        )
        
        # Update plot
        fig = self.plotter.create_plot(
            self.data_manager.frame,
            filtered_data.index,
            self.data_manager.ranges
        )
        
        self._update_view(fig)
        self._update_task_dropdown(filtered_data)

    def _handle_task_selection(self, change):
        """Handles changes in task selection"""
        # Clear any displayed trades
        self.trades_display.layout.display = 'none'
        self.trades_display.value = ''
        
        # Clear status
        self.status_output.value = ''

    def _handle_view_trades(self, _):
        """Handles the View Trades button click"""
        try:
            # Clear previous status
            self.status_output.value = ''
            
            # Get selected task
            task_id = self.task_dd.value.split(' ')[0]
            
            # Get trades for the task
            trades_frame = self.data_manager.get_trades_for_task(task_id)
            
            # Display trades
            self.trades_display.value = trades_frame.head(10).to_html()
            self.trades_display.layout.display = 'block'
            
        except Exception as e:
            self.status_output.value = f'<span style="color: red;">Error loading trades: {str(e)}</span>'
            self.trades_display.layout.display = 'none'

    def _update_view(self, fig: go.Figure):
        """Updates the main view with a new figure"""
        fig_widget = go.FigureWidget(fig)
        
        # Update the top section of the view while preserving the bottom section
        self.view.children = (
            ipw.VBox([
                self.turnover_slider,
                self.risk_slider,
                self.sector_dev_slider,
                self.pos_slider,
                fig_widget,
            ], layout={'border': '1px solid #ddd', 'padding': '10px', 'margin': '5px'}),
            self.view.children[1]  # Preserve the bottom section
        )

    def _update_task_dropdown(self, filtered_data: pd.DataFrame):
        """Updates task dropdown options based on filtered data"""
        self.task_dd.options = [
            f"{row['api_generated_id']} (Exp Rtn = {row['expected_return']:.4f})"
            for _, row in filtered_data.iterrows()
        ]
