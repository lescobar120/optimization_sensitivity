# visualization/portfolio_viz/plot_manager.py
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import ipywidgets as ipw

from typing import List, Optional, Tuple
import pandas as pd
from datetime import datetime, timedelta


from .data_manager import VisualizationRanges

class ParallelCoordinatesPlotter:
    """Handles creation and updating of parallel coordinates plots"""
    
    @staticmethod
    def create_dimension(label: str, range_vals: Tuple[float, float], 
                        values: pd.Series, tickformat: Optional[str] = None) -> dict:
        """Creates a standardized dimension configuration for parallel coordinates"""
        dim = {
            'range': range_vals,
            'label': label,
            'values': values
        }
        if tickformat:
            dim['tickformat'] = tickformat
        return dim
    
    @classmethod
    def create_plot(cls, results_df: pd.DataFrame, selected_indices: Optional[pd.Index] = None,
                   ranges: VisualizationRanges = None) -> go.Figure:
        """Creates a parallel coordinates plot"""
        if selected_indices is None:
            selected_mask = pd.Series(True, index=results_df.index)
        else:
            selected_mask = results_df.index.isin(selected_indices)
            
        if ranges is None:
            ranges = VisualizationRanges.from_dataframe(results_df)
            
        selected_df = results_df.loc[selected_mask]
        unselected_df = results_df.loc[~selected_mask]
        
        fig = go.Figure()
        
        # Add selected data trace
        if not selected_df.empty:
            cls._add_trace(fig, selected_df, ranges, is_selected=True)
            
        # Add unselected data trace
        if not unselected_df.empty:
            cls._add_trace(fig, unselected_df, ranges, is_selected=False)
        
        fig.update_layout(
            title='Multi-Dimensional Portfolio Optimization Result Pathways',
            height=600
        )
        
        return fig
    
    @staticmethod
    def _add_trace(fig: go.Figure, df: pd.DataFrame, ranges: VisualizationRanges, 
                   is_selected: bool = True):
        """Adds a trace to the parallel coordinates plot"""
        dimensions = [
            ParallelCoordinatesPlotter.create_dimension(
                'Turnover (%)', (ranges.turnover[0], ranges.turnover[1]),
                df['turnover'], '.1f'
            ),
            ParallelCoordinatesPlotter.create_dimension(
                'Active Risk (%)', (ranges.risk[0], ranges.risk[1]),
                df['active_total_risk'], '.3f'
            ),
            ParallelCoordinatesPlotter.create_dimension(
                'Max Sector Deviation', (ranges.optional_ranges['max_sector_deviation'][0], ranges.optional_ranges['max_sector_deviation'][1]),
                df['max_sector_deviation']
            ),
            ParallelCoordinatesPlotter.create_dimension(
                '# of Positions', (ranges.positions[0], ranges.positions[1]),
                df['maximum_positions']
            ),
            ParallelCoordinatesPlotter.create_dimension(
                'Expected Return (%)', (ranges.expected_return[0], ranges.expected_return[1]),
                df['expected_return'], '.3f'
            )
        ]
        
        line_props = (
            dict(
                color=df['expected_return'],
                colorscale='Hot',
                showscale=True,
                cmin=df['expected_return'].min(),
                cmax=df['expected_return'].max()
            )
            if is_selected else
            dict(color='rgba(200,200,200,1)')
        )
        
        fig.add_trace(go.Parcoords(line=line_props, dimensions=dimensions))


###  OPTIMIZATION HEALTH FIGURE BUILDERS  ###

def build_optimization_health_fig(frame):
    """
    build a donut chart with optimization run status distribution
    """
    
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

def build_recent_optimization_activity_plot(frame, num_recent=10):
    """
    build chart that plots most recent optimizations along with their status indicators
    """

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

def build_cumulative_optimizations_plot(frame):
    """
    Build sparkline chart to display cumulative optimization runs over time
    """
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

