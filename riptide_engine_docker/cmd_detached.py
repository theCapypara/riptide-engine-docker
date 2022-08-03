import os
from time import sleep

from docker import DockerClient
from docker.errors import NotFound, ContainerError

from riptide_engine_docker.container_builder import ContainerBuilder, get_network_name, EENV_USER, EENV_GROUP, \
    EENV_RUN_MAIN_CMD_AS_USER, EENV_NO_STDOUT_REDIRECT
from riptide.lib.cross_platform.cpuser import getuid, getgid
from riptide_engine_docker.network import add_network_links


def cmd_detached(client: DockerClient, project: 'Project', command: 'Command', run_as_root=False) -> (int, str):
    """See AbstractEngine.cmd_detached."""
    name = get_container_name(project["name"])

    # Pulling image
    # Check if image exists
    try:
        client.images.get(command["image"])
    except NotFound:
        image_name_full = command['image'] if ":" in command['image'] else command['image'] + ":latest"
        client.api.pull(image_name_full)

    image = client.images.get(command["image"])
    image_config = client.api.inspect_image(command["image"])["Config"]

    builder = ContainerBuilder(
        command["image"],
        command["command"] if "command" in command else image_config["Cmd"]
    )

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
        container = client.containers.create(**builder.build_docker_api())
        add_network_links(client, container, None, project["links"])
        container.start()
        exit_code = container.wait()
        output = container.logs()
        return exit_code['StatusCode'], output
    except ContainerError as err:
        return err.exit_status, err.stderr


def get_container_name(project_name: str):
    return 'riptide__' + project_name + '__detached_cmd__' + str(os.getpid())
