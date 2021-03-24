# Copyright 2021 pguimaraes
# See LICENSE file for licensing details.

import unittest

from ops.model import Relation
from ops.testing import Harness
from src.charm import CharmCinderThreeParCharm

TEST_3PAR_CONFIG = '\
{"cinder": \
{"/etc/cinder/cinder.conf": \
{"sections": \
{"charm-cinder-three-par": \
[["san_ip", "1.2.3.4"], \
["san_login", "login"], \
["san_password", "pwd"], \
["hpe3par_username", ""], \
["hpe3par_password", ""], \
["hpe3par_api_url", "test.url"], \
["hpe3par_cpg", ""], \
["volume-backend-name", "charm-cinder-three-par"], \
["volume_driver", \
"cinder.volume.drivers.hpe.hpe_3par_fc.HPE3PARFCDriver"]]}}}}'


class TestCharm(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(CharmCinderThreeParCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()
        self.model = self.harness.model
        self.storage_backend = \
            self.harness.add_relation('storage-backend', 'cinder')
        self.harness.add_relation_unit(self.storage_backend, 'cinder/0')

    def test_config_changed(self):
        self.harness.update_config({
          "san-ip": "1.2.3.4",
          "san-login": "login",
          "san-password": "pwd",
          "hpe3par-api-url": "test.url"
        })
        rel = self.model.get_relation('storage-backend', 0)
        self.assertIsInstance(rel, Relation)
        self.assertEqual(rel.data[self.model.unit],
                         {'backend_name': 'charm-cinder-three-par',
                          'subordinate_configuration': TEST_3PAR_CONFIG})
