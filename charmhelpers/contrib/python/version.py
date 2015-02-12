#!/usr/bin/env python
# coding: utf-8

# Copyright 2014-2015 Canonical Limited.
#
# This file is part of charm-helpers.
#
# charm-helpers is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3 as
# published by the Free Software Foundation.
#
# charm-helpers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with charm-helpers.  If not, see <http://www.gnu.org/licenses/>.

import sys

__author__ = "Jorge Niedbalski <jorge.niedbalski@canonical.com>"


def current_version():
    """Current system python version"""
    return sys.version_info


def current_version_string():
    """Current system python version as string major.minor.micro"""
    return "{0}.{1}.{2}".format(sys.version_info.major,
                                sys.version_info.minor,
                                sys.version_info.micro)
