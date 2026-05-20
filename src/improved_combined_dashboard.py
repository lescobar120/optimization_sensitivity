# improved_combined_dashboard.py

import ipywidgets as ipw
import threading
import time
from IPython.display import display
from .optimization_exec_summary import OptimizationExecutiveDashboard
from .constraint_sensitivity_analysis_view import ConstraintSensitivityView
from .trade_analytics_view import TradeAnalyticsView
from .gui import PortfolioOptimizationGUI
from .data_manager import OptimizationDataManager
from .analysis_utils import OptimizationAnalyzer

class OptimizationDataCache:
    """Caches data for different portfolios to avoid reloading."""
    
    def __init__(self, workflow_manager):
        """
        Initialize the data cache with the workflow manager
        
        Args:
            workflow_manager: instance of OptimizationWorkflowManager
        """
        self.workflow_manager = workflow_manager
        self.tracker = workflow_manager.tracker
        self.analyzer = OptimizationAnalyzer(self.tracker)
        
        # Cache containers
        self.pathway_data = {}  # Stores portfolio -> results_frame mapping
        self.optimization_ids = {}  # Stores portfolio -> optimization_ids mapping
        self.sensitivity_frames = {}  # Stores portfolio, goal -> sensitivity frames mapping
        self.trade_stats = {}  # Stores portfolio -> trade statistics data
        self.all_trades_frames = {}  # Stores portfolio -> all trades data
        
        # Default configurations
        self.default_goal = "CUSTOM_NUMBER(FIELD = 'CF_7459422178055815169')"
        self.goal_mapper = {
            "CUSTOM_NUMBER(FIELD = 'CF_7459422178055815169')": "expected_return",
            "active_total_risk": "active_total_risk"
        }
        self.constraint_mapper = {
            'max_active_risk': 'Max Active Total Risk',
            'max_positions': 'Max Positions',
            'max_turnover': 'Max Turnover',
            'max_sector_deviation': 'Max Sector Deviation',
            'max_security_weight': 'Max Security Weight'
        }
        self.constraint_list = list(self.constraint_mapper.keys())
        
        # Flag to track preloading status
        self.loading_status = {}


    def _load_optimization_ids(self, portfolio):
        """Load optimization IDs for a portfolio if not already cached"""

        if portfolio not in self.optimization_ids:
            frame = self.tracker.filter_optimizations(
                portfolio=portfolio, 
                status='success'
            )
            self.optimization_ids[portfolio] = list(frame['optimization_id'])
        
        return self.optimization_ids[portfolio]
    
    def _load_pathway_data(self, portfolio):
        """Load optimization pathway data for a portfolio if not already cached"""
        
        if portfolio not in self.pathway_data:
            # Ensure optimization IDs are loaded first
            optimization_ids = self._load_optimization_ids(portfolio)
            
            if optimization_ids:
                try:
                    results_frame = self.analyzer.compare_optimizations(
                        optimization_ids=optimization_ids, 
                        comparison_type="optimization_pathways"
                    ).rename(columns=self.goal_mapper)
                    self.pathway_data[portfolio] = results_frame
                except Exception as e:
                    print(f"Error loading pathway data for {portfolio}: {e}")
                    self.pathway_data[portfolio] = None
        
        return self.pathway_data.get(portfolio)

    def _load_sensitivity_frames(self, portfolio, goal):
        """Load sensitivity frames for a portfolio and goal if not already cached."""
        key = (portfolio, goal)
        if key not in self.sensitivity_frames:
            try:
                frames = self.analyzer.load_goal_constraint_sensitivity_frames(
                    goal, self.constraint_list, portfolio)
                self.sensitivity_frames[key] = frames
            except Exception as e:
                print(f"Error loading sensitivity frames for {portfolio}, goal {goal}: {e}")
                self.sensitivity_frames[key] = None
        
        return self.sensitivity_frames.get(key)

    def _load_trade_data(self, portfolio):
        """Load trade data for a portfolio if not already cached"""

        # Check if we need to load trade data
        if portfolio not in self.all_trades_frames:
            # Ensure optimization IDs are loaded first
            optimization_ids = self._load_optimization_ids(portfolio)
            
            if optimization_ids:
                try:
                    # Use existing analyzer method to get all trades
                    all_trades_frame = self.analyzer.compare_optimizations(
                        optimization_ids=optimization_ids, 
                        comparison_type='trades'
                    )
                    self.all_trades_frames[portfolio] = all_trades_frame
                    
                    # Get successful optimizations for trade stats
                    successful_optimizations = self.tracker.filter_optimizations(
                        portfolio=portfolio, 
                        status='success'
                    )
                    
                    # Calculate trade statistics
                    try:
                        trade_stats_frame = self.analyzer.get_security_trade_stats(
                            all_trades_frame, 
                            successful_optimizations,
                            portfolio
                        )
                        self.trade_stats[portfolio] = trade_stats_frame
                    
                    except Exception as e:
                        print(f"Error calculating trade stats for {portfolio}: {e}")
                        self.trade_stats[portfolio] = None
                
                except Exception as e:
                    print(f"Error loading trade data for {portfolio}: {e}")
                    self.all_trades_frames[portfolio] = None
                    self.trade_stats[portfolio] = None
        
        return self.trade_stats.get(portfolio)
    
    def preload_portfolio_data(self, portfolio, goal=None, callback=None):
        """
        Preload data for a specific portfolio and goal
        
        Args:
            portfolio: Portfolio name to preload
            goal: Goal to preload (defaults to self.default_goal)
            callback: Optional callback to execute when loading completes
        """
        # Use default goal if none specified
        goal = goal or self.default_goal
        
        # Mark as loading
        self.loading_status[portfolio] = "loading"
        
        # Get optimization IDs for this portfolio
        self._load_optimization_ids(portfolio)
        # Get optimization pathway data
        self._load_pathway_data(portfolio)
        # Get sensitivity frames for the specified goal
        self._load_sensitivity_frames(portfolio, goal)
        # Get trade data
        self._load_trade_data(portfolio)

        # Mark as loaded
        self.loading_status[portfolio] = "loaded"
        
        # Execute callback if provided
        if callback:
            callback(portfolio)
    
    def get_optimization_ids(self, portfolio):
        """Get optimization IDs for a portfolio, loading if necessary"""
        if portfolio not in self.optimization_ids:
            self.preload_portfolio_data(portfolio)
        return self.optimization_ids.get(portfolio, [])
    
    def get_pathway_data(self, portfolio):
        """Get pathway data for a portfolio, loading if necessary"""
        if portfolio not in self.pathway_data:
            self.preload_portfolio_data(portfolio)
        return self.pathway_data.get(portfolio)
    
    def get_sensitivity_frames(self, portfolio, goal=None):
        """Get sensitivity frames for a portfolio/goal, loading if necessary"""
        goal = goal or self.default_goal
        key = (portfolio, goal)
        if key not in self.sensitivity_frames:
            self.preload_portfolio_data(portfolio, goal)
        return self.sensitivity_frames.get(key)
    
    def get_trade_stats(self, portfolio):
        """Get trade statistics for a portfolio, loading if necessary"""
        if portfolio not in self.trade_stats:
            self.preload_portfolio_data(portfolio)
        return self.trade_stats.get(portfolio)
    
    def get_all_trades_frame(self, portfolio):
        """Get all trades frame for a portfolio, loading if necessary"""
        if portfolio not in self.all_trades_frames:
            self.preload_portfolio_data(portfolio)
        return self.all_trades_frames.get(portfolio)
    
    def is_portfolio_loaded(self, portfolio):
        """Check if a portfolio's data is loaded"""
        return self.loading_status.get(portfolio) == "loaded"
    
    def is_portfolio_loading(self, portfolio):
        """Check if a portfolio's data is currently loading"""
        return self.loading_status.get(portfolio) == "loading"
    
    def preload_all_portfolios(self, portfolios, goal=None, progress_callback=None):
        """
        Preload data for all given portfolios in the background with detailed progress
        
        Args:
            portfolios: List of portfolio names to preload
            goal: Goal to preload (defaults to self.default_goal)
            progress_callback: Optional callback to report progress
        """

        # Use default goal if none specified
        goal = goal or self.default_goal
        
        # Number of steps per portfolio
        STEPS_PER_PORTFOLIO = 4  # optimization_ids, pathway_data, sensitivity_frames, trade_data
        total_steps = len(portfolios) * STEPS_PER_PORTFOLIO
        current_step = 0
        
        def update_progress(portfolio_name, step_name):
            nonlocal current_step
            current_step += 1
            if progress_callback:
                progress_callback(
                    current_step, 
                    total_steps, 
                    f"Portfolio {portfolio_name} - {step_name}"
                )
        
        def preload_worker():
            for portfolio in portfolios:
                try:
                    # Mark as loading
                    self.loading_status[portfolio] = "loading"
                    
                    # Load each data type and update progress
                    self._load_optimization_ids(portfolio)
                    update_progress(portfolio, "Loaded optimization IDs")
                    
                    self._load_pathway_data(portfolio)
                    update_progress(portfolio, "Loaded pathway data")
                    
                    self._load_sensitivity_frames(portfolio, goal)
                    update_progress(portfolio, "Loaded sensitivity frames")
                    
                    self._load_trade_data(portfolio)
                    update_progress(portfolio, "Loaded trade data")
                    
                    # Mark as loaded
                    self.loading_status[portfolio] = "loaded"
                    
                except Exception as e:
                    print(f"Error preloading data for {portfolio}: {e}")
                    self.loading_status[portfolio] = "error"
        
        # Start background thread
        thread = threading.Thread(target=preload_worker)
        thread.daemon = True
        thread.start()

    def clear_cache_for_portfolio(self, portfolio):
        """Remove all cached data for a specific portfolio"""

        # Clear pathway data
        if portfolio in self.pathway_data:
            del self.pathway_data[portfolio]
        
        # Clear sensitivity frames for all goals associated with this portfolio
        keys_to_remove = []
        for key in self.sensitivity_frames:
            if key[0] == portfolio:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.sensitivity_frames[key]
        
        # Clear trade statistics
        if portfolio in self.all_trades_frames:
            del self.trade_stats[portfolio]

        if portfolio in self.trade_stats:
            del self.trade_stats[portfolio]
        
        # Clear optimization IDs
        if portfolio in self.optimization_ids:
            del self.optimization_ids[portfolio]
        
        # Clear loading status
        if portfolio in self.loading_status:
            del self.loading_status[portfolio]
        
        print(f"Cleared all cached data for portfolio: {portfolio}")

    def load_data_for_tab(self, tab_index, portfolio, goal=None, callback=None):
        """
        Load only the data needed for a specific tab and track overall portfolio loading
        
        Args:
            tab_index: Index of the tab (0-3)
            portfolio: Portfolio to load data for
            goal: Goal to use for data loading (if applicable)
            callback: Function to call when loading completes
        """
        
        goal = goal or self.default_goal
        
        # Mark as loading if not already
        if self.loading_status.get(portfolio) != "loaded":
            self.loading_status[portfolio] = "loading"
        
        try:
            # Executive Summary (tab 0) needs no data
            if tab_index == 0:
                pass
            
            # Constraint Sensitivity tab (tab 1)
            elif tab_index == 1:
                self._load_optimization_ids(portfolio)
                self._load_sensitivity_frames(portfolio, goal)
                
            # Trade Analytics tab (tab 2)
            elif tab_index == 2:
                self._load_optimization_ids(portfolio)
                self._load_trade_data(portfolio)
                
            # Pathway tab (tab 3)
            elif tab_index == 3:
                self._load_optimization_ids(portfolio)
                self._load_pathway_data(portfolio)
            
            # Mark appropriate tab data as loaded
            self.loading_status[f"{portfolio}_tab_{tab_index}"] = "loaded"
            
            # Check if all tabs are loaded and update portfolio status
            self._check_portfolio_loading_complete(portfolio)
            
            # Execute callback if provided
            if callback:
                callback(portfolio)
                
        except Exception as e:
            print(f"Error loading data for tab {tab_index}, portfolio {portfolio}: {e}")
            self.loading_status[f"{portfolio}_tab_{tab_index}"] = "error"
        
    def _check_portfolio_loading_complete(self, portfolio):
        """
        Check if all tabs for a portfolio have been loaded and update the portfolio status
        
        Args:
            portfolio: Portfolio to check
        """

        # We only care about tabs 1-3 (indices 0-3 excluding 0 since it has no data requirements)
        all_tabs_loaded = True
        
        for tab_index in range(1, 4):
            tab_status = self.loading_status.get(f"{portfolio}_tab_{tab_index}")
            if tab_status != "loaded":
                all_tabs_loaded = False
                break
        
        # Check if all required data components are loaded
        data_components_loaded = (
            portfolio in self.optimization_ids and
            portfolio in self.pathway_data and
            portfolio in self.trade_stats and
            (portfolio, self.default_goal) in self.sensitivity_frames
        )
        
        # Update portfolio status if all data is loaded
        if all_tabs_loaded and data_components_loaded:
            self.loading_status[portfolio] = "loaded"
            print(f"All data for portfolio {portfolio} is now fully loaded")


