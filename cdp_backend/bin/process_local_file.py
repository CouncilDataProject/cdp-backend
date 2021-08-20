#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import traceback
from pathlib import Path

from cdp_backend.file_store.functions import upload_file
from cdp_backend.pipeline import event_gather_pipeline as pipeline
from cdp_backend.pipeline.ingestion_models import EventIngestionModel
from cdp_backend.pipeline.pipeline_config import EventGatherPipelineConfig

###############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)4s: %(module)s:%(lineno)4s %(asctime)s] %(message)s",
)
log = logging.getLogger(__name__)

###############################################################################


class Args(argparse.Namespace):
    def __init__(self) -> None:
        self.__parse()

    def __parse(self) -> None:
        p = argparse.ArgumentParser(
            prog="process_local_file",
            description="Process local video file into the event pipeline.",
        )
        p.add_argument(
            "--event_details_file",
            type=Path,
            help="Path to the JSON file with event details.",
        )
        p.add_argument(
            "--event_gather_config_file",
            type=Path,
            help="Path to the JSON file with event gather pipeline configuration.",
        )
        p.parse_args(namespace=self)


def main() -> None:
    try:
        args = Args()

        # Read pipeline config
        with open(args.event_gather_config_file, "r") as open_resource:
            config = EventGatherPipelineConfig.from_json(  # type: ignore
                open_resource.read()
            )

        # Convert event details file to EventIngestionModel
        with open(args.event_details_file, "r") as open_resource:
            ingestion_model = EventIngestionModel.from_json(  # type: ignore
                open_resource.read()
            )

            for session in ingestion_model.sessions:
                # Upload video file to file store
                video_uri = upload_file(
                    credentials_file=config.google_credentials_file,
                    bucket=config.validated_gcs_bucket_name,
                    filepath=session.video_uri,
                )

                # Replace video_uri of session
                session.video_uri = video_uri

        # Create event gather pipeline flow
        flow = pipeline.create_event_gather_flow(
            config=config, prefetched_events=[ingestion_model], from_local=True
        )

        # Run flow
        flow.run()

    except Exception as e:
        log.error("=============================================")
        log.error("\n\n" + traceback.format_exc())
        log.error("=============================================")
        log.error("\n\n" + str(e) + "\n")
        log.error("=============================================")
        sys.exit(1)


###############################################################################

if __name__ == "__main__":
    main()
