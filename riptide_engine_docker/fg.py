import sys
from time import sleep

import riptide.lib.cross_platform.cppty as pty
from typing import List, Union, Optional

from docker.errors import NotFound, APIError, ImageNotFound

from riptide.config.document.command import Command
from riptide.config.document.project import Project
from riptide.config.document.service import Service
from riptide.config.files import CONTAINER_SRC_PATH, get_current_relative_src_path
from riptide.engine.abstract import ExecError

from riptide_engine_docker.container_builder import get_cmd_container_name, get_network_name, \
    get_service_container_name, ContainerBuilder, EENV_USER, EENV_GROUP, EENV_RUN_MAIN_CMD_AS_USER, \
    EENV_NO_STDOUT_REDIRECT
from riptide.lib.cross_platform.cpuser import getuid, getgid
from riptide_engine_docker.network import add_network_links
import threading

DEFAULT_EXEC_FG_CMD = "if command -v bash >> /dev/null; then bash; else sh; fi"


def exec_fg(client,
            project: Project,
            service_name: str,
            cmd: str,
            cols=None,
            lines=None,
            root=False,
            environment_variables=None) -> int:
    """Open an interactive shell to one running service container"""
    if service_name not in project["app"]["services"]:
        raise ExecError("Service not found.")

    if environment_variables is None:
        environment_variables = {}

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
        for key, value in environment_variables.items():
            shell += ['-e', key + '=' + value]
        if "src" in service_obj["roles"]:
            # Service has source code, set workdir in container to current workdir
            shell += ["-w", CONTAINER_SRC_PATH + "/" + get_current_relative_src_path(project)]
        shell += [container_name, "sh", "-c", cmd]

        return _spawn(shell)

    except NotFound:
        raise ExecError('The service is not running. Try starting it first.')
    except APIError as err:
        raise ExecError('Error communicating with the Docker Engine.') from err


def service_fg(client, project: Project, service_name: str, command_group: str, arguments: List[str]) -> None:
    """Run a service in foreground"""
    if service_name not in project["app"]["services"]:
        raise ExecError("Service not found.")

    container_name = get_service_container_name(project['name'], service_name)
    command_obj = project["app"]["services"][service_name]

    fg(client, project, container_name, command_obj, arguments, command_group)


def cmd_fg(client, project: Project, command_name: str, arguments: List[str]) -> int:
    """Run a command in foreground, returns the exit code"""
    if command_name not in project["app"]["commands"]:
        raise ExecError("Command not found.")

    container_name = get_cmd_container_name(project['name'], command_name)
    command_obj = project["app"]["commands"][command_name]

    return fg(client, project, container_name, command_obj, arguments, None)


def cmd_in_service_fg(client, project: Project, command_name: str, service_name: str, arguments: List[str]) -> int:
    command_obj: 'Command' = project["app"]["commands"][command_name]
    command_string = (command_obj["command"] + " " + " ".join(f'"{w}"' for w in arguments)).rstrip()
    return exec_fg(client, project, service_name, command_string,
                   environment_variables=command_obj.collect_environment())


def fg(client, project: Project, container_name: str, exec_object: Union[Command, Service], arguments: List[str], command_group: Optional[str]) -> int:
    # TODO: Piping | <
    # TODO: Not only /src into container but everything

    # Check if image exists
    try:
        image = client.images.get(exec_object["image"])
        image_config = client.api.inspect_image(exec_object["image"])["Config"]
    except NotFound:
        print("Riptide: Pulling image... Your command will be run after that.", file=sys.stderr)
        try:
            client.api.pull(exec_object['image'] if ":" in exec_object['image'] else exec_object['image'] + ":latest")
            image = client.images.get(exec_object["image"])
            image_config = client.api.inspect_image(exec_object["image"])["Config"]
        except ImageNotFound as ex:
            print("Riptide: Could not pull. The image was not found. Your command will not run :(", file=sys.stderr)
            return
        except APIError as ex:
            print("Riptide: There was an error pulling the image. Your command will not run :(", file=sys.stderr)
            print('    ' + str(ex), file=sys.stderr)
            return

    command = image_config["Cmd"]
    if "command" in exec_object:
        if isinstance(exec_object, Service):
            command = exec_object.get_command(command_group)
        else:
            command = exec_object["command"]

    builder = ContainerBuilder(exec_object["image"], command)

    builder.set_workdir(CONTAINER_SRC_PATH + "/" + get_current_relative_src_path(project))
    builder.set_name(container_name)
    builder.set_network(get_network_name(project["name"]))

    builder.set_env(EENV_NO_STDOUT_REDIRECT, "yes")
    builder.set_args(arguments)

    if isinstance(exec_object, Service):
        builder.init_from_service(exec_object, image_config)
        builder.service_add_main_port(exec_object)
    else:
        builder.init_from_command(exec_object, image_config)
        builder.set_env(EENV_RUN_MAIN_CMD_AS_USER, "yes")
        builder.set_env(EENV_USER, str(getuid()))
        builder.set_env(EENV_GROUP, str(getgid()))

    # Using a new thread:
    # Add the container link networks after docker run started... I tried a combo of Docker API create and Docker CLI
    # start to make it cleaner, but 'docker start' does not work well for interactive commands at all,
    # so that's the best we can do
    AddNetLinks(container_name, client, project["links"]).start()

    return _spawn(builder.build_docker_cli())


def _spawn(shell: List[str]) -> int:
    # XXX: Needs to be shifted by 1 byte because the return value of os.waitpid is shifted for some reason???
    return pty.spawn(shell, win_repeat_argv0=True) >> 8


def _wait_until_container_exists(client, container_name):
    try:
        container = client.containers.get(container_name)
    except NotFound:
        sleep(0.0025)
        return _wait_until_container_exists(client, container_name)
    return container


class AddNetLinks(threading.Thread):
    def __init__(self, container_name, client, links):
        threading.Thread.__init__(self)
        self.links = links
        self.client = client
        self.container_name = container_name

    def run(self):
        container = _wait_until_container_exists(self.client, self.container_name)
        add_network_links(self.client, container, None, self.links)