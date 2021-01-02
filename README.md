# cdp-backend

[![Build Status](https://github.com/CouncilDataProject/cdp-backend/workflows/Build/badge.svg)](https://github.com/CouncilDataProject/cdp-backend/actions)
[![Documentation](https://github.com/CouncilDataProject/cdp-backend/workflows/Documentation/badge.svg)](https://CouncilDataProject.github.io/cdp-backend)
[![Code Coverage](https://codecov.io/gh/CouncilDataProject/cdp-backend/branch/main/graph/badge.svg)](https://codecov.io/gh/CouncilDataProject/cdp-backend)

Data storage utilities and processing pipelines to run on CDP server deployments.

---

## About

Council Data Project is an open-source project dedicated to providing journalists,
activists, researchers, and all members of each community we serve with the tools they
need to stay informed and hold their Council Members accountable.

By combining and simplifying sources of information on Council meetings and actions,
CDP ensures that everyone is empowered to participate in local government.

Each municipality that CDP supports (_a CDP instance_) has open source maintainers
which write code to gather municipality meeting information and compile them into a
single resource to then be processed, stored, and made accessible by our general CDP
tooling.

## Contributing

-   [cdp-backend](https://github.com/CouncilDataProject/cdp-backend): This repo. Contains
    all the database models, data processing pipelines, and infrastructure-as-code for CDP
    deployments. Contributions here will be available to all CDP instances. Entirely
    written in Python.
-   [cdp-frontend](https://github.com/CouncilDataProject/cdp-frontend): Contains all of
    the components used by the web apps to be hosted on GitHub Pages. Contributions here
    will be available to all CDP instances. Entirely written in
    TypeScript and React.
-   [cookiecutter-cdp-deployment](https://github.com/CouncilDataProject/cookiecutter-cdp-deployment):
    A template to be used by the Python `cookiecutter` package to create an entirely new
    deployment repository. This is where `cdp-backend` and `cdp-frontend` are imported and
    used. If you would like to create a new deployment under the
    `councildataproject.github.io` domain please
    [log a GitHub issue](https://github.com/CouncilDataProject/councildataproject.github.io/issues).
    If you want to utilize a different domain, simply use the template like any other
    `cookiecutter`.
-   [councildataproject.github.io](https://github.com/CouncilDataProject/councildataproject.github.io):
    Our landing page! Contributions here should largely be text changes and admin updates.

## Installation

**Stable Release:** `pip install cdp-backend`<br>
**Development Head:** `pip install git+https://github.com/CouncilDataProject/cdp-backend.git`<br>

**Dev Installation:**
For devs, please ensure that you have [dot / graphviz](https://graphviz.org/download/)
installed before working with tests and auto-documentation generation.

## Infrastructure

Please see [example-infrastructure](./example-infrastructure) for defaults on dev
deployments.

## Documentation

For full package documentation please visit [CouncilDataProject.github.io/cdp-backend](https://CouncilDataProject.github.io/cdp-backend).

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for information related to development of this
repository.

**Free software: MIT license**
