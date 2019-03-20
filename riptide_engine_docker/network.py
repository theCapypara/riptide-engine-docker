from docker import DockerClient
from docker.errors import NotFound

from riptide_engine_docker.labels import RIPTIDE_DOCKER_LABEL_IS_RIPTIDE
from riptide_engine_docker.names import get_network_name


def start(client: DockerClient, project_name: str):
    net_name = get_network_name(project_name)
    try:
        client.networks.get(net_name)
    except NotFound:
        client.networks.create(net_name, driver="bridge", attachable=True, labels={RIPTIDE_DOCKER_LABEL_IS_RIPTIDE: "1"})


