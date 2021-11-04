#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import logging
import sys
import traceback
from pathlib import Path

import fireo
from gcsfs import GCSFileSystem

from cdp_backend.database import models as db_models

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
            prog="remove_event",
            description=(
                "Remove event and related items from CDP database and file store."
            ),
        )
        p.add_argument(
            "event_id",
            type=str,
            help="Event ID in the database to remove.",
        )
        p.add_argument(
            "google_credentials_file",
            type=Path,
            help="Path to Google service account JSON key.",
        )
        p.parse_args(namespace=self)


def main() -> None:
    try:
        args = Args()

        # Connect to database
        fireo.connection(from_file=args.google_credentials_file)

        # Connect to filestore
        fs = GCSFileSystem(token=str(args.google_credentials_file))

        # Get event details
        event = db_models.Event.collection.get(
            f"{db_models.Event.collection_name}/{args.event_id}"
        )
        body = event.body_ref.get()

        # Get all sessions
        sessions = list(
            db_models.Session.collection.filter(
                "event_ref",
                "==",
                event.key,
            ).fetch()
        )

        # Delete all transcripts
        for session in sessions:
            transcripts = list(
                db_models.Transcript.collection.filter(
                    "session_ref",
                    "==",
                    session.key,
                ).fetch()
            )

            # Delete all files
            for transcript in transcripts:
                transcript_file = transcript.file_ref.get()
                print(fs.ls(transcript_file.uri))

                # fs.rm(transcript_file.uri)
                # db_models.File.collection.delete(transcript_file.key)
                # db_models.Transcript.collection.delete(transcript.key)

        # Get all votes that occurred in meeting
        votes = list(
            db_models.Vote.collection.filter(
                "event_ref",
                "==",
                event.key,
            ).fetch()
        )

        # Delete all metadata from votes if metadata is only tied to this meeting
        # for vote in votes:

        # Delete grams created from meeting

        # Delete event
        # db_models.Event.collection.delete(event.key)

        # Delete body if no longer tied to meeting
        events_for_body = list(
            db_models.Event.collection.filter(
                "body_ref",
                "==",
                body.key,
            ).fetch()
        )
        if len(events_for_body) == 0:
            # db_models.Body.collection.delete(body.key)
            pass

        print(event)
        print(sessions)

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
