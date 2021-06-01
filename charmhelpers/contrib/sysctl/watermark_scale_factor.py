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

WMARK_MAX = 1000
WMARK_DEFAULT = 10
MEM_TOTAL_MIN_KB = 16777152
MAX_PAGES = 2500000000
P = re.compile('\d+')


def calculate_watermark_scale_factor():
    """Calculates optimal vm.watermark_scale_factor value

    :returns: watermark_scale_factor
    :type: int
    """

    mem_total = get_memtotal()
    normal_managed_pages = get_normal_managed_pages()

    try:
        wmark = min([watermark_scale_factor(mem_total, managed_pages)
                     for managed_pages in normal_managed_pages])
    except ValueError as e:
        log("Failed to calculate watermark_scale_factor from normal managed pages: {}".format(normal_managed_pages), ERROR)
        raise e

    log("vm.watermark_scale_factor: {}".format(wmark), DEBUG)
    return wmark


def get_memtotal():
    memtotal = None
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                print(line)
                if "MemTotal" in line:
                    memtotal = int(P.search(line).group())
                    break
                else:
                    raise Exception("Could not find MemTotal")
    except (Exception, OSError) as e:
        log("Failed to parse /proc/meminfo in calculating watermark_scale_factor: {}".format(e), ERROR)
        raise e

    return memtotal


def get_normal_managed_pages():
    try:
        normal_managed_pages = []
        with open('/proc/zoneinfo', 'r') as f:
            for line in f:
                if "Node" in line and "zone" in line:
                    zone = [v for v in line.split(' ')
                            if v in ["DMA", "DMA32", "Normal", "Movable", "Device"]][0]

                if zone == "Normal" and "managed" in line:
                    managed = int([v for v in line.split(' ') if P.match(v)][0])
                    normal_managed_pages.append(managed)
    except OSError as e:
        log("Failed to read /proc/zoneinfo in calculating watermark_scale_factor: {}".format(e), ERROR)
        raise e

    return normal_managed_pages


def watermark_scale_factor(mem_total, managed_pages):
    # if < 16G ram return default
    if mem_total <= MEM_TOTAL_MIN_KB:
        return WMARK_DEFAULT
    else:
        wmark = int(MAX_PAGES / managed_pages)
        if wmark > 1000:
            return 1000
        else:
            return wmark