### OPTIMIZATION CONSTRAINT ANALYSIS FIGURE BUILDERS ###
from typing import Literal, Optional, Dict, Any
def create_distribution_plot(
    df: pd.DataFrame,
    x_column: str,
    y_column: str,
    plot_type: Literal['violin', 'box', 'combined', 'ridgeline', 'strip'] = 'violin',
    title: str = None,
    y_axis_title: str = None,
    x_axis_title: str = None,
    mode: Literal['group', 'overlay'] = 'overlay',
    color_scheme: Dict[str, Dict[str, str]] = None,
    show_points: bool = True,
    jitter: float = 0.3,
    custom_layout: Dict[str, Any] = None
) -> go.Figure:
    """
    Creates various distribution plots for visualizing data relationships.
    
    Parameters:
    -----------
    df : pandas DataFrame
        The dataframe containing the data
    x_column : str
        The column name for categories/grouping
    y_column : str
        The column name for values to visualize
    plot_type : str
        Type of plot to create ('violin', 'box', 'combined', 'ridgeline', 'strip')
    title : str, optional
        The title for the plot
    y_axis_title : str, optional
        The y-axis title
    x_axis_title : str, optional
        The x-axis title (used primarily for ridgeline plots)
    mode : str, optional
        'group' or 'overlay' mode for box and violin plots
    color_scheme : dict, optional
        Custom colors for different elements
    show_points : bool, optional
        Whether to show individual data points
    jitter : float, optional
        Amount of jitter for box plots
    custom_layout : dict, optional
        Additional layout parameters
        
    Returns:
    --------
    plotly.graph_objects.Figure
        The created figure object
    """
    # Set default values
    if title is None:
        title = f"{plot_type.title()} Plot"
    if y_axis_title is None:
        y_axis_title = y_column
    if x_axis_title is None:
        x_axis_title = "Values" if plot_type == 'ridgeline' else None
        
    # Create default color scheme if not provided
    if color_scheme is None:
        color_scheme = {
            'box': {
                'marker': 'rgb(9,56,125)',
                'line': 'rgb(9,56,125)'
            },
            'violin': {
                #'line': 'rgb(205,12,24)',
                'line': 'lightblue',
                #'fill': 'rgb(205,12,24)'
                'fill': 'lightblue'
            }
        }
    
    # Create figure
    fig = go.Figure()
    
    # Get sorted unique values from x_column
    categories = sorted(df[x_column].unique())
    
    # Determine points parameter for violin plots
    points_param = 'all' if show_points else False
    
    # Create the selected plot type
    if plot_type == 'violin':
        for value in categories:
            data = df.loc[df[x_column] == value][y_column]
            fig.add_trace(go.Violin(
                y=data,
                name=str(value),
                side='positive' if mode == 'overlay' else None,
                box_visible=True,
                meanline_visible=True,
                points=points_param,
                line_color=color_scheme['violin']['line'],
                fillcolor=color_scheme['violin']['fill']
            ))
        fig.update_layout(
            title=title,
            yaxis_title=y_axis_title,
            violinmode=mode
        )
    
    elif plot_type == 'box':
        for value in categories:
            data = df.loc[df[x_column] == value][y_column]
            fig.add_trace(go.Box(
                y=data,
                name=str(value),
                boxpoints='all' if show_points else 'outliers',
                jitter=jitter,
                whiskerwidth=0.2,
                marker_size=2,
                line_width=1,
                marker_color=color_scheme['box']['marker'],
                line_color=color_scheme['box']['line']
            ))
        fig.update_layout(
            title=title,
            yaxis_title=y_axis_title,
            boxmode=mode
        )
    
    elif plot_type == 'combined':
        for value in categories:
            data = df.loc[df[x_column] == value][y_column]
            # Add box plot
            fig.add_trace(go.Box(
                y=data,
                name=str(value),
                width=0.15,
                boxpoints='all' if show_points else None,
                jitter=jitter,
                marker_color=color_scheme['box']['marker'],
                line_color=color_scheme['box']['line'],
                showlegend=False
            ))
            
            # Add violin plot
            fig.add_trace(go.Violin(
                y=data,
                name=str(value),
                side='positive',
                line_color=color_scheme['violin']['line'],
                fillcolor=color_scheme['violin']['fill'],
                opacity=0.3,
                points=points_param
            ))
        fig.update_layout(
            title=title,
            yaxis_title=y_axis_title,
            violinmode=mode,
            boxmode=mode
        )
    
    elif plot_type == 'ridgeline':
        for value in categories:
            data = df.loc[df[x_column] == value][y_column]
            fig.add_trace(go.Violin(
                x=data,
                y=[value] * len(data),
                name=str(value),
                orientation='h',
                side='positive',
                width=2,
                points=points_param,
                #line_color=color_scheme['violin']['line'],
                #fillcolor=color_scheme['violin']['fill']
            ))
        fig.update_layout(
            title=title,
            xaxis_title=x_axis_title,
            showlegend=True
        )
    
    elif plot_type == 'strip':
        for value in categories:
            data = df.loc[df[x_column] == value][y_column]
            fig.add_trace(go.Box(
                y=data,
                name=str(value),
                boxpoints='all',
                jitter=jitter,
                pointpos=0,
                marker_color='rgba(7,7,7,0.3)',
                line_color='rgba(0,0,0,0)'
            ))
        fig.update_layout(
            title=title,
            yaxis_title=y_axis_title
        )
    
    # Apply any custom layout parameters
    if custom_layout:
        fig.update_layout(**custom_layout)
    
    return fig


