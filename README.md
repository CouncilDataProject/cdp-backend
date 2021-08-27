# cdp-backend

[![Build Status](https://github.com/CouncilDataProject/cdp-backend/workflows/Build/badge.svg)](https://github.com/CouncilDataProject/cdp-backend/actions)
[![Documentation](https://github.com/CouncilDataProject/cdp-backend/workflows/Documentation/badge.svg)](https://CouncilDataProject.github.io/cdp-backend)
[![Code Coverage](https://codecov.io/gh/CouncilDataProject/cdp-backend/branch/main/graph/badge.svg)](https://codecov.io/gh/CouncilDataProject/cdp-backend)

Data storage utilities and processing pipelines to run on Council Data Project server deployments.

---

## Council Data Project

Council Data Project is an open-source project dedicated to providing journalists, activists, researchers, and all members of each community we serve with the tools they need to stay informed and hold their Council Members accountable.

For more information about Council Data Project, please visit [our website](https://councildataproject.org/).

## About

`cdp-backend` is used to maintain the database models, infrastructure stack, and all pipelines for CDP Instance web applications.

The central goal is to create a single library that manages the whole backend of any CDP Instance.

## Installation

**Stable Release (with just data access dependencies):** `pip install cdp-backend`
**Stable Release (with full pipeline dependencies):** `pip install cdp-backend[pipeline]`

**Development Head:** `pip install git+https://github.com/CouncilDataProject/cdp-backend.git`

**Dev Installation:** For devs, please ensure that you have [dot / graphviz](https://graphviz.org/download/) installed before working with tests and auto-documentation generation.

## Infrastructure

Please see [dev-infrastructure](./dev-infrastructure) for defaults on dev deployments.

## Documentation

For full package documentation please visit [councildataproject.org/cdp-backend](https://councildataproject.org/cdp-backend).

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for information related to development of this repository.

## License

[MIT](./LICENSE)
