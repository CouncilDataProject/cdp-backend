#!/usr/bin/env python
# -*- coding: utf-8 -*-

import inspect
from typing import Any, List, Type

###############################################################################


def get_all_class_attr_values(cls: Type) -> List[Any]:
    """
    Get all class attributes of the provided class.
    Intended to be used to get all constant values of a class.

    Parameters
    ----------
    cls: Type
        The class to get the class attributes values for.

    Returns
    -------
    class_attr_values: List[Any]:
        The class attributes values.
    """
    return [
        i[1]
        for i in inspect.getmembers(cls)
        if not i[0].startswith("_") and not inspect.isroutine(i[1])
    ]
