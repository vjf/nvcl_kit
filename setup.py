import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="pynvcl",
    version="0.1.0",
    description="Extract NVCL data",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/csiro-geoanalytics/python-shared/pynvcl",
    author="Vincent Fazio",
    author_email="vincent.fazio@csiro.au",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    packages=["nvcl_kit"],
    include_package_data=False,
    install_requires=["OWSlib"],
)
