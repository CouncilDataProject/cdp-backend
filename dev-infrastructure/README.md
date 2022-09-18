# Dev CDP Infrastructure

Full infrastructure setup for whole system / integration level testing.

---

## Initial Comments

This is primarily used for developer stack creation and management.
We have an example stack, infrastructure, pipeline, and web app available for
demonstration and example data usage in our
[Seattle staging repo](https://github.com/CouncilDataProject/seattle-staging).
The web page for the Seattle staging instance can be found
[here](https://councildataproject.org/seattle-staging).

If you are just trying to process example CDP data (or for front-end: visualize example
CDP data) and not _upload_ data, it is recommended to simply point your requests at the
example stack.

For in-depth details on infrastructure terminology and uses refer to the documentation
found in our
[cookiecutter-cdp-deployment repository](https://github.com/CouncilDataProject/cookiecutter-cdp-deployment).

---

## Dependencies

Deploying the CDP infrastructure requires having `cdp-backend` installed.

For more detailed information please see the
[project installation details](https://github.com/CouncilDataProject/cdp-backend#installation).

## Account Setup

1.  Create (or sign in to) a Google Cloud Platform (GCP) account.
    ([Google Cloud Console Home](https://console.cloud.google.com/))
2.  Create (or re-use) a [billing account](https://console.cloud.google.com/billing)
    and attach it to your GCP account.

## Environment Setup

The only environment setup needed to run this deployment is to make
sure the [`gcloud` SDK](https://cloud.google.com/sdk/install) is installed.

_If this was the first time installing either of those packages, it is recommended to
restart your terminal after installation._

After `gcloud` has both been installed and terminal restarted, run the
following commands to log in to gcloud: `just login`

## Create a New Project and Deploy the Infrastructure

```bash
get_cdp_infrastructure_stack {OPTIONAL: dir path to store to}
just init {project-name}
just setup-and-deploy {project-name} {OPTIONAL: region}
```

Example:

_Assuming user is within the `dev-infrastructure` dir._

```bash
get_cdp_infrastructure_stack .
just init cdp-eva-dev-001
just setup-and-deploy cdp-eva-dev-001
```

## Update an Existing Project

```bash
just deploy {project-name}
```

Example:

```bash
just deploy cdp-eva-dev-001
```

Enable video / audio clipping:

```bash
just deploy-clipping {key} {region}
```

Example:

```bash
just deploy-clipping /home/active/cdp/cdp-eva-dev-001.json us-central
```

### All Commands

-   See Justfile commands with `just` or open the Justfile.


### Changing the Stack

The actual infrastructure files live in the `cdp_backend/infrastructure` module.
To make changes to the infrastructure stack, change the files in that module and then
rerun `get-cdp-infrastructure-stack`.

Note: the database indexes are store in the `cdp_backend/database/models.py` module
with each collection model.

## Google Cloud Functions

Useful links for managing Cloud Functions:

* [Pre-installed System Packages](https://cloud.google.com/functions/docs/reference/system-packages)
* [Execution Environments](https://cloud.google.com/functions/docs/concepts/execution-environment)