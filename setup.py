#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import find_packages, setup

with open("README.md") as readme_file:
    readme = readme_file.read()

setup_requirements = [
    "pytest-runner>=5.2",
]

test_requirements = [
    "black>=19.10b0",
    "codecov>=2.1.4",
    "flake8>=3.8.3",
    "flake8-debugger>=3.2.1",
    "isort>=5.7.0",
    "mypy>=0.790",
    "networkx>=2.5",
    "pydot>=1.4",
    "pytest>=5.4.3",
    "pytest-cov>=2.9.0",
    "pytest-raises>=0.11",
]

dev_requirements = [
    *setup_requirements,
    *test_requirements,
    "bump2version>=1.0.1",
    "coverage>=5.1",
    "ipython>=7.15.0",
    "jinja2>=2.11.2",
    "m2r>=0.2.1",
    "pytest-runner>=5.2",
    "Sphinx>=2.0.0b1,<3",
    "sphinx_rtd_theme>=0.4.3",
    "tox>=3.15.2",
    "twine>=3.1.1",
    "wheel>=0.34.2",
]

requirements = [
    "dask[bag]~=2.30.0",
    "fireo~=1.3.7",
    "fsspec~=0.8.3",
    "gcsfs~=0.7.1",
    "graphviz~=0.14",
    "pandas~=1.1.3",
    "pulumi~=2.16.2",
    "pulumi-gcp~=4.6.0",
    "prefect~=0.14.0"
]

extra_requirements = {
    "setup": setup_requirements,
    "test": test_requirements,
    "dev": dev_requirements,
    "all": [
        *requirements,
        *dev_requirements,
    ],
}

setup(
    author="Jackson Maxfield Brown",
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
            "create_cdp_database_uml=cdp_backend.bin.create_cdp_database_uml:main",
            (
                "create_cdp_ingestion_model_doc="
                "cdp_backend.bin.create_ingestion_model_doc:main"
            ),
            "cdp_event_gather=cdp_backend.bin.cdp_event_gather:main",
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
    version="3.0.0.dev3",
    zip_safe=False,
)
