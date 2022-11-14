import numpy as np
from tqdm.auto import tqdm
from scipy.stats import entropy
from message import Message 
from protocols import Protocol
from adversary import Adversary

class Simulator():
    """Abstraction to simulate message passing on a P2P network"""
    
    def __init__(self, protocol: Protocol, adv: Adversary, num_msg: int=10, verbose=True):
        """
        Parameters
        ----------
        protocol : protocol.Protocol
            protocol that determines the rules of message passing
        adv : adversary.Adversary
            adversary that observe messages in the P2P network
        num_msg : int
            number of messages to simulate
        """
        if num_msg > 10:
            self.verbose = False
        else:
            self.verbose = verbose
        self.protocol = protocol
        self.adversary = adv
        self.messages = [Message(sender) for sender in self.protocol.network.sample_random_sources(num_msg)]
        
    def run(self, coverage_threshold: float=0.9, epsilon=0.001):
        """
        Run simulation
        
        Parameters
        ----------
        coverage_threshold : float
            stop propagating a message if it reached the given fraction of network nodes
        epsilon : adversary.Adversary
            stop propagating a message if it is in the spreading phase and could not reach more than epsilon fraction of network nodes in the previous step
        """
        for msg in tqdm(self.messages):
            reached_nodes = 0.0
            delta = 1.0
            while reached_nodes < coverage_threshold and delta >= epsilon:
                old_reached_nodes = reached_nodes
                reached_nodes, spreading_phase = msg.process(self.protocol, self.adversary)
                if spreading_phase and old_reached_nodes >= reached_nodes:
                    delta = old_reached_nodes - reached_nodes
                if self.verbose:
                    print(msg.mid, reached_nodes, delta)
            if self.verbose:
                print()
                

class Evaluator:
    """Measures the deanonymization performance of the adversary for a given simulation"""
    
    def __init__(self, simulator: Simulator):
        """
        Parameters
        ----------
        simulator : Simulator
            Specify the simulation for evaluation
        """
        self.simulator = simulator
        self.probas = simulator.adversary.predict_msg_source()
        self.proba_ranks = self.probas.rank(axis=1, ascending=False, method="average")
    
    @property
    def exact_hits(self):
        hits = []
        for msg in self.simulator.messages:
            # adversary might not see every message
            if msg.mid in self.probas.index and self.probas.loc[msg.mid, msg.source] == 1.0:
                hits.append(1.0)
            else:
                hits.append(0.0)
        return np.array(hits)
    
    @property
    def ranks(self):
        ranks = []
        for msg in self.simulator.messages:
            # adversary might not see every message
            if msg.mid in self.probas.index:
                ranks.append(self.proba_ranks.loc[msg.mid, msg.source])
            else:
                # what to do with unseen messages? random rank might be better...
                ranks.append(len(self.simulator.protocol.network.num_nodes))
        return np.array(ranks)
    
    @property
    def inverse_ranks(self):
        return 1.0 / self.ranks
        
    @property
    def entropies(self):
        num_nodes = self.simulator.protocol.network.num_nodes
        rnd_entropy = entropy(1.0/num_nodes * np.ones(num_nodes))
        entropies = []
        for msg in self.simulator.messages:
            # adversary might not see every message
            if msg.mid in self.probas.index:
                entropies.append(entropy(self.probas.loc[msg.mid].values))
            else:
                entropies.append(rnd_entropy)
        return np.array(entropies)
        