### OPTIMIZATION TRADE/SECURITY ANALYSIS FIGURE BUILDERS ###

def build_security_action_frequency_fig(trade_stats_frame, portfolio):
    """
    build security action frequency figure - display optimization counts for each security by Buys/Sells/New Holdings/Liquidated Holdings
    """

    # Use your existing trade_stats_frame
    fig = go.Figure()

    trade_types = ['Buys', 'Sells', 'New Holdings', 'Liquidated Holdings']
    colors = ['green', 'red', 'blue', 'orange']

    for trade_type, color in zip(trade_types, colors):
        if trade_type in trade_stats_frame.columns:
            fig.add_trace(go.Bar(
                name=trade_type,
                x=trade_stats_frame.index,
                y=trade_stats_frame[trade_type],
                marker_color=color
            ))

    fig.update_layout(
        barmode='stack',
        title=f'Security Action Frequency for {portfolio}',
        xaxis_title='Security',
        yaxis_title='Number of Optimizations',
        height=600,
        xaxis={'categoryorder':'total descending'}
    )

    fig_box = go.FigureWidget(fig)

    return fig_box

def build_security_trade_consistency_fig(
        trade_stats_frame,
        portfolio,
        ticker_display='nearby' # nearby or activity
        ):
    """
    build security trade consistency figure of buy consistency vs sell consistency
    size represents total actions
    color represents trade type distribution
    """
    
    # Clean up ticker names by removing exchange code
    df_for_plot = trade_stats_frame.reset_index()
    df_for_plot['ticker'] = df_for_plot['ticker'].str.split(' ').str[0]

    # Create the scatter plot with improved formatting
    fig = px.scatter(df_for_plot, 
                    x='buy_consistency', 
                    y='sell_consistency',
                    size='total_actions',
                    text='ticker',
                    color='buy_consistency',
                    title=f'Security Consistency Analysis for {portfolio}',
                    labels={'buy_consistency': 'Buy Consistency Ratio',
                            'sell_consistency': 'Sell Consistency Ratio',
                            'new_holdings_consistency': 'New Holdings Ratio'})

    # Adjust text display - only show text for points with significant activity
    fig.update_traces(
        textposition='top center',
        textfont_size=9,  # Smaller text size
        texttemplate='%{text}',  # Show only ticker text
        selector=dict(mode='markers+text'),
        marker=dict(
            sizemode='area',
            sizeref=2.*max(df_for_plot['total_actions'])/(30.**2),  # Adjust this divisor to make markers smaller
            sizemin=3  # Minimum marker size
        ),
    )

    # Calculate which tickers to display based on proximity
    def has_space_around(row, df, threshold=0.01):
        """Check if a point has space around it"""
        x, y = row['buy_consistency'], row['sell_consistency']
        # Find points within threshold distance
        nearby = df[
            (abs(df['buy_consistency'] - x) < threshold) & 
            (abs(df['sell_consistency'] - y) < threshold) &
            (df.index != row.name)  # Exclude the current point
        ]
        return len(nearby) == 0

    if ticker_display == 'nearby':
        # Identify tickers with space around them
        df_for_plot['show_label'] = df_for_plot.apply(lambda row: has_space_around(row, df_for_plot), axis=1)

        # Update text to only show labels for tickers with space
        fig.for_each_trace(
            lambda trace: trace.update(text=df_for_plot['ticker'].where(df_for_plot['show_label'], ''))
        )
    else:
        # Only show text for securities with significant activity
        threshold = df_for_plot['total_actions'].quantile(0.9)  # Top 10% most active
        fig.for_each_trace(
            lambda trace: trace.update(text=df_for_plot['ticker'].where(df_for_plot['total_actions'] >= threshold, ''))
        )

    # Update layout for better spacing
    fig.update_layout(
        height=1000,  # Taller chart
        width=1500,   # Wider chart
        xaxis=dict(
            range=[-0.05, 1.05],  # Add padding to x-axis
            tickmode='linear',
            tick0=0,
            dtick=0.1,  # Show ticks every 0.1
            gridwidth=1,
            gridcolor='LightGray'
        ),
        yaxis=dict(
            range=[-0.05, 1.05],  # Add padding to y-axis
            tickmode='linear',
            tick0=0,
            dtick=0.1,  # Show ticks every 0.1
            gridwidth=1,
            gridcolor='LightGray'
        ),
        showlegend=False,
        hovermode='closest'
    )

    # Add hover info with full details
    fig.update_traces(
        customdata=df_for_plot['ticker'],
        hovertemplate="<b>%{customdata}</b><br>" +
                    "Buy Consistency: %{x:.2f}<br>" +
                    "Sell Consistency: %{y:.2f}<br>" +
                    "Total Actions: %{marker.size}<br>" +
                    "<extra></extra>"
    )

    fig_box = go.FigureWidget(fig)

    return fig_box

