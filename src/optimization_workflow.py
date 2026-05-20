# optimization_workflow.py


"""
This file contains low-level functions that handle specific optimization tasks:

API Communication

send_optimization_request(): Sends requests to the Bloomberg API
poll_optimization_result(): Polls for results until completion
get_optimization_response(): Combines the above functions


Task Management

build_optimization_request(): Formats tasks for the API
register_optimization_tasks(): Creates and registers optimization tasks
build_task(): Builds optimization tasks from parameters


Results Handling

display_optimization_response(): Shows results in a readable format
run_pending_optimizations(): Executes pending optimization tasks
generate_optimization_report(): Creates HTML reports of results
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import time
from datetime import datetime

from .optimization_tracker import OptimizationTracker
from .config_loader import load_optimization_config, generate_all_parameter_combinations
from .task_builder import build_task
from .template_utils import load_trade_universe_mappings, load_goal_mappings, load_constraint_mappings
from .api_config import (
    OPTIMIZATION_TRIGGER_ENDPOINT, 
    RESULTS_RETRIEVAL_ENDPOINT,
    WAIT_TIME_SECONDS,
    get_authorization_headers
)



def send_optimization_request(optimization_request: dict, task_optimization_id: str, auth_headers={}, tracker=None):
    """
    Sends the initial POST request to start the optimization.
    
    Parameters:
    - optimization_request: The optimization request payload
    - task_optimization_id: Our internally generated optimization ID (for tracker)
    - auth_headers: Authentication headers
    - tracker: Optional tracker object to update optimization status
    
    Returns:
    - api_optimization_id: The ID returned by the API for polling
    - initial_response_json: The full response data
    
    Raises exceptions if the request fails
    """
    auth_headers = auth_headers or {}
    
    try:
        initial_response = requests.post(
            OPTIMIZATION_TRIGGER_ENDPOINT,
            data=json.dumps(optimization_request),
            headers={'Content-Type': 'application/json', **auth_headers}
        )
        
        initial_response.raise_for_status()
        initial_response_json = initial_response.json()
        api_optimization_id = initial_response_json['optimizationId']
        
        # Update tracker using our task optimization ID
        if tracker:
            tracker.update_optimization_status(task_optimization_id, api_generated_id=api_optimization_id, status="RUNNING")
            
        return api_optimization_id, initial_response_json
        
    except requests.exceptions.RequestException as e:
        error_message = f"Failed to start optimization: {str(e)}"
        
        # Additional error details if available
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                error_message += f" - Details: {error_details}"
            except:
                error_message += f" - Status code: {e.response.status_code}"
        
        # Update tracker with our task optimization ID
        if tracker:
            tracker.update_optimization_status(task_optimization_id, status="FAILED", error_message=error_message)
            
        raise RuntimeError(error_message)


def poll_optimization_result(api_optimization_id: str, task_optimization_id: str, 
                            auth_headers={}, max_retries=30, 
                            initial_wait=WAIT_TIME_SECONDS, tracker=None):
    """
    Polls the optimization result endpoint until completion or failure.
    
    Parameters:
    - api_optimization_id: The ID returned by the API for polling
    - task_optimization_id: Our internally generated optimization ID (for tracker)
    - auth_headers: Authentication headers
    - max_retries: Maximum number of retry attempts
    - initial_wait: Initial wait time between retries (in seconds)
    - tracker: Optional tracker object to update status
    
    Returns:
    - The final optimization result
    
    Raises exceptions if polling fails
    """
    auth_headers = auth_headers or {}
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            opt_response = requests.get(
                RESULTS_RETRIEVAL_ENDPOINT + api_optimization_id,
                headers=auth_headers
            )
            
            # Success case - optimization completed
            if opt_response.status_code == 200:
                result = opt_response.json()
                    
                return result
                
            # Still processing - continue polling
            elif opt_response.status_code == 202:
                wait_time = initial_wait * (1.1 ** retry_count)  # Exponential backoff
                time.sleep(wait_time)
                retry_count += 1
                
            # Error case - unexpected status code
            else:
                error_data = opt_response.json() if opt_response.text else {"message": "Unknown error"}
                error_message = f"Error retrieving optimization results: {opt_response.status_code} - {error_data}"
                
                # Update tracker using our task optimization ID
                if tracker:
                    tracker.update_optimization_status(task_optimization_id, status="FAILED", error_message=error_message)
                    
                return error_data
                
        except requests.exceptions.RequestException as e:
            error_message = f"Error polling optimization results: {str(e)}"
            
            # Update tracker using our task optimization ID
            if tracker:
                tracker.update_optimization_status(task_optimization_id, status="FAILED", error_message=error_message)
                
            raise RuntimeError(error_message)
    
    # Handle case where max retries exceeded
    timeout_message = f"Optimization polling timed out after {max_retries} attempts"
    
    # Update tracker using our task optimization ID
    if tracker:
        tracker.update_optimization_status(task_optimization_id, status="FAILED", error_message=timeout_message)
        
    raise TimeoutError(timeout_message)


def get_optimization_response(optimization_request: dict, task_optimization_id: str, auth_headers={}, tracker=None):
    """
    Sends the optimization request and polls until the results are ready.
    
    Parameters:
    - optimization_request: The optimization request payload
    - task_optimization_id: Our internally generated optimization ID (for tracker)
    - auth_headers: Authentication headers
    - tracker: Optional tracker object to update optimization status
    
    Returns:
    - The optimization result
    """

    auth_headers = auth_headers or {}
    
    try:
        # Start the optimization
        api_optimization_id, _ = send_optimization_request(
            optimization_request, 
            task_optimization_id,
            auth_headers=auth_headers,
            tracker=tracker
        )
        
        # Poll for the result
        return poll_optimization_result(
            api_optimization_id,
            task_optimization_id,
            auth_headers=auth_headers,
            tracker=tracker
        )
        
    except Exception as e:
        # Handle any unexpected exceptions
        error_message = f"Optimization failed: {str(e)}"
        
        # Update tracker using our task optimization ID
        if tracker:
            tracker.update_optimization_status(task_optimization_id, status="FAILED", error_message=error_message)
            
        # Re-raise the exception for the caller to handle
        raise


def build_optimization_request(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build full optimization request from task.
    
    Args:
        task: Optimization task dictionary
    
    Returns:
        Complete optimization request for API
    """
    
    # trade_univ = [
    #     {
    #         "instrumentSource": {
    #             "id": task['benchmarkId'],
    #             "type": "INDEX_TICKER"
    #         },
    #         "tradingRule": "BUY_AND_SELL",
    #         "useAsSecondaryBenchmark": False,
    #     },
    # ]
    
    return {
        ## PORTFOLIO ##
        "portfolio": {
            "id": task['portfolioId'],
            "type": "PORTFOLIO_NAME"
        },
        ## BENCHMARK ##
        "benchmark": {
            "id": task['benchmarkId'],
            "type": "INDEX_TICKER"
        },
        ## TRADE UNIVERSES ##
        #"tradeUniverse": trade_univ,
        "tradeUniverse": task['tradeUniverse'],
        ## OPTIMIZATION TASK ##
        "task": {
            "goals": task['goals'],
            "portfolioConstraints": task['portfolioConstraints'],
            "instrumentConstraints": task['instrumentConstraints'],
            "riskOptions": task['riskOptions'],
            "options": task['options']
        },
        
        ## ADDITIONAL ##
        "asOfDate": task['asOfDate'],
        "reportingCurrency": "USD",
        "saveTo": task['saveTo'] if 'saveTo' in task else "NONE",
        "enableLookThrough": task['enableLookThrough'] if 'enableLookThrough' in task else False,
        "infusedCashAmount": task['infusedCashAmount'] if 'infusedCashAmount' in task else 0
    }


