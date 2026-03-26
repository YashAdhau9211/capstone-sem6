"""Causal inference engine using DoWhy library."""

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from dowhy import CausalModel
from dowhy.causal_estimator import CausalEstimate

from src.models.causal_graph import CausalDAG

logger = logging.getLogger(__name__)


@dataclass
class ATEResult:
    """Average Treatment Effect estimation result."""
    
    treatment: str
    outcome: str
    ate: float
    confidence_interval: Tuple[float, float]  # 95% CI
    method: str
    adjustment_set: Set[str]
    sample_size: int
    metadata: Dict[str, any] = field(default_factory=dict)


@dataclass
class CausalEffectMatrix:
    """Pre-computed causal effect matrix for fast counterfactual computation."""
    
    dag_id: str
    effect_matrix: np.ndarray  # Matrix of total causal effects between all node pairs
    node_order: List[str]  # Ordering of nodes in the matrix
    topo_order: List[str]  # Topological ordering for propagation
    adj_list: Dict[str, List[str]]  # Adjacency list for efficient traversal
    edge_coefficients: Dict[Tuple[str, str], float]  # Direct edge coefficients


class CausalInferenceEngine:
    """
    Causal inference engine for estimating causal effects and generating counterfactuals.
    
    Uses DoWhy library for causal inference pipeline:
    1. Model: Convert CausalDAG to DoWhy CausalModel
    2. Identify: Use backdoor criterion to find valid adjustment sets
    3. Estimate: Apply estimation method (linear regression, PSM, IPW)
    4. Refute: Run validation tests on estimates
    """
    
    def __init__(self, n_jobs: int = -1):
        """
        Initialize the causal inference engine.
        
        Args:
            n_jobs: Number of parallel jobs for bootstrap computation.
                   -1 uses all available CPU cores, 1 disables parallelization.
        """
        self.logger = logging.getLogger(__name__)
        self.n_jobs = n_jobs
        
        # Cache for pre-computed causal effect matrices
        self._effect_matrix_cache: Dict[str, CausalEffectMatrix] = {}
        
        # Cache for intermediate counterfactual results
        self._counterfactual_cache: Dict[str, pd.DataFrame] = {}
        self._cache_max_size = 100  # Maximum number of cached results
    
    def identify_adjustment_set(
        self,
        dag: CausalDAG,
        treatment: str,
        outcome: str
    ) -> Optional[Set[str]]:
        """
        Identify valid adjustment set using backdoor criterion.
        
        Args:
            dag: Causal DAG structure
            treatment: Treatment variable name
            outcome: Outcome variable name
            
        Returns:
            Set of variables to adjust for, or None if effect is not identifiable
            
        Raises:
            ValueError: If treatment or outcome not in DAG
        """
        if treatment not in dag.nodes:
            raise ValueError(f"Treatment variable '{treatment}' not in DAG")
        if outcome not in dag.nodes:
            raise ValueError(f"Outcome variable '{outcome}' not in DAG")
        
        self.logger.info(
            f"Identifying adjustment set for treatment='{treatment}', outcome='{outcome}'"
        )
        
        # Build graph structure for DoWhy
        gml_str = self._dag_to_gml_string(dag)
        
        try:
            # Create a minimal DataFrame for model initialization
            # DoWhy needs data to initialize, but we only need the graph structure here
            dummy_data = pd.DataFrame({node: [0] for node in dag.nodes})
            
            # Create DoWhy causal model
            model = CausalModel(
                data=dummy_data,
                treatment=treatment,
                outcome=outcome,
                graph=gml_str
            )
            
            # Identify causal effect using backdoor criterion
            identified_estimand = model.identify_effect(
                proceed_when_unidentifiable=False
            )
            
            # Extract adjustment set from backdoor variables
            # Filter out DoWhy's internal variables (like 'Unobserved Confounders')
            if identified_estimand.backdoor_variables:
                # Only include variables that are actually in our DAG
                adjustment_set = {
                    var for var in identified_estimand.backdoor_variables
                    if var in dag.nodes
                }
                self.logger.info(f"Found adjustment set: {adjustment_set}")
                return adjustment_set
            else:
                self.logger.info("No adjustment set needed (direct effect)")
                return set()
                
        except Exception as e:
            self.logger.warning(f"Could not identify causal effect: {e}")
            return None
    
    def _dag_to_gml_string(self, dag: CausalDAG) -> str:
        """
        Convert CausalDAG to GML string format for DoWhy.
        
        Args:
            dag: Causal DAG structure
            
        Returns:
            GML format string representation
        """
        lines = ["graph ["]
        lines.append("  directed 1")
        
        # Add nodes
        for node in dag.nodes:
            lines.append(f'  node [')
            lines.append(f'    id "{node}"')
            lines.append(f'    label "{node}"')
            lines.append(f'  ]')
        
        # Add edges
        for edge in dag.edges:
            lines.append(f'  edge [')
            lines.append(f'    source "{edge.source}"')
            lines.append(f'    target "{edge.target}"')
            lines.append(f'  ]')
        
        lines.append("]")
        return '\n'.join(lines)
    
    def _dag_to_dowhy_model(
        self,
        dag: CausalDAG,
        data: pd.DataFrame,
        treatment: str,
        outcome: str
    ) -> CausalModel:
        """
        Convert CausalDAG to DoWhy CausalModel.
        
        Args:
            dag: Causal DAG structure
            data: Observational data
            treatment: Treatment variable name
            outcome: Outcome variable name
            
        Returns:
            DoWhy CausalModel instance
        """
        gml_str = self._dag_to_gml_string(dag)
        
        model = CausalModel(
            data=data,
            treatment=treatment,
            outcome=outcome,
            graph=gml_str
        )
        
        return model

    
    def estimate_ate(
        self,
        data: pd.DataFrame,
        dag: CausalDAG,
        treatment: str,
        outcome: str,
        method: str = "linear_regression",
        bootstrap_iterations: int = 1000
    ) -> ATEResult:
        """
        Estimate Average Treatment Effect (ATE) with confidence intervals.
        
        Args:
            data: Observational data with treatment, outcome, and covariates
            dag: Causal DAG structure
            treatment: Treatment variable name
            outcome: Outcome variable name
            method: Estimation method - "linear_regression", "propensity_score_matching", 
                   or "inverse_propensity_weighting"
            bootstrap_iterations: Number of bootstrap iterations for confidence intervals
            
        Returns:
            ATEResult with estimate, confidence intervals, and metadata
            
        Raises:
            ValueError: If treatment/outcome not in data or DAG, or if effect not identifiable
        """
        # Validate inputs
        if treatment not in data.columns:
            raise ValueError(f"Treatment variable '{treatment}' not in data")
        if outcome not in data.columns:
            raise ValueError(f"Outcome variable '{outcome}' not in data")
        
        self.logger.info(
            f"Estimating ATE: treatment='{treatment}', outcome='{outcome}', method='{method}'"
        )
        
        # Identify adjustment set
        adjustment_set = self.identify_adjustment_set(dag, treatment, outcome)
        
        if adjustment_set is None:
            raise ValueError(
                f"Causal effect of '{treatment}' on '{outcome}' is not identifiable. "
                "No valid adjustment set exists."
            )
        
        # Create DoWhy model
        model = self._dag_to_dowhy_model(dag, data, treatment, outcome)
        
        # Store GML string for bootstrap
        gml_str = self._dag_to_gml_string(dag)
        
        # Identify causal effect
        identified_estimand = model.identify_effect(proceed_when_unidentifiable=False)
        
        # Map method names to DoWhy estimator names
        method_map = {
            "linear_regression": "backdoor.linear_regression",
            "propensity_score_matching": "backdoor.propensity_score_matching",
            "inverse_propensity_weighting": "backdoor.propensity_score_weighting"
        }
        
        if method not in method_map:
            raise ValueError(
                f"Unknown method '{method}'. "
                f"Valid methods: {list(method_map.keys())}"
            )
        
        dowhy_method = method_map[method]
        
        # Estimate causal effect
        try:
            estimate = model.estimate_effect(
                identified_estimand,
                method_name=dowhy_method
            )
            
            ate_value = float(estimate.value)
            
            self.logger.info(f"Point estimate ATE: {ate_value:.6f}")
            
        except Exception as e:
            self.logger.error(f"Failed to estimate causal effect: {e}")
            raise ValueError(f"Estimation failed: {e}")
        
        # Compute confidence intervals using bootstrap
        self.logger.info(f"Computing 95% CI with {bootstrap_iterations} bootstrap iterations")
        
        ci_lower, ci_upper = self._bootstrap_confidence_interval(
            gml_str=gml_str,
            identified_estimand=identified_estimand,
            method_name=dowhy_method,
            data=data,
            treatment=treatment,
            outcome=outcome,
            iterations=bootstrap_iterations
        )
        
        self.logger.info(f"95% CI: [{ci_lower:.6f}, {ci_upper:.6f}]")
        
        # Create result
        result = ATEResult(
            treatment=treatment,
            outcome=outcome,
            ate=ate_value,
            confidence_interval=(ci_lower, ci_upper),
            method=method,
            adjustment_set=adjustment_set,
            sample_size=len(data),
            metadata={
                "estimand": str(identified_estimand),
                "bootstrap_iterations": bootstrap_iterations
            }
        )
        
        return result
    
    def _bootstrap_confidence_interval(
        self,
        gml_str: str,
        identified_estimand,
        method_name: str,
        data: pd.DataFrame,
        treatment: str,
        outcome: str,
        iterations: int = 1000,
        confidence_level: float = 0.95
    ) -> Tuple[float, float]:
        """
        Compute confidence interval using parallel bootstrap resampling.
        
        Args:
            gml_str: GML string representation of the DAG
            identified_estimand: Identified causal estimand
            method_name: DoWhy estimator method name
            data: Original data
            treatment: Treatment variable
            outcome: Outcome variable
            iterations: Number of bootstrap iterations
            confidence_level: Confidence level (default 0.95 for 95% CI)
            
        Returns:
            Tuple of (lower_bound, upper_bound) for confidence interval
        """
        if self.n_jobs == 1:
            # Sequential execution
            return self._bootstrap_sequential(
                gml_str, identified_estimand, method_name, data, 
                treatment, outcome, iterations, confidence_level
            )
        else:
            # Parallel execution
            return self._bootstrap_parallel(
                gml_str, identified_estimand, method_name, data,
                treatment, outcome, iterations, confidence_level
            )
    
    def _bootstrap_sequential(
        self,
        gml_str: str,
        identified_estimand,
        method_name: str,
        data: pd.DataFrame,
        treatment: str,
        outcome: str,
        iterations: int,
        confidence_level: float
    ) -> Tuple[float, float]:
        """Sequential bootstrap implementation."""
        bootstrap_estimates = []
        n_samples = len(data)
        
        for i in range(iterations):
            # Resample with replacement
            bootstrap_sample = data.sample(n=n_samples, replace=True)
            
            try:
                estimate = self._estimate_on_sample(
                    bootstrap_sample, gml_str, treatment, outcome, 
                    method_name
                )
                bootstrap_estimates.append(estimate)
                
            except Exception as e:
                # Skip failed bootstrap iterations
                self.logger.debug(f"Bootstrap iteration {i} failed: {e}")
                continue
        
        return self._compute_percentile_ci(bootstrap_estimates, confidence_level, iterations)
    
    def _bootstrap_parallel(
        self,
        gml_str: str,
        identified_estimand,
        method_name: str,
        data: pd.DataFrame,
        treatment: str,
        outcome: str,
        iterations: int,
        confidence_level: float
    ) -> Tuple[float, float]:
        """Parallel bootstrap implementation using ProcessPoolExecutor."""
        import multiprocessing
        
        # Determine number of workers
        if self.n_jobs == -1:
            n_workers = multiprocessing.cpu_count()
        else:
            n_workers = min(self.n_jobs, multiprocessing.cpu_count())
        
        self.logger.debug(f"Using {n_workers} workers for parallel bootstrap")
        
        n_samples = len(data)
        bootstrap_estimates = []
        
        # Create bootstrap tasks
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            # Submit all bootstrap iterations
            futures = []
            for i in range(iterations):
                # Generate random seed for each iteration
                seed = np.random.randint(0, 2**31 - 1)
                future = executor.submit(
                    _bootstrap_worker,
                    data, n_samples, gml_str, treatment, outcome,
                    method_name, seed
                )
                futures.append(future)
            
            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    estimate = future.result()
                    if estimate is not None:
                        bootstrap_estimates.append(estimate)
                except Exception as e:
                    self.logger.debug(f"Bootstrap iteration failed: {e}")
                    continue
        
        return self._compute_percentile_ci(bootstrap_estimates, confidence_level, iterations)
    
    def _estimate_on_sample(
        self,
        sample: pd.DataFrame,
        gml_str: str,
        treatment: str,
        outcome: str,
        method_name: str
    ) -> float:
        """Estimate ATE on a single sample."""
        bootstrap_model = CausalModel(
            data=sample,
            treatment=treatment,
            outcome=outcome,
            graph=gml_str
        )
        
        bootstrap_estimand = bootstrap_model.identify_effect(
            proceed_when_unidentifiable=False
        )
        bootstrap_estimate = bootstrap_model.estimate_effect(
            bootstrap_estimand,
            method_name=method_name
        )
        
        return float(bootstrap_estimate.value)
    
    def _compute_percentile_ci(
        self,
        estimates: List[float],
        confidence_level: float,
        total_iterations: int
    ) -> Tuple[float, float]:
        """Compute percentile-based confidence interval."""
        if len(estimates) < total_iterations * 0.5:
            self.logger.warning(
                f"Only {len(estimates)}/{total_iterations} bootstrap iterations succeeded"
            )
        
        if len(estimates) == 0:
            raise ValueError("All bootstrap iterations failed")
        
        # Compute percentile-based confidence interval
        alpha = 1 - confidence_level
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100
        
        ci_lower = np.percentile(estimates, lower_percentile)
        ci_upper = np.percentile(estimates, upper_percentile)
        
        return (float(ci_lower), float(ci_upper))
    
    def compute_counterfactual(
        self,
        data: pd.DataFrame,
        dag: CausalDAG,
        interventions: Dict[str, float],
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Compute counterfactual predictions using do-calculus intervention.
        
        This method performs causal interventions on specified variables and propagates
        the effects through the causal DAG to predict counterfactual outcomes for all
        downstream variables.
        
        Performance optimizations:
        - Pre-computes causal effect matrices for fast propagation
        - Caches intermediate results for repeated queries
        - Uses efficient topological ordering for propagation
        
        Args:
            data: Observational data with all variables in the DAG
            dag: Causal DAG structure
            interventions: Dictionary mapping variable names to intervention values
                          e.g., {"temperature": 1500, "pressure": 2.5}
            use_cache: Whether to use cached effect matrices (default: True)
        
        Returns:
            DataFrame with counterfactual predictions for all variables in the DAG.
            Intervened variables have their fixed intervention values, and downstream
            variables have predicted counterfactual values.
        
        Raises:
            ValueError: If intervention variables not in DAG or data
        
        Performance:
            Target <500ms for single intervention at 95th percentile
        """
        # Validate interventions
        for var in interventions:
            if var not in dag.nodes:
                raise ValueError(f"Intervention variable '{var}' not in DAG")
        
        # Validate data contains all DAG variables
        missing_vars = set(dag.nodes) - set(data.columns)
        if missing_vars:
            raise ValueError(f"Data missing variables: {missing_vars}")
        
        self.logger.info(
            f"Computing counterfactual with interventions: {interventions}"
        )
        
        # Check cache for pre-computed effect matrix
        dag_cache_key = str(dag.dag_id)
        
        if use_cache and dag_cache_key in self._effect_matrix_cache:
            effect_matrix_data = self._effect_matrix_cache[dag_cache_key]
            self.logger.debug("Using cached effect matrix")
        else:
            # Pre-compute effect matrix for this DAG
            effect_matrix_data = self._precompute_effect_matrix(dag)
            
            if use_cache:
                self._effect_matrix_cache[dag_cache_key] = effect_matrix_data
                self.logger.debug("Cached effect matrix for future use")
        
        # Initialize counterfactual data with original values
        counterfactual = data.copy()
        
        # Apply interventions (do-operator)
        for var, value in interventions.items():
            counterfactual[var] = value
        
        # Propagate effects through causal paths in topological order
        for node in effect_matrix_data.topo_order:
            # Skip if this node was intervened on (it's fixed)
            if node in interventions:
                continue
            
            # Find all parents of this node
            parents = [
                edge_source 
                for edge_source, edge_target in effect_matrix_data.edge_coefficients.keys()
                if edge_target == node
            ]
            
            if not parents:
                # No parents, keep original value
                continue
            
            # Compute counterfactual value using structural equation
            # For linear edges: Y = sum(coef_i * X_i) + noise
            # We use the learned coefficients and parent values
            
            # Compute predicted values using linear combination
            predicted = np.zeros(len(counterfactual))
            
            for parent in parents:
                coef = effect_matrix_data.edge_coefficients[(parent, node)]
                predicted += coef * counterfactual[parent].values
            
            # For counterfactual prediction, we use the structural equation
            # without the noise term (deterministic prediction)
            counterfactual[node] = predicted
        
        self.logger.info(
            f"Counterfactual computation complete for {len(interventions)} interventions"
        )
        
        return counterfactual
    
    def _precompute_effect_matrix(self, dag: CausalDAG) -> CausalEffectMatrix:
        """
        Pre-compute causal effect matrix for fast counterfactual propagation.
        
        This method computes:
        1. Topological ordering of nodes
        2. Adjacency list for efficient traversal
        3. Direct edge coefficients
        4. Total causal effect matrix (for future optimization)
        
        Args:
            dag: Causal DAG structure
        
        Returns:
            CausalEffectMatrix with pre-computed data structures
        """
        # Build adjacency list and edge coefficients
        adj_list: Dict[str, List[str]] = {node: [] for node in dag.nodes}
        edge_coefficients: Dict[Tuple[str, str], float] = {}
        
        for edge in dag.edges:
            adj_list[edge.source].append(edge.target)
            edge_coefficients[(edge.source, edge.target)] = edge.coefficient
        
        # Compute topological order
        topo_order = self._topological_sort(dag)
        
        # Initialize effect matrix (total causal effects between all pairs)
        n = len(dag.nodes)
        node_order = sorted(dag.nodes)  # Consistent ordering
        node_to_idx = {node: i for i, node in enumerate(node_order)}
        
        effect_matrix = np.zeros((n, n))
        
        # Compute total causal effects using path analysis
        # effect_matrix[i][j] = total causal effect from node i to node j
        for source in dag.nodes:
            for target in dag.nodes:
                if source == target:
                    effect_matrix[node_to_idx[source]][node_to_idx[target]] = 1.0
                else:
                    # Compute total effect by summing over all paths
                    total_effect = self._compute_total_effect(
                        source, target, dag, edge_coefficients
                    )
                    effect_matrix[node_to_idx[source]][node_to_idx[target]] = total_effect
        
        return CausalEffectMatrix(
            dag_id=str(dag.dag_id),
            effect_matrix=effect_matrix,
            node_order=node_order,
            topo_order=topo_order,
            adj_list=adj_list,
            edge_coefficients=edge_coefficients
        )
    
    def _compute_total_effect(
        self,
        source: str,
        target: str,
        dag: CausalDAG,
        edge_coefficients: Dict[Tuple[str, str], float]
    ) -> float:
        """
        Compute total causal effect from source to target by summing over all paths.
        
        For linear systems, the total effect is the sum of products of coefficients
        along all directed paths from source to target.
        
        Args:
            source: Source node
            target: Target node
            dag: Causal DAG structure
            edge_coefficients: Dictionary of edge coefficients
        
        Returns:
            Total causal effect (0.0 if no path exists)
        """
        # Find all paths from source to target
        all_paths = self._find_all_paths(source, target, dag)
        
        if not all_paths:
            return 0.0
        
        # Sum the product of coefficients along each path
        total_effect = 0.0
        
        for path in all_paths:
            path_effect = 1.0
            for i in range(len(path) - 1):
                edge_key = (path[i], path[i + 1])
                if edge_key in edge_coefficients:
                    path_effect *= edge_coefficients[edge_key]
                else:
                    path_effect = 0.0
                    break
            total_effect += path_effect
        
        return total_effect
    
    def _find_all_paths(
        self,
        source: str,
        target: str,
        dag: CausalDAG,
        max_depth: int = 10
    ) -> List[List[str]]:
        """
        Find all directed paths from source to target in DAG.
        
        Args:
            source: Source node
            target: Target node
            dag: Causal DAG structure
            max_depth: Maximum path length to prevent infinite loops
        
        Returns:
            List of paths, where each path is a list of nodes
        """
        if source == target:
            return [[source]]
        
        # Build adjacency list
        adj_list: Dict[str, List[str]] = {node: [] for node in dag.nodes}
        for edge in dag.edges:
            adj_list[edge.source].append(edge.target)
        
        all_paths = []
        
        def dfs(current: str, path: List[str], depth: int):
            if depth > max_depth:
                return
            
            if current == target:
                all_paths.append(path.copy())
                return
            
            for neighbor in adj_list[current]:
                if neighbor not in path:  # Avoid cycles
                    path.append(neighbor)
                    dfs(neighbor, path, depth + 1)
                    path.pop()
        
        dfs(source, [source], 0)
        return all_paths
    
    def clear_cache(self):
        """Clear all cached effect matrices and counterfactual results."""
        self._effect_matrix_cache.clear()
        self._counterfactual_cache.clear()
        self.logger.info("Cleared all caches")
    
    def _load_station_data(self, station_id: str) -> pd.DataFrame:
        """
        Load station data for inference.
        
        In production, this would query the time-series database.
        For now, we generate mock data.
        
        Args:
            station_id: Station identifier
        
        Returns:
            DataFrame with time-series data
        """
        # TODO: Implement actual data loading from time-series database
        # For now, generate mock data for testing
        import numpy as np
        
        self.logger.info(f"Loading data for station {station_id}")
        
        # Generate mock data with causal structure
        n_samples = 1000
        np.random.seed(42)
        
        # Create causal structure: temperature -> pressure -> flow_rate -> quality
        # Also: temperature -> energy_consumption
        temperature = np.random.randn(n_samples) * 50 + 1500  # Mean 1500, std 50
        pressure = 0.8 * temperature + np.random.randn(n_samples) * 30 + 100
        flow_rate = 0.6 * temperature + 0.5 * pressure + np.random.randn(n_samples) * 20 + 500
        quality_score = 0.4 * flow_rate + np.random.randn(n_samples) * 5 + 90
        
        # Energy consumption affected by temperature and pressure
        energy_consumption = 0.7 * temperature + 0.3 * pressure + np.random.randn(n_samples) * 100 + 2000
        
        # Yield affected by temperature, flow_rate, and quality
        yield_value = 0.5 * temperature + 0.3 * flow_rate + 0.2 * quality_score + np.random.randn(n_samples) * 10 + 1000
        
        data = pd.DataFrame({
            "temperature": temperature,
            "pressure": pressure,
            "flow_rate": flow_rate,
            "quality_score": quality_score,
            "energy_consumption": energy_consumption,
            "yield": yield_value,
        })
        
        self.logger.info(f"Loaded {len(data)} samples with {len(data.columns)} variables")
        
        return data
    
    def _topological_sort(self, dag: CausalDAG) -> List[str]:
        """
        Compute topological ordering of DAG nodes.
        
        Args:
            dag: Causal DAG structure
        
        Returns:
            List of nodes in topological order (parents before children)
        """
        # Build adjacency list and in-degree count
        adj_list: Dict[str, List[str]] = {node: [] for node in dag.nodes}
        in_degree: Dict[str, int] = {node: 0 for node in dag.nodes}
        
        for edge in dag.edges:
            adj_list[edge.source].append(edge.target)
            in_degree[edge.target] += 1
        
        # Kahn's algorithm for topological sort
        queue = [node for node in dag.nodes if in_degree[node] == 0]
        topo_order = []
        
        while queue:
            node = queue.pop(0)
            topo_order.append(node)
            
            for neighbor in adj_list[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(topo_order) != len(dag.nodes):
            raise ValueError("DAG contains a cycle (should not happen)")
        
        return topo_order


def _bootstrap_worker(
    data: pd.DataFrame,
    n_samples: int,
    gml_str: str,
    treatment: str,
    outcome: str,
    method_name: str,
    seed: int
) -> Optional[float]:
    """
    Worker function for parallel bootstrap.
    
    This function is defined at module level to be picklable for multiprocessing.
    """
    try:
        # Set random seed for reproducibility
        np.random.seed(seed)
        
        # Resample with replacement
        bootstrap_sample = data.sample(n=n_samples, replace=True)
        
        # Create model and estimate
        bootstrap_model = CausalModel(
            data=bootstrap_sample,
            treatment=treatment,
            outcome=outcome,
            graph=gml_str
        )
        
        bootstrap_estimand = bootstrap_model.identify_effect(
            proceed_when_unidentifiable=False
        )
        bootstrap_estimate = bootstrap_model.estimate_effect(
            bootstrap_estimand,
            method_name=method_name
        )
        
        return float(bootstrap_estimate.value)
        
    except Exception:
        # Return None for failed iterations
        return None
