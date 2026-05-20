# constraint_sensitivity_analysis_view.py

import ipywidgets as ipw
import plotly.graph_objects as go
from typing import Dict, List, Any, Tuple, Optional
import pandas as pd

class ConstraintSensitivityView:
    """
    UI component for constraint sensitivity analysis visualization.
    Provides a three-column view of distribution plots showing how different
    constraint values affect goal outcomes, with optional filtering.
    """
    
    def __init__(self, analyzer, portfolio: str, goal: str, 
                custom_goal_mapper: Dict[str, str], constraint_description_mapper: Dict[str, str],
                preloaded_sensitivity_frames: Optional[Dict] = None):
        """
        Initialize the constraint sensitivity view.
        
        Args:
            analyzer: The OptimizationAnalyzer instance
            portfolio: Portfolio name to analyze
            goal: Goal metric to visualize
            custom_goal_mapper: Mapping of goal IDs to human-readable names
            constraint_description_mapper: Mapping of constraint IDs to display names
            preloaded_sensitivity_frames: Optional pre-loaded sensitivity frames
        """

        self.analyzer = analyzer
        self.portfolio = portfolio
        self.goal = goal
        self.custom_goal_mapper = custom_goal_mapper
        self.constraint_description_mapper = constraint_description_mapper
        
        # Load data once at initialization
        self.constraint_list = list(constraint_description_mapper.keys())
        
        # Use preloaded data if provided, otherwise load it
        if preloaded_sensitivity_frames is not None and self._validate_sensitivity_frames(preloaded_sensitivity_frames, goal, self.constraint_list):
            self.sensitivity_frames = preloaded_sensitivity_frames
        else:
            # Fall back to loading data if not provided
            self.sensitivity_frames = self.analyzer.load_goal_constraint_sensitivity_frames(
                goal, self.constraint_list, portfolio)
        
        # Set up constraints and options
        self._setup_constraint_options()
        
        # Build UI elements
        self._build_ui_components()
        
        # Initialize plots
        self.all_constraint_figs = self._generate_all_constraint_plots()
        self.first_filtered_figs = None
        self.second_filtered_figs = None
        
        # Create initial view with just the controls
        self.constraint_analysis_view = ipw.VBox([
            self.constraint_analysis_inputs
        ])

    def _validate_sensitivity_frames(self, frames, goal, constraint_list):
        """Validate that sensitivity frames contain expected data"""
        if not frames:
            print("Validation failed: frames is empty")
            return False
            
        # Check if all expected constraints are present
        for constraint in constraint_list:
            if constraint not in frames:
                print(f"Validation failed: missing constraint {constraint}")
                return False
                
        # Check if frames contain data for the right goal and portfolio
        for constraint, frame in frames.items():
            # Check required columns
            required_columns = ['goal_name', 'portfolio', 'constraint_value', 'goal_value']
            for col in required_columns:
                if col not in frame.columns:
                    print(f"Validation failed: missing column {col} in frame for {constraint}")
                    return False
            
            # Check for expected goal
            if goal not in frame['goal_name'].unique():
                print(f"Validation failed: goal {goal} not found in frame for {constraint}")
                return False
                
            # Check if there's actual data (not empty after filtering)
            if frame[frame['goal_name'] == goal].empty:
                print(f"Validation failed: no data for goal {goal} in frame for {constraint}")
                return False
        
        return True
    
    def _setup_constraint_options(self):
        """Set up constraint options and threshold values"""
        
        # Create dropdown options list for constraints
        self.constraint_options = [(v, k) for k, v in self.constraint_description_mapper.items()]
        
        # Build a mapping of constraints to their available threshold values
        self.constraint_threshold_mapper = {}
        for constraint in self.sensitivity_frames.keys():
            self.constraint_threshold_mapper[constraint] = sorted(
                self.sensitivity_frames[constraint]['constraint_value'].unique())
    
    def _build_ui_components(self):
        """Create all UI components and layout."""
        # Create HTML headers
        self.constraint_sensitivity_analysis_html = ipw.HTML("<h2>Constraint Sensitivity Analysis</h2>")
        self.all_constraints_html = ipw.HTML(
            f"<b>Portfolio: {self.portfolio} <br> Goal: {self.custom_goal_mapper[self.goal]}<br> All Constraints</b>")
        
        # Create dropdowns for constraint selection
        self.first_constraint_dd = self._create_dropdown(
            self.constraint_options, 'First Constraint Filter', width='300px')
        
        self.first_constraint_enum_dd = self._create_dropdown(
            description=self.constraint_description_mapper[self.first_constraint_dd.value],
            options=self.constraint_threshold_mapper[self.first_constraint_dd.value],
            width='190px')
        
        # Create second constraint dropdown, excluding the first constraint
        second_options = [c for c in self.constraint_options 
                          if c[1] != self.first_constraint_dd.value]
        
        self.second_constraint_dd = self._create_dropdown(
            second_options, 'Second Constraint Filter', width='300px')
        
        self.second_constraint_enum_dd = self._create_dropdown(
            description=self.constraint_description_mapper[self.second_constraint_dd.value],
            options=self.constraint_threshold_mapper[self.second_constraint_dd.value],
            width='190px')
        
        # Create button for updating the view
        self.load_btn = ipw.Button(
            description="Load Constraint Sensitivity Distributions",
            button_style="info",
            layout={'width': 'max-content'}
        )
        
        # Bind event handlers
        self._bind_callbacks()
        
        # Create input panel layout
        self.constraint_analysis_inputs = self._create_input_panel()
    
    def _create_dropdown(self, options, description, width='max-content'):
        """Helper method to create standardized dropdowns."""
        return ipw.Dropdown(
            description=description,
            options=options,
            layout={'width': width},
            style={'description_width': 'initial'}
        )
    
    def _bind_callbacks(self):
        """Bind event handlers to UI components."""
        self.first_constraint_dd.observe(
            handler=self._first_constraint_changed, 
            type='change', 
            names='value'
        )
        
        self.second_constraint_dd.observe(
            handler=self._second_constraint_changed, 
            type='change', 
            names='value'
        )
        
        self.load_btn.on_click(self._load_distributions)
    
    def _first_constraint_changed(self, evt):
        """Handler for when first constraint selection changes"""
        new_value = evt['new']
        # Update the description and available values
        self.first_constraint_enum_dd.description = self.constraint_description_mapper[new_value]
        self.first_constraint_enum_dd.options = self.constraint_threshold_mapper[new_value]
        
        # If the same constraint is selected for both dropdowns, update second dropdown
        if new_value == self.second_constraint_dd.value:
            second_options = [c for c in self.constraint_options if c[1] != new_value]
            self.second_constraint_dd.options = second_options
            self.second_constraint_dd.value = second_options[0][1]
    
    def _second_constraint_changed(self, evt):
        """Handler for when second constraint selection changes."""
        new_value = evt['new']
        # Update the description and available values
        self.second_constraint_enum_dd.description = self.constraint_description_mapper[new_value]
        self.second_constraint_enum_dd.options = self.constraint_threshold_mapper[new_value]
    
    def _create_input_panel(self):
        """Create the input control panel"""

        return ipw.VBox([
            self.constraint_sensitivity_analysis_html,
            ipw.VBox(layout={'height': '20px'}),  # Spacing
            ipw.HBox([
                self.first_constraint_dd, 
                ipw.HBox(layout={'width': '20px'}),  # Horizontal spacing
                self.first_constraint_enum_dd
            ]),
            ipw.VBox(layout={'height': '8px'}),  # Spacing
            ipw.HBox([
                self.second_constraint_dd, 
                ipw.HBox(layout={'width': '20px'}),  # Horizontal spacing
                self.second_constraint_enum_dd
            ]),
            ipw.VBox(layout={'height': '20px'}),  # Spacing
            self.load_btn,
            ipw.VBox(layout={'height': '40px'}),  # Bottom spacing
        ])
    
    def _load_distributions(self, _):
        """Handler for the load button click"""

        # Get current selections
        first_constraint = self.first_constraint_dd.value
        first_constraint_value = self.first_constraint_enum_dd.value
        second_constraint = self.second_constraint_dd.value
        second_constraint_value = self.second_constraint_enum_dd.value
        
        # Generate first filtered plots (if not already generated or if filter changed)
        self.first_filtered_figs = self._generate_filtered_constraint_plots(
            first_constraint, first_constraint_value)
        
        # Generate second filtered plots
        self.second_filtered_figs = self._generate_double_filtered_constraint_plots(
            first_constraint, first_constraint_value,
            second_constraint, second_constraint_value)
        
        # Create HTML headers for the filtered views
        filtered_constraints_html = ipw.HTML(
            f"<b>Portfolio: {self.portfolio} <br> "
            f"Goal: {self.custom_goal_mapper[self.goal]}<br> "
            f"{self.constraint_description_mapper[first_constraint]} = {first_constraint_value}</b>")
        
        second_filtered_constraints_html = ipw.HTML(
            f"<b>Portfolio: {self.portfolio} <br> "
            f"Goal: {self.custom_goal_mapper[self.goal]}<br> "
            f"{self.constraint_description_mapper[first_constraint]} = {first_constraint_value}; "
            f"{self.constraint_description_mapper[second_constraint]} = {second_constraint_value}</b>")
        
        # Create the three-column layout
        distribution_view = ipw.HBox([
            ipw.VBox([self.all_constraints_html] + self.all_constraint_figs),
            ipw.VBox(layout={'width': '20px'}),
            ipw.VBox([filtered_constraints_html] + self.first_filtered_figs),
            ipw.VBox(layout={'width': '20px'}),
            ipw.VBox([second_filtered_constraints_html] + self.second_filtered_figs)
        ])
        
        # Update the main view
        self.constraint_analysis_view.children = [self.constraint_analysis_inputs, distribution_view]
    
    def _generate_all_constraint_plots(self):
        """Generate plots for all constraints without filtering"""
        
        all_figs = []
        
        for constraint, title in self.constraint_description_mapper.items():
            df = self.sensitivity_frames[constraint]
            
            fig = self._create_distribution_plot(
                df, 'constraint_value', 'goal_value', title)
            
            all_figs.append(fig)
        
        return all_figs
    
    def _generate_filtered_constraint_plots(self, filter_constraint, filter_value):
        """
        Generate plots for all constraints, filtered by a single constraint value.
        
        Args:
            filter_constraint: Constraint name to filter by
            filter_value: Value of the constraint to filter for
            
        Returns:
            List of plot figures
        """

        filtered_figs = []
        
        for constraint, title in self.constraint_description_mapper.items():
            if constraint == filter_constraint:
                # Skip this constraint as it's used as a filter
                filtered_figs.append(ipw.VBox(layout={'height': '400px'}))
            else:
                # Apply filter to the data
                df = self.sensitivity_frames[constraint]
                mask = df[filter_constraint] == filter_value
                filtered_df = df.loc[mask, :]
                
                if len(filtered_df) > 0:
                    fig = self._create_distribution_plot(
                        filtered_df, 'constraint_value', 'goal_value', title)
                    filtered_figs.append(fig)
                else:
                    # No data after filtering
                    filtered_figs.append(ipw.VBox(layout={'height': '400px'}))
        
        return filtered_figs
    
    def _generate_double_filtered_constraint_plots(self, 
                                                first_constraint, first_value,
                                                second_constraint, second_value):
        """
        Generate plots for all constraints, filtered by two constraint values.
        
        Args:
            first_constraint: First constraint name to filter by
            first_value: Value of the first constraint to filter for
            second_constraint: Second constraint name to filter by
            second_value: Value of the second constraint to filter for
            
        Returns:
            List of plot figures
        """
        double_filtered_figs = []
        
        for constraint, title in self.constraint_description_mapper.items():
            if constraint in [first_constraint, second_constraint]:
                # Skip constraints used as filters
                double_filtered_figs.append(ipw.VBox(layout={'height': '400px'}))
            else:
                # Apply both filters to the data
                df = self.sensitivity_frames[constraint]
                first_mask = df[first_constraint] == first_value
                second_mask = df[second_constraint] == second_value
                filtered_df = df.loc[(first_mask) & (second_mask), :]
                
                if len(filtered_df) > 0:
                    fig = self._create_distribution_plot(
                        filtered_df, 'constraint_value', 'goal_value', title)
                    double_filtered_figs.append(fig)
                else:
                    # No data after filtering
                    double_filtered_figs.append(ipw.VBox(layout={'height': '400px'}))
        
        return double_filtered_figs
    
    def _create_distribution_plot(self, df, x_column, y_column, title):
        """
        Create a combined violin and box plot for distribution visualization.
        
        Args:
            df: DataFrame containing the data
            x_column: Column name for x-axis (categories)
            y_column: Column name for y-axis (values)
            title: Plot title
            
        Returns:
            A FigureWidget
        """
        # Create a combined violin and box plot
        fig = go.Figure()
        
        # Get categories (constraint values)
        categories = sorted(df[x_column].unique())
        
        for value in categories:
            data = df.loc[df[x_column] == value][y_column]
            
            # Add box plot
            fig.add_trace(go.Box(
                y=data,
                name=str(value),
                width=0.15,
                boxpoints=False,  # No individual points for cleaner look
                jitter=0.3,
                marker_color='rgb(9,56,125)',
                line_color='rgb(9,56,125)',
                showlegend=False
            ))
            
            # Add violin plot
            fig.add_trace(go.Violin(
                y=data,
                name=str(value),
                side='positive',
                line_color='lightblue',
                fillcolor='lightblue',
                opacity=0.3,
                points=False  # No individual points for cleaner look
            ))
        
        # Update layout
        fig.update_layout(
            title=f'Goal Value Distribution by {title} Threshold',
            yaxis_title=self.custom_goal_mapper[self.goal],
            violinmode='overlay',
            boxmode='overlay',
            height=400,
            legend_title_text=title
        )
        
        return go.FigureWidget(fig)
    
    def get_view(self):
        """Return the main view component."""
        return self.constraint_analysis_view