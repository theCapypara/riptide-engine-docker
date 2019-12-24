from typing import List, Union

from docker import DockerClient
from docker.errors import NotFound
from docker.models.containers import Container

from riptide_engine_docker.container_builder import get_network_name, RIPTIDE_DOCKER_LABEL_IS_RIPTIDE


def start(client: DockerClient, project_name: str):
    net_name = get_network_name(project_name)
    try:
        client.networks.get(net_name)
    except NotFound:
        client.networks.create(net_name, driver="bridge", attachable=True, labels={RIPTIDE_DOCKER_LABEL_IS_RIPTIDE: "1"})


def collect_names_for_links(client: DockerClient, links: List[str]) -> List[str]:
    """Collects a list of Docker networks for all known Riptide projects."""
    names = [get_network_name(p) for p in links]
    if len(names) > 0:
        return [n.name for n in client.networks.list(names=names, filters={'type': 'custom'})]
    return []


def add_network_links(client: DockerClient, container: Container, name: Union[str, None], links: List[str]):
    """Adds a project to all container networks specified in the links. Links is a list of Riptide projects."""
    for network_name in collect_names_for_links(client, links):
        if name is not None:
            client.networks.get(network_name).connect(container, aliases=[name])
        else:
            client.networks.get(network_name).connect(container)
