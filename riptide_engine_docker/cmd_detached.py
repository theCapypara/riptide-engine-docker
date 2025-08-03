from __future__ import annotations

import os
from typing import Tuple

from docker import DockerClient
from docker.errors import ContainerError, NotFound
from riptide.config.document.command import Command
from riptide.config.document.project import Project
from riptide.lib.cross_platform.cpuser import getgid, getuid
from riptide_engine_docker.container_builder import (
    EENV_GROUP,
    EENV_NO_STDOUT_REDIRECT,
    EENV_RUN_MAIN_CMD_AS_USER,
    EENV_USER,
    ContainerBuilder,
    get_network_name,
)
from riptide_engine_docker.network import add_network_links


def cmd_detached(client: DockerClient, project: Project, command: Command, run_as_root=False) -> Tuple[int, str]:
    """See AbstractEngine.cmd_detached."""
    # Pulling image
    # Check if image exists
    try:
        client.images.get(command["image"])
    except NotFound:
        image_name_full = command["image"] if ":" in command["image"] else command["image"] + ":latest"
        client.api.pull(image_name_full)

    client.images.get(command["image"])  # must not throw
    image_config = client.api.inspect_image(command["image"])["Config"]
    image_command = image_config["Cmd"] if "Cmd" in image_config else None

    builder = ContainerBuilder(command["image"], command["command"] if "command" in command else image_command)

    builder.set_name(get_container_name(project["name"]))
    # network_mode host not supported atm
    builder.set_network(get_network_name(project["name"]))

    builder.set_env(EENV_NO_STDOUT_REDIRECT, "yes")

    builder.init_from_command(command, image_config)
    if not run_as_root:
        builder.set_env(EENV_RUN_MAIN_CMD_AS_USER, "yes")
        builder.set_env(EENV_USER, str(getuid()))
        builder.set_env(EENV_GROUP, str(getgid()))

    try:
        container = client.containers.create(**builder.build_docker_api())  # type: ignore
        add_network_links(client, container, None, project["links"])
        container.start()
        exit_code = container.wait()
        output = container.logs()
        return exit_code["StatusCode"], str(output)
    except ContainerError as err:
        return err.exit_status, err.stderr  # type: ignore


def get_container_name(project_name: str):
    return "riptide__" + project_name + "__detached_cmd__" + str(os.getpid())