def display_optimization_response(tracker: OptimizationTracker, optimization_id: str):
    """
    Display optimization response in a user-friendly format.
    
    Args:
        tracker: OptimizationTracker instance
        optimization_id: The optimization ID to load
    """

    results = tracker.load_optimization_results(optimization_id)
    print(results['summary'])


def register_optimization_tasks(
    config_path: str = "config/optimization_parameters.yaml",
    trade_univ_mappings_path: str = "config/trade_universe_mappings.yaml",
    goal_mappings_path: str = "config/goal_mappings.yaml",
    constraint_mappings_path: str = "config/constraint_mappings.yaml",
    tasks_dir: str = "tasks",
    tracker: Optional[OptimizationTracker] = None
) -> List[str]:
    """
    Register all optimization tasks from configuration.
    
    Args:
        config_path: Path to optimization parameters YAML
        mappings_path: Path to constraint mappings YAML
        tasks_dir: Directory to save task JSON files
        tracker: OptimizationTracker instance (creates new one if None)
        
    Returns:
        List of registered optimization IDs
    """
    # Ensure tasks directory exists
    os.makedirs(tasks_dir, exist_ok=True)
    
    # Create tracker if not provided
    if tracker is None:
        tracker = OptimizationTracker()
    
    # Load configurations
    config = load_optimization_config(config_path)
    trade_universe_mappings = load_trade_universe_mappings(trade_univ_mappings_path)
    goal_mappings = load_goal_mappings(goal_mappings_path)
    constraint_mappings = load_constraint_mappings(constraint_mappings_path)
    
    # Generate all parameter combinations
    all_params = generate_all_parameter_combinations(config)
    
    registered_ids = []
    
    # Register each task
    for params in all_params:
        task = build_task(params, trade_universe_mappings, goal_mappings, constraint_mappings)
        
        # Create a filename for this task
        import hashlib
        fs_friendly_id = hashlib.md5(params['optimization_id'].encode()).hexdigest()
        filename = f"{fs_friendly_id}.json"
        filepath = Path(tasks_dir) / filename
        
        # Save the task to a file
        with open(filepath, 'w') as file:
            json.dump(task, file, indent=2)
        
        # Register the task with the tracker
        optimization_id = tracker.register_optimization_task(task, str(filepath))
        registered_ids.append(optimization_id)
    
    return registered_ids