def build_security_actions_treemap(trade_stats_frame, portfolio):
    """
    build treemap to display distribution of trade actions for securities grouped by trade action
    """

    # Create a treemap visualization
    melted_trade_stats = trade_stats_frame[['Buys','Sells','New Holdings','Liquidated Holdings']].reset_index().melt(
        id_vars=['ticker'],
        var_name='action_type',
        value_name='count'
    )
    melted_trade_stats = melted_trade_stats[melted_trade_stats['count'] > 0]

    fig = px.treemap(melted_trade_stats,
                    path=['action_type', 'ticker'],
                    values='count',
                    title=f'Security Actions Treemap for {portfolio}',
                    color='action_type',
                    color_discrete_map={'Buys': 'green', 
                                        'Sells': 'red', 
                                        'New Holdings': 'blue', 
                                        'Liquidated Holdings': 'orange'})

    fig.update_layout(height=700)
    fig_box = go.FigureWidget(fig)

    return fig_box







# def create_efficient_frontier_plot(frame):
#     """
#     Creates an enhanced efficient frontier plot showing a horizontal parabola that encompasses
#     the optimization results. The parabola consists of two parts:
#     1. The upper curve (orange) representing the efficient frontier
#     2. The lower curve (light grey) representing inefficient portfolios
#     Both curves meet at a vertex near the minimum observed risk value.
#     """
#     def create_hover_text(row):
#         try:
#             risk_constraint = float(row['risk_constraint'])
#             risk_constraint_text = f"{risk_constraint:.3f}%"
#         except (ValueError, TypeError):
#             risk_constraint_text = str(row['risk_constraint'])
        
#         return (
#             f"Task ID: {row['task_id']}<br>" +
#             f"Risk: {row['actual_risk']:.3f}%<br>" +
#             f"Return: {row['expected_return']:.3f}%<br>" +
#             f"Positions: {row['actual_pos']}<br>" +
#             f"Turnover: {row['actual_turnover']:.2f}%<br>" +
#             f"Active Risk: {risk_constraint_text}"
#         )
    
#     hover_text = frame.apply(create_hover_text, axis=1)
    
#     # Create figure
#     fig = go.Figure()
    
#     # Add optimization results as scatter points
#     fig.add_trace(
#         go.Scatter(
#             x=frame['actual_risk'],
#             y=frame['expected_return'],
#             mode='markers',
#             name='Optimization Results',
#             marker=dict(
#                 size=5,  # Smaller points as requested
#                 color='blue'
#             ),
#             text=hover_text,
#             hovertemplate="%{text}<extra></extra>"
#         )
#     )
    
