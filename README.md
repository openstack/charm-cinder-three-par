# charm-cinder-three-par

# Overview


Cinder is the OpenStack block storage (volume) service and allow for different
backends to be used to provision volumes. The cinder 3PAR charm provides integration
between Cinder service and HPE 3PAR storage array solution. Users can request volumes
using OpenStack APIs and get them provisioned on 3PAR and distributed with either
Fiber Channel or iSCSI connection.

# Usage

## Configuration

This section covers common and/or important configuration options. See file
`config.yaml` for the full list of options, along with their descriptions and
default values. See the [Juju documentation][juju-docs-config-apps] for details
on configuring applications.

## Deployment

### HPE3PAR-backed storage

Cinder can be backed by HPE 3PAR SAN Array, which provides commercial hardware backend
for the volumes.

File `cinder.yaml` contains the following:

```yaml
    cinder-three-par:
```

Here, Cinder HPE 3PAR backend is deployed to a container on machine '1' 
and related the cinder subordinate charm:

    juju deploy --to lxd:1 --config cinder-three-par.yaml cinder
    juju deploy cinder-three-par
    juju add-relation cinder-three-par:storage-backend cinder:storage-backend

# Developing

Create and activate a virtualenv with the development requirements:

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r requirements-dev.txt

# Testing

The Python operator framework includes a very nice harness for testing
operator behaviour without full deployment. You can run tests with tox.