def run_pending_optimizations(
    tracker: OptimizationTracker,
    status: str = 'pending',
    max_runs: int = 5,
    delay_between_runs: int = 2,
    display_results=False
) -> List[str]:
    """
    Run pending optimizations that haven't been executed yet.
    
    Args:
        tracker: OptimizationTracker instance
        max_runs: Maximum number of optimizations to run
        delay_between_runs: Delay between runs in seconds
        display: Whether or not to display results of each run
        
    Returns:
        List of executed optimization IDs
    """

    # Get pending optimization tasks
    if status == 'pending':
        pending_tasks = tracker.get_pending_optimizations()
    elif status == 'FAILED':
        pending_tasks = tracker.get_failed_optimizations()
    else:
        raise ValueError("Invalid Status (valid optons are pending and FAILED)")
    
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
            
            # Submit the optimization request using our enhanced method
            opt_response = get_optimization_response(
                optimization_request=opt_request,
                task_optimization_id=optimization_id,
                auth_headers=get_authorization_headers(),
                tracker=tracker
            )
            
            # Save the optimization results
            tracker.save_optimization_results(
                optimization_id=optimization_id,
                opt_response=opt_response
            )
            
            if display_results:
                # Display the results
                display_optimization_response(tracker, optimization_id)
            
            executed_ids.append(optimization_id)
            
            # Add delay between runs to avoid overloading the API
            if delay_between_runs > 0 and task_record != tasks_to_run[-1]:
                time.sleep(delay_between_runs)
                
        except Exception as e:
            print(f"Error running optimization {optimization_id}: {str(e)}")
            
            # Update status to failed
            tracker.update_optimization_status(
                optimization_id=optimization_id,
                status='FAILED',
                error_message=str(e)
            )
    
    return executed_ids


def generate_optimization_report(
    tracker: OptimizationTracker,
    output_file: str = "optimization_report.html",
    filters: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a report of optimization runs with results.
    
    Args:
        tracker: OptimizationTracker instance
        output_file: Path to save the HTML report
        filters: Optional dictionary of filters to apply
        
    Returns:
        Path to the generated report file
    """
    # Get optimizations, filtered if specified
    if filters:
        df = tracker.filter_optimizations(**filters)
    else:
        df = tracker.index_df
    
    # Generate a simple HTML report
    html = f"""
    <html>
    <head>
        <title>Portfolio Optimization Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2 {{ color: #2c3e50; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ text-align: left; padding: 8px; border: 1px solid #ddd; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .success {{ color: green; }}
            .failed {{ color: red; }}
            .running {{ color: blue; }}
            .not-run {{ color: gray; }}
        </style>
    </head>
    <body>
        <h1>Portfolio Optimization Report</h1>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Optimization Runs</h2>
        <table>
            <tr>
                <th>Optimization ID</th>
                <th>Portfolio</th>
                <th>Benchmark</th>
                <th>As of Date</th>
                <th>Status</th>
                <th>Risk Model</th>
                <th>Max Active Risk</th>
                <th>Max Positions</th>
                <th>Max Turnover</th>
                <th>Run Timestamp</th>
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
                <td class="{status_class}">{row.get('status', '')}</td>
                <td>{row.get('risk_model', '')}</td>
                <td>{row.get('max_active_risk', '')}</td>
                <td>{row.get('max_positions', '')}</td>
                <td>{row.get('max_turnover', '')}</td>
                <td>{row.get('run_timestamp', '')}</td>
            </tr>
        """
    
    html += """
        </table>
    </body>
    </html>
    """
    
    # Save the HTML report
    with open(output_file, 'w') as f:
        f.write(html)
    
    return output_file


def view_optimization_report(tracker: OptimizationTracker, 
                             report_path: str="optimization_report.html") -> str:
    """
    Opens the optimization report in the default web browser.
    
    Args:
        tracker: The OptimizationTracker instance containing the data
        report_path: Optional custom path for the report
    """
    import webbrowser
    import os
    
    if not Path(report_path).exists():
        # Generate the report if it doesn't exist
        report_path = self.generate_optimization_report(tracker, "optimization_report.html")
    
    # Convert to URI and open
    abs_path = os.path.abspath(report_path)
    file_uri = f"file://{abs_path}"
    webbrowser.open(file_uri)
    
    return abs_path


if __name__ == "__main__":
    # Create the tracker
    tracker = OptimizationTracker()
    
    # Register optimization tasks
    print("Registering optimization tasks...")
    registered_ids = register_optimization_tasks(tracker=tracker)
    print(f"Registered {len(registered_ids)} optimization tasks")
    
    # Run pending optimizations
    print("Running pending optimizations...")
    executed_ids = run_pending_optimizations(tracker=tracker, max_runs=3)
    print(f"Executed {len(executed_ids)} optimizations")
    
    # Generate a report
    print("Generating optimization report...")
    report_file = generate_optimization_report(tracker=tracker)
    print(f"Report generated at: {report_file}")