#     # Find the vertex point for our parabola
#     min_risk = frame['actual_risk'].min() * 0.98  # Slightly left of minimum observed risk
    
#     # Get points for upper and lower curves
#     df_sorted = frame.sort_values('actual_risk')
#     risk_buckets = pd.qcut(df_sorted['actual_risk'], 20)
    
#     # Calculate upper frontier points
#     max_returns = df_sorted.groupby(risk_buckets, observed=True)['expected_return'].max().reset_index()
#     max_returns['actual_risk'] = df_sorted.groupby(risk_buckets, observed=True)['actual_risk'].mean().values
    
#     # Calculate lower boundary points ensuring we encompass all points
#     min_returns = []
#     for risk in np.linspace(frame['actual_risk'].min(), frame['actual_risk'].max(), 20):
#         nearby_points = frame[
#             (frame['actual_risk'] >= risk - 0.001) & 
#             (frame['actual_risk'] <= risk + 0.001)
#         ]
#         if not nearby_points.empty:
#             # Use a lower percentile to ensure boundary encompasses points
#             min_returns.append({
#                 'actual_risk': risk,
#                 'expected_return': nearby_points['expected_return'].quantile(0.01)
#             })
#     min_returns = pd.DataFrame(min_returns)
    
#     # Fit parabolic curves that meet at the vertex
#     # For upper curve
#     upper_mask = max_returns['actual_risk'] >= min_risk
#     upper_coeffs = np.polyfit(
#         max_returns.loc[upper_mask, 'actual_risk'],
#         max_returns.loc[upper_mask, 'expected_return'],
#         2
#     )
#     upper_poly = np.poly1d(upper_coeffs)
    
#     # For lower curve
#     lower_mask = min_returns['actual_risk'] >= min_risk
#     lower_coeffs = np.polyfit(
#         min_returns.loc[lower_mask, 'actual_risk'],
#         min_returns.loc[lower_mask, 'expected_return'],
#         2
#     )
#     lower_poly = np.poly1d(lower_coeffs)
    
#     # Generate points for curves
#     x_range = np.linspace(min_risk, frame['actual_risk'].max() * 1.02, 100)
#     upper_y = upper_poly(x_range)
#     lower_y = lower_poly(x_range)
    
#     # Add efficient frontier (upper curve)
#     fig.add_trace(
#         go.Scatter(
#             x=x_range,
#             y=upper_y,
#             mode='lines',
#             name='Efficient Frontier',
#             line=dict(
#                 color='orange',
#                 width=2
#             ),
#             hovertemplate=(
#                 "Risk: %{x:.3f}<br>" +
#                 "Return: %{y:.3f}<br>" +
#                 "<extra></extra>"
#             )
#         )
#     )
    
#     # Add lower boundary
#     fig.add_trace(
#         go.Scatter(
#             x=x_range,
#             y=lower_y,
#             mode='lines',
#             name='Lower Boundary',
#             line=dict(
#                 color='rgba(200,200,200,0.8)',  # Light solid grey
#                 width=1.5
#             ),
#             hovertemplate=(
#                 "Risk: %{x:.3f}<br>" +
#                 "Return: %{y:.3f}<br>" +
#                 "<extra></extra>"
#             )
#         )
#     )
    
#     # Configure layout
#     fig.update_layout(
#         title='Portfolio Optimization Efficient Frontier',
#         xaxis_title='Risk (%)',
#         yaxis_title='Expected Return (%)',
#         hovermode='closest',
#         height=600,
#         width=800,
#         showlegend=True,
#         template='plotly_white',
#         # Set axes to start at 0 while maintaining appropriate data range
#         xaxis=dict(
#             range=[0, frame['actual_risk'].max() * 1.1],
#             zeroline=True,
#             zerolinewidth=1,
#             zerolinecolor='black'
#         ),
#         yaxis=dict(
#             range=[0, frame['expected_return'].max() * 1.1],
#             zeroline=True,
#             zerolinewidth=1,
#             zerolinecolor='black'
#         )
#     )
    
#     return fig
        



