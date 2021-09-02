#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import find_packages, setup

with open("README.md") as readme_file:
    readme = readme_file.read()

setup_requirements = [
    "pytest-runner>=5.2",
]

pipeline_requirements = [
    "dask[distributed]>=2021.7.0",
    "ffmpeg-python~=0.2.0",
    "google-cloud-speech~=1.3",
    "graphviz~=0.16",
    "imageio~=2.9",
    "imageio-ffmpeg~=0.4.4",
    "nltk~=3.6",
    "pandas~=1.2",
    "prefect~=0.14.0",
    "pulumi~=3.3",
    "pulumi-google-native~=0.1.0",
    "pulumi-gcp~=5.7",
    "rapidfuzz~=1.4",
    "spacy~=3.0",
    "truecase~=0.0.12",
    "webvtt-py~=0.4.6",
]

test_requirements = [
    *pipeline_requirements,
    "black>=19.10b0",
    "codecov==2.1.12",
    "fastparquet~=0.7",
    "flake8>=3.8.3",
    "flake8-debugger>=3.2.1",
    "isort>=5.7.0",
    "mypy>=0.790",
    "networkx>=2.5",
    "pyarrow~=5.0",
    "pydot>=1.4",
    "pytest>=5.4.3",
    "pytest-cov>=2.9.0",
    "pytest-raises>=0.11",
    "types-pytz>=2021.1.2",
    "types-requests~=0.1.11",
]

dev_requirements = [
    *setup_requirements,
    *test_requirements,
    "bokeh>=2.3.2",
    "bump2version>=1.0.1",
    "coverage==5.4",
    "ipython>=7.15.0",
    "jinja2>=2.11.2",
    "m2r2>=0.2.7",
    "prefect[viz]~=0.14.0",
    "pytest-runner>=5.2",
    "Sphinx>=3.4.3",
    "sphinx_rtd_theme>=0.5.1",
    "tox>=3.15.2",
    "twine>=3.1.1",
    "wheel>=0.34.2",
]

requirements = [
    "dataclasses-json~=0.5",
    "fireo~=1.4",
    "fsspec",  # Version pin set by gcsfs
    "gcsfs~=2021.7.0",
]

extra_requirements = {
    "setup": setup_requirements,
    "pipeline": pipeline_requirements,
    "test": test_requirements,
    "dev": dev_requirements,
    "all": [
        *requirements,
        *dev_requirements,
    ],
}

setup(
    author="Jackson Maxfield Brown, To Huynh, Isaac Na",
    author_email="jmaxfieldbrown@gmail.com",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    description=(
        "Data storage utilities and processing pipelines to run on CDP server "
        "deployments."
    ),
    entry_points={
        "console_scripts": [
            "clean_cdp_database=cdp_backend.bin.clean_cdp_database:main",
            "clean_cdp_filestore=cdp_backend.bin.clean_cdp_filestore:main",
            "create_cdp_database_uml=cdp_backend.bin.create_cdp_database_uml:main",
            (
                "create_cdp_ingestion_models_doc="
                "cdp_backend.bin.create_cdp_ingestion_models_doc:main"
            ),
            (
                "create_cdp_transcript_model_doc="
                "cdp_backend.bin.create_cdp_transcript_model_doc:main"
            ),
            (
                "create_cdp_event_gather_flow_viz="
                "cdp_backend.bin.create_cdp_event_gather_flow_viz:main"
            ),
            "run_cdp_event_gather=cdp_backend.bin.run_cdp_event_gather:main",
            "run_cdp_event_index=cdp_backend.bin.run_cdp_event_index:main",
            "search_cdp_events=cdp_backend.bin.search_cdp_events:main",
            "process_local_file=cdp_backend.bin.process_local_file:main",
        ],
    },
    install_requires=requirements,
    license="MIT license",
    long_description=readme,
    long_description_content_type="text/markdown",
    include_package_data=True,
    keywords="civic technology, open government",
    name="cdp-backend",
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*"]),
    python_requires=">=3.7",
    setup_requires=setup_requirements,
    test_suite="cdp_backend/tests",
    tests_require=test_requirements,
    extras_require=extra_requirements,
    url="https://github.com/CouncilDataProject/cdp-backend",
    # Do not edit this string manually, always use bump2version
    # Details in CONTRIBUTING.rst
    version="3.0.0.dev11",
    zip_safe=False,
)
