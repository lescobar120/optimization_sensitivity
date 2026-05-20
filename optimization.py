from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import time
import pandas as pd
from IPython.display import display
import bloomberg.enterprise.portfolio.optimization as SDK

import logging
from utils.logging_config import setup_logger

logger = setup_logger('optimization')


@dataclass
class OptimizationResult:
    """
    OptimizationResult class that handles both storage and display of optimization results.
    Integrates with the SDK's result retrieval and display functionality.
    """
    optimization_id: str
    response_data: Any
    created_at: datetime = field(default_factory=datetime.now)
    _detailed_result: Optional[Any] = None  # Cache for detailed results
    logger: logging.Logger = field(default_factory=lambda: setup_logger('optimization_result'))

    def wait_for_completion(self, optimization_api, max_attempts: int = 100, 
                          sleep_time: int = 1) -> bool:
        """
        Waits for optimization to complete and fetches results.
        
        Args:
            optimization_api: SDK optimization API instance
            max_attempts: Maximum number of polling attempts
            sleep_time: Seconds to wait between polling attempts
            
        Returns:
            bool: True if completed successfully, False otherwise
        """
        for attempt in range(max_attempts):
            response = optimization_api.retrieve_optimization(self.optimization_id)
            if response.status_code != 202:  # 202 means still processing
                self._detailed_result = response
                return response.status_code == 200
                
            print(f"Still waiting for result... (Attempt {attempt + 1}/{max_attempts})")
            time.sleep(sleep_time)
            
        return False

    def get_detailed_results(self, optimization_api, force_refresh: bool = False):
        """
        Retrieves detailed optimization results.
        
        Args:
            optimization_api: SDK optimization API instance
            force_refresh: Whether to force a refresh of cached results
            
        Returns:
            Detailed optimization results
        """
        if self._detailed_result is None or force_refresh:
            self._detailed_result = optimization_api.retrieve_optimization(self.optimization_id)
        return self._detailed_result

    def display_summary(self):
        """Displays a concise summary of optimization results"""

        if self._detailed_result is None:
            print("Results not yet retrieved. Call get_detailed_results first.")
            return

        obj_result = self._detailed_result.data
        
        print("\n=== Optimization Summary ===")
        print(f"Session ID: {obj_result.session_id}")
        print(f"Optimization ID: {self.optimization_id}")
        print(f"Created: {self.created_at}")
        
        if hasattr(obj_result, 'summary'):
            print("\nKey Metrics:")
            display(pd.DataFrame(obj_result.summary.to_dict(), index=[0]))

    def display_full_results(self):
        """Displays comprehensive optimization results with all available details"""
        
        if self._detailed_result is None:
            print("Results not yet retrieved. Call get_detailed_results first.")
            return

        obj_result = self._detailed_result.data

        # Display session information
        print("\n==================== Session ====================")
        print(f"Session ID: {obj_result.session_id}")

        # Display summary
        print("\n==================== Summary ====================")
        if hasattr(obj_result, 'summary'):
            display(pd.DataFrame(obj_result.summary.to_dict(), index=[0]))

        # Display goals
        print("\n==================== Goals ====================")
        if obj_result.goals:
            goals_df = pd.DataFrame([goal.to_dict() for goal in obj_result.goals])
            display(goals_df)

        # Display constraints
        if obj_result.constraints:
            print("\n==================== Constraints ====================")
            constraints_df = pd.DataFrame([con.to_dict() for con in obj_result.constraints])
            display(constraints_df)

        # Display trades
        if obj_result.proposed_trades:
            print("\n==================== Proposed Trades ====================")
            trades_list = []
            for trade in obj_result.proposed_trades:
                trade_dict = trade.to_dict()
                # Handle the nested quantity value
                trade_dict["changedQuantity"] = trade_dict["changedQuantity"]["value"]
                trades_list.append(trade_dict)
            trades_df = pd.DataFrame(trades_list)
            display(trades_df)

        # Display any failures
        if obj_result.failures:
            print("\n==================== Failures ====================")
            failures_df = pd.DataFrame([failure.to_dict() for failure in obj_result.failures])
            display(failures_df)

        # Display any exceptions
        if obj_result.exceptions:
            print("\n==================== Exceptions ====================")
            exceptions_df = pd.DataFrame([exception.to_dict() for exception in obj_result.exceptions])
            display(exceptions_df)


    def get_summary_dataframe(self) -> pd.DataFrame:
        """Returns optimization summary as a pandas DataFrame for further analysis."""
        if self._detailed_result is None or not self._detailed_result.data.summary:
            self.logger.debug("No summary data available")
            return pd.DataFrame()

        return pd.DataFrame(self._detailed_result.data.summary.to_dict(), index=[0])
    
    def get_goals_dataframe(self) -> pd.DataFrame:
        """Returns optimization goals as a pandas DataFrame for further analysis."""
        if self._detailed_result is None or not self._detailed_result.data.goals:
            self.logger.debug("No goals data available")
            return pd.DataFrame()
        
        goals_df = pd.DataFrame([goal.to_dict() for goal in self._detailed_result.data.goals])
        return goals_df
    
    def get_constraints_dataframe(self) -> pd.DataFrame:
        """Returns optimization constraints as a pandas DataFrame for further analysis."""
        if self._detailed_result is None or not self._detailed_result.data.constraints:
            self.logger.debug("No summary data available")
            return pd.DataFrame()

        constraints_df = pd.DataFrame([con.to_dict() for con in self._detailed_result.data.constraints])
        return constraints_df

    def get_trades_dataframe(self) -> pd.DataFrame:
        """Returns proposed trades as a pandas DataFrame for further analysis."""
        if self._detailed_result is None or not self._detailed_result.data.proposed_trades:
            self.logger.debug("No trades data available")
            return pd.DataFrame()

        try:
            trades_list = []
            for trade in self._detailed_result.data.proposed_trades:
                # Log the type and structure of each trade
                self.logger.debug(f"Processing trade: {type(trade)}")
                trade_dict = trade.to_dict()
                self.logger.debug(f"Trade dictionary structure: {trade_dict.keys()}")
                
                # Log the changedQuantity structure before processing
                self.logger.debug(f"instrumentUniqueId: {trade_dict['instrumentUniqueId']}")
                self.logger.debug(f"changedQuantity type: {type(trade_dict['changedQuantity'])}")
                self.logger.debug(f"changedQuantity value: {trade_dict['changedQuantity']}")
                
                # Handle the quantity conversion safely
                if isinstance(trade_dict['changedQuantity'], dict):
                    quantity = trade_dict['changedQuantity'].get('value')
                    self.logger.debug(f"Extracted quantity value: {quantity}")
                else:
                    self.logger.error(f"Unexpected changedQuantity type: {type(trade_dict['changedQuantity'])}")
                    quantity = trade_dict['changedQuantity']  # Use as is
                
                trade_dict["changedQuantity"] = quantity
                trades_list.append(trade_dict)
                
            return pd.DataFrame(trades_list)
            
        except Exception as e:
            self.logger.error(f"Error processing trades: {str(e)}", exc_info=True)
            self.logger.error(f"Current trade being processed: {trade_dict if 'trade_dict' in locals() else 'Not available'}")
            raise

    


