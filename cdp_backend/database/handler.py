#!/usr/bin/env python
# -*- coding: utf-8 -*-

from copy import deepcopy
from typing import List

from .models import Model

###############################################################################


class ModelHandler:
    def __init__(self, database: "Database", entity: Model):
        # Store provided
        self.db = database
        self.entity = entity

        # Store entity key lookups
        # i.e. Body -> body
        # i.e. Body -> body_id
        self.collection_name = type(entity).__name__.lower()
        self.collection_id_key = f"{self.collection_name}_id"
        # self.collection_ref = self.db.collection(self.collection_name)
        self.entity_id = self.entity.__getattribute__(self.collection_id_key)

        # Pre-compute doc-ref
        if self.entity_id:
            self.doc_ref = self.db\
                .collection(self.collection_name)\
                .document(self.entity_id)
        else:
            self.doc_ref = None

    def get_full_details(self):
        # If the id was provided the doc ref will be filled
        # In this case we can simply pull the doc
        if self.doc_ref:
            self.doc = self.doc_ref.get()

            # Raise in case not found
            if not self.doc.exists():
                raise ValueError(
                    f"Provided {self.collection_id_key} ({self.entity_id}) "
                    f"was not found in database."
                )

        # Query for matching using pks
        else:
            query = deepcopy(self.collection_ref)
            # Apply conditions
            for pk in self.entity.primary_keys():
                query = query.where(pk, "==", self.entity.__getattribute__(pk))

            # Stream results
            # We only want the first result, if there is more than one result
            # the primary keys weren't maintained
            for i, doc in enumerate(query.stream()):
                if i > 0:
                    query_str = ""
                    for pk in self.entity.primary_keys():
                        query_str += (
                            f".where({pk}, "
                            f"'==', "
                            f"{self.entity.__getattribute__(pk)})"
                        )

                    raise ValueError(
                        f"Multiple entities found in {self.collection_name} with "
                        f" overlapping primary keys ({self.entity.primary_keys()})."
                        f"To view query results use:\n"
                        f"\t`db.collection({self.collection_name}){query_str}`"
                    )
                else:
                    self.doc = doc

            # If doc ref wasn't used, nor doc was found using querying
            # No matching doc found at all
            if self.doc is None:
                print("No matching doc found with provided details.")

    def check_primary_keys(self):
        pass

    def insert(self):
        pass

    def delete(self):
        pass

    def update(self):
        pass
