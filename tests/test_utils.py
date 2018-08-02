#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Suite of unit-tests for testing Michel
"""

# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0. If a copy of the MPL was not distributed
# with this file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

import michel as m

class TestMichel(unittest.TestCase):

    def test_parse_provider_url(self):
        protocol, path, params = m.parse_provider_url("test://node1/node2?param1=2&param2=1")
        self.assertEqual(protocol, "test")
        self.assertEqual(path, ["node1", "node2"])
        self.assertEqual(params, {"param1": "2", "param2": "1"})

    def test_get_provider(self):
        provider = m.get_provider("gtask://__default/default")
        self.assertIsNotNone(provider)
