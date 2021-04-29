# Dev CDP Infrastructure

Full infrastructure setup for whole system / integration level testing.

---

## Initial Comments

This is primarily used for developer stack creation and management.
We have an example stack, infrastructure, pipeline, and web app available for
demonstration and example data usage in our
[example repo](https://github.com/CouncilDataProject/example).

If you are just trying to process example CDP data (or for front-end: visualize example
CDP data) and not _upload_ data, it is recommended to simply point your requests at the
example stack.

For in-depth details on infrastructure terminology and uses refer to the documentation
found in our
[cookiecutter-cdp-deployment repository](https://github.com/CouncilDataProject/cookiecutter-cdp-deployment).

---

## Dependencies

Deploying the CDP infrastructure requires having `cdp-backend` installed.

```bash
pip install -e ../[dev]
```

For more detailed information please see the
[project installation details](https://github.com/CouncilDataProject/cdp-backend#installation).

## Account Setup

1.  Create (or sign in to) a Google Cloud Platform (GCP) account.
    ([Google Cloud Console Home](https://console.cloud.google.com/))
2.  Create (or re-use) a [billing account](https://console.cloud.google.com/billing)
    and attach it to your GCP account.
3.  Create (or sign in to) a
    [Pulumi account](https://app.pulumi.com/signup).

## Environment Setup

The only environment setup needed to run this deployment is to make sure `pulumi` itself
and the `gcloud` SDK are both installed.

-   [pulumi](https://www.pulumi.com/docs/get-started/install/)
-   [gcloud](https://cloud.google.com/sdk/install)

_If this was the first time installing either of those packages, it is recommended to
restart your terminal after installation._

After `pulumi` and `gcloud` have both been installed and terminal restarted, run the
following commands to setup your local machine with credentials to both services.

**Note:** Pulumi only supports Python 3.7, when creating dev infrastructures you
need to run these scripts in a py37 environment.

```bash
make login
make init project={project-name}
make build
```

## Infrastrure Management Commands

-   To log in to GCloud and Pulumi:

    ```bash
    make login
    ```

-   To create a new service account JSON key:

    ```bash
    make gen-key project={project-name}
    ```

-   To create a new dev infrastructure:

    ```bash
    make init project={project-name}
    ```

    And follow the link logged to link a billing account to the created project.

    **Note:** This will create a new GCP project.

-   To set up infrastructure:

    ```bash
    make build
    ```

    **Note:** You should run `make gen-key` prior to build and ensure you have
    `GOOGLE_CREDENTIALS` set in your environment variables using:

    ```bash
    export GOOGLE_CREDENTIALS=$(cat ../.keys/{project-name}-sa-dev.json)
    ```

    and replacing `{project-name}` with your project name.

-   To clean and remove all database documents and file store objects:

    ```bash
    make clean key={path-to-key}
    ```

    **Note:** Cleaning infrastructure is best practice when comparing pipeline
    outputs and database models aren't changing (specifically database indices).

-   To reset infrastructure but reuse the same Google project:

    ```bash
    make reset
    ```

    **Note:** Reseting infrastructure is likely required when iterating on
    database models (specifically database indices). Cleaning infrastructure
    should always be attempted first before reset or destroy as `make clean`
    will not use any extra Google Cloud (or Firebase) projects and applications.

-   To delete all Pulumi and GCloud resources entirely:

    ```bash
    make destroy project={project-name}
    ```

    **Note:** This will delete the GCP project.

Try to use the same project and infrastructure as much as possible, there are
limits for how many projects and Firestore applications a single user can have.

### All Commands

-   See Makefile commands with `make help`.
    Or simply open the Makefile. All the commands are decently easy to follow.
-   See Pulumi [CLI documentation](https://www.pulumi.com/docs/reference/cli/)
    for all Pulumi commands.

## Non-Default Parameters

If you want to edit the default behavior of the `__main__.py` file and change the
parameters, please see the documentation for the
[CDPStack object](https://councildataproject.github.io/cdp-backend/cdp_backend.infrastructure.html#module-cdp_backend.infrastructure.cdp_stack)

## Running Pipelines Against Dev Infra

Once you have a dev infrastructure set up and a key downloaded (`make gen-key`)
you can run pipelines and store data in the infrastructure by moving up to the
base directory of this repository and running the following:

-   To run a semi-random (large permutation) event pipeline:

    ```bash
    make run-rand-event-pipeline key=.keys/{key-name.json}
    ```

-   To run a minimal (by definition) event pipeline:

    ```bash
    make run-min-event-pipeline key=.keys/{key-name.json}
    ```
