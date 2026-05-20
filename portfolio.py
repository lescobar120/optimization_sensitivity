from typing import Dict, List, Optional, Any
from datetime import datetime
from enums import TaskStatus
from optimization import OptimizationTask, Optimizer, OptimizationResult

class Portfolio:
    """
    A class to manage optimization tasks for a specific portfolio.
    This class serves as a task manager for a portfolio identified by its ID,
    allowing you to create, store, and execute different optimization scenarios.
    """
    def __init__(self, portfolio_id: str, name: str):
        # Basic portfolio identification
        self.portfolio_id = portfolio_id
        self.name = name
        
        # Store optimization tasks associated with this portfolio
        self.optimization_tasks: Dict[str, OptimizationTask] = {}
        
        # Track when portfolio configuration was last modified
        self.last_modified = datetime.now()

    def create_task(
            self,
            name: str,
            description: str,
            benchmark_id: str,
            trade_universe: List[Dict],
            goals: List[Dict],
            portfolio_constraints: List[Dict],
            instrument_constraints: List[Dict],
            risk_options: Optional[Any] = None,
            enable_look_through: Optional[bool] = True,
            save_to: Optional[str] = 'TEMPORARY_PORTFOLIO',
            as_of_date: Optional[str] = None
        ) -> str:
        """
        Creates a new optimization task for this portfolio.
        
        Args:
            name: Name of the optimization task
            description: Detailed description of what the task does
            benchmark_id: ID of the benchmark to use (e.g., "SPX")
            trade_universe: List of trade universe configurations
            goals: List of optimization goals
            portfolio_constraints: List of portfolio-level constraints
            instrument_constraints: List of instrument-level constraints
            
        Returns:
            str: The ID of the created task
        """
        task = OptimizationTask(
            name=name,
            description=description,
            portfolio_id=self.portfolio_id,
            benchmark_id=benchmark_id,
            trade_universe=trade_universe,
            goals=goals,
            portfolio_constraints=portfolio_constraints,
            instrument_constraints=instrument_constraints,
            risk_options=risk_options,
            save_to=save_to,
            as_of_date=as_of_date,
            enable_look_through=enable_look_through
        )
        
        self.optimization_tasks[task.id] = task
        return task.id

    def get_task(self, task_id: str) -> Optional[OptimizationTask]:
        """
        Retrieves a specific optimization task by its ID.
        
        Args:
            task_id: The ID of the task to retrieve
            
        Returns:
            OptimizationTask if found, None otherwise
        """
        return self.optimization_tasks.get(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> Dict[str, Dict]:
        """
        Lists all optimization tasks for this portfolio, optionally filtered by status.
        
        Args:
            status: Optional filter for task status
            
        Returns:
            Dictionary of task summaries
        """
        tasks = self.optimization_tasks
        if status:
            tasks = {k: v for k, v in tasks.items() if v.status == status}
            
        return {
            task_id: {
                "name": task.name,
                "description": task.description,
                "status": task.status.value,
                "last_run": task.last_run,
                "benchmark_id": task.benchmark_id,
                "has_results": task.last_result is not None
            }
            for task_id, task in tasks.items()
        }

    def run_task(self, task_id: str, optimizer: Optimizer) -> OptimizationResult:
        """
        Executes a specific optimization task using the provided optimizer.
        
        Args:
            task_id: ID of the task to run
            optimizer: Initialized Optimizer instance with SDK client
            
        Returns:
            OptimizationResult containing the optimization results
            
        Raises:
            ValueError: If task_id is not found
            Exception: If optimization fails
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.status = TaskStatus.RUNNING
        
        try:
            result = optimizer.optimize(task)
            task.last_result = result
            task.last_run = datetime.now()
            task.status = TaskStatus.COMPLETED
            return result
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            raise Exception(f"Task execution failed: {str(e)}")

    def add_task_from_template(self, optimizer: Optimizer, template_name: str, benchmark_id: str) -> str:
        """
        Creates a new task from a template and adds it to this portfolio.
        
        Args:
            optimizer: Optimizer instance containing the template
            template_name: Name of the template to use
            benchmark_id: Benchmark ID for the new task
            
        Returns:
            str: ID of the created task
        """
        task = optimizer.create_task_from_template(
            template_name,
            self.portfolio_id,
            benchmark_id
        )
        self.optimization_tasks[task.id] = task
        return task.id