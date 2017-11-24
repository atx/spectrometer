#! /usr/bin/env python3

import sys
import setuptools.command.install
from subprocess import check_output
from setuptools import setup


class WrapperInstall(setuptools.command.install.install):

    def run(self):
        out = check_output(["make", "-C", "wrappers"])
        sys.stdout.buffer.write(out)
        super(WrapperInstall, self).run()

setup(
    name="ieapspect",
    version="0.1",
    packages=["ieapspect", "ieapspect.web"],
    package_data={"": ["*.css", "*.html", "*.js", "*.ico"]},
    include_package_data=True,
    scripts=["bin/ieapspect-cpm", "bin/ieapspect-filedump", "bin/ieapspect-web",
             "bin/ieapspect-dm100", "bin/ieapspect-spectrig", "bin/ieapspect-simplegui"],
    data_files=[("bin", ["wrappers/ieapspect-wrapper-" + f
                         for f in ["dm100", "spectrig"]])],
    description="Python library for some of the spectrometers developed at the IEAP",
    author="Josef Gajdusek",
    author_email="atx@atx.name",
    url="https://github.com/atalax/spectrometer",
    license="MIT",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Utilities",
    ],
    cmdclass={"install": WrapperInstall}
)
