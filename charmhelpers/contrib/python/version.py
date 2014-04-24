#!/usr/bin/env python
# coding: utf-8

__author__ = "Jorge Niedbalski <jorge.niedbalski@canonical.com>"

import sys


def current_version():
    """Current system python version"""
    return sys.version_info


def current_version_string():
    """Current system python version as string major.minor.micro"""
    return "{0}.{1}.{2}".format(sys.version_info.major,
                                sys.version_info.minor,
                                sys.version_info.micro)
