import pandas as pd
import numpy as np
import networkx as nx
from protocols import ProtocolEvent
from network import Network
from typing import NoReturn, Iterable, Union


class EavesdropEvent:
    """
    Information related to the observed message

    Parameters
    ----------
    node : str
        Message identifier
    source : int
        Source node of the message
    protocol_event : protocols.ProtocolEvent
        Contains message spreading related information
    """

    def __init__(self, mid: str, source: int, pe: ProtocolEvent):
        self.mid = mid
        self.source = source
        self.protocol_event = pe

    @property
    def sender(self) -> int:
        return self.protocol_event.sender

    @property
    def receiver(self) -> int:
        return self.protocol_event.receiver

    def __repr__(self):
        return "EavesdropEvent(%s, %i, %s)" % (
            self.mid,
            self.source,
            self.protocol_event,
        )


class Adversary:
    """
    Abstraction for the entity that tries to deanonymize Ethereum addresses by observing p2p network traffic

    Parameters
    ----------
    network : network.Network
        Simulated P2P network
    ratio : float
        Fraction of adversary nodes in the P2P network
    """

    def __init__(self, network: Network, ratio: float, active: bool = False):
        self.ratio = ratio
        self.network = network
        self.active = active
        self.captured_events = []
        self.captured_msgs = set()
        self._sample_adversary_nodes(network)

    def __repr__(self):
        return "Adversary(ratio=%.2f, active=%s)" % (self.ratio, self.active)

    @property
    def candidates(self) -> list:
        return list(self.network.graph.nodes())

    def _sample_adversary_nodes(self, network: Network) -> NoReturn:
        """Randomly select given fraction of nodes to be adversaries"""
        num_adversaries = int(len(self.candidates) * self.ratio)
        self.nodes = network.sample_random_nodes(
            num_adversaries, use_weights=False, replace=False
        )

    def eavesdrop_msg(self, ee: EavesdropEvent) -> NoReturn:
        """Adversary records the observed information"""
        self.captured_events.append(ee)
        self.captured_msgs.add(ee.mid)

    def _find_first_contact(
        self, estimator: str
    ) -> Iterable[Union[dict, pd.DataFrame]]:
        contact_time = {}
        received_from = {}
        contact_node = {}
        for ee in self.captured_events:
            message_id = ee.mid
            sender = ee.sender
            receiver = ee.receiver
            if estimator == "first_sent":
                timestamp = ee.protocol_event.delay - self.network.get_edge_weight(
                    sender, receiver
                )
            else:
                timestamp = ee.protocol_event.delay
            if (not message_id in contact_time) or timestamp < contact_time[message_id]:
                contact_time[message_id] = timestamp
                received_from[message_id] = sender
                contact_node[message_id] = receiver
        arr = np.zeros((len(self.captured_msgs), len(self.candidates)))
        empty_predictions = pd.DataFrame(
            arr, columns=self.candidates, index=list(self.captured_msgs)
        )
        return contact_time, contact_node, received_from, empty_predictions

    def _shortest_path_estimator(self) -> pd.DataFrame:
        (
            contact_time,
            contact_node,
            received_from,
            predictions,
        ) = self._find_first_contact(estimator="first_reach")
        active_adversary_nodes = set(contact_node.values())
        probas_by_adversary = {}
        # precompute predictions for adversary nodes
        for a in active_adversary_nodes:
            # TODO: later we can eliminate candidates where there are other adversaries on the shortest path! Handle the case when there are multiple adversaries on the path!
            distances = nx.single_source_dijkstra(
                self.network.graph, a, weight="latency"
            )[0]
            # delete adversary nodes as they are never predicted as message source
            for adv in self.nodes:
                del distances[adv]
            inverse_distances = {n: 1.0 / distances[n] for n in distances}
            s = sum(inverse_distances.values())
            probas_by_adversary[a] = [
                inverse_distances.get(n, 0.0) / s for n in self.candidates
            ]
        # fill prediction matrix with probas
        for mid, observer in contact_node.items():
            predictions.loc[mid] = probas_by_adversary[observer]
        return predictions

    def _dummy_estimator(self) -> pd.DataFrame:
        N = len(self.candidates) - len(self.nodes)
        arr = np.ones((len(self.captured_msgs), len(self.candidates))) / N
        predictions = pd.DataFrame(
            arr, columns=self.candidates, index=list(self.captured_msgs)
        )
        for node in self.nodes:
            predictions[node] *= 0
        return predictions

    def predict_msg_source(self, estimator: str = "first_reach") -> pd.DataFrame:
        """
        Predict source nodes for each message

        By default, the node from whom the adversary first heard the message is assigned 1.0 probability while every other node receives zero.

        Parameters
        ----------
        estimator : {'first_reach', 'first_sent', 'shortest_path', 'dummy'}, default 'first_reach'
            Strategy to assign probabilities to network nodes:
            * first_reach: the node from whom the adversary first heard the message is assigned 1.0 probability while every other node receives zero.
            * shortest_path: predicted node probability is proportional (inverse distance) to the shortest weighted path length
            * dummy: the probability is divided equally between non-adversary nodes.
        """
        if estimator in ["first_reach", "first_sent"]:
            _, _, received_from, predictions = self._find_first_contact(estimator)
            for mid, node in received_from.items():
                predictions.at[mid, node] = 1.0
            return predictions
        elif estimator == "shortest_path":
            return self._shortest_path_estimator()
        elif estimator == "dummy":
            return self._dummy_estimator()
        else:
            raise ValueError(
                "Choose 'estimator' from values ['first_reach', 'shortest_path', 'dummy']!"
            )
