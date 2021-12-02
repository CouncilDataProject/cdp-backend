# cdp-backend

[![Build Status](https://github.com/CouncilDataProject/cdp-backend/workflows/Build/badge.svg)](https://github.com/CouncilDataProject/cdp-backend/actions)
[![Documentation](https://github.com/CouncilDataProject/cdp-backend/workflows/Documentation/badge.svg)](https://CouncilDataProject.github.io/cdp-backend)
[![Code Coverage](https://codecov.io/gh/CouncilDataProject/cdp-backend/branch/main/graph/badge.svg)](https://codecov.io/gh/CouncilDataProject/cdp-backend)
[![DOI](https://joss.theoj.org/papers/10.21105/joss.03904/status.svg)](https://doi.org/10.21105/joss.03904)

Data storage utilities and processing pipelines to run on Council Data Project server deployments.

---

## Council Data Project

Council Data Project is an open-source project dedicated to providing journalists, activists, researchers, and all members of each community we serve with the tools they need to stay informed and hold their Council Members accountable.

For more information about Council Data Project, please visit [our website](https://councildataproject.org/).

## About

`cdp-backend` is used to maintain the database models, infrastructure stack, and all pipelines for CDP Instance web applications.

The central goal is to create a single library that manages the whole backend of any CDP Instance.

## Installation

**Stable Release (with just data access dependencies):** `pip install cdp-backend`<br/>
**Stable Release (with full pipeline dependencies):** `pip install cdp-backend[pipeline]`

**Development Head:** `pip install git+https://github.com/CouncilDataProject/cdp-backend.git`

**Dev Installation:** For devs, please ensure that you have [dot / graphviz](https://graphviz.org/download/) installed before working with tests and auto-documentation generation.

## Infrastructure

Please see [dev-infrastructure](./dev-infrastructure) for defaults on dev deployments.

## Documentation

For full package documentation please visit [councildataproject.org/cdp-backend](https://councildataproject.org/cdp-backend).

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for information related to development of this repository.

## Citation

If you have found CDP software, data, or ideas useful in your own work, please consider citing us:

Brown et al., (2021). Council Data Project: Software for Municipal Data Collection, Analysis, and Publication. Journal of Open Source Software, 6(68), 3904, https://doi.org/10.21105/joss.03904

```bibtex
@article{Brown2021,
  doi = {10.21105/joss.03904},
  url = {https://doi.org/10.21105/joss.03904},
  year = {2021},
  publisher = {The Open Journal},
  volume = {6},
  number = {68},
  pages = {3904},
  author = {Jackson Maxfield Brown and To Huynh and Isaac Na and Brian Ledbetter and Hawk Ticehurst and Sarah Liu and Emily Gilles and Katlyn M. f. Greene and Sung Cho and Shak Ragoler and Nicholas Weber},
  title = {{Council Data Project: Software for Municipal Data Collection, Analysis, and Publication}},
  journal = {Journal of Open Source Software}
}
```

## License

[MIT](./LICENSE)
