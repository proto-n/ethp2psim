import networkx as nx
import numpy as np
from .data import StakedEthereumDistribution
from typing import Optional, NoReturn, Union, List


class NodeWeightGenerator:
    """
    Reusable object to generate weights for Peer-to-peer network nodes

    Parameters
    ----------
    mode: {'random', 'stake'}, default 'random'
        Nodes are weighted either randomly, according to their staked Ethereum value
    seed: int (optional)
        Random seed (disabled by default)
    """

    def __init__(self, mode: str = "random", seed: Optional[int] = None):
        self._rng = np.random.default_rng(seed)
        if mode in ["random", "stake"]:
            self.mode = mode
            if self.mode == "stake":
                self._staked_eth = StakedEthereumDistribution()
        else:
            raise ValueError("Choose 'node_weight' from values ['random', 'stake']!")

    def generate(
        self, graph: nx.Graph, rng: Optional[np.random._generator.Generator] = None
    ) -> dict:
        """
        Generate node weights for the nodes of the input graph.

        Parameters
        ----------
        graph : networkx.Graph
            Provide graph to generate node weights
        rng : Optional[np.random._generator.Generator]
            Random number generator

        Examples
        --------
        >>> import networkx as nx
        >>> G = nx.Graph()
        >>> G.add_edges_from([(0,1),(1,2),(2,0)])
        >>> nw_gen = NodeWeightGenerator('stake')
        >>> len(nw_gen.generate(G))
        3
        """
        if rng is None:
            rng = self._rng
        nodes = graph.nodes
        if self.mode == "stake":
            # nodes are weighted by their staked ether ratio
            weights = rng.choice(self._staked_eth.weights, size=len(nodes))
            weights = weights / np.sum(weights)
            weights = dict(zip(nodes, weights))
        else:
            # nodes are weighted uniformly at random
            weights = dict(zip(nodes, rng.random(size=len(nodes))))
        return weights


class EdgeWeightGenerator:
    """
    Reusable object to generate latencies for connections between Peer-to-peer network nodes

    Parameters
    ----------
    mode: {'random', 'normal', 'unweighted', 'custom'}, default 'random'
        Choose setting for connection latency generation!
    seed: int (optional)
        Random seed (disabled by default)
    """

    def __init__(self, mode: str = "random", seed: Optional[int] = None):
        self._rng = np.random.default_rng(seed)
        if mode in ["random", "normal", "unweighted", "custom"]:
            self.mode = mode
        else:
            raise ValueError(
                "Choose 'edge_weight' from values ['random', 'normal', 'custom', 'unweighted']!"
            )

    def generate(
        self, graph: nx.Graph, rng: Optional[np.random._generator.Generator] = None
    ) -> dict:
        """
        Generate edge weights (latency) for the edges of the input graph.

        Parameters
        ----------
        graph : networkx.Graph
            Provide graph to generate connections latencies
        rng : Optional[np.random._generator.Generator]
            Random number generator

        Examples
        --------
        >>> import networkx as nx
        >>> G = nx.Graph()
        >>> G.add_edges_from([(0,1),(1,2),(2,3),(2,0)])
        >>> ew_gen = EdgeWeightGenerator('normal')
        >>> len(ew_gen.generate(G))
        4
        """
        if rng is None:
            rng = self._rng
        weights = {}
        edges = graph.edges
        if self.mode == "random":
            # set p2p latencies uniformly at random
            weights = dict(zip(edges, 1000 * rng.random(size=len(edges))))
        elif self.mode == "normal":
            # set p2p latencies according to Table 2: https://arxiv.org/pdf/1801.03998.pdf
            # negative latency values are prohibited
            weights = dict(
                zip(edges, np.abs(rng.normal(loc=171, scale=76, size=len(edges))))
            )
        elif self.mode == "unweighted":
            weights = dict(zip(edges, np.ones(len(edges))))
        elif self.mode == "custom":
            weights = {}
            for u, v, l in graph.edges(data=True):
                weights[(u, v)] = l["latency"]
        return weights


