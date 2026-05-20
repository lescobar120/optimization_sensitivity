# example_usage.py
import pandas as pd
import os
from workflow_manager import OptimizationWorkflowManager

# Initialize the workflow manager
manager = OptimizationWorkflowManager()

print("=== Portfolio Optimization Workflow Example ===")

# Step 1: Register optimization tasks from configuration
print("\n1. Registering optimization tasks...")
registered_ids = manager.register_tasks()
print(f"Registered {len(registered_ids)} optimization tasks")

# Step 2: Run a subset of pending optimizations
print("\n2. Running a subset of optimizations...")
executed_ids = manager.run_tasks(max_runs=3)
print(f"Executed {len(executed_ids)} optimizations")

# If no optimizations were executed, exit
if not executed_ids:
    print("No optimizations executed. Exiting.")
    exit()

# Step 3: Analyze constraint sensitivity
print("\n3. Analyzing constraint sensitivity...")
constraint_name = "max_active_risk"
sensitivity_df = manager.analyze_constraints(
    constraint_name=constraint_name,
    create_dashboard=True,
    show_dashboard=False
)
print(f"Sensitivity analysis results for {constraint_name}:")
print(sensitivity_df.head())

# Step 4: Calculate efficient frontier
print("\n4. Calculating efficient frontier...")
frontier_df = manager.analyze_efficient_frontier(
    x_goal="ActiveTotalRisk",
    y_goal="ExpectedReturn",
    create_dashboard=True,
    show_dashboard=False
)
print("Efficient frontier results:")
print(frontier_df.head())

# Step 5: Find optimal constraints
print("\n5. Finding optimal constraint values...")
optimal_df = manager.find_optimal_constraints(
    target_goal="ExpectedReturn",
    optimize_direction="maximize"
)
print("Optimal constraint values for maximizing ExpectedReturn:")
print(optimal_df.head())

# Step 6: Compare optimizations
print("\n6. Comparing optimizations...")
# Use the first two executed optimizations for comparison
comparison_ids = executed_ids[:min(2, len(executed_ids))]
comparisons = manager.compare_optimizations(
    optimization_ids=comparison_ids,
    create_dashboard=True,
    show_dashboard=False
)
print(f"Compared {len(comparison_ids)} optimizations")
print("Goals comparison:")
print(comparisons["goals"].head())

# Step 7: Create summary dashboard
print("\n7. Creating summary dashboard...")
dashboard_path = manager.create_summary_dashboard(show_dashboard=False)
print(f"Summary dashboard created at: {dashboard_path}")

# Step 8: Generate comprehensive report
print("\n8. Generating comprehensive report...")
report_path = manager.generate_report()
print(f"Report generated at: {report_path}")

print("\n=== Workflow Complete ===")
print("All results have been saved to disk.")
print(f"To view the summary dashboard:   file://{os.path.abspath(dashboard_path)}")
print(f"To view the comprehensive report: file://{os.path.abspath(report_path)}")