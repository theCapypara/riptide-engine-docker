import os
import riptide.lib.cross_platform.cppty as pty
from typing import List, Union

from docker.errors import NotFound, APIError, ImageNotFound

from riptide.config.document.command import Command
from riptide.config.document.project import Project
from riptide.config.document.service import Service
from riptide.config.files import CONTAINER_SRC_PATH, get_current_relative_src_path
from riptide.engine.abstract import ExecError

from riptide_engine_docker.assets import riptide_engine_docker_assets_dir
from riptide_engine_docker.labels import RIPTIDE_DOCKER_LABEL_IS_RIPTIDE
from riptide_engine_docker.mounts import create_cli_mount_strings
from riptide_engine_docker.names import get_cmd_container_name, get_network_name, get_service_container_name
from riptide_engine_docker.service import collect_logging_commands, collect_service_entrypoint_user_settings, \
    collect_labels, add_main_port
from riptide_engine_docker.constants import ENTRYPOINT_CONTAINER_PATH, EENV_USER, EENV_GROUP, EENV_RUN_MAIN_CMD_AS_USER, \
    EENV_NO_STDOUT_REDIRECT
from riptide_engine_docker.entrypoint import parse_entrypoint
from riptide.lib.cross_platform.cpuser import getuid, getgid


def exec_fg(client, project: Project, service_name: str, cols=None, lines=None, root=False) -> None:
    """Open an interactive shell to one running service container"""
    if service_name not in project["app"]["services"]:
        raise ExecError("Service not found.")

    container_name = get_service_container_name(project["name"], service_name)
    service_obj = project["app"]["services"][service_name]

    user = getuid()
    user_group = getgid()

    try:
        container = client.containers.get(container_name)
        if container.status == "exited":
            container.remove()
            raise ExecError('The service is not running. Try starting it first.')

        # TODO: The Docker Python API doesn't seem to support interactive exec - use pty.spawn for now
        shell = ["docker", "exec", "-it"]
        if not root:
            shell += ["-u", str(user) + ":" + str(user_group)]
        if cols and lines:
            # Add COLUMNS and LINES env variables
            shell += ['-e', 'COLUMNS=' + str(cols), '-e', 'LINES=' + str(lines)]
        if "src" in service_obj["roles"]:
            # Service has source code, set workdir in container to current workdir
            shell += ["-w", CONTAINER_SRC_PATH + "/" + get_current_relative_src_path(project)]
        shell += [container_name, "sh", "-c", "if command -v bash >> /dev/null; then bash; else sh; fi"]
        pty.spawn(shell, win_repeat_argv0=True)

    except NotFound:
        raise ExecError('The service is not running. Try starting it first.')
    except APIError as err:
        raise ExecError('Error communicating with the Docker Engine.') from err


def service_fg(client, project: Project, service_name: str, arguments: List[str]) -> None:
    """Run a service in foreground"""
    if service_name not in project["app"]["services"]:
        raise ExecError("Service not found.")

    container_name = get_service_container_name(project['name'], service_name)
    command_obj = project["app"]["services"][service_name]

    fg(client, project, container_name, command_obj, arguments)


def cmd_fg(client, project: Project, command_name: str, arguments: List[str]) -> None:
    """Run a command in foreground"""
    if command_name not in project["app"]["commands"]:
        raise ExecError("Command not found.")

    container_name = get_cmd_container_name(project['name'], command_name)
    command_obj = project["app"]["commands"][command_name]

    fg(client, project, container_name, command_obj, arguments)


def fg(client, project: Project, container_name: str, exec_object: Union[Command, Service], arguments: List[str]) -> None:
    # TODO: Get rid of code duplication
    # TODO: Piping | <
    # TODO: Not only /src into container but everything
    user = getuid()
    user_group = getgid()

    # Check if image exists
    try:
        image = client.images.get(exec_object["image"])
        image_config = client.api.inspect_image(exec_object["image"])["Config"]
    except NotFound:
        print("Riptide: Pulling image... Your command will be run after that.")
        try:
            client.api.pull(exec_object['image'] if ":" in exec_object['image'] else exec_object['image'] + ":latest")
        except ImageNotFound as ex:
            print("Riptide: Could not pull. The image was not found. Your command will not run :(")
            return
        except APIError as ex:
            print("Riptide: There was an error pulling the image. Your command will not run :(")
            print('    ' + str(ex))
            return

    # TODO: The Docker Python API doesn't seem to support interactive run - use pty.spawn for now
    # Containers are run as root, just like the services the entrypoint script manages the rest
    shell = [
        "docker", "run",
        "--label", "%s=1" % RIPTIDE_DOCKER_LABEL_IS_RIPTIDE,
        "--rm",
        "-it",
        "-w", CONTAINER_SRC_PATH + "/" + get_current_relative_src_path(project),
        "--network", get_network_name(project["name"]),
        "--name", container_name
    ]

    volumes = exec_object.collect_volumes()
    # Add custom entrypoint as volume
    entrypoint_script = os.path.join(riptide_engine_docker_assets_dir(), 'entrypoint.sh')
    volumes[entrypoint_script] = {'bind': ENTRYPOINT_CONTAINER_PATH, 'mode': 'ro'}
    mounts = create_cli_mount_strings(volumes)

    environment = exec_object.collect_environment()
    environment[EENV_NO_STDOUT_REDIRECT] = "yes"
    # Add original entrypoint, see services.
    environment.update(parse_entrypoint(image_config["Entrypoint"]))

    if isinstance(exec_object, Service):
        # TODO: Noch besser zusammenführen und aufräumen
        # ADDITIONAL SERVICE SETTINGS:
        # Collect labels
        labels = collect_labels(exec_object, project["name"])
        # Add ports
        ports = exec_object.collect_ports()
        add_main_port(exec_object, ports, labels)
        # Logging commands
        environment.update(collect_logging_commands(exec_object))
        # User settings for the entrypoint
        environment.update(collect_service_entrypoint_user_settings(exec_object, user, user_group))
        # Add shell flags
        for name, val in labels.items():
            shell += ['--label', name + '=' + val]
        for cnt_port, host_port in ports.items():
            shell += ['-p', str(host_port) + ':' + str(cnt_port)]

    else:
        # ADDITIONAL COMMAND SETTINGS:
        # User settings for the entrypoint
        environment[EENV_RUN_MAIN_CMD_AS_USER] = "yes"
        environment[EENV_USER] = str(user)
        environment[EENV_GROUP] = str(user_group)

    shell += mounts

    for key, value in environment.items():
        shell += ['-e', key + '=' + value]

    command = exec_object["command"] if "command" in exec_object else " ".join(image_config["Cmd"])

    shell += [
        "--entrypoint", ENTRYPOINT_CONTAINER_PATH,
        exec_object["image"],
        command + " " + " ".join('"{0}"'.format(w) for w in arguments)
    ]

    pty.spawn(shell, win_repeat_argv0=True)
