# test_optimization_tracker.py
import unittest
import pandas as pd
import numpy as np
import os
import shutil
import json
from pathlib import Path
import tempfile
from datetime import datetime

from optimization_tracker import OptimizationTracker


class TestOptimizationTracker(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment with temporary directories."""
        self.temp_dir = tempfile.mkdtemp()
        self.index_path = os.path.join(self.temp_dir, "test_index.parquet")
        self.results_dir = os.path.join(self.temp_dir, "test_results")
        
        # Create tracker with test paths
        self.tracker = OptimizationTracker(
            index_path=self.index_path,
            results_dir=self.results_dir
        )
        
        # Create a sample task for testing
        self.sample_task = {
            "optimizationId": "test_opt_123",
            "portfolioId": "TEST_PORTFOLIO",
            "benchmarkId": "TEST_BENCHMARK",
            "asOfDate": "2025-04-15",
            "riskOptions": {
                "riskModel": "TEST_MODEL",
                "riskModelScaling": "YEAR",
                "riskModelHorizon": "ANNUAL"
            },
            "goals": [
                {"name": "ActiveTotalRisk", "configuration": {"weight": 0.5}}
            ],
            "portfolioConstraints": [
                {
                    "name": "ActiveTotalRisk",
                    "configuration": {"upperBound": 0.05}
                },
                {
                    "name": "Diversification",
                    "configuration": {"maxPositions": 250}
                }
            ],
            "instrumentConstraints": [
                {
                    "name": "MaxPosition",
                    "configuration": {"maxWeight": 0.03}
                }
            ]
        }
        
        # Create a sample task file
        self.task_file_path = os.path.join(self.temp_dir, "test_task.json")
        with open(self.task_file_path, 'w') as f:
            json.dump(self.sample_task, f)
        
        # Create a sample optimization response
        self.sample_response = {
            "id": "api-123456",
            "status": "Completed",
            "portfolioId": "TEST_PORTFOLIO",
            "benchmarkId": "TEST_BENCHMARK",
            "asOfDate": "2025-04-15"
        }
    
    def tearDown(self):
        """Clean up temporary files and directories."""
        shutil.rmtree(self.temp_dir)
    
    def test_create_empty_index(self):
        """Test creation of an empty index."""
        df = self.tracker._create_empty_index()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue("optimization_id" in df.columns)
        self.assertTrue("portfolio" in df.columns)
        self.assertTrue("status" in df.columns)
    
    def test_register_optimization_task(self):
        """Test registering an optimization task."""
        opt_id = self.tracker.register_optimization_task(
            self.sample_task,
            self.task_file_path
        )
        
        self.assertEqual(opt_id, "test_opt_123")
        self.assertTrue(opt_id in self.tracker.index_df['optimization_id'].values)
        
        # Check that constraint values were extracted correctly
        mask = self.tracker.index_df['optimization_id'] == opt_id
        self.assertEqual(self.tracker.index_df.loc[mask, 'max_active_risk'].iloc[0], 0.05)
        self.assertEqual(self.tracker.index_df.loc[mask, 'max_positions'].iloc[0], 250)
        self.assertEqual(self.tracker.index_df.loc[mask, 'max_security_weight'].iloc[0], 0.03)
    
    def test_update_optimization_status(self):
        """Test updating optimization status."""
        # First register a task
        opt_id = self.tracker.register_optimization_task(
            self.sample_task,
            self.task_file_path
        )
        
        # Update its status
        self.tracker.update_optimization_status(
            optimization_id=opt_id,
            api_generated_id="api-123456",
            status="running"
        )
        
        # Check that status was updated
        mask = self.tracker.index_df['optimization_id'] == opt_id
        self.assertEqual(self.tracker.index_df.loc[mask, 'status'].iloc[0], "running")
        self.assertEqual(self.tracker.index_df.loc[mask, 'api_generated_id'].iloc[0], "api-123456")
        
        # Update with error
        self.tracker.update_optimization_status(
            optimization_id=opt_id,
            status="failed",
            error_message="Test error message"
        )
        
        # Check error message
        self.assertEqual(self.tracker.index_df.loc[mask, 'status'].iloc[0], "failed")
        self.assertEqual(
            self.tracker.index_df.loc[mask, 'error_message'].iloc[0], 
            "Test error message"
        )
    
    def test_save_optimization_results(self):
        """Test saving optimization results."""
        # First register a task
        opt_id = self.tracker.register_optimization_task(
            self.sample_task,
            self.task_file_path
        )
        
        # Update its status to running
        self.tracker.update_optimization_status(
            optimization_id=opt_id,
            status="running"
        )
        
        # Save results
        self.tracker.save_optimization_results(
            optimization_id=opt_id,
            opt_response=self.sample_response
        )
        
        # Check that status was updated to success
        mask = self.tracker.index_df['optimization_id'] == opt_id
        self.assertEqual(self.tracker.index_df.loc[mask, 'status'].iloc[0], "success")
        self.assertEqual(
            self.tracker.index_df.loc[mask, 'api_generated_id'].iloc[0],
            "api-123456"
        )
        
        # Check that results files were created
        results_dir = Path(self.tracker.index_df.loc[mask, 'results_path'].iloc[0])
        self.assertTrue((results_dir / "api_response.json").exists())
        self.assertTrue((results_dir / "summary.parquet").exists())
        self.assertTrue((results_dir / "goals.parquet").exists())
        self.assertTrue((results_dir / "constraints.parquet").exists())
        self.assertTrue((results_dir / "trades.parquet").exists())
    
    def test_get_pending_optimizations(self):
        """Test getting pending optimizations."""
        # Register two tasks
        opt_id1 = self.tracker.register_optimization_task(
            self.sample_task,
            self.task_file_path
        )
        
        # Clone the task with a different ID
        task2 = self.sample_task.copy()
        task2["optimizationId"] = "test_opt_456"
        opt_id2 = self.tracker.register_optimization_task(
            task2,
            self.task_file_path
        )
        
        # Mark one as running
        self.tracker.update_optimization_status(
            optimization_id=opt_id1,
            status="running"
        )
        
        # Get pending optimizations
        pending = self.tracker.get_pending_optimizations()
        
        # Should only have the second one as pending
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['optimization_id'], opt_id2)
    
    def test_filter_optimizations(self):
        """Test filtering optimizations."""
        # Register tasks with different properties
        self.sample_task["optimizationId"] = "test_opt_a"
        self.sample_task["portfolioId"] = "PORTFOLIO_A"
        self.tracker.register_optimization_task(
            self.sample_task,
            self.task_file_path
        )
        
        self.sample_task["optimizationId"] = "test_opt_b"
        self.sample_task["portfolioId"] = "PORTFOLIO_B"
        self.tracker.register_optimization_task(
            self.sample_task,
            self.task_file_path
        )
        
        # Filter by portfolio
        filtered = self.tracker.filter_optimizations(portfolio="PORTFOLIO_A")
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered.iloc[0]['optimization_id'], "test_opt_a")
        
        # Filter by a combination
        self.tracker.update_optimization_status(
            optimization_id="test_opt_a",
            status="success"
        )
        
        filtered = self.tracker.filter_optimizations(
            portfolio="PORTFOLIO_A",
            status="success"
        )
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered.iloc[0]['optimization_id'], "test_opt_a")
        
        # Filter that should return empty
        filtered = self.tracker.filter_optimizations(
            portfolio="PORTFOLIO_B",
            status="success"
        )
        
        self.assertEqual(len(filtered), 0)


if __name__ == '__main__':
    unittest.main()