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

"""Charm for deploying and maintaining the Cinder HPE 3PAR backend driver."""

import json
import logging

from ops.charm import CharmBase
from ops.main import main
from ops.framework import StoredState
from ops.model import MaintenanceStatus, ActiveStatus, BlockedStatus

from ops_openstack.plugins.classes import CinderStoragePluginCharm

from charmhelpers.fetch.ubuntu import apt_install

logger = logging.getLogger(__name__)

# Based on check_flags() in
# https://github.com/openstack/cinder/blob/master/cinder/ \
#     volume/drivers/hpe/hpe_3par_base.py
REQUIRED_OPTS = [
    'hpe3par-api-url',
    'hpe3par-username',
    'hpe3par-password',
    'san-ip',
    'san-login',
    'san-password',
]

# Based on initialize-iscsi-ports() in
# https://github.com/openstack/cinder/blob/master/cinder/ \
#     volume/drivers/hpe/hpe-3par-iscsi.py
REQUIRED_OPTS_ISCSI = ['hpe3par-iscsi-ips']


class InvalidConfigError(Exception):
    """Exception raised on invalid configurations."""

    pass


def CinderThreeParContext(charm_config, service):
    """Configure context

    :param charm_config: Charm config data
    :type charm_config: ConfigData
    :param service: application name
    :type service: str
    :returns: dictionary for service config
    :rtype: dict
    :raises: InvalidConfigError
    """
    ctxt = []
    for key in charm_config.keys():
        ctxt.append((key.replace('-', '_'), charm_config[key]))
    if charm_config['driver-type'] == 'fc':
        ctxt.append((
            'volume_driver',
            'cinder.volume.drivers.hpe.hpe_3par_fc.HPE3PARFCDriver'))
    elif charm_config['driver-type'] == 'iscsi':
        ctxt.append((
            'volume_driver',
            'cinder.volume.drivers.hpe.hpe_3par_iscsi.HPE3PARISCSIDriver'))
    else:
        raise InvalidConfigError('Invalid config (driver-type)')
    return ctxt


class CharmCinderThreeParCharm(CinderStoragePluginCharm):
    """Charm the Cinder HPE 3PAR driver."""

    MANDATORY_CONFIG = REQUIRED_OPTS
    PACKAGES = ['python3-3parclient', 'sysfsutils']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stored.is_started = True

    def on_config(self, event):
        prev_status = self.unit.status
        try:
            super().on_config(event)
        except InvalidConfigError as e:
            self.unit.status = BlockedStatus(str(e))
        finally:
            self.unit.status = prev_status

    def _on_config(self, event):
        # The list of mandatory config options isn't static for this
        # charm, so we need to manually adjust here.
        if self.framework.model.config.get('driver-type') == 'iscsi':
            self.MANDATORY_CONFIG = REQUIRED_OPTS + REQUIRED_OPTS_ISCSI
        else:
            self.MANDATORY_CONFIG = REQUIRED_OPTS

        super()._on_config(event)

    def cinder_configuration(self, charm_config):
        svc_name = self.framework.model.app.name
        # According to the HPE 3par driver code, expiration and retention can
        # be left unset and won't be configured:
        # https://github.com/openstack/cinder/blob/stable/ussuri/cinder/ \
        #     volume/drivers/hpe/hpe_3par_common.py#L2834
        for opt in ('hpe3par-snapshot-retention',
                    'hpe3par-snapshot-expiration'):
            if charm_config.get(opt, -1) < 0:
                charm_config.pop(opt, None)
        return CinderThreeParContext(charm_config, svc_name)


if __name__ == "__main__":
    main(CharmCinderThreeParCharm)