class CombinedOptimizationDashboard:
    """Improved dashboard with data caching and lazy tab initialization"""
    
    def __init__(self, workflow_manager):
        """
        Main container for the combined optimization dashboard.

        Args:
            workflow_manager: instance of OptimizationWorkflowManager
        """

        self.workflow_manager = workflow_manager
        self.tracker = workflow_manager.tracker
        
        # Create data cache
        self.data_cache = OptimizationDataCache(workflow_manager)
        
        # Get available portfolios
        self.available_portfolios = self.tracker.index_df['portfolio'].dropna().unique().tolist()
        self.default_portfolio = self.available_portfolios[0] if self.available_portfolios else None
        
        # UI components
        self.portfolio_selector = ipw.Dropdown(
            options=self.available_portfolios,
            value=self.default_portfolio,
            description="Portfolio:",
            style={'description_width': 'initial'}
        )
        self.refresh_button = ipw.Button(
            description='🔄 Refresh Portfolio Views', 
            button_style='primary',
            layout={'width':'initial'}
        )
        self.preload_button = ipw.Button(
            description='⏳ Preload All Portfolios',
            button_style='info',
            layout={'width':'initial'}
        )
        self.progress_bar = ipw.FloatProgress(
            value=0,
            min=0,
            max=100,
            description='Loading:',
            bar_style='info',
            style={'bar_color': '#2196F3'},
            layout={'width': '300px', 'visibility': 'hidden'}
        )
        
        self.status_label = ipw.HTML(
            value="",
            layout={'margin': '0 10px'}
        )
        
        # Create tabs container
        self.tab_contents = ipw.Tab()
        self.tab_contents.observe(self._on_tab_select, names='selected_index')
        
        # Track initialization status of tabs
        self.initialized_tabs = {i: False for i in range(4)}

        self.tab_creators = [
            self._create_exec_summary_tab,
            self._create_constraint_sensitivity_tab,
            self._create_trade_analytics_tab,
            self._create_pathway_tab
        ]
        self.tab_placeholders = [
            self._create_loading_widget("Executive Summary"),
            self._create_loading_widget("Constraint Sensitivity"),
            self._create_loading_widget("Trade Analytics"),
            self._create_loading_widget("Goal Pathway")
        ]
        
        # Set up initial tab placeholders
        self.tab_contents.children = self.tab_placeholders
        tab_titles = ["Executive Summary", "Constraint Sensitivity", "Trade Analytics", "Goal Pathway"]
        for i, title in enumerate(tab_titles):
            self.tab_contents.set_title(i, title)
        
        # Controls layout
        self.controls_bar = ipw.HBox([
            self.portfolio_selector,
            self.refresh_button,
            self.preload_button,
            self.progress_bar,
            self.status_label
        ], layout={'justify_content': 'flex-start', 'margin': '10px 0'})
        
        # Main dashboard layout
        self.dashboard = ipw.VBox([
            self.controls_bar,
            self.tab_contents
        ])
        
        # Bind event handlers
        self.portfolio_selector.observe(self._on_portfolio_change, names='value')
        self.refresh_button.on_click(self._refresh_portfolio_data)
        self.preload_button.on_click(self._preload_all_portfolios)
        
        # Initialize the Executive Summary tab immediately since it doesn't need portfolio data
        self._initialize_tab(0, self.default_portfolio)

        # # Preload data for default portfolio
        # if self.default_portfolio:
        #     self._show_loading_status(f"Loading data for {self.default_portfolio}...")
        #     self.data_cache.preload_portfolio_data(
        #         self.default_portfolio, 
        #         callback=lambda p: self._on_portfolio_loaded(p)
        #     )
        
        
        # Start background loading of default portfolio data
        if self.default_portfolio:
            self._start_background_loading_for_portfolio(self.default_portfolio)


    def _start_background_loading_for_portfolio(self, portfolio, check_if_loaded=True):
        """
        Start background loading for all data for a portfolio
        
        Args:
            portfolio: Portfolio to load data for
            check_if_loaded: If True, only load if data isn't already loaded
        """
        
        def background_loader():
            # Check if we should load this data
            if not check_if_loaded or not self.data_cache.is_portfolio_loaded(portfolio):
                print(f"Starting background data loading for {portfolio}...")
                try:
                    self.data_cache.preload_portfolio_data(portfolio)
                    print(f"Background data loading complete for {portfolio}")
                except Exception as e:
                    print(f"Error in background data loading for {portfolio}: {str(e)}")
        
        # Start in a background thread
        thread = threading.Thread(target=background_loader)
        thread.daemon = True
        thread.start()
    
    
    def _create_loading_widget(self, tab_name):
        """Create a loading placeholder widget for a tab"""

        spinner = ipw.HTML(
            value='<i class="fa fa-spinner fa-spin fa-3x fa-fw"></i>',
            layout={'margin': 'auto'}
        )
        
        return ipw.VBox([
            ipw.Label(f"Loading {tab_name}..."),
            spinner
        ], layout={
            'align_items': 'center',
            'justify_content': 'center',
            'width': '100%',
            'height': '400px'
        })
    
    def _on_tab_select(self, change):
        """Handle tab selection to implement lazy loading"""

        #print(change.keys())
        name = change['name']
        old = change['old']
        new = change['new']
        type = change['type']
        #print(name, old, new, type)
        #print(self.tab_contents.selected_index)
        if 'new' not in change:
            return
            
        tab_index = change['new']
        current_portfolio = self.portfolio_selector.value

        # If this tab hasn't been initialized yet
        if not self.initialized_tabs.get(tab_index, False): 
            # we should just be able to initialize a tab without reloading portoflio data bc data loading would already be kicked off
            # whether it is on app initialization or portfolio change - both kick off background data loading regardless of index
            self._initialize_tab(tab_index, current_portfolio)
            # if tab_index == 0:
            #     # Executive Summary tab doesn't need portfolio data
            #     self._initialize_tab(tab_index, current_portfolio)
            # else:
            #     # Check if data is available for portfolio-specific tabs
            #     if self.data_cache.is_portfolio_loaded(current_portfolio):
            #         # Initialize the tab
            #         self._initialize_tab(tab_index, current_portfolio)
            #     else:
            #         # Schedule initialization after data loads
            #         self._show_loading_status(f"Loading data for {current_portfolio}...")
            #         self.data_cache.preload_portfolio_data(
            #             current_portfolio,
            #             callback=lambda p: self._initialize_tab(tab_index, p)
            #         )
        else:
            #self._initialize_tab(tab_index, current_portfolio)
            self._show_loading_status(f"{self.tab_contents.get_title(tab_index)} view ready")
    
    def _initialize_tab(self, tab_index, portfolio):
        """Initialize a specific tab"""

        # Make sure this is still the current portfolio
        if portfolio != self.portfolio_selector.value:
            return
        
        # Store the current selected tab
        current_selected = self.tab_contents.selected_index

        # Show initialization status    
        self._show_loading_status(f"Initializing {self.tab_contents.get_title(tab_index)} view...")
        
        # Create the tab content
        try:
            #print(tab_index)
            tab_content = self.tab_creators[tab_index](portfolio)
            
            # Replace the placeholder with actual content
            children = list(self.tab_contents.children)
            children[tab_index] = tab_content
            self.tab_contents.children = children
            
            # Mark as initialized
            self.initialized_tabs[tab_index] = True

            # Restore the original tab selection (even if it's not the tab we just initialized)
            self.tab_contents.selected_index = current_selected
            #print(self.tab_contents.selected_index)

            self._show_loading_status(f"{self.tab_contents.get_title(tab_index)} view ready")
        
        except Exception as e:
            self._show_loading_status(f"Error initializing tab: {str(e)}", is_error=True)
    
    def _create_exec_summary_tab(self, portfolio):
        """Create the executive summary tab content."""
        exec_summary_view = OptimizationExecutiveDashboard(
            self.tracker, 
            self.data_cache.analyzer
        )
        return exec_summary_view.get_view()
    
    def _create_constraint_sensitivity_tab(self, portfolio):
        """Create the constraint sensitivity tab content with preloaded data"""

        goal = self.data_cache.default_goal
        
        # Get preloaded sensitivity frames
        sensitivity_frames = self.data_cache.get_sensitivity_frames(portfolio, goal)
        
        # Create view with preloaded data
        constraint_view = ConstraintSensitivityView(
            self.data_cache.analyzer,
            portfolio,
            goal,
            self.data_cache.goal_mapper,
            self.data_cache.constraint_mapper,
            preloaded_sensitivity_frames=sensitivity_frames
        )
        return constraint_view.get_view()
    
    def _create_trade_analytics_tab(self, portfolio):
        """Create the trade analytics tab content with preloaded data"""
        
        # Get preloaded data
        trade_stats = self.data_cache.get_trade_stats(portfolio)
        
        # Create view with preloaded data
        trade_view = TradeAnalyticsView(
            self.data_cache.analyzer,
            self.tracker,
            portfolio,
            preloaded_trade_stats=trade_stats
        )
        return trade_view.get_view()
    
    def _create_pathway_tab(self, portfolio):
        """Create the pathway tab content."""
        # Get cached pathway data
        results_frame = self.data_cache.get_pathway_data(portfolio)
        
        if results_frame is not None and not results_frame.empty:
            data_manager = OptimizationDataManager(results_frame, self.tracker)
            pathway_view = PortfolioOptimizationGUI(data_manager)
            return pathway_view.view
        else:
            return ipw.HTML(f"<h3>No pathway data available for {portfolio}</h3>")
    
    def _on_portfolio_change(self, change):
        """Handle portfolio selection changes"""

        # print(change)

        if change['type'] != 'change':
            return
        
        new_portfolio = change['new']
        current_tab = self.tab_contents.selected_index

        print(f"DEBUG: Portfolio change - current tab is {current_tab}")
        self._show_loading_status(f"Switching to {new_portfolio}...")
        
        # Reset tab initialization flags for portfolio-specific tabs only (1-3)
        self.initialized_tabs = {**self.initialized_tabs, **{i: False for i in range(1, 4)}}
        
        # IMPORTANT: Instead of replacing tab children entirely, let's try a different approach
        # Create a tab observer to check if tab selection changes unexpectedly
        def tab_observer(change):
            if 'new' in change and change['new'] != current_tab:
                print(f"DEBUG: Tab selection unexpectedly changed from {current_tab} to {change['new']}")

        # Add temporary observer to track tab selection changes
        observer = self.tab_contents.observe(tab_observer, names='selected_index')

        # Instead of replacing children, let's try to modify the existing children
        for i in range(1, 4):  # For each portfolio-specific tab
            # Update tab content to placeholder without changing the children array
            try:
                if isinstance(self.tab_contents.children[i], ipw.VBox):
                    # If it's already a VBox, let's update its children instead of replacing it
                    self.tab_contents.children[i].children = [
                        ipw.Label(f"Loading {self.tab_contents.get_title(i)}..."),
                        ipw.HTML(
                            value='<i class="fa fa-spinner fa-spin fa-3x fa-fw"></i>',
                            layout={'margin': 'auto'}
                        )
                    ]
                    self.tab_contents.children[i].layout = {
                        'align_items': 'center',
                        'justify_content': 'center',
                        'width': '100%',
                        'height': '400px'
                    }
                else:
                    # Fall back to replacement if needed
                    curr_children = list(self.tab_contents.children)
                    curr_children[i] = self.tab_placeholders[i]
                    self.tab_contents.children = curr_children
            except Exception as e:
                print(f"DEBUG: Error updating tab {i}: {e}")

        

        # # Restore placeholders for portfolio-specific tabs only
        # children = list(self.tab_contents.children)
        # for i in range(1, 4):
        #     children[i] = self.tab_placeholders[i]
        # self.tab_contents.children = children
                
        print(f"DEBUG: After update, tab selection is {self.tab_contents.selected_index}")

        # Explicitly set tab selection
        if self.tab_contents.selected_index != current_tab:
            print(f"DEBUG: Forcing tab selection back to {current_tab}")
            self.tab_contents.selected_index = current_tab

        # Remove the observer
        self.tab_contents.unobserve(tab_observer, names='selected_index')

        # IMPORTANT: Explicitly maintain the tab selection
        # self.tab_contents.selected_index = current_tab

        # Reset the tab content more safely
        def delayed_tab_check():
            time.sleep(0.2)  # Wait 200ms
            actual_tab = self.tab_contents.selected_index
            print(f"DEBUG: After delay, tab selection is {actual_tab}")
            if actual_tab != current_tab:
                print(f"DEBUG: Re-applying tab selection to {current_tab}")
                self.tab_contents.selected_index = current_tab
        
        # Run tab check in background
        import threading
        threading.Thread(target=delayed_tab_check, daemon=True).start()

        # check if portfolio data is already available
        if self.data_cache.is_portfolio_loaded(new_portfolio):
            if current_tab > 0:  # Skip Executive Summary tab (index 0)
                # Initialize current tab immediately
                self._initialize_tab(current_tab, new_portfolio)
                self._show_loading_status(f"Switched to {new_portfolio}")
            else:
                # For Executive Summary tab, just update the status
                self._show_loading_status(f"Switched to {new_portfolio}")
        
        else: # if portfolio data is not available, we need to load it
            if current_tab == 0:
                # Executive Summary tab - just start background loading
                #self._start_background_loading_for_portfolio(new_portfolio)
                self._show_loading_status(f"Switched to {new_portfolio}")
                self._start_background_loading_for_remaining_tabs(new_portfolio, current_tab)
            else:
                # Portfolio-specific tab - load data for this tab first, then background load the rest
                self._show_loading_status(f"Loading data for {new_portfolio}, tab {self.tab_contents.get_title(current_tab)}...")
                
                # First load data just for the current tab
                self.data_cache.load_data_for_tab(
                    tab_index=current_tab,
                    portfolio=new_portfolio,
                    callback=lambda p: self._on_tab_data_loaded(current_tab, p)
                )
        
    
    def _on_tab_data_loaded(self, tab_index, portfolio):
        """Called when a specific tab's data has been loaded"""

        # Initialize the tab with the loaded data
        self._initialize_tab(tab_index, portfolio)

        # Explicitly set the tab selection back to the original tab
        # (This is a backup in case _initialize_tab doesn't preserve the selection)
        # self.tab_contents.selected_index = tab_index
        
        # Show status update
        self._show_loading_status(f"Tab {self.tab_contents.get_title(tab_index)} ready")
        
        # Continue loading other data in the background
        self._start_background_loading_for_remaining_tabs(portfolio, tab_index)

    def _start_background_loading_for_remaining_tabs(self, portfolio, current_tab):
        """Load data for remaining tabs in the background"""
        
        def load_remaining_tabs():
            for tab_index in range(1, 4):  # Skip Executive Summary
                if tab_index != current_tab:  # Skip the tab we already loaded
                    try:
                        self.data_cache.load_data_for_tab(tab_index, portfolio)
                    except Exception as e:
                        print(f"Error loading data for tab {tab_index}: {e}")
        
        thread = threading.Thread(target=load_remaining_tabs)
        thread.daemon = True
        thread.start()

    def _on_portfolio_loaded(self, portfolio):
        """Handle completion of portfolio data loading"""

        # Make sure this is still the current portfolio
        if portfolio != self.portfolio_selector.value:
            return
            
        # Initialize current tab
        current_tab = self.tab_contents.selected_index
        self._initialize_tab(current_tab, portfolio)
        self._show_loading_status(f"Data loaded for {portfolio}")
    
    def _refresh_portfolio_data(self, _=None):
        """
        Refresh all data for the current portfolio and rebuild the current tab.
        This clears cached data for the selected portfolio and reloads it,
        ensuring all tabs will use fresh data when viewed.
        """

        current_tab = self.tab_contents.selected_index
        portfolio = self.portfolio_selector.value

        # For Executive Summary tab, just refresh that tab without reloading data
        if current_tab == 0:
            self._show_loading_status("Refreshing Executive Summary...")
            self._initialize_tab(current_tab, portfolio)
            self._show_loading_status("Executive Summary refreshed")
            return
        
        self._show_loading_status(f"Refreshing all data for {portfolio}...")
        
        # Mark tab as uninitialized
        self.initialized_tabs[current_tab] = False
        
        # Replace with placeholder
        children = list(self.tab_contents.children)
        children[current_tab] = self.tab_placeholders[current_tab]
        self.tab_contents.children = children
        
        # Clear cache for this portfolio
        self.data_cache.clear_cache_for_portfolio(portfolio)
        
        # Reload data and reinitialize tab
        # self.data_cache.preload_portfolio_data(
        #     portfolio,
        #     callback=lambda p: self._initialize_tab(current_tab, p)
        # )

        # First load data just for the current tab
        self.data_cache.load_data_for_tab(
            tab_index=current_tab,
            portfolio=portfolio,
            callback=lambda p: self._on_tab_data_loaded(current_tab, p)
        )

    def _preload_all_portfolios(self, _=None):
        """Preload data for all portfolios in the background"""

        self.progress_bar.layout.visibility = 'visible'
        self.progress_bar.value = 0
        
        def update_progress(current, total, step_message=None):
            progress = (current / total) * 100
            self.progress_bar.value = progress
            if step_message:
                self.status_label.value = f"{step_message} ({current}/{total} steps)"
            else:
                self.status_label.value = f"Preloaded {current}/{total} steps"
                
            if current == total:
                self.progress_bar.layout.visibility = 'hidden'
                self.status_label.value = "All portfolios preloaded"
        
        self.data_cache.preload_all_portfolios(
            self.available_portfolios,
            goal=self.data_cache.default_goal,
            progress_callback=update_progress
        )
 
    def _show_loading_status(self, message, is_error=False):
        """Display a loading status message."""
        style = "color: red;" if is_error else ""
        self.status_label.value = f"<span style='{style}'>{message}</span>"
    
    def display(self):
        """Return the dashboard for display."""
        return self.dashboard