@dataclass
class OptimizationTask:
    """
    Represents a specific optimization scenario using SDK structures
    """
    name: str
    description: str
    portfolio_id: str
    benchmark_id: str
    trade_universe: List[SDK.InitiateOptimizationTradeUniverseInner]
    goals: List[SDK.OptimizationGoal]
    portfolio_constraints: List[SDK.PortfolioConstraint]
    instrument_constraints: List[SDK.InstrumentConstraint]
    risk_options: Optional[Any] = None,
    as_of_date: Optional[str] = None
    enable_look_through: bool = True
    save_to: SDK.InitiateOptimizationSaveToEnum = 'TEMPORARY_ENTERPRISE_PORTFOLIO'
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    status: str = "DEFINED"
    last_result: Optional['OptimizationResult'] = None

    def __post_init__(self):
        """Validates task configuration after initialization"""
        logger.debug(f"Initializing optimization task: {self.name}")
        self._validate_configuration()

    def _validate_configuration(self):
        """Validates the task configuration"""
        try:
            # Log and validate each component
            logger.debug("Validating task configuration...")
            
            if not self.goals:
                logger.warning("No optimization goals specified")
            else:
                logger.debug(f"Goals configured: {len(self.goals)}")
                
            if self.portfolio_constraints:
                logger.debug(f"Portfolio constraints: {len(self.portfolio_constraints)}")
                
            if self.instrument_constraints:
                logger.debug(f"Instrument constraints: {len(self.instrument_constraints)}")

            if not self.as_of_date:
                self.as_of_date = datetime.now().date().strftime('%Y-%m-%d')
                
            logger.debug("Task configuration validation complete")
            
        except Exception as e:
            logger.error(f"Task configuration validation failed: {str(e)}")
            raise ValueError(f"Invalid task configuration: {str(e)}")

    def to_sdk_request(self) -> SDK.InitiateOptimization:
        """Creates the complete API request using the SDK types."""
        logger.debug(f"Creating SDK request for task: {self.id}")
        try:
            request = SDK.InitiateOptimization.new()
            
            # Log each step of request creation
            logger.debug("Setting portfolio source...")
            request.portfolio = SDK.PositionSource(id=self.portfolio_id, type="PORTFOLIO_NAME")
            
            logger.debug("Setting benchmark source...")
            request.benchmark = SDK.BenchmarkSource(id=self.benchmark_id, type="INDEX_TICKER")
            
            logger.debug("Setting trade universe...")
            request.trade_universe = self.trade_universe
            
            logger.debug("Creating optimization task...")
            request.task = SDK.InitiateOptimizationTask(
                SDK.OptimizationTask(
                    goals=self.goals,
                    portfolio_constraints=self.portfolio_constraints,
                    instrument_constraints=self.instrument_constraints
                )
            )
            
            logger.debug("SDK request created successfully")
            return request
            
        except Exception as e:
            logger.error(f"Failed to create SDK request: {str(e)}")
            raise Exception(f"Failed to create SDK request: {str(e)}")
    

