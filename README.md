# ethsim

![build](https://github.com/ferencberes/ethsim/actions/workflows/main.yml/badge.svg)
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
```bash
pytest --cov
```