#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2014-2015 Canonical Limited.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from charmhelpers.core.hookenv import (
    log,
    DEBUG,
    ERROR,
)

import re
from charmhelpers.core.host import get_total_ram

WMARK_MAX = 1000
WMARK_DEFAULT = 10
MEMTOTAL_MIN_BYTES = 17179803648  # 16G
MAX_PAGES = 2500000000


def calculate_watermark_scale_factor():
    """Calculates optimal vm.watermark_scale_factor value

    :returns: watermark_scale_factor
    :rtype: int
    """

    memtotal = get_total_ram()
    normal_managed_pages = get_normal_managed_pages()

    try:
        wmark = min([watermark_scale_factor(memtotal, managed_pages)
                     for managed_pages in normal_managed_pages])
    except ValueError as e:
        log("Failed to calculate watermark_scale_factor from normal managed pages: {}".format(normal_managed_pages), ERROR)
        raise e

    log("vm.watermark_scale_factor: {}".format(wmark), DEBUG)
    return wmark


def get_normal_managed_pages():
    """Parse /proc/zoneinfo for managed pages of the
    normal zone on each node

    :returns: normal_managed_pages
    :rtype: [int]
    """
    try:
        normal_managed_pages = []
        with open('/proc/zoneinfo', 'r') as f:
            in_zone_normal = False
            # regex to search for strings that look like "Node 0, zone    Normal" and last string to group 1
            normal_zone_matcher = re.compile(r"^Node\s\d+,\s+zone\s+(\S+)$")
            # regex to match to a number at the end of the line.
            managed_matcher = re.compile(r"\s+managed\s+(\d+)$")
            for line in f.readlines():
                match = normal_zone_matcher.search(line)
                if match:
                    in_zone_normal = match.group(1) == 'Normal'
                if in_zone_normal:
                    # match the number at the end of "     managed    3840" into group 1.
                    managed_match = managed_matcher.search(line)
                    if managed_match:
                        normal_managed_pages.append(int(managed_match.group(1)))
                        in_zone_normal = False

    except OSError as e:
        log("Failed to read /proc/zoneinfo in calculating watermark_scale_factor: {}".format(e), ERROR)
        raise e

    return normal_managed_pages


def watermark_scale_factor(memtotal, managed_pages):
    """Calculate a value for vm.watermark_scale_factor

    :param memtotal: Total system memory in KB
    :type memtotal: int
    :param managed_pages: Number of managed pages
    :type managed_pages: int
    :returns: normal_managed_pages
    :rtype: int
    """
    if memtotal <= MEMTOTAL_MIN_BYTES:
        return WMARK_DEFAULT
    else:
        WMARK = int(MAX_PAGES / managed_pages)
        if WMARK > WMARK_MAX:
            return WMARK_MAX
        else:
            return WMARK
