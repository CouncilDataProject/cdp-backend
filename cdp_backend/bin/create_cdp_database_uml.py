#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import inspect
import logging
from pathlib import Path
import sys
import traceback

from fireo.fields import ReferenceField
from graphviz import Digraph

from cdp_backend.database import models

###############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)4s: %(module)s:%(lineno)4s %(asctime)s] %(message)s",
)
log = logging.getLogger(__name__)

###############################################################################


class Args(argparse.Namespace):
    def __init__(self):
        self.__parse()

    def __parse(self):
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


def _construct_dot_file(args: Args):
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
            "arrowhead": "none",
        },
    )

    # First pass: create nodes for each model
    for model_name, cls in inspect.getmembers(models, inspect.isclass):
        if model_name not in ["Model", "datetime"]:
            # Attach fields for each model by using the Example
            fields = []
            m = cls.Example()

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
                    f"{field_name}{required_status}\\l "
                    f" {field.__class__.__name__}\\r"
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
            node_label = f"{model_name} | {fields_as_text}"

            # Attach as a complete node
            dot.node(model_name, node_label)

    # Second pass: Create DAG
    for model_name, cls in inspect.getmembers(models, inspect.isclass):
        if model_name not in ["Model", "datetime"]:
            # Attach fields for each model by using the Example
            fields = []
            m = cls.Example()

            # Construct DAG points
            for field_name, field in m._meta.field_list.items():
                if isinstance(field, ReferenceField):
                    referenced_model = field.model_ref.__name__
                    dot.edge(f"{model_name}:{field_name}", referenced_model)

    # Save file
    dot.save(str(args.output_file))


def main():
    try:
        args = Args()
        _construct_dot_file(args)
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
