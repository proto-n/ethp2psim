# ethsim

[![CI for Ubuntu with Codecov sync](https://github.com/ferencberes/ethsim/actions/workflows/ubuntu.yml/badge.svg)](https://github.com/ferencberes/ethsim/actions/workflows/ubuntu.yml)
[![CI for MacOS without Codecov sync](https://github.com/ferencberes/ethsim/actions/workflows/macos.yml/badge.svg)](https://github.com/ferencberes/ethsim/actions/workflows/macos.yml)
[![codecov](https://codecov.io/gh/ferencberes/ethsim/branch/main/graph/badge.svg?token=6871LSZKSK)](https://codecov.io/gh/ferencberes/ethsim)

## Installation

Create your conda environment:
```bash
conda create -n ethsim python=3.8
```

Activate your environment, then install Python dependencies:
```bash
conda activate ethsim
pip install -r requirements.txt
```

## Tests

Run the following command at the root folder before pushing new commits to the repository!
Please, always write tests for new code sections to maintain high code coverage!
```bash
pytest --cov
```

## Quickstart

Here, we show an example on how to run a simulation with the Dandelion protocol in case of the most basic adversarial setting (predict a node to be the message source if adversarial nodes first heard of this message from the given node).


### i.) Initialize simulation components:
```python
import sys
sys.path.insert(0, "python")
from network import Network, EdgeWeightGenerator, NodeWeightGenerator
from protocols import DandelionProtocol
from adversary import Adversary
```

First, initialize a re-usable **generators for edge and node weights**, e.g. 
   * channel latency is sampled uniformly at random
   * nodes have weights proportional with their staked Ether amount
   
```python
ew_gen = EdgeWeightGenerator("normal")
nw_gen = NodeWeightGenerator("stake")
```

Initialize a random 4 regular graph with 20 nodes to be **the peer-to-peer (P2P) network**:
```python
net = Network(20, 4, edge_weight_gen=ew_gen)
```

Initialize the Dandelion **protocol** and draw the related line (anonymity) graph:
```python
import matplotlib.pyplot as plt

dp = DandelionProtocol(net, 0.1, broadcast_mode="sqrt")
nx.draw(dp.anonymity_graph, node_size=20)
```

With the `broadcast_mode="sqrt"` the message is only sent to a randomly selected square root of neighbors in the spreading phase to speed up the protocol.

Initilaize a passive **adversary** that controls random 10% of all nodes:
```python
adv = Adversary(net, 0.1, active=False)
```
You could also use an active adversary (by setting `active=True`) that refuse to propagate received messages.

### ii.) Run simulation

**Simulate** 10 random messages for the same P2P network and adversary with Dandelion protocol:
```python
from simulator import Simulation
sim = Simulator(dp, adv, 10, verbose=False)
sim.run(coverage_threshold=0.9)
```
**NOTE: By default every message is only simulated until it reaches 90% of all nodes**

We also highlight that source nodes for messages are randomly sampled with respect to their staked Ether amount due to the formerly prepared `NodeWeightGenerator`.

### iii.) Evaluate simulation

**Evaluate** the performance of the adversary for the given simulation. Here, you can choose different estimators for adversary performance evaluation (e.g.: "first_sent", "first_reach", "dummy"):
```python
from simulator import Evaluator
evaluator = Evaluator(sim, estimator="first_reach")
print(evaluator.get_report())
```

For a more complex experimental setting see the related [notebook](Experimental.ipynb) that takes approximately 30 minutes to execute.

## Documentation

Install every dependency that is needed to generate code documentation.
The commands below need to be executed only one:

```bash
cd docs
pip install -r requirements.txt
```

Then, you can update code documentation locally with the following command:
```bash
cd docs
make html
```

A generated documentation resides in the `docs/build/html/` folder.