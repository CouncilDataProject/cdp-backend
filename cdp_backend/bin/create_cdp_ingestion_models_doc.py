#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import traceback
from dataclasses import asdict
from pathlib import Path
from pprint import pformat
from typing import Any, Dict, List, Union

from jinja2 import Template

from cdp_backend.pipeline.ingestion_models import (
    EXAMPLE_FILLED_EVENT,
    EXAMPLE_MINIMAL_EVENT,
)

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
            prog="create_cdp_ingestion_models_doc",
            description="Create the ingestion models documentation file for CDP.",
        )
        p.add_argument(
            "-t",
            "--template-file",
            type=Path,
            default=(
                Path(__file__).parent.parent.parent
                / "docs"
                / "ingestion_models.template"
            ),
            dest="template_file",
            help="Path to the template markdown file.",
        )
        p.add_argument(
            "-o",
            "--output-file",
            type=Path,
            default=Path("ingestion_models.md"),
            dest="output_file",
            help="Path to where to store the created documentation file.",
        )
        p.parse_args(namespace=self)


###############################################################################


def _filter_none_values(d: Union[Dict, Any]) -> Union[Dict, Any]:
    if isinstance(d, Dict):
        return {k: _filter_none_values(v) for k, v in d.items() if v is not None}
    elif isinstance(d, List):
        return [_filter_none_values(v) for v in d if v is not None]
    else:
        return d


def _construct_ingestion_model_doc(template_file: Path, output_file: Path) -> Path:
    minimal_event_data = _filter_none_values(asdict(EXAMPLE_MINIMAL_EVENT))
    filled_event_data = _filter_none_values(asdict(EXAMPLE_FILLED_EVENT))

    # Read in the template
    with open(template_file, "r") as open_resource:
        template = Template(open_resource.read())

    # Fill the template with values
    filled = template.render(
        minimal_event_data=pformat(minimal_event_data, sort_dicts=False),
        filled_event_data=pformat(filled_event_data, sort_dicts=False),
    )

    # Store filled template
    with open(output_file, "w", encoding="utf-8") as open_resource:
        open_resource.write(filled)

    return output_file


def main() -> None:
    try:
        args = Args()
        _construct_ingestion_model_doc(
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
