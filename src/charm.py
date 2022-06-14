#!/usr/bin/env python3
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

from ops.main import main
from ops.model import ActiveStatus, BlockedStatus
from ops_openstack.plugins.classes import CinderStoragePluginCharm


def _check_config(charm_config):
    """
    These checks are in addition to the parent class checks
    for MANDATORY_CONFIG.
    """
    if charm_config["driver-type"] not in ("fc", "iscsi"):
        return BlockedStatus(
            "Invalid driver-type value: " + charm_config["driver-type"]
        )

    # iscsi driver type requires an extra config option
    # Based on initialize-iscsi-ports() in
    # https://github.com/openstack/cinder/blob/master/cinder/volume/drivers/hpe/hpe-3par-iscsi.py
    if charm_config["driver-type"] == "iscsi" and not charm_config.get(
        "hpe3par-iscsi-ips"
    ):
        return BlockedStatus("Missing option: hpe3par-iscsi-ips")

    return ActiveStatus()


class CharmCinderThreeParCharm(CinderStoragePluginCharm):
    """Charm the Cinder HPE 3PAR driver."""

    PACKAGES = [
        "python3-3parclient",
        # os_brick lib needs systool from sysfsutils to be able to retrieve
        # the data from FC links:
        # https://github.com/openstack/os-brick/blob/1b2e2295421615847d86508dcd487ec51fa45f25/os_brick/initiator/linuxfc.py#L151
        "sysfsutils",
    ]

    # Based on check_flags() in
    # https://github.com/openstack/cinder/blob/master/cinder/ \
    #     volume/drivers/hpe/hpe_3par_base.py
    MANDATORY_CONFIG = [
        "hpe3par-api-url",
        "hpe3par-username",
        "hpe3par-password",
        "san-ip",
        "san-login",
        "san-password",
    ]

    def on_config(self, event):
        status = _check_config(self.framework.model.config)
        if not isinstance(status, ActiveStatus):
            self.unit.status = status
            return

        super().on_config(event)

    def cinder_configuration(self, charm_config):
        options = []
        for key, value in charm_config.items():
            # According to the HPE 3par driver code,
            # expiration and retention can
            # be left unset and won't be configured:
            # https://github.com/openstack/cinder/blob/stable/ussuri/cinder/volume/drivers/hpe/hpe_3par_common.py#L2834
            if (
                key
                in (
                    "hpe3par-snapshot-retention",
                    "hpe3par-snapshot-expiration",
                ) and value < 0
            ):
                continue

            # volume-backend-name has a dynamic default value, set here
            if key == "volume-backend-name" and not value:
                value = self.framework.model.app.name

            options.append((key.replace("-", "_"), value))

        if charm_config["driver-type"] == "fc":
            options.append((
                "volume_driver",
                "cinder.volume.drivers.hpe.hpe_3par_fc.HPE3PARFCDriver",
            ))
        elif charm_config["driver-type"] == "iscsi":
            options.append((
                "volume_driver",
                "cinder.volume.drivers.hpe.hpe_3par_iscsi.HPE3PARISCSIDriver",
            ))

        return options


if __name__ == "__main__":
    main(CharmCinderThreeParCharm)
