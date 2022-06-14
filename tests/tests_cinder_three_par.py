#!/usr/bin/env python3

# Copyright 2021 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Encapsulate cinder-purestorage testing."""

import zaza.model
from zaza.openstack.charm_tests.test_utils import BaseCharmTest


class CinderThreeParTest(BaseCharmTest):
    """Encapsulate three-par tests."""

    def test_cinder_config(self):
        """Test that configuration options match our expectations."""
        zaza.model.run_on_leader(
            "cinder",
            "sudo cp /etc/cinder/cinder.conf /tmp/",
        )
        zaza.model.block_until_oslo_config_entries_match(
            "cinder",
            "/tmp/cinder.conf",
            {
                "cinder-three-par": {
                    # sanity test a few common params
                    "volume_backend_name": ["cinder-three-par"],
                    "hpe3par_api_url": ["https://127.0.0.1:8080/api/v1/"],
                    "san_login": ["admin"],
                    "use_multipath_for_image_xfer": ["True"],
                    "enforce_multipath_for_image_xfer": ["True"],
                }
            },
            timeout=2,
        )
