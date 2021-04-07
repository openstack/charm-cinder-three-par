# charm-cinder-three-par

## Description


Cinder is the OpenStack block storage (volume) service and allow for different backends to be used to provision volumes.

The cinder 3PAR charm provides integration between Cinder service and HPE 3PAR storage array solution. Users can request volumes using OpenStack APIs and get them provisioned on 3PAR and distributed with either Fiber Channel or iSCSI connection.

## Usage

TODO: Provide high-level usage, such as required config or relations


## Developing

Create and activate a virtualenv with the development requirements:

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r requirements-dev.txt

## Testing

The Python operator framework includes a very nice harness for testing
operator behaviour without full deployment. You can run tests with tox.
