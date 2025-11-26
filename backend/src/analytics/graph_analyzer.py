"""
Graph Analyzer using GraphSAGE for arbitrage path discovery
Advanced graph neural network for opportunity detection
"""
import numpy as np
import networkx as nx
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class GraphSAGEAnalyzer:
    """
    GraphSAGE (Graph Sample and Aggregate) for arbitrage path analysis
    Identifies complex multi-hop arbitrage opportunities
    """
    
    def __init__(self, embedding_dim: int = 64):
        self.embedding_dim = embedding_dim
        self.node_embeddings: Dict[str, np.ndarray] = {}
        
    def generate_embeddings(self, graph: nx.DiGraph) -> Dict[str, np.ndarray]:
        """
        Generate node embeddings using GraphSAGE-like aggregation
        
        Args:
            graph: NetworkX directed graph with price edges
        
        Returns:
            Dictionary mapping node names to embedding vectors
        """
        embeddings = {}
        
        for node in graph.nodes():
            # Initialize with random embedding
            node_features = self._extract_node_features(graph, node)
            
            # Aggregate neighbor information
            neighbor_embeddings = []
            for neighbor in graph.neighbors(node):
                edge_data = graph[node][neighbor]
                neighbor_features = self._extract_edge_features(edge_data)
                neighbor_embeddings.append(neighbor_features)
            
            if neighbor_embeddings:
                aggregated = np.mean(neighbor_embeddings, axis=0)
                combined = np.concatenate([node_features, aggregated])
            else:
                combined = node_features
            
            # Apply non-linear transformation
            embedding = self._transform(combined)
            embeddings[node] = embedding
        
        self.node_embeddings = embeddings
        return embeddings
    
    def _extract_node_features(self, graph: nx.DiGraph, node: str) -> np.ndarray:
        """Extract features for a node"""
        features = []
        
        # Degree features
        in_degree = graph.in_degree(node)
        out_degree = graph.out_degree(node)
        features.extend([in_degree, out_degree])
        
        # Node name encoding (simple hash)
        node_hash = hash(node) % 1000 / 1000.0
        features.append(node_hash)
        
        # Pad to embedding dimension
        while len(features) < self.embedding_dim // 2:
            features.append(0.0)
        
        return np.array(features[:self.embedding_dim // 2])
    
    def _extract_edge_features(self, edge_data: Dict) -> np.ndarray:
        """Extract features from edge data"""
        features = []
        
        # Price feature
        features.append(edge_data.get('price', 1.0))
        
        # Weight (negative log price)
        features.append(edge_data.get('weight', 0.0))
        
        # Liquidity feature
        features.append(np.log1p(edge_data.get('liquidity', 1.0)))
        
        # Exchange type encoding
        exchange_type = edge_data.get('exchange_type', 'unknown')
        features.append(hash(str(exchange_type)) % 100 / 100.0)
        
        # Pad to half embedding dimension
        while len(features) < self.embedding_dim // 2:
            features.append(0.0)
        
        return np.array(features[:self.embedding_dim // 2])
    
    def _transform(self, features: np.ndarray) -> np.ndarray:
        """Apply non-linear transformation"""
        # Simple ReLU-like activation
        transformed = np.maximum(0, features)
        
        # Normalize
        norm = np.linalg.norm(transformed)
        if norm > 0:
            transformed = transformed / norm
        
        return transformed
    
    def find_similar_nodes(
        self,
        node: str,
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Find most similar nodes based on embeddings
        
        Args:
            node: Source node
            top_k: Number of similar nodes to return
        
        Returns:
            List of (node_name, similarity_score) tuples
        """
        if node not in self.node_embeddings:
            return []
        
        source_embedding = self.node_embeddings[node]
        similarities = []
        
        for other_node, other_embedding in self.node_embeddings.items():
            if other_node == node:
                continue
            
            # Cosine similarity
            similarity = np.dot(source_embedding, other_embedding)
            similarities.append((other_node, float(similarity)))
        
        # Sort by similarity and return top k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def detect_communities(
        self,
        graph: nx.DiGraph,
        resolution: float = 1.0
    ) -> Dict[str, int]:
        """
        Detect communities (clusters) in the graph
        Useful for identifying related tokens/exchanges
        
        Args:
            graph: NetworkX graph
            resolution: Resolution parameter for community detection
        
        Returns:
            Dictionary mapping nodes to community IDs
        """
        try:
            # Convert to undirected for community detection
            undirected = graph.to_undirected()
            
            # Use Louvain community detection
            import community as community_louvain
            communities = community_louvain.best_partition(undirected)
            
            return communities
        except ImportError:
            logger.warning("python-louvain not installed, using simple clustering")
            return self._simple_clustering(graph)
    
    def _simple_clustering(self, graph: nx.DiGraph) -> Dict[str, int]:
        """Simple clustering based on connected components"""
        undirected = graph.to_undirected()
        components = nx.connected_components(undirected)
        
        clustering = {}
        for idx, component in enumerate(components):
            for node in component:
                clustering[node] = idx
        
        return clustering
    
    def rank_arbitrage_paths(
        self,
        paths: List[List[str]],
        graph: nx.DiGraph
    ) -> List[Tuple[List[str], float]]:
        """
        Rank arbitrage paths using embeddings and graph features
        
        Args:
            paths: List of paths (each path is list of nodes)
            graph: NetworkX graph
        
        Returns:
            List of (path, score) tuples sorted by score
        """
        scored_paths = []
        
        for path in paths:
            score = self._score_path(path, graph)
            scored_paths.append((path, score))
        
        scored_paths.sort(key=lambda x: x[1], reverse=True)
        return scored_paths
    
    def _score_path(self, path: List[str], graph: nx.DiGraph) -> float:
        """Calculate score for an arbitrage path"""
        if len(path) < 2:
            return 0.0
        
        scores = []
        
        # Path profitability (negative cycle weight)
        total_weight = 0
        for i in range(len(path) - 1):
            if graph.has_edge(path[i], path[i+1]):
                edge = graph[path[i]][path[i+1]]
                total_weight += edge.get('weight', 0)
        
        profit_score = -total_weight if total_weight < 0 else 0
        scores.append(profit_score)
        
        # Path liquidity
        min_liquidity = float('inf')
        for i in range(len(path) - 1):
            if graph.has_edge(path[i], path[i+1]):
                edge = graph[path[i]][path[i+1]]
                liquidity = edge.get('liquidity', 0)
                min_liquidity = min(min_liquidity, liquidity)
        
        liquidity_score = np.log1p(min_liquidity) / 10.0
        scores.append(liquidity_score)
        
        # Embedding similarity (how related are nodes in path)
        if all(node in self.node_embeddings for node in path):
            similarity_scores = []
            for i in range(len(path) - 1):
                emb1 = self.node_embeddings[path[i]]
                emb2 = self.node_embeddings[path[i+1]]
                sim = np.dot(emb1, emb2)
                similarity_scores.append(sim)
            
            avg_similarity = np.mean(similarity_scores) if similarity_scores else 0
            scores.append(avg_similarity)
        
        # Path length penalty (shorter is better)
        length_penalty = 1.0 / len(path)
        scores.append(length_penalty)
        
        # Weighted average
        weights = [0.5, 0.2, 0.2, 0.1]
        final_score = sum(s * w for s, w in zip(scores, weights))
        
        return final_score