# def create_3d_efficient_frontier(results_df):
#     """
#     Creates an interactive 3D scatter plot showing the efficient frontier surface
#     """
#     fig = go.Figure()
    
#     # Create a scatter plot for each turnover constraint
#     for turnover in results_df['turnover_constraint'].unique():
#         mask = results_df['turnover_constraint'] == turnover
#         data = results_df[mask]
        
#         fig.add_trace(go.Scatter3d(
#             x=data['actual_turnover'],
#             y=data['actual_risk'],
#             z=data['expected_return'],
#             name=f'Turnover {turnover}',
#             mode='markers',
#             marker=dict(
#                 size=8,
#                 opacity=0.8,
#             ),
#             hovertemplate=(
#                 "Turnover: %{x:.2f}%<br>" +
#                 "Active Risk: %{y:.2f}%<br>" +
#                 "Expected Return: %{z:.2f}%<br>" +
#                 "<extra></extra>"
#             )
#         ))
    
#     fig.update_layout(
#         title='Portfolio Optimization Efficient Frontier',
#         scene=dict(
#             xaxis_title='Turnover (%)',
#             yaxis_title='Active Risk (%)',
#             zaxis_title='Expected Return (%)',
#             camera=dict(
#                 eye=dict(x=1.5, y=1.5, z=1.5)
#             )
#         ),
#         showlegend=True,
#         template='plotly_dark',
#         height=800
#     )
    
#     return fig
        


# def create_multi_view_scatter(results_df):
#     """
#     Creates a grid of 2D scatter plots showing different metric relationships
#     """
#     fig = make_subplots(
#         rows=1, cols=3,
#         subplot_titles=(
#             'Risk vs Return',
#             'Turnover vs Return',
#             'Risk vs Turnover'
#         )
#     )
    
#     for turnover in results_df['turnover_constraint'].unique():
#         mask = results_df['turnover_constraint'] == turnover
#         data = results_df[mask]
        
#         # Risk vs Return
#         fig.add_trace(
#             go.Scatter(
#                 x=data['actual_risk'],
#                 y=data['expected_return'],
#                 name=f'Turnover {turnover}',
#                 mode='markers',
#                 showlegend=True,
#                 hovertemplate=(
#                     "Risk: %{x:.2f}%<br>" +
#                     "Return: %{y:.2f}%<br>" +
#                     "<extra></extra>"
#                 )
#             ),
#             row=1, col=1
#         )
        
#         # Turnover vs Return
#         fig.add_trace(
#             go.Scatter(
#                 x=data['actual_turnover'],
#                 y=data['expected_return'],
#                 name=f'Turnover {turnover}',
#                 mode='markers',
#                 showlegend=False,
#                 hovertemplate=(
#                     "Turnover: %{x:.2f}%<br>" +
#                     "Return: %{y:.2f}%<br>" +
#                     "<extra></extra>"
#                 )
#             ),
#             row=1, col=2
#         )
        
#         # Risk vs Turnover
#         fig.add_trace(
#             go.Scatter(
#                 x=data['actual_risk'],
#                 y=data['actual_turnover'],
#                 name=f'Turnover {turnover}',
#                 mode='markers',
#                 showlegend=False,
#                 hovertemplate=(
#                     "Risk: %{x:.2f}%<br>" +
#                     "Turnover: %{y:.2f}%<br>" +
#                     "<extra></extra>"
#                 )
#             ),
#             row=1, col=3
#         )
    
#     fig.update_layout(
#         height=400,
#         width=1200,
#         title_text="Optimization Results - Multiple Views",
#         template='plotly_dark'
#     )
    
#     # Update axes labels
#     fig.update_xaxes(title_text="Active Risk (%)", row=1, col=1)
#     fig.update_yaxes(title_text="Expected Return (%)", row=1, col=1)
    
#     fig.update_xaxes(title_text="Turnover (%)", row=1, col=2)
#     fig.update_yaxes(title_text="Expected Return (%)", row=1, col=2)
    
#     fig.update_xaxes(title_text="Active Risk (%)", row=1, col=3)
#     fig.update_yaxes(title_text="Turnover (%)", row=1, col=3)
    
#     return fig

# # Create and show the multi-view plot
# fig_multi = create_multi_view_scatter(frame)
# fig_multi.show()
        


