#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pulumi
import pulumi_gcp as gcp

from ..database import DATABASE_MODELS

###############################################################################


class CDPStack(pulumi.ComponentResource):
    def __init__(
        self,
        gcp_project_id: str,
        firestore_location: str = "us-west2",
        opts: pulumi.ResourceOptions = None,
    ):
        """
        Creates all required infrastructure and enables all required services for CDP
        backend stacks.

        Parameters
        ----------
        gcp_project_id: str
            The id of the gcp_project, the Pulumi stack, and any other required
            names for resources created during infrastructure creation will use this id
            as a prefix.
            I.E. `cdp-seattle` would create a Cloud Firestore instance called
            `cdp-seattle`, a GCP bucket called `cdp-seattle`, etc.

        firestore_location: str
            The location for the Cloud Firestore database and file storage servers
            to be hosted.
            List of locations: https://firebase.google.com/docs/firestore/locations
            Default: "us-west2"

        opts: pulumi.ResourceOptions
            Extra resource options to initialize the entire stack with.
            Default: None

        Notes
        -----
        When using this resource it is recommended to run set Pulumi parallel resource
        creation to five (5) max. GCP has limits on how many resources you can create
        in parallel.
        """
        super().__init__("CDPStack", gcp_project_id, None, opts)

        # Store parameters
        self.gcp_project_id = gcp_project_id
        self.firestore_location = firestore_location

        # Enable all required services
        self.firestore_service = gcp.projects.Service(
            f"{self.gcp_project_id}-firestore-service",
            disable_dependent_services=True,
            project=self.gcp_project_id,
            service="firestore.googleapis.com",
            opts=pulumi.ResourceOptions(parent=self),
        )
        self.speech_service = gcp.projects.Service(
            f"{self.gcp_project_id}-speech-service",
            disable_dependent_services=True,
            project=self.gcp_project_id,
            service="speech.googleapis.com",
            opts=pulumi.ResourceOptions(parent=self),
        )
        self.compute_service = gcp.projects.Service(
            f"{self.gcp_project_id}-compute-service",
            disable_dependent_services=True,
            project=self.gcp_project_id,
            service="compute.googleapis.com",
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Create the firestore application
        self.firestore_app = gcp.appengine.Application(
            f"{self.gcp_project_id}-firestore-app",
            project=self.gcp_project_id,
            location_id=self.firestore_location,
            database_type="CLOUD_FIRESTORE",
            opts=pulumi.ResourceOptions(parent=self.firestore_service),
        )

        # Create all firestore indexes
        for model_cls in DATABASE_MODELS:
            for idx_field_set in model_cls._INDEXES:

                # Add fields to field list
                idx_set_name_parts = []
                idx_set_fields = []
                for idx_field in idx_field_set.fields:
                    idx_set_name_parts += [idx_field.name, idx_field.order]
                    idx_set_fields.append(
                        {
                            "fieldPath": idx_field.name,
                            "order": idx_field.order,
                        }
                    )

                # Finish creating the index set name
                idx_set_name = "_".join(idx_set_name_parts)
                fq_idx_set_name = f"{model_cls.collection_name}-{idx_set_name}"

                gcp.firestore.Index(
                    fq_idx_set_name,
                    collection=model_cls.collection_name,
                    fields=idx_set_fields,
                    project=self.gcp_project_id,
                    opts=pulumi.ResourceOptions(parent=self.firestore_app),
                )

        super().register_outputs({})
