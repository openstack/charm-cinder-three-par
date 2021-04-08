#!/usr/bin/env python3
# Copyright 2021 pguimaraes
# See LICENSE file for licensing details.

import json
import logging

from ops.charm import CharmBase
from ops.main import main
from ops.framework import StoredState
from ops.model import MaintenanceStatus, ActiveStatus, BlockedStatus

from charmhelpers.fetch.ubuntu import apt_install, apt_purge

logger = logging.getLogger(__name__)

# Based on check_flags() in
# https://github.com/openstack/cinder/blob/master/cinder/volume/drivers/hpe/hpe_3par_base.py
REQUIRED_OPTS = [
    'hpe3par-api-url',
    'hpe3par-username',
    'hpe3par-password',
    'san-ip',
    'san-login',
    'san-password']

# Based on initialize-iscsi-ports() in
# https://github.com/openstack/cinder/blob/master/cinder/volume/drivers/hpe/hpe-3par-iscsi.py
REQUIRED_OPTS_ISCSI = [
    'hpe3par-iscsi-ips']


def CinderThreeParContext(charm_config, service):
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
    """Charm the service."""

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
        return self.framework.model.get_relation(rel_name).units

    def _on_install(self, _):
        self.unit.status = MaintenanceStatus(
            "Installing packages")
        apt_install(['python3-3parclient'])
        try:
            apt_purge(['python3-certifi',
                       'python3-urllib3',
                       'python3-requests'])
        except Exception as e:
            logger.debug("Tried removing packages on install and failed "
                         "with {}, ignoring".format(str(e)))
        self.unit.status = ActiveStatus("Unit is ready")

    def _on_config_changed_or_upgrade(self, event):
        svc_name = self.framework.model.app.name
        charm_config = self.framework.model.config
        r = self.framework.model.relations.get('storage-backend')[0]
        for u in self._rel_get_remote_units('storage-backend'):
            r.data[self.unit]['backend_name'] = \
                charm_config['volume-backend-name'] or svc_name
            r.data[self.unit]['subordinate_configuration'] = \
                json.dumps(CinderThreeParContext(charm_config, svc_name))
        self.check_config()

    def _on_render_storage_backend(self, event):
        svc_name = self.framework.model.app.name
        charm_config = self.framework.model.config
#        relations = self.framework.model.relations
#        data = relations.get(event.relation.name)[0].data
        data = event.relation.data
        data[self.unit]['backend_name'] = \
            charm_config['volume-backend-name'] or svc_name
        data[self.unit]['subordinate_configuration'] = \
            json.dumps(CinderThreeParContext(charm_config, svc_name))

    def check_config(self):
        """
        Check whether required options are set.
        """
        required_opts = REQUIRED_OPTS
        charm_config = self.framework.model.config
        if charm_config['driver-type'] == 'iscsi':
            required_opts += REQUIRED_OPTS_ISCSI
        missing_opts = set(required_opts) - set(charm_config.keys())
        if missing_opts:
            self.unit.status = BlockedStatus(
                'Missing options: {}'.format(','.join(missing_opts)))
        else:
            self.unit.status = ActiveStatus("Unit is ready")


if __name__ == "__main__":
    main(CharmCinderThreeParCharm)
