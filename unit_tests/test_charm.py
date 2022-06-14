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

from ops.model import Relation, BlockedStatus, ActiveStatus
from ops.testing import Harness
from src.charm import CharmCinderThreeParCharm


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
        self.harness.update_config(
            {
                "hpe3par-api-url": "test.url",
                "hpe3par-username": "testusername",
                "hpe3par-password": "pass",
                "san-ip": "0.0.0.0",
                "san-login": "some-login",
                "san-password": "testpassword",
            }
        )

    def _get_sub_conf(self):
        rel = self.model.get_relation('storage-backend', 0)
        self.assertIsInstance(rel, Relation)
        rdata = rel.data[self.model.unit]
        rdata = json.loads(rdata['subordinate_configuration'])
        return dict(rdata['cinder']['/etc/cinder/cinder.conf'][
            'sections']['cinder-three-par'])

    def test_backend_name_in_data(self):
        rel = self.model.get_relation('storage-backend', 0)
        rdata = rel.data[self.model.unit]
        self.assertEqual(rdata['backend_name'], 'cinder-three-par')

    def test_config_changed(self):
        self.harness.update_config({
            'san-ip': '1.2.3.4',
            'san-login': 'login',
            'san-password': 'pwd',
            'hpe3par-api-url': 'test.url'
        })
        self.assertEqual(
            self._get_sub_conf(),
            {
                'driver_type': 'fc',
                'enforce_multipath_for_image_xfer': False,
                'hpe3par_api_url': 'test.url',
                'hpe3par_debug': False,
                'hpe3par_iscsi_chap_enabled': True,
                'hpe3par_password': 'pass',
                'hpe3par_username': 'testusername',
                'max_over_subscription_ratio': 20.0,
                'reserved_percentage': 15,
                'san_ip': '1.2.3.4',
                'san_login': 'login',
                'san_password': 'pwd',
                'use_multipath_for_image_xfer': False,
                'volume_backend_name': 'cinder-three-par',
                'volume_driver':
                'cinder.volume.drivers.hpe.hpe_3par_fc.HPE3PARFCDriver',
            }
        )

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
        self.assertEqual(
            self._get_sub_conf(),
            {
                'driver_type': 'fc',
                'enforce_multipath_for_image_xfer': False,
                'hpe3par_api_url': 'test.url',
                'hpe3par_debug': False,
                'hpe3par_iscsi_chap_enabled': True,
                'hpe3par_password': 'pass',
                'hpe3par_username': 'testusername',
                'max_over_subscription_ratio': 20.0,
                'reserved_percentage': 15,
                'san_ip': '0.0.0.0',
                'san_login': 'some-login',
                'san_password': 'testpassword',
                'use_multipath_for_image_xfer': False,
                'volume_backend_name': 'cinder-three-par',
                'volume_driver':
                'cinder.volume.drivers.hpe.hpe_3par_fc.HPE3PARFCDriver',
            }
        )

    def test_blocked_decimal_retention_expiration(self):
        self.harness.update_config({
            "hpe3par-snapshot-retention": 12,
            "hpe3par-snapshot-expiration": 48})
        conf = self._get_sub_conf()
        self.assertEqual(conf.get("hpe3par_snapshot_retention"), 12)
        self.assertEqual(conf.get("hpe3par_snapshot_expiration"), 48)

    def test_status_with_mandatory_config(self):
        self.assertEqual(
            self.harness.charm.unit.status.message,
            "Unit is ready"
        )
        self.assertIsInstance(self.harness.charm.unit.status, ActiveStatus)
        self.harness.update_config(
            unset=["san-ip", "san-login"],
        )
        self.assertEqual(
            self.harness.charm.unit.status.message,
            "Missing option(s): san-ip,san-login",
        )
        self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)

    def test_invalid_driver_type(self):
        self.harness.update_config(
            {
                "driver-type": "justwrong",
            }
        )
        self.assertEqual(
            self.harness.charm.unit.status.message,
            "Invalid driver-type value: justwrong"
        )
        self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)

    def test_required_params_when_iscsi_driver(self):
        self.harness.update_config(
            {
                "driver-type": "iscsi",
            }
        )
        self.assertEqual(
            self.harness.charm.unit.status.message,
            "Missing option: hpe3par-iscsi-ips",
        )
        self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)

        self.harness.update_config(
            {
                "hpe3par-iscsi-ips": "127.0.0.1",
            }
        )
        self.assertEqual(
            self.harness.charm.unit.status.message,
            "Unit is ready",
        )
        self.assertIsInstance(self.harness.charm.unit.status, ActiveStatus)

    def test_multipath_config(self):
        self.harness.update_config(
            {
                "enforce-multipath-for-image-xfer": True,
                "use-multipath-for-image-xfer": True,
            }
        )
        conf = self._get_sub_conf()
        self.assertTrue(conf.get("use_multipath_for_image_xfer"))
        self.assertTrue(conf.get("enforce_multipath_for_image_xfer"))

    def test_volume_backend_name_config(self):
        self.assertEqual(
            self._get_sub_conf().get("volume_backend_name"),
            "cinder-three-par"
        )

        self.harness.update_config(
            {
                "volume-backend-name": "test-backend",
            }
        )
        self.assertEqual(
            self._get_sub_conf().get("volume_backend_name"),
            "test-backend"
        )

    def test_iscsi_driver(self):
        self.harness.update_config({
            "driver-type": "iscsi",
            "hpe3par-iscsi-ips": "127.0.0.1",
        })
        conf = self._get_sub_conf()
        self.assertEqual(conf.get("driver_type"), "iscsi")
        self.assertEqual(
            conf.get("volume_driver"),
            "cinder.volume.drivers.hpe.hpe_3par_iscsi.HPE3PARISCSIDriver"
        )
