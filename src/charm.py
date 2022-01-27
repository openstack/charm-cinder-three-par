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
    'san-password']

# Based on initialize-iscsi-ports() in
# https://github.com/openstack/cinder/blob/master/cinder/ \
#     volume/drivers/hpe/hpe-3par-iscsi.py
REQUIRED_OPTS_ISCSI = [
    'hpe3par-iscsi-ips']


class InvalidConfigError(Exception):
    """Exception raised on invalid configurations."""

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


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
        if key == 'volume-backend-name':
            ctxt.append((key, service))
        else:
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
    return {
        "cinder": {
            "/etc/cinder/cinder.conf": {
                "sections": {
                    service: ctxt
                }
            }
        }
    }


class CharmCinderThreeParCharm(CharmBase):
    """Charm the Cinder HPE 3PAR driver."""

    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(
            self.on.install,
            self._on_install)
        self.framework.observe(
            self.on.config_changed,
            self._on_config_changed_or_upgrade)
        self.framework.observe(
            self.on.upgrade_charm,
            self._on_config_changed_or_upgrade)
        self.framework.observe(
            self.on.storage_backend_relation_joined,
            self._on_render_storage_backend)
        self.framework.observe(
            self.on.storage_backend_relation_changed,
            self._on_render_storage_backend)

    def _rel_get_remote_units(self, rel_name):
        """Get relations remote units"""
        return self.framework.model.get_relation(rel_name).units

    def _on_install(self, _):
        """Install packages"""
        self.unit.status = MaintenanceStatus(
            "Installing packages")
        # os_brick lib needs systool from sysfsutils to be able to retrieve
        # the data from FC links:
        # https://github.com/openstack/os-brick/blob/ \
        #     1b2e2295421615847d86508dcd487ec51fa45f25/ \
        #     os_brick/initiator/linuxfc.py#L151
        apt_install(['python3-3parclient',
                     'sysfsutils'])
        self.unit.status = ActiveStatus("Unit is ready")

    def _on_config_changed_or_upgrade(self, event):
        """Update on changed config or charm upgrade"""
        svc_name = self.framework.model.app.name
        # Copying to a new dict as charm_config will be edited according to
        # the settings
        charm_config = dict(self.framework.model.config)
        if not self.check_config(charm_config):
            # The config checks failed, drop this event as the operator
            # needs to intervene manually
            return
        r = self.framework.model.relations.get('storage-backend')[0]
        try:
            ctx = CinderThreeParContext(charm_config, svc_name)
        except InvalidConfigError as e:
            self.unit.status = BlockedStatus(str(e))
            return

        for u in self._rel_get_remote_units('storage-backend'):
            r.data[self.unit]['backend_name'] = \
                charm_config['volume-backend-name'] or svc_name
            r.data[self.unit]['subordinate_configuration'] = json.dumps(ctx)
        self.unit.status = ActiveStatus("Unit is ready")

    def _on_render_storage_backend(self, event):
        """Render the current configuration"""
        svc_name = self.framework.model.app.name
        charm_config = self.framework.model.config
        data = event.relation.data
        data[self.unit]['backend_name'] = \
            charm_config['volume-backend-name'] or svc_name
        try:
            ctx = CinderThreeParContext(charm_config, svc_name)
        except InvalidConfigError as e:
            self.unit.status = BlockedStatus(str(e))
            return

        data[self.unit]['subordinate_configuration'] = json.dumps(ctx)

    def check_config(self, charm_config):
        """Check whether required options are set."""
        # According to the HPE 3par driver code, expiration and retention can
        # be left unset and won't be configured:
        # https://github.com/openstack/cinder/blob/stable/ussuri/cinder/ \
        #     volume/drivers/hpe/hpe_3par_common.py#L2834
        for opt in ("hpe3par-snapshot-retention",
                    "hpe3par-snapshot-expiration"):
            # Setting as < 0 will remove the given option from the request.
            if charm_config.get(opt, -1) < 0:
                charm_config.pop(opt, None)
        required_opts = REQUIRED_OPTS
        charm_config = self.framework.model.config
        if charm_config['driver-type'] == 'iscsi':
            required_opts += REQUIRED_OPTS_ISCSI
        missing_opts = set(required_opts) - set(charm_config.keys())
        if missing_opts:
            self.unit.status = BlockedStatus(
                'Missing options: {}'.format(','.join(missing_opts)))
            return False
        else:
            self.unit.status = MaintenanceStatus("Sharing configs with Cinder")
        return True


if __name__ == "__main__":
    main(CharmCinderThreeParCharm)
