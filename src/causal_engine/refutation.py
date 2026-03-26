"""Refutation module for validating causal estimates."""

import logging
import time
from concurrent.futures import ProcessPoolExecutor, TimeoutError, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from src.causal_engine.inference import ATEResult, CausalInferenceEngine
from src.models.causal_graph import CausalDAG, CausalEdge

logger = logging.getLogger(__name__)


@dataclass
class RefutationTest:
    """Result of a single refutation test."""
    
    test_name: str
    passed: bool
    original_ate: float
    refuted_ate: float
    threshold: float
    details: Dict[str, any] = field(default_factory=dict)
    execution_time: float = 0.0


@dataclass
class RefutationReport:
    """Comprehensive refutation report with all test results."""
    
    tests: List[RefutationTest]
    overall_pass: bool
    confidence_assessment: str  # "high", "medium", "low"
    warnings: List[str] = field(default_factory=list)
    total_execution_time: float = 0.0


class RefutationModule:
    """
    Refutation module for validating causal estimates through robustness tests.
    
    Implements three refutation tests:
    1. Placebo Treatment Test: Replace treatment with random variable, expect ATE ≈ 0
    2. Random Common Cause Test: Add random confounder, expect ATE unchanged
    3. Data Subset Test: Estimate ATE on random subsets, expect consistent results
    """
    
    def __init__(self, inference_engine: Optional[CausalInferenceEngine] = None, n_jobs: int = -1):
        """
        Initialize the refutation module.
        
        Args:
            inference_engine: CausalInferenceEngine instance for ATE estimation.
                            If None, creates a new instance.
            n_jobs: Number of parallel jobs for test execution.
                   -1 uses all available CPU cores, 1 disables parallelization.
        """
        self.logger = logging.getLogger(__name__)
        self.inference_engine = inference_engine or CausalInferenceEngine(n_jobs=n_jobs)
        self.n_jobs = n_jobs
        
        # Timeout for all refutation tests (30 seconds)
        self.timeout = 30.0
    
    def placebo_treatment_test(
        self,
        ate_result: ATEResult,
        data: pd.DataFrame,
        dag: CausalDAG
    ) -> RefutationTest:
        """
        Placebo treatment test: Replace treatment with random variable.
        
        The test replaces the treatment variable with a random variable that has
        no causal relationship with the outcome. The estimated ATE should be close
        to zero if the original estimate is valid.
        
        Pass criteria: |ATE_placebo| < 0.1 × |ATE_original|
        
        Args:
            ate_result: Original ATE estimation result
            data: DataFrame with observational data
            dag: Causal DAG structure
            
        Returns:
            RefutationTest result with pass/fail status
        """
        start_time = time.time()
        self.logger.info("Running placebo treatment test")
        
        try:
            # Create a copy of the data with placebo treatment
            data_placebo = data.copy()
            
            # Generate random placebo treatment (same distribution as original)
            original_treatment = data[ate_result.treatment].values
            placebo_treatment = np.random.permutation(original_treatment)
            data_placebo[ate_result.treatment] = placebo_treatment
            
            # Estimate ATE with placebo treatment
            placebo_ate_result = self.inference_engine.estimate_ate(
                data=data_placebo,
                dag=dag,
                treatment=ate_result.treatment,
                outcome=ate_result.outcome,
                method=ate_result.method
            )
            
            # Check pass criteria: |ATE_placebo| < 0.1 × |ATE_original|
            threshold = 0.1 * abs(ate_result.ate)
            passed = abs(placebo_ate_result.ate) < threshold
            
            execution_time = time.time() - start_time
            
            return RefutationTest(
                test_name="placebo_treatment_test",
                passed=passed,
                original_ate=ate_result.ate,
                refuted_ate=placebo_ate_result.ate,
                threshold=threshold,
                details={
                    "placebo_ci": placebo_ate_result.confidence_interval,
                    "original_ci": ate_result.confidence_interval,
                    "ratio": abs(placebo_ate_result.ate) / abs(ate_result.ate) if ate_result.ate != 0 else float('inf')
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            self.logger.error(f"Placebo treatment test failed with error: {e}")
            execution_time = time.time() - start_time
            return RefutationTest(
                test_name="placebo_treatment_test",
                passed=False,
                original_ate=ate_result.ate,
                refuted_ate=0.0,
                threshold=0.0,
                details={"error": str(e)},
                execution_time=execution_time
            )
    
    def random_common_cause_test(
        self,
        ate_result: ATEResult,
        data: pd.DataFrame,
        dag: CausalDAG
    ) -> RefutationTest:
        """
        Random common cause test: Add random confounder to the model.
        
        The test adds a random variable as a common cause of treatment and outcome.
        If the original adjustment set is valid, adding this random confounder
        should not significantly change the ATE.
        
        Pass criteria: |ATE_new - ATE_original| < 0.15 × |ATE_original|
        
        Args:
            ate_result: Original ATE estimation result
            data: DataFrame with observational data
            dag: Causal DAG structure
            
        Returns:
            RefutationTest result with pass/fail status
        """
        start_time = time.time()
        self.logger.info("Running random common cause test")
        
        try:
            # Create a copy of the data with random common cause
            data_rcc = data.copy()
            
            # Generate random common cause variable
            random_confounder = np.random.randn(len(data))
            confounder_name = "_random_confounder_"
            data_rcc[confounder_name] = random_confounder
            
            # Create modified DAG with random confounder as common cause
            modified_dag = self._add_random_confounder_to_dag(
                dag=dag,
                confounder_name=confounder_name,
                treatment=ate_result.treatment,
                outcome=ate_result.outcome
            )
            
            # Estimate ATE with random confounder
            rcc_ate_result = self.inference_engine.estimate_ate(
                data=data_rcc,
                dag=modified_dag,
                treatment=ate_result.treatment,
                outcome=ate_result.outcome,
                method=ate_result.method
            )
            
            # Check pass criteria: |ATE_new - ATE_original| < 0.15 × |ATE_original|
            threshold = 0.15 * abs(ate_result.ate)
            ate_difference = abs(rcc_ate_result.ate - ate_result.ate)
            passed = ate_difference < threshold
            
            execution_time = time.time() - start_time
            
            return RefutationTest(
                test_name="random_common_cause_test",
                passed=passed,
                original_ate=ate_result.ate,
                refuted_ate=rcc_ate_result.ate,
                threshold=threshold,
                details={
                    "ate_difference": ate_difference,
                    "rcc_ci": rcc_ate_result.confidence_interval,
                    "original_ci": ate_result.confidence_interval,
                    "relative_change": ate_difference / abs(ate_result.ate) if ate_result.ate != 0 else float('inf')
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            self.logger.error(f"Random common cause test failed with error: {e}")
            execution_time = time.time() - start_time
            return RefutationTest(
                test_name="random_common_cause_test",
                passed=False,
                original_ate=ate_result.ate,
                refuted_ate=0.0,
                threshold=0.0,
                details={"error": str(e)},
                execution_time=execution_time
            )
    
    def data_subset_test(
        self,
        ate_result: ATEResult,
        data: pd.DataFrame,
        dag: CausalDAG,
        n_subsets: int = 5
    ) -> RefutationTest:
        """
        Data subset test: Estimate ATE on random subsets of data.
        
        The test estimates ATE on multiple random subsets (80% of data each).
        If the original estimate is robust, all subset ATEs should fall within
        the original 95% confidence interval.
        
        Pass criteria: All subset ATEs within original 95% CI
        
        Args:
            ate_result: Original ATE estimation result
            data: DataFrame with observational data
            dag: Causal DAG structure
            n_subsets: Number of random subsets to test (default: 5)
            
        Returns:
            RefutationTest result with pass/fail status
        """
        start_time = time.time()
        self.logger.info(f"Running data subset test with {n_subsets} subsets")
        
        try:
            subset_ates = []
            subset_cis = []
            
            # Generate and test multiple random subsets
            for i in range(n_subsets):
                # Sample 80% of data randomly
                subset_data = data.sample(frac=0.8, random_state=i)
                
                # Estimate ATE on subset
                subset_ate_result = self.inference_engine.estimate_ate(
                    data=subset_data,
                    dag=dag,
                    treatment=ate_result.treatment,
                    outcome=ate_result.outcome,
                    method=ate_result.method
                )
                
                subset_ates.append(subset_ate_result.ate)
                subset_cis.append(subset_ate_result.confidence_interval)
            
            # Check pass criteria: All subset ATEs within original 95% CI
            original_ci_lower, original_ci_upper = ate_result.confidence_interval
            passed = all(
                original_ci_lower <= ate <= original_ci_upper
                for ate in subset_ates
            )
            
            execution_time = time.time() - start_time
            
            return RefutationTest(
                test_name="data_subset_test",
                passed=passed,
                original_ate=ate_result.ate,
                refuted_ate=np.mean(subset_ates),
                threshold=0.0,  # Not applicable for this test
                details={
                    "subset_ates": subset_ates,
                    "subset_cis": subset_cis,
                    "original_ci": ate_result.confidence_interval,
                    "n_subsets": n_subsets,
                    "n_passed": sum(
                        1 for ate in subset_ates
                        if original_ci_lower <= ate <= original_ci_upper
                    ),
                    "mean_subset_ate": np.mean(subset_ates),
                    "std_subset_ate": np.std(subset_ates)
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            self.logger.error(f"Data subset test failed with error: {e}")
            execution_time = time.time() - start_time
            return RefutationTest(
                test_name="data_subset_test",
                passed=False,
                original_ate=ate_result.ate,
                refuted_ate=0.0,
                threshold=0.0,
                details={"error": str(e)},
                execution_time=execution_time
            )
    
    def generate_report(
        self,
        ate_result: ATEResult,
        data: pd.DataFrame,
        dag: CausalDAG,
        run_parallel: bool = True
    ) -> RefutationReport:
        """
        Generate comprehensive refutation report with all tests.
        
        Runs all three refutation tests and generates an overall assessment
        of the causal estimate's reliability.
        
        Args:
            ate_result: Original ATE estimation result
            data: DataFrame with observational data
            dag: Causal DAG structure
            run_parallel: Whether to run tests in parallel (default: True)
            
        Returns:
            RefutationReport with all test results and overall assessment
        """
        start_time = time.time()
        self.logger.info("Generating refutation report")
        
        tests = []
        warnings = []
        
        try:
            if run_parallel and self.n_jobs != 1:
                # Run tests in parallel with timeout
                tests = self._run_tests_parallel(ate_result, data, dag)
            else:
                # Run tests sequentially
                tests = self._run_tests_sequential(ate_result, data, dag)
            
            # Determine overall pass/fail
            overall_pass = all(test.passed for test in tests)
            
            # Assess confidence level
            n_passed = sum(1 for test in tests if test.passed)
            if n_passed == 3:
                confidence_assessment = "high"
            elif n_passed == 2:
                confidence_assessment = "medium"
                warnings.append("One refutation test failed - estimate may be unreliable")
            else:
                confidence_assessment = "low"
                warnings.append("Multiple refutation tests failed - estimate is likely unreliable")
            
            # Check for timeout warnings
            total_time = time.time() - start_time
            if total_time > self.timeout:
                warnings.append(f"Refutation tests exceeded timeout ({self.timeout}s)")
            
            return RefutationReport(
                tests=tests,
                overall_pass=overall_pass,
                confidence_assessment=confidence_assessment,
                warnings=warnings,
                total_execution_time=total_time
            )
            
        except Exception as e:
            self.logger.error(f"Refutation report generation failed: {e}")
            return RefutationReport(
                tests=tests,
                overall_pass=False,
                confidence_assessment="low",
                warnings=[f"Report generation failed: {str(e)}"],
                total_execution_time=time.time() - start_time
            )
    
    def _run_tests_sequential(
        self,
        ate_result: ATEResult,
        data: pd.DataFrame,
        dag: CausalDAG
    ) -> List[RefutationTest]:
        """Run refutation tests sequentially."""
        tests = []
        
        # Run placebo treatment test
        test1 = self.placebo_treatment_test(ate_result, data, dag)
        tests.append(test1)
        
        # Run random common cause test
        test2 = self.random_common_cause_test(ate_result, data, dag)
        tests.append(test2)
        
        # Run data subset test
        test3 = self.data_subset_test(ate_result, data, dag)
        tests.append(test3)
        
        return tests
    
    def _run_tests_parallel(
        self,
        ate_result: ATEResult,
        data: pd.DataFrame,
        dag: CausalDAG
    ) -> List[RefutationTest]:
        """Run refutation tests in parallel with timeout."""
        tests = []
        
        with ProcessPoolExecutor(max_workers=3) as executor:
            # Submit all tests
            future_to_test = {
                executor.submit(self.placebo_treatment_test, ate_result, data, dag): "placebo",
                executor.submit(self.random_common_cause_test, ate_result, data, dag): "common_cause",
                executor.submit(self.data_subset_test, ate_result, data, dag): "subset"
            }
            
            # Collect results with timeout
            for future in as_completed(future_to_test, timeout=self.timeout):
                test_name = future_to_test[future]
                try:
                    test_result = future.result()
                    tests.append(test_result)
                except TimeoutError:
                    self.logger.warning(f"{test_name} test timed out")
                    tests.append(RefutationTest(
                        test_name=f"{test_name}_test",
                        passed=False,
                        original_ate=ate_result.ate,
                        refuted_ate=0.0,
                        threshold=0.0,
                        details={"error": "Test timed out"},
                        execution_time=self.timeout
                    ))
                except Exception as e:
                    self.logger.error(f"{test_name} test failed: {e}")
                    tests.append(RefutationTest(
                        test_name=f"{test_name}_test",
                        passed=False,
                        original_ate=ate_result.ate,
                        refuted_ate=0.0,
                        threshold=0.0,
                        details={"error": str(e)},
                        execution_time=0.0
                    ))
        
        return tests
    
    def _add_random_confounder_to_dag(
        self,
        dag: CausalDAG,
        confounder_name: str,
        treatment: str,
        outcome: str
    ) -> CausalDAG:
        """
        Create a modified DAG with random confounder as common cause.
        
        Args:
            dag: Original causal DAG
            confounder_name: Name of the random confounder variable
            treatment: Treatment variable name
            outcome: Outcome variable name
            
        Returns:
            Modified CausalDAG with random confounder added
        """
        # Create new nodes list with confounder
        new_nodes = dag.nodes + [confounder_name]
        
        # Create new edges list with confounder edges
        new_edges = dag.edges.copy()
        
        # Add edge from confounder to treatment
        new_edges.append(CausalEdge(
            source=confounder_name,
            target=treatment,
            coefficient=0.0,  # Random, no real effect
            confidence=1.0,
            edge_type="linear",
            metadata={"refutation_test": "random_common_cause"}
        ))
        
        # Add edge from confounder to outcome
        new_edges.append(CausalEdge(
            source=confounder_name,
            target=outcome,
            coefficient=0.0,  # Random, no real effect
            confidence=1.0,
            edge_type="linear",
            metadata={"refutation_test": "random_common_cause"}
        ))
        
        # Create modified DAG
        modified_dag = CausalDAG(
            dag_id=dag.dag_id,
            station_id=dag.station_id,
            version=dag.version,
            nodes=new_nodes,
            edges=new_edges,
            algorithm=dag.algorithm,
            created_at=dag.created_at,
            created_by=dag.created_by,
            metadata={**dag.metadata, "refutation_test": "random_common_cause"}
        )
        
        return modified_dag
