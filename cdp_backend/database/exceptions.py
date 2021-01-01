#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Any, Dict, List

from fireo.models import Model

###############################################################################


class UniquenessError(Exception):
    def __init__(self, model: Model, conflicting_results: List[Model]):
        super().__init__()
        self.model = model
        self.conflicting_results = conflicting_results

    @property
    def pk_values(self) -> Dict[str, Any]:
        return {pk: getattr(self.model, pk) for pk in self.model._PRIMARY_KEYS}

    @property
    def conflicting_ids(self) -> List[str]:
        return [r.id for r in self.conflicting_results]

    def __str__(self) -> str:
        return (
            f"Uniqueness constraint failed for {self.model.collection_name}. "
            f"Found {len(self.conflicting_results)} for values: {self.pk_values}. "
            f"Conflicting IDs: {self.conflicting_ids}."
        )
