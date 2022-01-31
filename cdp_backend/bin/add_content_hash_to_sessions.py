#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import traceback
from pathlib import Path

import fireo

from cdp_backend.database.models import Session, Transcript

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
            prog="add_content_hash_to_sessions",
            description=(
                "Add content hash to all existing session rows in the database."
            ),
        )
        p.add_argument(
            "--google_credentials_file",
            type=Path,
            help="Path to Google service account JSON key.",
        )
        p.parse_args(namespace=self)


###############################################################################


def add_content_hash_to_sessions(google_creds_path: Path) -> None:
    # Connect to database
    fireo.connection(from_file=google_creds_path)

    # Fetch all sessions
    sessions = Session.collection.fetch()

    # Sessions without a content hash
    unfixed_sessions = set([s.id for s in sessions if not s.session_content_hash])

    # Fetch all transcripts
    transcripts = Transcript.collection.fetch()

    # Unfortunately firestore doesn't have built in distinct querying
    # Create list where each transcripts is for a unique session
    transcripts_unique_sessions = list({t.session_ref: t for t in transcripts}.values())

    # Fetch all sessions
    for transcript in transcripts_unique_sessions:
        # Get file db ref
        _file = transcript.file_ref.get()

        # Get session
        session = transcript.session_ref.get()

        # If no session_content_hash found
        if not session.session_content_hash:
            # Extract hash  from file
            session_content_hash = _file.name.split("-")[0]

            # Need to set event reference since autoload is disabled,
            # and FireO throws an error if the model has a ReferenceDocLoader
            # on a property during any db write action
            session.event_ref = session.event_ref.get()

            # Give GCSFilSystem permissions to read GCS resources
            session.set_validator_kwargs(
                kwargs={"google_credentials_file": str(google_creds_path)}
            )

            # Add content hash to session db model
            session.session_content_hash = session_content_hash

            # Upsert existing session
            session.upsert()

            log.info(f"Updated session {session.id} with content hash")

        # Mark session as fixed
        if session.id in unfixed_sessions:
            unfixed_sessions.remove(session.id)

    # Log any sessions that still don't have a content hash
    # Could happen if there are db inconsistencies
    # (like a session is orphaned w/o a transcript)
    if unfixed_sessions:
        log.error(
            "The following sessions were not fixed with a "
            f"content hash: {unfixed_sessions}"
        )


def main() -> None:
    try:
        args = Args()
        add_content_hash_to_sessions(
            google_creds_path=args.google_credentials_file,
        )
    except Exception as e:
        log.error("=============================================")
        log.error("\n\n" + traceback.format_exc())
        log.error("=============================================")
        log.error("\n\n" + str(e) + "\n")
        log.error("=============================================")
        sys.exit(1)
