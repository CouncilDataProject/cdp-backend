#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import traceback
from pathlib import Path

from fireo.fields import ReferenceField
from graphviz import Digraph

from cdp_backend.database import DATABASE_MODELS

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
            prog="create_cdp_database_uml", description="Create a CDP UML dot file."
        )
        p.add_argument(
            "-o",
            "--output-file",
            type=Path,
            default=Path("cdp_database_diagram.dot"),
            dest="output_file",
            help="Path to where to store the created dot file.",
        )
        p.parse_args(namespace=self)


###############################################################################


def _construct_dot_file(output_file: str) -> str:
    dot = Digraph(
        comment="CDP Database Diagram",
        graph_attr={
            "rankdir": "LR",
            "bgcolor": "transparent",
            "splines": "compound",
        },
        node_attr={
            "shape": "record",
            "style": "filled",
            "fillcolor": "white",
        },
        edge_attr={
            "arrowhead": "vee",
        },
    )

    # First pass: create nodes for each model
    for model_cls in DATABASE_MODELS:
        # Attach fields for each model by using the Example
        fields = []
        m = model_cls.Example()

        # Construct label
        for field_name, field in m._meta.field_list.items():
            # Check if field is required and if so prepend an asterisk
            if field.field_attribute.required:
                required_status = " *"
            else:
                required_status = ""

            # Construct basic field text
            # I.E. "* name       TextField"
            field_text = (
                f"{field_name}{required_status}\\l " f" {field.__class__.__name__}\\r"
            )

            # Check if field is a ReferenceField
            # and append a dot quick ref to the field text
            # <blah> is a dot quick ref
            if isinstance(field, ReferenceField):
                field_text = f"<{field_name}> {field_text}"

            # Finally append to the rest of the fields
            fields.append(field_text)

        # All fields are complete, join them with `|` characters for dot format
        fields_as_text = "|".join(fields)

        # Create the entire node label with the header then field rows
        node_label = f"{model_cls.__name__} | {fields_as_text}"

        # Attach as a complete node
        dot.node(model_cls.__name__, node_label)

    # Second pass: Create DAG
    for model_cls in DATABASE_MODELS:
        # Attach fields for each model by using the Example
        m = model_cls.Example()

        # Construct DAG points
        for field_name, field in m._meta.field_list.items():
            if isinstance(field, ReferenceField):
                referenced_model = field.model_ref.__name__
                dot.edge(f"{model_cls.__name__}:{field_name}", referenced_model)

    # Save file
    dot.save(str(output_file))

    return output_file


def main() -> None:
    try:
        args = Args()
        _construct_dot_file(output_file=args.output_file)
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
