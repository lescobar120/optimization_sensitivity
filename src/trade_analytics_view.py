# trade_analytics_view.py

import ipywidgets as ipw
import plotly.graph_objects as go
from typing import Dict, List, Any, Optional
import pandas as pd
from .plot_manager import build_security_action_frequency_fig, build_security_trade_consistency_fig, build_security_actions_treemap

class TradeAnalyticsView:
    """
    UI component for portfolio trade analytics visualization.
    Provides visualizations of security action frequencies and trade consistency metrics.
    """
    
    def __init__(self, analyzer, tracker, portfolio: str,
                preloaded_trade_stats: Optional[pd.DataFrame] = None):
        """
        Initialize the trade analytics view.
        
        Args:
            analyzer: OptimizationAnalyzer instance
            tracker: OptimizationTracker instance
            portfolio: Portfolio name to analyze
            preloaded_trade_stats: Optional pre-loaded trade statistics
        """
        self.analyzer = analyzer
        self.tracker = tracker
        self.portfolio = portfolio
        
        # Load initial data
        self._load_data(preloaded_trade_stats)
        
        # Build UI components
        self._build_ui_components()
        
        # Create initial view
        self.trade_analytics_view = self._create_layout()

    def _validate_trade_stats(self, trade_stats):
        """Validate that trade statistics data is correct"""
        if trade_stats is None or trade_stats.empty:
            return False
            
        # Check for required columns
        required_columns = ['Buys', 'Sells', 'New Holdings', 'Liquidated Holdings', 
                           'buy_consistency', 'sell_consistency']
        for col in required_columns:
            if col not in trade_stats.columns:
                return False
                
        return True
    
    def _load_data(self, preloaded_trade_stats=None):
        """Load and prepare the data needed for visualizations"""

        # Use preloaded trade stats if provided and valid
        if preloaded_trade_stats is not None and self._validate_trade_stats(preloaded_trade_stats):
            self.trade_stats_frame = preloaded_trade_stats
        else:
            # Get successful optimizations
            successful_optimizations_frame = self.tracker.filter_optimizations(
                portfolio=self.portfolio, 
                status='success'
            ).copy()
            successful_ids = list(successful_optimizations_frame['optimization_id'])
            
            # Load trades - local variable, not class attribute
            all_trades_frame = self.analyzer.compare_optimizations(
                successful_ids, 'trades')
            
            # Generate trade statistics
            self.trade_stats_frame = self.analyzer.get_security_trade_stats(
                all_trades_frame,
                successful_optimizations_frame,
                self.portfolio)
    
    def _build_ui_components(self):
        """Create all UI components"""
        # Create HTML header
        self.trade_analytics_html = ipw.HTML(f"<h2>Optimization Trade Analytics for {self.portfolio}</h2>")
        
        # Create accordions for visualizations
        self.security_action_frequency_fig = build_security_action_frequency_fig(
            self.trade_stats_frame, self.portfolio)
        self.security_action_frequency_accordion = ipw.Accordion(
            children=[self.security_action_frequency_fig])
        self.security_action_frequency_accordion.set_title(0, "Security Action Frequency")
        self.security_action_frequency_accordion.selected_index = None
        
        self.security_trade_consistency_fig = build_security_trade_consistency_fig(
            self.trade_stats_frame, self.portfolio)
        self.security_trade_consistency_accordion = ipw.Accordion(
            children=[self.security_trade_consistency_fig])
        self.security_trade_consistency_accordion.set_title(0, "Security Trade Consistency")
        self.security_trade_consistency_accordion.selected_index = None
        
        self.security_action_distribution_fig = build_security_actions_treemap(
            self.trade_stats_frame, self.portfolio)
        self.security_action_distribution_accordion = ipw.Accordion(
            children=[self.security_action_distribution_fig])
        self.security_action_distribution_accordion.set_title(0, "Security Action Distribution")
        self.security_action_distribution_accordion.selected_index = None
    
    def _create_layout(self):
        """Create the main layout"""
        return ipw.VBox([
            self.trade_analytics_html,
            self.security_action_frequency_accordion,
            self.security_trade_consistency_accordion,
            self.security_action_distribution_accordion
        ])
    
    def get_view(self):
        """Return the main view component"""
        return self.trade_analytics_view