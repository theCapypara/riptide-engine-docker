"""
Module for manipulating and listing Docker named volumes. For function docs, see engine interface specifications.
"""
from typing import List

from docker import DockerClient
from docker.errors import NotFound, ContainerError

from riptide.engine.abstract import ExecError
from riptide_engine_docker.container_builder import RIPTIDE_DOCKER_LABEL_IS_RIPTIDE, ContainerBuilder
from riptide_engine_docker.path_utils import IMAGE as PATH_UTILS_IMAGE

NAMED_VOLUME_INTERNAL_PREFIX = 'riptide__'


def list(client: DockerClient) -> List[str]:
    volumes = client.volumes.list(filters={'label': RIPTIDE_DOCKER_LABEL_IS_RIPTIDE})
    volumes_wo_prefix = []
    len_prefix = len(NAMED_VOLUME_INTERNAL_PREFIX)
    for v in volumes:
        if v.name.startswith(NAMED_VOLUME_INTERNAL_PREFIX):
            volumes_wo_prefix.append(v.name[len_prefix:])
        else:
            # ???
            volumes_wo_prefix.append(v.name)
    return volumes_wo_prefix


def delete(client: DockerClient, name: str) -> None:
    try:
        client.volumes.get(NAMED_VOLUME_INTERNAL_PREFIX + name).remove(True)
    except NotFound:
        # this is fine.
        pass


def exists(client: DockerClient, name: str) -> bool:
    try:
        client.volumes.get(NAMED_VOLUME_INTERNAL_PREFIX + name)
        return True
    except NotFound:
        return False


def copy(client: DockerClient, from_name: str, target_name: str) -> None:
    if not exists(client, from_name):
        raise FileExistsError(f"The named volume {from_name} does not exist.")
    if exists(client, target_name):
        raise FileExistsError(f"The named volume {target_name} already exists.")

    builder = ContainerBuilder(PATH_UTILS_IMAGE, 'cp -a /copy_from/. /copy_to/')
    builder.set_named_volume_mount(from_name, '/copy_from', 'rw')
    builder.set_named_volume_mount(target_name, '/copy_to', 'rw')

    try:
        container = client.containers.create(**builder.build_docker_api())
        container.start()
        container.remove(force=True)
    except ContainerError as err:
        raise ExecError(f"Error copying the named volume {from_name} -> {target_name}: {err.stderr}") from err


def create(client: DockerClient, name: str) -> None:
    if exists(client, name):
        raise FileExistsError(f"The named volume {name} already exists.")

    client.volumes.create(NAMED_VOLUME_INTERNAL_PREFIX + name, labels={RIPTIDE_DOCKER_LABEL_IS_RIPTIDE: "1"})
