from charmhelpers.core.hookenv import (
    config,
    service_name,
    log,
    relation_ids
)
from charmhelpers.contrib.openstack.context import (
    OSContextGenerator,
)


class ThreeParSubordinateContext(OSContextGenerator):
    interfaces = ['storage-backend']

    def __call__(self):
        log('Generating cinder.conf stanza')
        ctxt = []
        charm_config = config()
        # Grab the service name in case the user wants the default backend name
        service = charm_config['volume-backend-name'] or service_name()
        for key in charm_config.keys():
            if key is 'volume-backend-name':
                ctxt.append((key, service))
            else:
                ctxt.append((key.replace('-', '_'), charm_config[key]))
        ctxt.append((
            'volume_driver',
            'cinder.volume.drivers.hpe.hpe_3par_fc.HPE3PARFCDriver'))
        for rid in relation_ids(self.interfaces[0]):
            log('Setting relation data for {}'.format(rid))
            self.related = True
            return {
                "cinder": {
                    "/etc/cinder/cinder.conf": {
                        "sections": {
                            service: ctxt
                        }
                    }
                }
            }
