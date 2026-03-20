"""Causal discovery engine for learning causal relationships from observational data."""

import logging
from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

import numpy as np
import pandas as pd
from lingam import DirectLiNGAM, RESIT
from sklearn.ensemble import RandomForestRegressor
from sklearn.utils import resample

from src.models.causal_graph import CausalDAG, CausalEdge

logger = logging.getLogger(__name__)


class CausalDiscoveryEngine:
    """Engine for automated causal discovery using DirectLiNGAM and RESIT algorithms."""

    def __init__(
        self,
        random_state: Optional[int] = None,
        n_bootstrap: int = 100,
        use_cache: bool = True,
    ):
        """
        Initialize the causal discovery engine.

        Args:
            random_state: Random seed for reproducibility
            n_bootstrap: Number of bootstrap iterations for confidence scores (default: 100)
            use_cache: Whether to cache intermediate results for performance (default: True)
                      Caches ICA decomposition and confidence scores to speed up repeated analyses
        """
        self.random_state = random_state
        self.n_bootstrap = n_bootstrap
        self.use_cache = use_cache
        self._cache: Dict = {}

    def clear_cache(self) -> None:
        """
        Clear the internal cache of ICA decompositions and confidence scores.

        This can be useful to free memory or force recomputation of results.
        """
        self._cache.clear()
        logger.info("Cleared causal discovery cache")

    def discover_linear(
        self,
        data: pd.DataFrame,
        algorithm: str = "DirectLiNGAM",
        station_id: str = "unknown",
        created_by: str = "system",
    ) -> CausalDAG:
        """
        Discover linear causal relationships using DirectLiNGAM algorithm.

        This method applies the DirectLiNGAM algorithm to learn causal structure from
        observational data. It uses Independent Component Analysis (ICA) for causal
        ordering and linear regression for coefficient estimation.

        Args:
            data: Preprocessed time-series data as DataFrame (rows=observations, cols=variables)
            algorithm: Algorithm name (default: "DirectLiNGAM")
            station_id: Manufacturing station identifier
            created_by: User or system identifier

        Returns:
            CausalDAG object with discovered causal relationships

        Raises:
            ValueError: If data is empty or contains invalid values
            RuntimeError: If DirectLiNGAM algorithm fails to converge

        Requirements:
            - 4.1: Apply DirectLiNGAM algorithm to preprocessed time-series data
            - 4.2: Output DAG representing discovered causal relationships
            - 4.5: Complete analysis within 5 minutes for 50 variables × 10,000 time points
        """
        logger.info(
            f"Starting DirectLiNGAM causal discovery for station {station_id} "
            f"with {len(data)} observations and {len(data.columns)} variables"
        )

        # Validate input data
        self._validate_data(data)

        # Apply DirectLiNGAM algorithm
        start_time = datetime.now()
        model = self._fit_directlingam(data)
        fit_duration = (datetime.now() - start_time).total_seconds()

        logger.info(f"DirectLiNGAM fitting completed in {fit_duration:.2f} seconds")

        # Extract causal structure
        adjacency_matrix = model.adjacency_matrix_
        causal_order = model.causal_order_

        # Compute confidence scores using bootstrap
        logger.info(f"Computing confidence scores with {self.n_bootstrap} bootstrap iterations")
        confidence_matrix = self._compute_confidence_scores(data, adjacency_matrix)

        # Build CausalDAG from results
        dag = self._build_dag(
            data=data,
            adjacency_matrix=adjacency_matrix,
            confidence_matrix=confidence_matrix,
            causal_order=causal_order,
            station_id=station_id,
            algorithm=algorithm,
            created_by=created_by,
        )

        total_duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Causal discovery completed in {total_duration:.2f} seconds. "
            f"Discovered {len(dag.edges)} causal edges"
        )

        return dag

    def discover_nonlinear(
        self,
        data: pd.DataFrame,
        algorithm: str = "RESIT",
        station_id: str = "unknown",
        created_by: str = "system",
        adaptive_sample_size: bool = True,
        max_samples: Optional[int] = None,
    ) -> CausalDAG:
        """
        Discover nonlinear causal relationships using RESIT algorithm.

        RESIT (Regression with Subsequent Independence Test) detects nonlinear
        causal relationships by testing for independence between residuals and
        potential causes using HSIC (Hilbert-Schmidt Independence Criterion).

        Args:
            data: Preprocessed time-series data as DataFrame (rows=observations, cols=variables)
            algorithm: Algorithm name (default: "RESIT")
            station_id: Manufacturing station identifier
            created_by: User or system identifier
            adaptive_sample_size: Use adaptive sampling for independence tests (default: True)
            max_samples: Maximum samples for independence tests (default: None, uses all data)

        Returns:
            CausalDAG object with discovered nonlinear causal relationships

        Raises:
            ValueError: If data is empty or contains invalid values
            RuntimeError: If RESIT algorithm fails to converge

        Requirements:
            - 5.1: Apply RESIT algorithm when nonlinear analysis is enabled
            - 5.2: Output DAG representing nonlinear causal relationships
            - 5.4: Complete analysis within 15 minutes for 50 variables × 10,000 time points
        """
        logger.info(
            f"Starting RESIT nonlinear causal discovery for station {station_id} "
            f"with {len(data)} observations and {len(data.columns)} variables"
        )

        # Validate input data
        self._validate_data(data)

        # Apply adaptive sampling for large datasets to improve performance
        working_data = data
        if adaptive_sample_size and len(data) > 5000:
            # For datasets > 5000 samples, use adaptive sampling
            sample_size = min(max_samples or 5000, len(data))
            logger.info(f"Using adaptive sampling: {sample_size} samples from {len(data)}")
            working_data = data.sample(n=sample_size, random_state=self.random_state)

        # Apply RESIT algorithm
        start_time = datetime.now()
        model = self._fit_resit(working_data)
        fit_duration = (datetime.now() - start_time).total_seconds()

        logger.info(f"RESIT fitting completed in {fit_duration:.2f} seconds")

        # Extract causal structure
        adjacency_matrix = model.adjacency_matrix_

        # Compute confidence scores from p-values
        logger.info("Computing confidence scores from independence test p-values")
        confidence_matrix = self._compute_resit_confidence_scores(model, adjacency_matrix)

        # Build CausalDAG from results
        dag = self._build_dag_nonlinear(
            data=data,
            adjacency_matrix=adjacency_matrix,
            confidence_matrix=confidence_matrix,
            station_id=station_id,
            algorithm=algorithm,
            created_by=created_by,
        )

        total_duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Nonlinear causal discovery completed in {total_duration:.2f} seconds. "
            f"Discovered {len(dag.edges)} causal edges"
        )

        return dag

    def _fit_resit(self, data: pd.DataFrame) -> RESIT:
        """
        Fit RESIT model to data with performance optimizations.

        Args:
            data: Input DataFrame

        Returns:
            Fitted RESIT model

        Raises:
            RuntimeError: If fitting fails
        """
        # Check cache if enabled
        cache_key = None
        if self.use_cache:
            # Create cache key from data hash
            cache_key = f"resit_{hash(data.values.tobytes())}"
            if cache_key in self._cache:
                logger.debug("Using cached RESIT model")
                return self._cache[cache_key]

        try:
            # Initialize RESIT with RandomForestRegressor for nonlinear regression
            # RandomForest is efficient and handles nonlinear relationships well
            regressor = RandomForestRegressor(
                n_estimators=50,  # Reduced for performance
                max_depth=5,  # Limit depth to prevent overfitting
                min_samples_split=10,  # Require more samples for splits
                random_state=self.random_state,
                n_jobs=-1,  # Use all CPU cores for parallel processing
            )
            
            # Initialize RESIT with HSIC for nonlinear independence testing
            model = RESIT(
                regressor=regressor,
                random_state=self.random_state,
                alpha=0.05,  # Significance level for independence tests
            )

            # Fit the model
            logger.debug(f"Fitting RESIT on {data.shape[0]} samples × {data.shape[1]} variables")
            model.fit(data.values)

            # Cache the fitted model if caching is enabled
            if self.use_cache and cache_key:
                self._cache[cache_key] = model
                logger.debug(f"Cached RESIT model with key: {cache_key}")

            return model

        except Exception as e:
            logger.error(f"RESIT fitting failed: {str(e)}")
            raise RuntimeError(f"RESIT algorithm failed: {str(e)}") from e

    def _compute_resit_confidence_scores(
        self, model: RESIT, adjacency_matrix: np.ndarray
    ) -> np.ndarray:
        """
        Compute confidence scores for nonlinear causal edges from RESIT p-values.

        RESIT performs independence tests and provides p-values. We convert these
        to confidence scores where lower p-values (stronger evidence of dependence)
        result in higher confidence scores.

        Args:
            model: Fitted RESIT model
            adjacency_matrix: Adjacency matrix from RESIT

        Returns:
            Confidence matrix (same shape as adjacency_matrix) with values in [0, 1]

        Requirements:
            - 5.3: Assign confidence scores to each discovered nonlinear causal edge
        """
        # Check cache if enabled
        cache_key = None
        if self.use_cache:
            cache_key = f"resit_confidence_{id(model)}"
            if cache_key in self._cache:
                logger.debug("Using cached RESIT confidence scores")
                return self._cache[cache_key]

        # Get p-values from RESIT model if available
        # RESIT stores p-values from independence tests
        if hasattr(model, "p_values_") and model.p_values_ is not None:
            # Convert p-values to confidence scores: confidence = 1 - p_value
            # Lower p-value (stronger evidence) -> higher confidence
            confidence_matrix = 1.0 - model.p_values_
            
            # Ensure confidence is in [0, 1] range
            confidence_matrix = np.clip(confidence_matrix, 0.0, 1.0)
            
            # Set confidence to 0 for non-edges (where adjacency is 0)
            confidence_matrix = confidence_matrix * (np.abs(adjacency_matrix) > 1e-8)
        else:
            # Fallback: use binary confidence based on edge existence
            # If edge exists, assign moderate confidence of 0.7
            logger.warning("RESIT model does not have p_values_, using fallback confidence scores")
            confidence_matrix = (np.abs(adjacency_matrix) > 1e-8).astype(float) * 0.7

        # Cache the result if caching is enabled
        if self.use_cache and cache_key:
            self._cache[cache_key] = confidence_matrix
            logger.debug(f"Cached RESIT confidence scores with key: {cache_key}")

        return confidence_matrix

    def _build_dag_nonlinear(
        self,
        data: pd.DataFrame,
        adjacency_matrix: np.ndarray,
        confidence_matrix: np.ndarray,
        station_id: str,
        algorithm: str,
        created_by: str,
    ) -> CausalDAG:
        """
        Build CausalDAG object from RESIT results.

        Args:
            data: Original input data
            adjacency_matrix: Causal coefficients matrix
            confidence_matrix: Confidence scores matrix
            station_id: Station identifier
            algorithm: Algorithm name
            created_by: Creator identifier

        Returns:
            CausalDAG object

        Requirements:
            - 5.2: Output DAG representing nonlinear causal relationships
        """
        nodes = data.columns.tolist()
        edges = []

        # Extract edges from adjacency matrix
        for i in range(len(nodes)):
            for j in range(len(nodes)):
                coefficient = adjacency_matrix[i, j]
                confidence = confidence_matrix[i, j]

                # Only include edges with non-zero coefficients
                if abs(coefficient) > 1e-8:
                    edge = CausalEdge(
                        source=nodes[j],  # Note: adjacency_matrix[i,j] means j->i
                        target=nodes[i],
                        coefficient=float(coefficient),
                        confidence=float(confidence),
                        edge_type="nonlinear",
                        metadata={
                            "algorithm": algorithm,
                            "independence_test": "HSIC",
                        },
                    )
                    edges.append(edge)

        # Create DAG
        dag = CausalDAG(
            dag_id=uuid4(),
            station_id=station_id,
            version=1,
            nodes=nodes,
            edges=edges,
            algorithm=algorithm,
            created_at=datetime.now(),
            created_by=created_by,
            metadata={
                "n_observations": len(data),
                "n_variables": len(nodes),
                "n_edges": len(edges),
                "independence_test": "HSIC",
            },
        )

        return dag

    def _validate_data(self, data: pd.DataFrame) -> None:
        """
        Validate input data for causal discovery.

        Args:
            data: Input DataFrame to validate

        Raises:
            ValueError: If data is invalid
        """
        if data.empty:
            raise ValueError("Input data is empty")

        if data.shape[0] < 2:
            raise ValueError(f"Need at least 2 observations, got {data.shape[0]}")

        if data.shape[1] < 2:
            raise ValueError(f"Need at least 2 variables, got {data.shape[1]}")

        # Check for NaN or infinite values
        if data.isnull().any().any():
            raise ValueError("Input data contains NaN values")

        if np.isinf(data.values).any():
            raise ValueError("Input data contains infinite values")

        # Check for constant columns
        constant_cols = data.columns[data.std() == 0].tolist()
        if constant_cols:
            raise ValueError(f"Input data contains constant columns: {constant_cols}")

    def _fit_directlingam(self, data: pd.DataFrame) -> DirectLiNGAM:
        """
        Fit DirectLiNGAM model to data with performance optimizations.

        Args:
            data: Input DataFrame

        Returns:
            Fitted DirectLiNGAM model

        Raises:
            RuntimeError: If fitting fails
        """
        # Check cache if enabled
        cache_key = None
        if self.use_cache:
            # Create cache key from data hash
            cache_key = f"directlingam_{hash(data.values.tobytes())}"
            if cache_key in self._cache:
                logger.debug("Using cached DirectLiNGAM model")
                return self._cache[cache_key]

        try:
            # Use FastICA with parallel computation for efficiency
            # measure='logcosh' is faster than 'exp' for large datasets
            model = DirectLiNGAM(random_state=self.random_state, measure="logcosh")

            # Fit the model
            logger.debug(f"Fitting DirectLiNGAM on {data.shape[0]} samples × {data.shape[1]} variables")
            model.fit(data.values)

            # Cache the fitted model if caching is enabled
            if self.use_cache and cache_key:
                self._cache[cache_key] = model
                logger.debug(f"Cached DirectLiNGAM model with key: {cache_key}")

            return model

        except Exception as e:
            logger.error(f"DirectLiNGAM fitting failed: {str(e)}")
            raise RuntimeError(f"DirectLiNGAM algorithm failed: {str(e)}") from e

    def _compute_confidence_scores(
        self, data: pd.DataFrame, adjacency_matrix: np.ndarray
    ) -> np.ndarray:
        """
        Compute confidence scores for causal edges using bootstrap resampling.

        This method performs bootstrap resampling with 100 iterations to estimate
        the stability and confidence of discovered causal relationships.

        Args:
            data: Original input data
            adjacency_matrix: Adjacency matrix from DirectLiNGAM

        Returns:
            Confidence matrix (same shape as adjacency_matrix) with values in [0, 1]

        Requirements:
            - 4.3: Assign confidence scores to each discovered causal edge
        """
        # Check cache if enabled
        cache_key = None
        if self.use_cache:
            cache_key = f"confidence_{hash(data.values.tobytes())}_{self.n_bootstrap}"
            if cache_key in self._cache:
                logger.debug("Using cached confidence scores")
                return self._cache[cache_key]

        n_samples, n_vars = data.shape
        edge_counts = np.zeros_like(adjacency_matrix)

        logger.debug(f"Running {self.n_bootstrap} bootstrap iterations")

        for i in range(self.n_bootstrap):
            if (i + 1) % 20 == 0:
                logger.debug(f"Bootstrap iteration {i + 1}/{self.n_bootstrap}")

            # Resample data with replacement
            bootstrap_data = resample(
                data.values, n_samples=n_samples, random_state=self.random_state + i if self.random_state else None
            )
            bootstrap_df = pd.DataFrame(bootstrap_data, columns=data.columns)

            try:
                # Fit DirectLiNGAM on bootstrap sample
                model = DirectLiNGAM(random_state=self.random_state, measure="logcosh")
                model.fit(bootstrap_df.values)

                # Count edges that appear in bootstrap sample
                bootstrap_adj = model.adjacency_matrix_
                edge_counts += (np.abs(bootstrap_adj) > 1e-8).astype(int)

            except Exception as e:
                logger.warning(f"Bootstrap iteration {i} failed: {str(e)}")
                continue

        # Compute confidence as proportion of bootstrap samples containing each edge
        confidence_matrix = edge_counts / self.n_bootstrap

        # Cache the result if caching is enabled
        if self.use_cache and cache_key:
            self._cache[cache_key] = confidence_matrix
            logger.debug(f"Cached confidence scores with key: {cache_key}")

        return confidence_matrix

    def _build_dag(
        self,
        data: pd.DataFrame,
        adjacency_matrix: np.ndarray,
        confidence_matrix: np.ndarray,
        causal_order: np.ndarray,
        station_id: str,
        algorithm: str,
        created_by: str,
    ) -> CausalDAG:
        """
        Build CausalDAG object from DirectLiNGAM results.

        Args:
            data: Original input data
            adjacency_matrix: Causal coefficients matrix
            confidence_matrix: Confidence scores matrix
            causal_order: Causal ordering of variables
            station_id: Station identifier
            algorithm: Algorithm name
            created_by: Creator identifier

        Returns:
            CausalDAG object

        Requirements:
            - 4.2: Output DAG representing discovered causal relationships
            - 4.4: Include causal coefficient magnitude for each relationship
        """
        nodes = data.columns.tolist()
        edges = []

        # Extract edges from adjacency matrix
        for i in range(len(nodes)):
            for j in range(len(nodes)):
                coefficient = adjacency_matrix[i, j]
                confidence = confidence_matrix[i, j]

                # Only include edges with non-zero coefficients
                if abs(coefficient) > 1e-8:
                    # Find causal order indices - handle numpy version differences
                    # Convert causal_order to 1d array explicitly to avoid 0d array issues
                    causal_order_1d = np.atleast_1d(causal_order)
                    source_order_idx = np.where(causal_order_1d == j)[0]
                    target_order_idx = np.where(causal_order_1d == i)[0]
                    
                    edge = CausalEdge(
                        source=nodes[j],  # Note: adjacency_matrix[i,j] means j->i
                        target=nodes[i],
                        coefficient=float(coefficient),
                        confidence=float(confidence),
                        edge_type="linear",
                        metadata={
                            "algorithm": algorithm,
                            "causal_order_source": int(source_order_idx[0]) if len(source_order_idx) > 0 else -1,
                            "causal_order_target": int(target_order_idx[0]) if len(target_order_idx) > 0 else -1,
                        },
                    )
                    edges.append(edge)

        # Create DAG
        dag = CausalDAG(
            dag_id=uuid4(),
            station_id=station_id,
            version=1,
            nodes=nodes,
            edges=edges,
            algorithm=algorithm,
            created_at=datetime.now(),
            created_by=created_by,
            metadata={
                "n_observations": len(data),
                "n_variables": len(nodes),
                "n_edges": len(edges),
                "causal_order": causal_order.tolist() if hasattr(causal_order, 'tolist') else list(causal_order),
                "n_bootstrap_iterations": self.n_bootstrap,
            },
        )

        return dag

    def compute_confidence_scores(self, dag: CausalDAG, data: pd.DataFrame) -> CausalDAG:
        """
        Recompute confidence scores for an existing DAG.

        This method can be used to update confidence scores when new data becomes available.

        Args:
            dag: Existing CausalDAG
            data: New data for confidence computation

        Returns:
            Updated CausalDAG with new confidence scores
        """
        logger.info(f"Recomputing confidence scores for DAG {dag.dag_id}")

        # Validate data
        self._validate_data(data)

        # Reconstruct adjacency matrix from DAG edges
        nodes = dag.nodes
        n_vars = len(nodes)
        adjacency_matrix = np.zeros((n_vars, n_vars))

        node_to_idx = {node: i for i, node in enumerate(nodes)}

        for edge in dag.edges:
            i = node_to_idx[edge.target]
            j = node_to_idx[edge.source]
            adjacency_matrix[i, j] = edge.coefficient

        # Compute new confidence scores
        confidence_matrix = self._compute_confidence_scores(data, adjacency_matrix)

        # Update edges with new confidence scores
        updated_edges = []
        for edge in dag.edges:
            i = node_to_idx[edge.target]
            j = node_to_idx[edge.source]
            new_confidence = confidence_matrix[i, j]

            updated_edge = CausalEdge(
                source=edge.source,
                target=edge.target,
                coefficient=edge.coefficient,
                confidence=float(new_confidence),
                edge_type=edge.edge_type,
                metadata=edge.metadata,
            )
            updated_edges.append(updated_edge)

        # Create updated DAG
        updated_dag = CausalDAG(
            dag_id=dag.dag_id,
            station_id=dag.station_id,
            version=dag.version + 1,
            nodes=dag.nodes,
            edges=updated_edges,
            algorithm=dag.algorithm,
            created_at=datetime.now(),
            created_by=dag.created_by,
            metadata={
                **dag.metadata,
                "confidence_recomputed_at": datetime.now().isoformat(),
                "n_bootstrap_iterations": self.n_bootstrap,
            },
        )

        return updated_dag

    def save_dag(self, dag: CausalDAG, station_id: str, metadata: Dict) -> str:
        """
        Save discovered DAG to persistent storage.

        Args:
            dag: CausalDAG to save
            station_id: Station identifier
            metadata: Additional metadata to store

        Returns:
            DAG identifier (UUID as string)

        Note:
            This is a placeholder implementation. Full database integration
            will be implemented in later tasks.
        """
        logger.info(f"Saving DAG {dag.dag_id} for station {station_id}")

        # TODO: Implement database persistence in later tasks
        # For now, just return the DAG ID
        return str(dag.dag_id)
