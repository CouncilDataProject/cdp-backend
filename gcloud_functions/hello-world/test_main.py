#!/usr/bin/env python
# -*- coding: utf-8 -*-f

import flask
import pytest

import main

from cdp_backend import __version__


###############################################################################


# Create a fake "app" for generating test request contexts.
@pytest.fixture(scope="module")
def app():
    return flask.Flask(__name__)


def test_hello_http_no_args(app: flask.Flask) -> None:
    with app.test_request_context():
        res = main.hello_http(flask.request)
        assert f"Hello World -- using CDP version: {__version__}! Caller: None" in res


def test_hello_http_get(app: flask.Flask) -> None:
    with app.test_request_context(query_string={"name": "test"}):
        res = main.hello_http(flask.request)
        assert f"Hello test -- using CDP version: {__version__}! Caller: None" in res


def test_hello_http_args(app: flask.Flask) -> None:
    with app.test_request_context(json={"name": "test"}):
        res = main.hello_http(flask.request)
        assert f"Hello test -- using CDP version: {__version__}! Caller: None" in res
