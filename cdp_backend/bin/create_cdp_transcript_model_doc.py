#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import logging
import sys
import traceback
from pathlib import Path

from jinja2 import Template

from cdp_backend.pipeline.transcript_model import EXAMPLE_TRANSCRIPT

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
            prog="create_cdp_transcript_model_doc",
            description="Create the transcript model documentation file for CDP.",
        )
        p.add_argument(
            "-t",
            "--template-file",
            type=Path,
            default=(
                Path(__file__).parent.parent.parent
                / "docs"
                / "transcript_model.template"
            ),
            dest="template_file",
            help="Path to the template markdown file.",
        )
        p.add_argument(
            "-o",
            "--output-file",
            type=Path,
            default=Path("transcript_model.md"),
            dest="output_file",
            help="Path to where to store the created documentation file.",
        )
        p.parse_args(namespace=self)


###############################################################################


def _construct_transcript_model_doc(template_file: Path, output_file: Path) -> Path:
    example_transcript_jsons = EXAMPLE_TRANSCRIPT.to_json()  # type: ignore
    example_transcript_dict = json.loads(example_transcript_jsons)
    example_transcript_str = json.dumps(example_transcript_dict, indent=4)

    # Read in the template
    with open(template_file, "r") as open_resource:
        template = Template(open_resource.read())

    # Fill the template with values
    filled = template.render(example_transcript=example_transcript_str)

    # Store filled template
    with open(output_file, "w", encoding="utf-8") as open_resource:
        open_resource.write(filled)

    return output_file


def main() -> None:
    try:
        args = Args()
        _construct_transcript_model_doc(
            template_file=args.template_file,
            output_file=args.output_file,
        )
    except Exception as e:
        log.error("=============================================")
        log.error("\n\n" + traceback.format_exc())
        log.error("=============================================")
        log.error("\n\n" + str(e) + "\n")
        log.error("=============================================")
        sys.exit(1)


###############################################################################
# Allow caller to directly run this module (usually in development scenarios)

if __name__ == "__main__":
    main()
