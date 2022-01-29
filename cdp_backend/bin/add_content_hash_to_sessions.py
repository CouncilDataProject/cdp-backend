#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import traceback
from pathlib import Path

import fireo

from cdp_backend.database.models import Session, Transcript
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
            prog="add_content_hash_to_sessions",
            description="Add content hash to all existing session rows in the database.",
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

    # Session set
    unfixed_sessions = set([s.id for s in sessions])
    
    # Fetch all transcripts 
    transcripts = Transcript.collection.fetch()
    
    # Unfortunately firestore doesn't have built in distinct querying
    # Create list where each transcripts is for a unique session
    transcripts_unique_sessions = list({t.session_ref: t for t in transcripts}.values())

    # Fetch all sessions
    for transcript in transcripts_unique_sessions:
        # Get file db ref 
        _file = transcript.file_ref.get()

        # Extract hash 
        session_content_hash = _file.name.split('-')[0]

         
        # Update session
        session = transcript.session_ref.get()
        # Need to set event reference since autoload is disabled
        session.event_ref = session.event_ref.get()


        session.session_content_hash = session_content_hash

        session.set_validator_kwargs(
        kwargs={"google_credentials_file": str(google_creds_path)}
        )


        # Upsert existign session
        session.upsert()

        # Mark session as fixed
        if session.id in unfixed_sessions:
            unfixed_sessions.remove(session.id)



    if unfixed_sessions:
        log.error(f"The following sessions were not fixed with session content hash: {unfixed_sessions}")
        

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