class Network:
    """
    Peer-to-peer network abstraction

    Parameters
    ----------
    node_weight_gen: NodeWeightGenerator
        Set generator for node weights. By default random node weights are used.
    edge_weight_gen: EdgeWeightGenerator
        Set generator for edge weights. By default random edge weights are used.
    num_nodes : int
        Number of nodes in the peer-to-peer (P2P) graph
    k : int
        Regularity parameter
    graph : networkx.Graph
        Provide custom graph otherwise a k-regular random graph is generated
    seed: int (optional)
        Random seed (disabled by default)
    """

    def __init__(
        self,
        node_weight_gen: NodeWeightGenerator,
        edge_weight_gen: EdgeWeightGenerator,
        num_nodes: Optional[int] = 100,
        k: Optional[int] = 5,
        graph: Optional[nx.Graph] = None,
        seed: Optional[int] = None,
    ):
        self._rng = np.random.default_rng(seed)
        self._generate_graph(num_nodes, k, graph, seed)
        self.node_weight_generator = node_weight_gen
        self._set_node_weights()
        self.edge_weight_generator = edge_weight_gen
        self._set_edge_weights()

    def _generate_graph(
        self,
        num_nodes: int,
        k: int,
        graph: Optional[nx.Graph] = None,
        seed: Optional[int] = None,
    ) -> NoReturn:
        if graph is not None:
            self.graph = graph.copy()
            self.k = -1
        else:
            self.graph = nx.random_regular_graph(k, num_nodes, seed)
            self.k = k

    def __repr__(self):
        return "Network(nw_mode=%s, ew_mode=%s, num_nodes=%i, k=%i)" % (
            self.node_weight_generator.mode,
            self.edge_weight_generator.mode,
            self.num_nodes,
            self.k,
        )

    @property
    def num_nodes(self) -> int:
        return self.graph.number_of_nodes()

    @property
    def num_edges(self) -> int:
        return self.graph.number_of_edges()

    @property
    def nodes(self) -> list:
        return list(self.graph.nodes())

    def _set_node_weights(self) -> NoReturn:
        self.node_weights = self.node_weight_generator.generate(self.graph, self._rng)

    def _set_edge_weights(self) -> NoReturn:
        self.edge_weights = self.edge_weight_generator.generate(self.graph, self._rng)
        nx.set_edge_attributes(
            self.graph,
            {edge: {"latency": value} for edge, value in self.edge_weights.items()},
        )

    def get_edge_weight(
        self, node1: int, node2: int, external=None
    ) -> Union[float, None]:
        """
        Get edge weight for node pair

        Parameters
        ----------
        node1 : int
            First endpoint of the link to be removed
        node2 : int
            Second endpoint of the link to be removed

        Examples
        --------
        >>> import networkx as nx
        >>> G = nx.Graph()
        >>> G.add_weighted_edges_from([(0,1,0.1),(1,2,0.2),(2,0,0.3)], weight='latency')
        >>> nw_gen = NodeWeightGenerator('random')
        >>> ew_gen = EdgeWeightGenerator('custom')
        >>> net = Network(nw_gen, ew_gen, graph=G)
        >>> net.get_edge_weight(0, 2)
        0.3
        >>> net.get_edge_weight(0, 3) is None
        True
        """
        link = (node1, node2)
        if not link in self.edge_weights:
            link = (node2, node1)
        if link in self.edge_weights:
            return self.edge_weights[link]
        elif external is not None:
            return external.get_edge_weight(node1, node2)
        else:
            return None

    def get_central_nodes(self, k: int, metric: str = "degree"):
        """
        Get top central nodes of the P2P network

        Parameters
        ----------
        k : int
            Number of central nodes to return
        metric : str {'betweenness','pagerank','degree'}
            Choose centrality metric

        Examples
        --------
        >>> from .data import GoerliTestnet
        >>> nw_gen = NodeWeightGenerator('random')
        >>> ew_gen = EdgeWeightGenerator('normal')
        >>> goerli = GoerliTestnet()
        >>> net = Network(nw_gen, ew_gen, graph=goerli.graph)
        >>> net.get_central_nodes(3, 'degree')
        ['192', '772', '661']
        """
        if metric == "betweenness":
            scores = dict(nx.betweenness_centrality(self.graph))
        elif metric == "pagerank":
            weights = dict(nx.pagerank(self.graph))
        else:
            weights = dict(nx.degree(self.graph))
        ordered_nodes = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        top_nodes, top_scores = zip(*ordered_nodes[:k])
        return list(top_nodes)

    def sample_random_nodes(
        self,
        count: int,
        replace: bool,
        use_weights: bool = False,
        exclude: Optional[List[int]] = None,
        rng: Optional[np.random._generator.Generator] = None,
    ) -> List[int]:
        """
        Sample network nodes uniformly at random

        Parameters
        ----------
        count : int
            Number of nodes to sample
        replace : bool
            Whether the sample is with or without replacement
        use_weights : bool
            Set to sample nodes with respect to their weights
        exclude : Optional[list]
            List of nodes to exclude from the sample
        rng : Optional[np.random._generator.Generator]
            Random number generator

        Examples
        --------
        >>> nw_gen = NodeWeightGenerator('random')
        >>> ew_gen = EdgeWeightGenerator('normal')
        >>> net = Network(nw_gen, ew_gen, num_nodes=5, k=2)
        >>> candidates = net.sample_random_nodes(3, False, exclude=[3,4])
        >>> len(candidates)
        3
        >>> 3 in candidates
        False
        >>> 4 in candidates
        False
        """
        if rng is None:
            rng = self._rng
        nodes = list(self.graph.nodes())
        weights = self.node_weights.copy()
        if exclude is not None:
            intersection = np.intersect1d(nodes, exclude)
            for node in intersection:
                nodes.remove(node)
                del weights[node]
        sum_weights = np.sum(list(weights.values()))
        probas_arr = [weights[node] / sum_weights for node in nodes]
        if use_weights:
            return list(rng.choice(nodes, count, replace=replace, p=probas_arr))
        else:
            return list(rng.choice(nodes, count, replace=replace))

    def update(
        self,
        graph: nx.Graph,
        reset_edge_weights: bool = False,
        reset_node_weights: bool = False,
    ) -> NoReturn:
        """
        Update P2P network.

        Parameters
        ----------
        graph : networkx.Graph
            Update connections based on the provided graph.
        reset_edge_weights : bool (default: False)
            Set whether to reset weights for existing edges
        reset_node_weights : bool (default: False)
            Set whether to reset weights for existing nodes

        Examples
        --------
        >>> import networkx as nx
        >>> G1 = nx.Graph()
        >>> G1.add_edges_from([(0,1),(1,2),(2,0)])
        >>> G2 = nx.Graph()
        >>> G2.add_edges_from([(2,3),(3,4),(4,0)])
        >>> nw_gen = NodeWeightGenerator('random')
        >>> ew_gen = EdgeWeightGenerator('normal')
        >>> net = Network(nw_gen, ew_gen, graph=G1)
        >>> net.num_nodes
        3
        >>> net.update(G2)
        >>> net.num_nodes
        5
        """
        # update structure
        undirected_G = graph.to_undirected()
        self.graph.update(undirected_G.edges(data=True), undirected_G.nodes())
        # update node weight
        new_node_weights = self.node_weight_generator.generate(self.graph, self._rng)
        for node, weight in new_node_weights.items():
            if reset_node_weights or (self.node_weights.get(node) is None):
                self.node_weights[node] = weight
        # update edge weights
        new_edge_weights = self.edge_weight_generator.generate(self.graph, self._rng)
        for link, weight in new_edge_weights.items():
            if reset_edge_weights or (self.get_edge_weight(link[0], link[1]) is None):
                self.edge_weights[link] = weight
        nx.set_edge_attributes(
            self.graph,
            {edge: {"latency": value} for edge, value in self.edge_weights.items()},
        )

    def remove_edge(self, node1: int, node2: int) -> bool:
        """
        Delete edge from the network. The functions returns whether edge removal was successful.

        Parameters
        ----------
        node1 : int
            First endpoint of the link to be removed
        node2 : int
            Second endpoint of the link to be removed

        Examples
        --------
        >>> import networkx as nx
        >>> G = nx.Graph()
        >>> G.add_edges_from([(0,1),(1,2),(2,0),(2,3)])
        >>> nw_gen = NodeWeightGenerator('random')
        >>> ew_gen = EdgeWeightGenerator('normal')
        >>> net = Network(nw_gen, ew_gen, graph=G)
        >>> net.remove_edge(2,3)
        True
        >>> net.remove_edge(2,3)
        False
        >>> net.remove_edge(0,2)
        True
        """
        link = (node1, node2)
        if link in self.edge_weights:
            success = True
        else:
            link = (node2, node1)
            if link in self.edge_weights:
                success = True
            else:
                success = False
        if success:
            del self.edge_weights[link]
            self.graph.remove_edge(node1, node2)
        return success