class Optimizer:
    """Handles optimization requests using the SDK"""
    def __init__(self, client, SDK):
        self.client = client
        self.optimization_api = SDK.OptimizationsApi(base_api_client=client)
        self.task_templates = {}
        self.logger = setup_logger('optimizer')
        
    def optimize(self, task: OptimizationTask) -> OptimizationResult:
        """Execute optimization using SDK"""
        self.logger.info(f"Starting optimization for task: {task.name} ({task.id})")
        try:
            # Get the request object from the task
            self.logger.debug("Creating SDK request...")
            request = task.to_sdk_request()
            
            # Submit the optimization request
            self.logger.info("Submitting optimization request...")
            response = self.optimization_api.initiate_optimization(request)
            optimization_id = response.data.optimization_id
            
            self.logger.info(f"Optimization initiated successfully. ID: {optimization_id}")
            return OptimizationResult(
                optimization_id=optimization_id,
                response_data=response
            )
            
        except Exception as e:
            self.logger.error(f"Optimization failed: {str(e)}", exc_info=True)
            raise Exception(f"Optimization failed: {str(e)}")

    def save_task_template(self, task: OptimizationTask, template_name: str) -> None:
        """Saves task configuration as a template with detailed logging"""
        self.logger.info(f"Saving template: {template_name}")
        try:
            # Log the types of each component before saving
            self.logger.debug("Component types being saved:")
            for goal in task.goals:
                self.logger.debug(f"Goal type: {type(goal)}")
            for constraint in task.portfolio_constraints:
                self.logger.debug(f"Portfolio constraint type: {type(constraint)}")
            for constraint in task.instrument_constraints:
                self.logger.debug(f"Instrument constraint type: {type(constraint)}")

            template_data = {
                "name": task.name,
                "description": task.description,
                "trade_universe": task.trade_universe,
                "goals": task.goals,
                "portfolio_constraints": task.portfolio_constraints,
                "instrument_constraints": task.instrument_constraints,
                "save_to": task.save_to,
                "as_of_date": task.as_of_date,
                "enable_look_through": task.enable_look_through
            }
            
            # Log the saved template structure
            self.logger.debug("Template structure:")
            for key, value in template_data.items():
                self.logger.debug(f"{key}: {type(value)}")
            
            self.task_templates[template_name] = template_data
            
        except Exception as e:
            self.logger.error(f"Failed to save template: {str(e)}", exc_info=True)
            self.logger.error("Current template data structure:", exc_info=True)
            raise

    def create_task_from_template(self, template_name: str, portfolio_id: str, benchmark_id: str) -> OptimizationTask:
        """Creates a new task from a template with detailed logging"""
        self.logger.info(f"Creating task from template: {template_name}")
        
        if template_name not in self.task_templates:
            self.logger.error(f"Template '{template_name}' not found")
            raise ValueError(f"Template '{template_name}' not found")
            
        try:
            template = self.task_templates[template_name]
            
            # Log the types of components being loaded
            self.logger.debug("Template component types:")
            for key, value in template.items():
                self.logger.debug(f"{key}: {type(value)}")
                if isinstance(value, (list, tuple)):
                    for i, item in enumerate(value):
                        self.logger.debug(f"  {key}[{i}] type: {type(item)}")
            
            new_task = OptimizationTask(
                name=template["name"],
                description=template["description"],
                portfolio_id=portfolio_id,
                benchmark_id=benchmark_id,
                trade_universe=template["trade_universe"],
                goals=template["goals"],
                portfolio_constraints=template["portfolio_constraints"],
                instrument_constraints=template["instrument_constraints"],
                save_to=template["save_to"],
                as_of_date=template["as_of_date"],
                enable_look_through=template["enable_look_through"]
            )
            
            return new_task
            
        except Exception as e:
            self.logger.error(f"Failed to create task from template: {str(e)}", exc_info=True)
            self.logger.error("Template data being used:", exc_info=True)
            for key, value in template.items():
                self.logger.error(f"{key}: {type(value)}")
            raise
    
    
