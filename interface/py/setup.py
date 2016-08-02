#! /usr/bin/env python3

from setuptools import setup

setup(
    name = "ieapspect",
    version = "0.1",
    packages = ["ieapspect", "ieapspect.web"],
    package_data = {"": ["*.css", "*.html", "*.js", "*.ico"]},
    scripts = ["bin/ieapspect-cpm", "bin/ieapspect-filedump", "bin/ieapspect-web"],
    description = "Python library for some of the spectrometers developed at the IEAP",
    author = "Josef Gajdusek",
    author_email = "atx@atx.name",
    url = "https://github.com/atalax/spectrometer",
    license = "MIT",
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Utilities",
        ]
    )