# # Create a radar chart to compare different solutions
# def create_solution_comparison_radar(results_df):
#     """
#     Creates a radar chart comparing key metrics across different solutions
#     """
#     # Normalize the metrics to a 0-1 scale for comparison
#     metrics = ['expected_return', 'actual_risk', 'actual_turnover', 'actual_pos']
#     normalized_df = results_df.copy()
    
#     for metric in metrics:
#         min_val = results_df[metric].min()
#         max_val = results_df[metric].max()
#         normalized_df[metric] = (results_df[metric] - min_val) / (max_val - min_val)
    
#     fig = go.Figure()
    
#     # Add a trace for each solution
#     for idx, row in normalized_df.iterrows():
#         fig.add_trace(go.Scatterpolar(
#             r=[row['expected_return'], row['actual_risk'], row['actual_turnover'], row['actual_pos']],
#             theta=['Return', 'Risk', 'Turnover', '# of Positions'],
#             # name=f"Solution {idx}",
#             name=f"Task ID: {row['task_id']}",
#             fill='toself'
#         ))
    
#     fig.update_layout(
#         polar=dict(
#             radialaxis=dict(
#                 visible=True,
#                 range=[0, 1]
#             )),
#         showlegend=True,
#         title='Solution Comparison - Normalized Metrics'
#     )
    
#     return fig




# # Create a sensitivity analysis visualization
# def create_sensitivity_analysis(results_df):
#     """
#     Creates a visualization showing how sensitive outcomes are to constraint changes
#     """
#     fig = go.Figure()
    
#     # Calculate the gradient of expected return with respect to constraints
#     for turnover in results_df['turnover_constraint'].unique():
#         data = results_df[results_df['turnover_constraint'] == turnover]
        
#         # Sort by risk constraint to show sensitivity
#         data = data.sort_values('actual_risk')
        
#         fig.add_trace(go.Scatter(
#             x=data['actual_risk'],
#             y=data['expected_return'],
#             mode='lines+markers',
#             name=f'Turnover {turnover}',
#             line=dict(width=2),
#             marker=dict(size=8),
#         ))
        
#         # Add error bands to show solution stability
#         fig.add_trace(go.Scatter(
#             x=data['actual_risk'],
#             y=data['expected_return'] * 1.05,  # Upper bound
#             mode='lines',
#             line=dict(width=0),
#             showlegend=False,
#             fillcolor='rgba(68, 68, 68, 0.3)',
#             fill='tonexty'
#         ))
    
#     fig.update_layout(
#         title='Solution Sensitivity to Constraint Changes',
#         xaxis_title='Active Risk (%)',
#         yaxis_title='Expected Return (%)',
#         template='plotly_dark'
#     )
    
#     return fig

        

# ['aggrnyl', 'agsunset', 'algae', 'amp', 'armyrose', 'balance',
#              'blackbody', 'bluered', 'blues', 'blugrn', 'bluyl', 'brbg',
#              'brwnyl', 'bugn', 'bupu', 'burg', 'burgyl', 'cividis', 'curl',
#              'darkmint', 'deep', 'delta', 'dense', 'earth', 'edge', 'electric',
#              'emrld', 'fall', 'geyser', 'gnbu', 'gray', 'greens', 'greys',
#              'haline', 'hot', 'hsv', 'ice', 'icefire', 'inferno', 'jet',
#              'magenta', 'magma', 'matter', 'mint', 'mrybm', 'mygbm', 'oranges',
#              'orrd', 'oryel', 'oxy', 'peach', 'phase', 'picnic', 'pinkyl',
#              'piyg', 'plasma', 'plotly3', 'portland', 'prgn', 'pubu', 'pubugn',
#              'puor', 'purd', 'purp', 'purples', 'purpor', 'rdbu',
#              'rdgy', 'rdpu', 'rdylbu', 'rdylgn', 'redor', 'reds', 'solar',
#              'spectral', 'speed', 'sunset', 'sunsetdark', 'teal', 'tealgrn',
#              'tealrose', 'tempo', 'temps', 'thermal', 'tropic', 'turbid',
#              'turbo', 'twilight', 'viridis', 'ylgn', 'ylgnbu', 'ylorbr',
#              'ylorrd']