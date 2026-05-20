# cli.py
import argparse
import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional

from optimization_tracker import OptimizationTracker
from optimization_workflow import (
    register_optimization_tasks,
    run_pending_optimizations,
    generate_optimization_report
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Portfolio Optimization CLI')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Register command
    register_parser = subparsers.add_parser('register', help='Register optimization tasks')
    register_parser.add_argument('--config', default='config/optimization_parameters.yaml', 
                               help='Path to optimization parameters YAML')
    register_parser.add_argument('--goal-mappings', default='config/goal_mappings.yaml',
                               help='Path to goal mappings YAML')
    register_parser.add_argument('--constraint-mappings', default='config/constraint_mappings.yaml',
                               help='Path to constraint mappings YAML')
    register_parser.add_argument('--tasks-dir', default='tasks', 
                               help='Directory to save task JSON files')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run pending optimizations')
    run_parser.add_argument('--max-runs', type=int, default=5, 
                          help='Maximum number of optimizations to run')
    run_parser.add_argument('--delay', type=int, default=2,
                          help='Delay between optimization runs in seconds')
    run_parser.add_argument('--filter-portfolio', 
                          help='Only run optimizations for specified portfolio')
    run_parser.add_argument('--filter-benchmark', 
                          help='Only run optimizations for specified benchmark')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate optimization report')
    report_parser.add_argument('--output', default='optimization_report.html',
                             help='Output file for the report')
    report_parser.add_argument('--filter-portfolio',
                             help='Filter report by portfolio')
    report_parser.add_argument('--filter-benchmark',
                             help='Filter report by benchmark')
    report_parser.add_argument('--filter-status', choices=['success', 'failed', 'running', 'not_run'],
                             help='Filter report by optimization status')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List optimizations')
    list_parser.add_argument('--status', choices=['all', 'pending', 'success', 'failed', 'running'],
                           default='all', help='Filter by status')
    list_parser.add_argument('--portfolio',
                           help='Filter by portfolio')
    list_parser.add_argument('--benchmark',
                           help='Filter by benchmark')
    list_parser.add_argument('--output', default='console',
                           choices=['console', 'csv', 'json'],
                           help='Output format')
    list_parser.add_argument('--output-file',
                           help='Output file path (for csv/json output)')
    
    # View command
    view_parser = subparsers.add_parser('view', help='View optimization results')
    view_parser.add_argument('optimization_id', help='Optimization ID to view')
    view_parser.add_argument('--type', choices=['summary', 'goals', 'constraints', 'trades', 'all'],
                           default='all', help='Type of results to view')
    
    return parser.parse_args()


def main():
    """Main CLI function."""
    args = parse_args()
    
    if not args.command:
        print("Please specify a command. Use --help for more information.")
        return
    
    # Initialize the tracker
    tracker = OptimizationTracker()
    
    if args.command == 'register':
        print("Registering optimization tasks...")
        registered_ids = register_optimization_tasks(
            config_path=args.config,
            goal_mappings_path=args.goal_mappings,
            constraint_mappings_path=args.constraint_mappings,
            tasks_dir=args.tasks_dir,
            tracker=tracker
        )
        print(f"Registered {len(registered_ids)} optimization tasks")
    
    elif args.command == 'run':
        print("Running pending optimizations...")
        
        # Apply filters if specified
        filters = {}
        if hasattr(args, 'filter_portfolio') and args.filter_portfolio:
            filters['portfolio'] = args.filter_portfolio
        if hasattr(args, 'filter_benchmark') and args.filter_benchmark:
            filters['benchmark'] = args.filter_benchmark
        
        # Get filtered pending optimizations
        if filters:
            pending_df = tracker.filter_optimizations(status='not_run', **filters)
            pending_records = pending_df.to_dict('records')
            pending_ids = [record['optimization_id'] for record in pending_records]
            
            executed_ids = []
            for optimization_id in pending_ids[:args.max_runs]:
                # This is a simplified implementation - in practice, you would
                # need to modify the run_pending_optimizations function to accept
                # specific optimization IDs
                executed_id = run_single_optimization(tracker, optimization_id)
                if executed_id:
                    executed_ids.append(executed_id)
        else:
            # Run without filters
            executed_ids = run_pending_optimizations(
                tracker=tracker,
                max_runs=args.max_runs,
                delay_between_runs=args.delay
            )
        
        print(f"Executed {len(executed_ids)} optimizations")
    
    elif args.command == 'report':
        print("Generating optimization report...")
        
        # Apply filters if specified
        filters = {}
        if hasattr(args, 'filter_portfolio') and args.filter_portfolio:
            filters['portfolio'] = args.filter_portfolio
        if hasattr(args, 'filter_benchmark') and args.filter_benchmark:
            filters['benchmark'] = args.filter_benchmark
        if hasattr(args, 'filter_status') and args.filter_status:
            filters['status'] = args.filter_status
        
        report_file = generate_optimization_report(
            tracker=tracker,
            output_file=args.output,
            filters=filters if filters else None
        )
        print(f"Report generated at: {report_file}")
    
    elif args.command == 'list':
        # Get the filtered dataframe
        if args.status == 'all':
            df = tracker.index_df
        elif args.status == 'pending':
            df = tracker.index_df[tracker.index_df['status'] == 'not_run']
        else:
            df = tracker.index_df[tracker.index_df['status'] == args.status]
        
        # Apply additional filters
        if args.portfolio:
            df = df[df['portfolio'] == args.portfolio]
        if args.benchmark:
            df = df[df['benchmark'] == args.benchmark]
        
        # Output the results
        if args.output == 'console':
            # Print a simplified table to console
            print(f"Found {len(df)} optimizations:")
            if len(df) > 0:
                # Select relevant columns for display
                display_cols = ['optimization_id', 'portfolio', 'benchmark', 'as_of_date', 
                               'status', 'run_timestamp']
                print(df[display_cols].to_string(index=False))
        
        elif args.output == 'csv':
            output_file = args.output_file or 'optimization_list.csv'
            df.to_csv(output_file, index=False)
            print(f"Saved {len(df)} optimizations to {output_file}")
        
        elif args.output == 'json':
            output_file = args.output_file or 'optimization_list.json'
            df.to_json(output_file, orient='records', indent=2)
            print(f"Saved {len(df)} optimizations to {output_file}")
    
    elif args.command == 'view':
        try:
            # Load the specified optimization results
            results = tracker.load_optimization_results(args.optimization_id)
            
            # Display the requested data
            if args.type == 'all' or args.type == 'summary':
                print("\n=== SUMMARY ===")
                print(results['summary'].to_string(index=False))
            
            if args.type == 'all' or args.type == 'goals':
                print("\n=== GOALS ===")
                print(results['goals'].to_string(index=False))
            
            if args.type == 'all' or args.type == 'constraints':
                print("\n=== CONSTRAINTS ===")
                print(results['constraints'].to_string(index=False))
            
            if args.type == 'all' or args.type == 'trades':
                print("\n=== TRADES ===")
                # For trades, we might want to limit the output if there are many
                trades_df = results['trades']
                if len(trades_df) > 20:
                    print(f"Showing top 20 of {len(trades_df)} trades:")
                    print(trades_df.head(20).to_string(index=False))
                    print(f"... and {len(trades_df) - 20} more trades")
                else:
                    print(trades_df.to_string(index=False))
        
        except ValueError as e:
            print(f"Error: {str(e)}")


def run_single_optimization(tracker, optimization_id):
    """
    Run a specific optimization by ID.
    
    Args:
        tracker: OptimizationTracker instance
        optimization_id: ID of the optimization to run
        
    Returns:
        The executed optimization ID if successful, None otherwise
    """
    # This is a simplified version that would need to be implemented
    # based on the run_pending_optimizations function
    
    # In practice, you would:
    # 1. Get the task record from the tracker
    # 2. Load the task from its file
    # 3. Build and submit the optimization request
    # 4. Process and save the results
    
    print(f"Not implemented: would run optimization {optimization_id}")
    return None


if __name__ == "__main__":
    main()