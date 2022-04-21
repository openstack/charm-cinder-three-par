# Copyright 2022 Canonical Ltd
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

import unittest
import json
import copy

from ops.model import Relation, BlockedStatus, ActiveStatus
from ops.testing import Harness
from src.charm import CharmCinderThreeParCharm

TEST_3PAR_CONFIG = {
    'cinder': {
        '/etc/cinder/cinder.conf': {
            'sections': {
                'cinder-three-par': [
                    ['hpe3par_debug', False],
                    ['driver_type', 'fc'],
                    ['use_multipath_image_xfer', False],
                    ['enforce_multipath_for_image_xfer', False],
                    ['hpe3par_iscsi_chap_enabled', True],
                    ['hpe3par_snapshot_expiration', 72],
                    ['hpe3par_snapshot_retention', 48],
                    ['max_over_subscription_ratio', 20.0],
                    ['reserved_percentage', 15],
                    ['san_ip', '0.0.0.0'],
                    ['san_login', 'some-login'],
                    ['volume_backend_name', 'cinder-three-par'],
                    ['volume_driver',
                     'cinder.volume.drivers.hpe.hpe_3par_fc.HPE3PARFCDriver']
                ]
            }
        }
    }
}

TEST_3PAR_CONFIG_CHANGED = {
    'cinder': {
        '/etc/cinder/cinder.conf': {
            'sections': {
                'cinder-three-par': [
                    ['hpe3par_debug', False],
                    ['driver_type', 'fc'],
                    ['use_multipath_image_xfer', False],
                    ['enforce_multipath_for_image_xfer', False],
                    ['hpe3par_iscsi_chap_enabled', True],
                    ['max_over_subscription_ratio', 20.0],
                    ['reserved_percentage', 15],
                    ['san_ip', '1.2.3.4'],
                    ['san_login', 'login'],
                    ['san_password', 'pwd'],
                    ['hpe3par_api_url', 'test.url'],
                    ['volume_backend_name', 'cinder-three-par'],
                    ['volume_driver',
                     'cinder.volume.drivers.hpe.hpe_3par_fc.HPE3PARFCDriver']
                ]
            }
        }
    }
}


def get_inner_data(config):
    return config['cinder']['/etc/cinder/cinder.conf'][
        'sections']['cinder-three-par']


class TestCharm(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.harness = Harness(CharmCinderThreeParCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()
        self.harness.set_leader(True)
        self.model = self.harness.model
        self.storage_backend = \
            self.harness.add_relation('storage-backend', 'cinder')
        self.harness.add_relation_unit(self.storage_backend, 'cinder/0')
        self.test_config = copy.deepcopy(TEST_3PAR_CONFIG)
        self.test_changed = copy.deepcopy(TEST_3PAR_CONFIG_CHANGED)
        self.harness.update_config({'driver-type': 'fc',
                                    'volume-backend-name':
                                      'cinder-three-par',
                                    'san-login': 'some-login',
                                    'san-ip': '0.0.0.0'})

    def test_config_changed(self):
        self.harness.update_config({
            'san-ip': '1.2.3.4',
            'san-login': 'login',
            'san-password': 'pwd',
            'hpe3par-api-url': 'test.url'
        })
        rel = self.model.get_relation('storage-backend', 0)
        self.assertIsInstance(rel, Relation)
        rdata = rel.data[self.model.unit]
        self.assertEqual(rdata['backend_name'], 'cinder-three-par')
        rdata = json.loads(rdata['subordinate_configuration'])
        self.assertEqual(sorted(get_inner_data(rdata)),
                         sorted(get_inner_data(self.test_changed)))

    def test_blocked_status(self):
        self.harness.update_config(unset=["san-ip", "san-login"])
        self.assertIsInstance(
            self.harness.charm.unit.status,
            BlockedStatus)
        message = self.harness.charm.unit.status.message
        self.assertIn('san-login', message)
        self.assertIn('san-ip', message)

    def test_blocked_unset_retention_expiration(self):
        self.harness.update_config({
            "hpe3par-snapshot-retention": -1,
            "hpe3par-snapshot-expiration": -1})
        inner = get_inner_data(self.test_config)
        inner.remove(['hpe3par_snapshot_retention', 48])
        inner.remove(['hpe3par_snapshot_expiration', 72])
        rel = self.model.get_relation('storage-backend', 0)
        self.assertIsInstance(rel, Relation)
        rdata = rel.data[self.model.unit]['subordinate_configuration']
        self.assertEqual(sorted(get_inner_data(json.loads(rdata))),
                         sorted(inner))

    def test_blocked_decimal_retention_expiration(self):
        self.harness.update_config({
            "hpe3par-snapshot-retention": 12,
            "hpe3par-snapshot-expiration": 48})
        rel = self.model.get_relation('storage-backend', 0)
        self.assertIsInstance(rel, Relation)
        self.assertIn(
            ["hpe3par_snapshot_retention", 12],
            json.loads(rel.data[self.model.unit]['subordinate_configuration'])[
                'cinder']['/etc/cinder/cinder.conf']['sections'][
                'cinder-three-par'])
        self.assertIn(
            ["hpe3par_snapshot_expiration", 48],
            json.loads(rel.data[self.model.unit]['subordinate_configuration'])[
                'cinder']['/etc/cinder/cinder.conf'][
                'sections']['cinder-three-par'])

    def test_invalid_config_driver_type(self):
        self.harness.update_config({'driver-type': '???'})
        self.assertFalse(isinstance(self.harness.charm.unit.status,
                                    ActiveStatus))
