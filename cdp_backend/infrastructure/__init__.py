"""
The files required for setting up an infrastructure stack.

They are stored here in cdp-backend rather than the cookiecutter
so that all backend components are together and it makes it easy to
create dev-infrastructures for development.
"""

from pathlib import Path

INFRA_DIR = Path(__file__).parent


class GoverningBody:
    city_council = "city council"
    county_council = "county council"
    school_board = "school board"
    other = "other"
