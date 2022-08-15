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

```bash
cd cdp-backend/dev-infrastructure
just login
just init project={project-name}
just gen-key project={project-name}
just build
```

After generating the key, name your `key` file in `cdp-backend/.keys` to `cdp-dev.json`. In case you have many keys, note that by default, the random and minimal event pipelines use the key named `cdp-dev.json`.

## Infrastructure Management Commands

All of these commands should be run from within the `cdp-backend/dev-infrastructure` directory.

-   To log in to GCloud and Pulumi:

    ```bash
    just login
    ```

-   To create a new service account JSON key:

    ```bash
    just gen-key project={project-name}
    ```

-   To create a new dev infrastructure:

    ```bash
    just init project={project-name}
    ```

    And follow the link logged to link a billing account to the created project.

    **Note:** This will create a new GCP project.

-   To set up infrastructure:

    ```bash
    just build
    ```

    **Note:** You should run `just gen-key` prior to build and ensure you have
    `GOOGLE_CREDENTIALS` set in your environment variables using:

    ```bash
    export GOOGLE_CREDENTIALS=$(cat ../.keys/{project-name}-sa-dev.json)
    ```

    and replacing `{project-name}` with your project name.

    or if you have already renamed your key:

    ```bash
    export GOOGLE_CREDENTIALS=$(cat ../.keys/cdp-dev.json)
    ```

-   To clean and remove all database documents and file store objects:

    ```bash
    just clean key={path-to-key}
    ```

    **Note:** Cleaning infrastructure is best practice when comparing pipeline
    outputs and database models aren't changing (specifically database indices).

-   To reset infrastructure but reuse the same Google project:

    ```bash
    just reset
    ```

    **Note:** Reseting infrastructure is likely required when iterating on
    database models (specifically database indices). Cleaning infrastructure
    should always be attempted first before reset or destroy as `just clean`
    will not use any extra Google Cloud (or Firebase) projects and applications.

-   To delete all Pulumi and GCloud resources entirely:

    ```bash
    just destroy project={project-name}
    ```

    **Note:** This will delete the GCP project.

Try to use the same project and infrastructure as much as possible, there are
limits for how many projects and Firestore applications a single user can have.

### All Commands

-   See Justfile commands with `just`.
    Or simply open the Justfile. All the commands are decently easy to follow.
-   See Pulumi [CLI documentation](https://www.pulumi.com/docs/reference/cli/)
    for all Pulumi commands.

## Non-Default Parameters

If you want to edit the default behavior of the `__main__.py` file and change the
parameters, please see the documentation for the
[CDPStack object](https://councildataproject.github.io/cdp-backend/cdp_backend.infrastructure.html#module-cdp_backend.infrastructure.cdp_stack)

## Running Pipelines Against Dev Infra

Once you have a dev infrastructure set up and a key downloaded (`just gen-key`)
you can run pipelines and store data in the infrastructure by moving up to the
base directory of this repository and running the following from `cdp-backend/`:

-   To run a semi-random (large permutation) event pipeline:

    ```bash
    just run-rand-event-pipeline
    ```

-   To run a minimal (by definition) event pipeline:

    ```bash
    just run-min-event-pipeline
    ```
