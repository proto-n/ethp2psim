import networkx as nx
import numpy as np

class NodeWeightGenerator:
    """Reusable object to generate weights for Peer-to-peer network nodes"""
    
    def __init__(self, mode: str="random"):
        """
        Parameters
        ----------
        mode: {'random', 'stake'}, default 'random'
            Nodes are weighted either randomly or according to their staked Ethereum value
        """
        if mode in ["random", "stake"]:
            self.mode = mode
        else:
            raise ValueError("Choose 'node_weight' from values ['random', 'stake']!")
            
    def generate(self, graph: nx.Graph):
        """
        Parameters
        ----------
        graph : networkx.Graph
            Provide graph to generate node weights
        """
        nodes = graph.nodes
        if self.mode == "random":
            # nodes are weighted uniformly at random
            weights = dict(zip(nodes, np.random.random(size=len(nodes))))
        elif self.mode == "stake":
            # TODO: sample from a distribution instead.. not very nice to load hard-coded file
            weights = np.load(open('figures/sendingProbabilities.npy', 'rb'), allow_pickle=True)
            weights = weights / np.sum(weights)
            # nodes are weighted by their staked ether ratio
            # TODO: what if there are more nodes than in the loaded file!!??
            weights = dict(zip(nodes, weights[:len(nodes)]))
        return weights

class EdgeWeightGenerator:
    """Reusable object to generate latencies for connections between Peer-to-peer network nodes"""
    
    def __init__(self, mode: str="random"):
        """
        Parameters
        ----------
        mode: {'random', 'normal', 'unweighted', 'custom'}, default 'random'
            Choose setting for connection latency generation!
        """
        if mode in ["random", "normal", "unweighted", "custom"]:
            self.mode= mode
        else:
            raise ValueError("Choose 'edge_weight' from values ['random', 'normal', 'custom', 'unweighted']!")
        
    def generate(self, graph: nx.Graph):
        """
        Parameters
        ----------
        graph : networkx.Graph
            Provide graph to generate connections latencies
        """
        weights = {}
        edges = graph.edges
        if self.mode== "random":
            # set p2p latencies uniformly at random
            weights = dict(zip(edges, 1000*np.random.random(size=len(edges))))
        elif self.mode== "normal":
            # set p2p latencies according to Table 2: https://arxiv.org/pdf/1801.03998.pdf
            # negative latency values are prohibited
            weights = dict(zip(edges, np.abs(np.random.normal(loc=171, scale=76, size=len(edges)))))
        elif self.mode== "unweighted":
            weights = dict(zip(edges, np.ones(len(edges))))
        elif self.mode== "custom":
            weights = {}
            for u,v,l in graph.edges(data=True):
                weights[(u,v)] = l["latency"]
        return weights

class Network:
    """Peer-to-peer network abstraction"""
    
    def __init__(self, num_nodes: int=100, k: int=5, graph: nx.Graph=None, seed: int=None, node_weight: str="random", edge_weight: str="random"):
        """
        Parameters
        ----------
        num_nodes : int
            Number of nodes in the peer-to-peer (P2P) graph
        k : int
            Regularity parameter
        graph : networkx.Graph
            Provide custom graph otherwise a k-regular random graph is generated
        seed: int (optional)
            Random seed (disabled by default)
        node_weight: {'random', 'stake'}, default 'random'
            Nodes are weighted either randomly or according to their staked Ethereum value
        edge_weight: {'random', 'normal', 'unweighted', 'custom'}, default 'random'
            P2P connection latencies are weighted either randomly or according to normal distribution
        """
        self._rng = np.random.default_rng(seed)
        self._generate_graph(num_nodes, k, graph)
        self._node_weight_generator = NodeWeightGenerator(node_weight)
        self._set_node_weights()
        self._edge_weight_generator = EdgeWeightGenerator(edge_weight)
        self._set_edge_weights()
        
    def _generate_graph(self, num_nodes: int, k: int, graph: nx.Graph=None):
        if graph is not None:
            self.graph = graph.copy()
            self.k = -1
        else:
            self.graph = nx.random_regular_graph(k, num_nodes)
            self.k = k
            
    @property
    def num_nodes(self):
        return self.graph.number_of_nodes()
    
    @property
    def num_edges(self):
        return self.graph.number_of_edges()
    
    @property
    def nodes(self):
        return self.graph.nodes()

    def _set_node_weights(self):
        self.node_weights = self._node_weight_generator.generate(self.graph)
    
    def _set_edge_weights(self):
        self.edge_weights = self._edge_weight_generator.generate(self.graph)
        nx.set_edge_attributes(self.graph, {edge:{"latency":value} for edge, value in self.edge_weights.items()})
            
    def get_edge_weight(self, sender: int, receiver: int):
        """Get edge weight for node pair"""
        link = (sender, receiver)
        if not link in self.edge_weights:
            link = (receiver, sender)
        return self.edge_weights[link]
        
    def sample_random_nodes(self, count: int, replace: bool, use_weights: bool=False, exclude: list=None):
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
        exclude : list
            List of nodes to exclude from the sample
        """
        nodes = list(self.graph.nodes())
        weights = self.node_weights.copy()
        if exclude is not None:
            intersection = np.intersect1d(nodes, exclude)
            for node in intersection:
                nodes.remove(node)
                del weights[node]
        sum_weights = np.sum(list(weights.values()))
        probas_arr = [weights[node] / sum_weights  for node in nodes]
        if use_weights:
            return self._rng.choice(nodes, count, replace=replace, p=probas_arr)
        else:
            return self._rng.choice(nodes, count, replace=replace)