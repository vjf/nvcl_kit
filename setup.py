import pathlib
import sys
import setuptools
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup_info = dict(
    name="pynvcl",
    version="0.1.6",
    description="Downloads Australian NVCL datasets",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/csiro-geoanalytics/python-shared/pynvcl",
    author="Vincent Fazio",
    author_email="vincent.fazio@csiro.au",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    packages=setuptools.find_packages(),
    python_requires='>3.6',
    install_requires=['OWSLib']
)


setup(**setup_info)
