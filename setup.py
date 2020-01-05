#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2020, Stonks Development Team
# Distributed under the terms of the Apache License 2.0

from setuptools import setup

with open('requirements.txt', 'r') as f:
    deps = [ln.strip() for ln in f.readlines()
            if not ln.strip().startswith('#')]

setup(name='stonks',
      install_requires=deps)
