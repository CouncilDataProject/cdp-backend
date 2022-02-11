#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

import pulumi
import pulumi_gcp as gcp
from pulumi_google_native.firestore import v1 as firestore

from ..database import DATABASE_MODELS
from ..version import __version__

###############################################################################


class GoverningBody:
    city_council = "city council"
    county_council = "county council"
    school_board = "school board"
    other = "other"


class CDPStack(pulumi.ComponentResource):
    def __init__(
        self,
        gcp_project_id: str,
        municipality_name: str = "dev_municipality",
        hosting_github_url: str = "no_github_host",
        hosting_web_app_address: str = "no_web_app_address",
        firestore_location: str = "us-west2",
        governing_body: str = GoverningBody.other,
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

        municipality_name: str
            The name of the municipality this instance will be for.
            I.E. "Seattle", "King County", etc.

        hosting_github_url: str
            The GitHub repo this instance configuration details will be stored.
            I.E. https://github.com/councildataproject/seattle-staging

        hosting_web_app_address: str
            The web address for this instances web portal.
            I.E. https://councildataproject.org/seattle-staging

        firestore_location: str
            The location for the Cloud Firestore database and file storage servers
            to be hosted.
            List of locations: https://firebase.google.com/docs/firestore/locations
            Default: "us-west2"

        governing_body: str
            What governing body this instance will archive.
            Default: GoverningBody.other

        opts: pulumi.ResourceOptions
            Extra resource options to initialize the entire stack with.
            Default: None

        Notes
        -----
        When using this resource it is recommended to run set Pulumi parallel resource
        creation to five (5) max. GCP has limits on how many resources you can create
        in parallel.

        The default values for many parameters are set to fake values as this object
        should primarily be used with the cookiecutter / automated scripts. The default
        values in this case are set because when using this object outside of
        the cookiecutter it is likely for dev infrastructures.
        """
        super().__init__("CDPStack", gcp_project_id, None, opts)

        # Store parameters
        self.gcp_project_id = gcp_project_id
        self.firestore_location = firestore_location

        # Enable all required services
        self.cloudresourcemanager = gcp.projects.Service(
            f"{self.gcp_project_id}-cloudresourcemanager-service",
            disable_dependent_services=True,
            project=self.gcp_project_id,
            service="cloudresourcemanager.googleapis.com",
            opts=pulumi.ResourceOptions(parent=self),
        )
        self.speech_service = gcp.projects.Service(
            f"{self.gcp_project_id}-speech-service",
            disable_dependent_services=True,
            project=self.gcp_project_id,
            service="speech.googleapis.com",
            opts=pulumi.ResourceOptions(
                parent=self, depends_on=[self.cloudresourcemanager]
            ),
        )
        self.firebase_service = gcp.projects.Service(
            f"{self.gcp_project_id}-firebase-service",
            disable_dependent_services=True,
            project=self.gcp_project_id,
            service="firebase.googleapis.com",
            opts=pulumi.ResourceOptions(
                parent=self, depends_on=[self.cloudresourcemanager]
            ),
        )
        self.app_engine_service = gcp.projects.Service(
            f"{self.gcp_project_id}-app-engine-service",
            disable_dependent_services=True,
            project=self.gcp_project_id,
            service="appengine.googleapis.com",
            opts=pulumi.ResourceOptions(
                parent=self, depends_on=[self.cloudresourcemanager]
            ),
        )
        self.firestore_service = gcp.projects.Service(
            f"{self.gcp_project_id}-firestore-service",
            disable_dependent_services=True,
            project=self.gcp_project_id,
            service="firestore.googleapis.com",
            opts=pulumi.ResourceOptions(
                parent=self, depends_on=[self.cloudresourcemanager]
            ),
        )
        self.firebase_rules_service = gcp.projects.Service(
            f"{self.gcp_project_id}-firebase-rules-service",
            disable_dependent_services=True,
            project=self.gcp_project_id,
            service="firebaserules.googleapis.com",
            opts=pulumi.ResourceOptions(
                parent=self, depends_on=[self.cloudresourcemanager]
            ),
        )

        # Create the firestore application
        self.firestore_app = gcp.appengine.Application(
            f"{self.gcp_project_id}-firestore-app",
            project=self.gcp_project_id,
            location_id=self.firestore_location,
            database_type="CLOUD_FIRESTORE",
            opts=pulumi.ResourceOptions(
                parent=self,
                depends_on=[
                    self.firebase_service,
                    self.app_engine_service,
                    self.firestore_service,
                    self.firebase_rules_service,
                ],
            ),
        )

        # Init firebase project
        self.firebase_init = gcp.firebase.Project(
            resource_name=f"{self.gcp_project_id}-firebase-init",
            project=self.gcp_project_id,
            opts=pulumi.ResourceOptions(parent=self, depends_on=[self.firestore_app]),
        )

        # Connect app engine (firestore) + bucket
        self.firebase_project = gcp.firebase.ProjectLocation(
            resource_name=f"{self.gcp_project_id}-firebase-project",
            project=self.gcp_project_id,
            location_id=self.firestore_location,
            opts=pulumi.ResourceOptions(parent=self.firebase_init),
        )

        # Set full public read on bucket
        self.storage_public_read = gcp.storage.DefaultObjectAccessControl(
            f"{self.gcp_project_id}-storage-acl-public-viewer",
            bucket=self.firestore_app.default_bucket,
            entity="allUsers",
            role="READER",
            opts=pulumi.ResourceOptions(parent=self.firestore_app),
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
                        firestore.GoogleFirestoreAdminV1IndexFieldArgs(
                            field_path=idx_field.name,
                            order=idx_field.order,
                        )
                    )

                # Finish creating the index set name
                idx_set_name = "_".join(idx_set_name_parts)
                fq_idx_set_name = f"{model_cls.collection_name}-{idx_set_name}"
                firestore.Index(
                    fq_idx_set_name,
                    project=self.gcp_project_id,
                    database_id="(default)",
                    collection_group_id=model_cls.collection_name,
                    fields=idx_set_fields,
                    query_scope="COLLECTION",
                    opts=pulumi.ResourceOptions(parent=self.firestore_app),
                )

        # Add metadata document
        gcp.firestore.Document(
            f"{self.gcp_project_id}-metadata-doc",
            collection="metadata",
            document_id="configuration",
            fields=json.dumps(
                {
                    "infrastructure_version": {"stringValue": __version__},
                    "municipality_name": {"stringValue": municipality_name},
                    "hosting_github_url": {"stringValue": hosting_github_url},
                    "hosting_web_app_address": {"stringValue": hosting_web_app_address},
                    "firestore_location": {"stringValue": firestore_location},
                    "governing_body": {"stringValue": governing_body},
                }
            ),
            project=self.gcp_project_id,
            opts=pulumi.ResourceOptions(parent=self.firestore_app),
        )

        super().register_outputs({})
