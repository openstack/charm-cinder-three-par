import charms_openstack.charm as charm
import charms.reactive as reactive


import charm.openstack.three_par as three_par
assert three_par

charm.use_defaults('charm.installed')


@reactive.when_any('storage-backend.connected', 'storage-backend.changed')
@reactive.when_not('storage-backend.available')
def storage_backend():
    with charm.provide_charm_instance() as charm_class:
        charm_class.set_relation_data()
    reactive.set_state('storage-backend.available')


@reactive.when('config.changed')
def update_config():
    reactive.remove_state('storage-backend.available')
    with charm.provide_charm_instance() as charm_class:
        charm_class.set_relation_data()
    reactive.set_state('storage-backend.available')
