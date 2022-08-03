"""Container builder module."""
from collections import OrderedDict

import os
import platform
from pathlib import PurePosixPath
from typing import List, Union

from docker.types import Mount, Ulimit

from riptide.config.document.command import Command
from riptide.config.document.service import Service
from riptide.config.hosts import get_localhost_hosts
from riptide.config.service.ports import find_open_port_starting_at
from riptide.lib.cross_platform.cpuser import getgid, getuid
from riptide_engine_docker.assets import riptide_engine_docker_assets_dir

ENTRYPOINT_SH = 'entrypoint.sh'

RIPTIDE_DOCKER_LABEL_IS_RIPTIDE = 'riptide'
RIPTIDE_DOCKER_LABEL_SERVICE = "riptide_service"
RIPTIDE_DOCKER_LABEL_PROJECT = "riptide_project"
RIPTIDE_DOCKER_LABEL_MAIN = "riptide_main"
RIPTIDE_DOCKER_LABEL_HTTP_PORT = "riptide_port"

ENTRYPOINT_CONTAINER_PATH = '/entrypoint_riptide.sh'
EENV_DONT_RUN_CMD = "RIPTIDE__DOCKER_DONT_RUN_CMD"
EENV_USER = "RIPTIDE__DOCKER_USER"
EENV_USER_RUN = "RIPTIDE__DOCKER_USER_RUN"
EENV_GROUP = "RIPTIDE__DOCKER_GROUP"
EENV_RUN_MAIN_CMD_AS_USER = "RIPTIDE__DOCKER_RUN_MAIN_CMD_AS_USER"
EENV_ORIGINAL_ENTRYPOINT = "RIPTIDE__DOCKER_ORIGINAL_ENTRYPOINT"
EENV_COMMAND_LOG_PREFIX = "RIPTIDE__DOCKER_CMD_LOGGING_"
EENV_NO_STDOUT_REDIRECT = "RIPTIDE__DOCKER_NO_STDOUT_REDIRECT"
EENV_NAMED_VOLUMES = "RIPTIDE__DOCKER_NAMED_VOLUMES"
EENV_ON_LINUX = "RIPTIDE__DOCKER_ON_LINUX"
EENV_HOST_SYSTEM_HOSTNAMES = "RIPTIDE__DOCKER_HOST_SYSTEM_HOSTNAMES"
EENV_OVERLAY_TARGETS = "RIPTIDE__DOCKER_OVERLAY_TARGETS"

# For services map HTTP main port to a host port starting here
DOCKER_ENGINE_HTTP_PORT_BND_START = 30000


class ContainerBuilder:
    """
    ContainerBuilder.
    Builds Riptide Docker containers for use with the Python API and
    the Docker CLI
    """
    def __init__(self, image: str, command: Union[List, str, None]) -> None:
        """Create a new container builder. Specify image and command to run."""
        self.env = OrderedDict()
        self.labels = OrderedDict()
        self.mounts = OrderedDict()
        self.ports = OrderedDict()
        self.network = None
        self.name = None
        self.entrypoint = None
        self.command = command
        self.args = []
        self.work_dir = None
        self.image = image
        self.set_label(RIPTIDE_DOCKER_LABEL_IS_RIPTIDE, "1")
        self.run_as_root = False
        self.hostname = None
        self.allow_full_memlock = False
        self.cap_sys_admin = False
        self.use_host_network = False

        self.on_linux = platform.system().lower().startswith('linux')
        self.set_env(EENV_ON_LINUX, "1" if self.on_linux else "0")

        self.named_volumes_in_cnt = []

    def set_env(self, name: str, val: str):
        self.env[name] = val
        return self

    def set_label(self, name: str, val: str):
        self.labels[name] = val
        return self

    def set_mount(self, host_path: str, container_path: str, mode='rw'):
        self.mounts[host_path] = Mount(
            target=container_path,
            source=host_path,
            type='bind',
            read_only=mode == 'ro',
            consistency='delegated'  # Performance setting for Docker Desktop on Mac
        )
        return self

    def set_named_volume_mount(self, name: str, container_path: str, mode='rw'):
        """
        Add a named volume. Name is automatically prefixed with riptide__.
        """
        from riptide_engine_docker.named_volumes import NAMED_VOLUME_INTERNAL_PREFIX

        vol_name = NAMED_VOLUME_INTERNAL_PREFIX + name
        self.mounts[name] = Mount(
            target=container_path,
            source=vol_name,
            type='volume',
            read_only=mode == 'ro',
            labels={RIPTIDE_DOCKER_LABEL_IS_RIPTIDE: "1"}
        )
        self.named_volumes_in_cnt.append(container_path)
        return self

    def set_port(self, cnt: int, host: int):
        self.ports[cnt] = host
        return self

    def set_network(self, network: str):
        self.network = network
        return self

    def set_use_host_network(self, flag: bool):
        self.use_host_network = flag
        return self

    def set_name(self, name: str):
        self.name = name
        return self

    def set_entrypoint(self, entrypoint: str):
        self.entrypoint = entrypoint
        return self

    def set_args(self, args: List[str]):
        self.args = args
        return self

    def set_workdir(self, work_dir: str):
        self.work_dir = work_dir
        return self

    def set_hostname(self, hostname: str):
        self.hostname = hostname
        return self

    def set_allow_full_memlock(self, flag: bool):
        self.allow_full_memlock = flag
        return self

    def enable_riptide_entrypoint(self, image_config):
        """Add the Riptide entrypoint script and configure it."""
        # The original entrypoint of the image is replaced with
        # this custom entrypoint script, which may call the original entrypoint
        # if present

        # If the entrypoint is enabled, then run the entrypoint
        # as root. It will handle the rest.
        self.run_as_root = True
        entrypoint_script = os.path.join(riptide_engine_docker_assets_dir(), ENTRYPOINT_SH)
        self.set_mount(entrypoint_script, ENTRYPOINT_CONTAINER_PATH, 'ro')

        # Collect entrypoint settings
        for key, val in parse_entrypoint(image_config["Entrypoint"]).items():
            self.set_env(key, val)

        self.set_entrypoint(ENTRYPOINT_CONTAINER_PATH)

        return self

    def add_host_hostnames(self):
        """
        Adds all hostnames that must be routable to the host system within the container as a environment variable.
        """
        self.set_env(EENV_HOST_SYSTEM_HOSTNAMES, ' '.join(get_localhost_hosts()))

    def _init_common(self, doc: Union[Service, Command], image_config, use_named_volume, unimportant_paths):
        self.enable_riptide_entrypoint(image_config)
        self.add_host_hostnames()
        # Add volumes
        for host, volume in doc.collect_volumes().items():
            if use_named_volume and 'name' in volume:
                self.set_named_volume_mount(volume['name'], volume['bind'], volume['mode'] or 'rw')
            else:
                self.set_mount(host, volume['bind'], volume['mode'] or 'rw')
        # Collect environment
        for key, val in doc.collect_environment().items():
            self.set_env(key, val)
        # Add unimportant paths to the list of dirs to be used with overlayfs
        self.set_env(EENV_OVERLAY_TARGETS, ':'.join(unimportant_paths))
        # Mounting bind/overlayfs will require SYS_ADMIN caps:
        if len(unimportant_paths) > 0:
            self.cap_sys_admin = True

    def init_from_service(self, service: Service, image_config):
        """
        Initialize some data of this builder with the given service object.
        You need to call service_add_main_port separately.
        """
        perf_settings = service.get_project().parent()['performance']
        project_absolute_unimportant_paths = []
        if perf_settings['dont_sync_unimportant_src'] and 'unimportant_paths' in service.parent():
            project_absolute_unimportant_paths = [_make_abs_to_src(p) for p in service.parent()['unimportant_paths']]
        self._init_common(
            service,
            image_config,
            perf_settings['dont_sync_named_volumes_with_host'],
            project_absolute_unimportant_paths
        )
        # Collect labels
        labels = service_collect_labels(service, service.get_project()["name"])
        # Collect (and process!) additional_ports
        ports = service.collect_ports()
        # All command logging commands are added as environment variables for the
        # riptide entrypoint
        environment_updates = service_collect_logging_commands(service)
        # User settings for the entrypoint
        environment_updates.update(service_collect_entrypoint_user_settings(service, getuid(), getgid(), image_config))
        # Add to builder
        for key, value in environment_updates.items():
            self.set_env(key, value)
        for name, val in labels.items():
            self.set_label(name, val)
        for container, host in ports.items():
            self.set_port(container, host)
        # Check if ulimit memlock setting is enabled
        if "allow_full_memlock" in service and service["allow_full_memlock"]:
            self.set_allow_full_memlock(True)
        return self

    def service_add_main_port(self, service: Service):
        """
        Add main service port.
        Not thread-safe!
        If starting multiple services in multiple threads:
            This has to be done separately, right before start,
            and with a lock in place, so that multiple service starts don't reserve the
            same port.
        """
        if "port" in service:
            main_port = find_open_port_starting_at(DOCKER_ENGINE_HTTP_PORT_BND_START)
            self.set_label(RIPTIDE_DOCKER_LABEL_HTTP_PORT, str(main_port))
            self.set_port(service["port"], main_port)

    def init_from_command(self, command: Command, image_config):
        """
        Initialize some data of this builder with the given command object.
        """
        perf_settings = command.get_project().parent()['performance']
        project_absolute_unimportant_paths = []
        if perf_settings['dont_sync_unimportant_src'] and 'unimportant_paths' in command.parent():
            project_absolute_unimportant_paths = [_make_abs_to_src(p) for p in command.parent()['unimportant_paths']]
        self._init_common(
            command,
            image_config,
            perf_settings['dont_sync_named_volumes_with_host'],
            project_absolute_unimportant_paths
        )
        return self

    def build_docker_api(self) -> dict:
        """
        Build the docker container in the form of Docker API containers.run arguments.
        """
        args = {
            'image': self.image
        }

        if self.command is None:
            args['command'] = None
        elif isinstance(self.command, str):

            # COMMAND IS STRING
            args['command'] = self.command
            if len(self.args) > 0:
                args['command'] += " " + " ".join(f'"{w}"' for w in self.args)

        else:

            list_command = self.command.copy()
            # COMMAND IS LIST
            if len(self.args) > 0:
                list_command += self.args

            # Strange Docker API Bug (?) requires args with spaces to be quoted...
            args['command'] = []
            for item in list_command:
                if " " in item:
                    args['command'].append('"' + item + '"')
                else:
                    args['command'].append(item)

        if self.name:
            args['name'] = self.name

        if self.use_host_network:
            args['network_mode'] = 'host'
        else:
            if self.network:
                args['network'] = self.network
            args['ports'] = self.ports

        if self.entrypoint:
            args['entrypoint'] = [self.entrypoint]
        if self.work_dir:
            args['working_dir'] = self.work_dir
        if self.run_as_root:
            args['user'] = 0
        if self.hostname:
            args['hostname'] = self.hostname
        if self.allow_full_memlock:
            args['ulimits'] = [Ulimit(name='memlock', soft=-1, hard=-1)]
        if self.cap_sys_admin:
            args['cap_add'] = ['SYS_ADMIN']
            # Ubuntu and possibly other Distros:
            if self.on_linux:
                args['security_opt'] = ['apparmor:unconfined']

        args['environment'] = self.env.copy()

        # Add list of named volume paths for Docker to chown
        if len(self.named_volumes_in_cnt) > 0:
            args['environment'][EENV_NAMED_VOLUMES] = ':'.join(self.named_volumes_in_cnt)

        args['labels'] = self.labels

        args['mounts'] = list(self.mounts.values())

        return args

    def build_docker_cli(self) -> List[str]:
        """
        Build the docker container in the form of a Docker CLI command.
        """
        shell = [
            "docker", "run", "--rm", "-it"
        ]
        if self.name:
            shell += ["--name", self.name]

        if self.use_host_network:
            shell += ["--network", 'host']
        else:
            if self.network:
                shell += ["--network", self.network]
            for container, host in self.ports.items():
                shell += ['-p', str(host) + ':' + str(container)]
            
        if self.entrypoint:
            shell += ["--entrypoint", self.entrypoint]
        if self.work_dir:
            shell += ["-w", self.work_dir]
        if self.run_as_root:
            shell += ["-u", str(0)]
        if self.hostname:
            shell += ["--hostname", self.hostname]

        for key, value in self.env.items():
            shell += ['-e', key + '=' + value]

        # Add list of named volume paths for Docker to chown
        if len(self.named_volumes_in_cnt) > 0:
            shell += ['-e', EENV_NAMED_VOLUMES + '=' + ':'.join(self.named_volumes_in_cnt)]

        for key, value in self.labels.items():
            shell += ['--label', key + '=' + value]

        # Mac: Add delegated
        mac_add = ',consistency=delegated' if platform.system().lower().startswith('mac') else ''
        for mount in self.mounts.values():
            mode = 'ro' if mount['ReadOnly'] else 'rw'
            if mount["Type"] == "bind":
                # --mount type=bind,src=/tmp/test,comma,dst=/tmp/test
                shell += ['--mount',
                          f'type=bind,dst={mount["Target"]},src={mount["Source"]},ro={"0" if mode == "rw" else "1"}' + mac_add]
            else:
                shell += ['--mount',
                          f'type=volume,target={mount["Target"]},src={mount["Source"]},ro={"0" if mode == "rw" else "1"},'
                          f'volume-label={RIPTIDE_DOCKER_LABEL_IS_RIPTIDE}=1']

        # ulimits
        if self.allow_full_memlock:
            shell += ['--ulimit', 'memlock=-1:-1']

        if self.cap_sys_admin:
            shell += ['--cap-add=SYS_ADMIN']
            # On Ubuntu and possibly other distros:
            if self.on_linux:
                shell += ['--security-opt', 'apparmor:unconfined']

        command = self.command
        if command is None:
            command = ""
        if isinstance(command, list):
            command = self.command[0]
            # If the command itself contains arguments, they have to be joined with
            # quotes, just like self.args
            if len(self.command) > 1:
                command += " " + " ".join(f'"{w}"' for w in self.command[1:])

        shell += [
            self.image,
            (command + " " + " ".join(f'"{w}"' for w in self.args)).rstrip()
        ]
        return shell


def get_cmd_container_name(project_name: str, command_name: str):
    return 'riptide__' + project_name + '__cmd__' + command_name + '__' + str(os.getpid())


def get_network_name(project_name: str):
    return 'riptide__' + project_name


def get_service_container_name(project_name: str, service_name: str):
    return 'riptide__' + project_name + '__' + service_name


def parse_entrypoint(entrypoint):
    """
    Parse the original entrypoint of an image and return a map of variables for the riptide entrypoint script.
    RIPTIDE__DOCKER_ORIGINAL_ENTRYPOINT: Original entrypoint as string to be used with exec.
                                         Empty if original entrypoint is not set.
    RIPTIDE__DOCKER_DONT_RUN_CMD:        true or unset.
                                         When the original entrypoint is a string, the command does not get run.
                                         See table at https://docs.docker.com/engine/reference/builder/#shell-form-entrypoint-example
    """
    # Is the original entrypoint set?
    if not entrypoint:
        return {EENV_ORIGINAL_ENTRYPOINT: ""}
    # Is the original entrypoint shell or exec format?
    if isinstance(entrypoint, list):
        # exec format
        # Turn the list into a string, but quote all arguments
        command = entrypoint.pop(0)
        arguments = " ".join([f'"{entry}"' for entry in entrypoint])
        return {
            EENV_ORIGINAL_ENTRYPOINT: command + " " + arguments
        }
    else:
        # shell format
        return {
            EENV_ORIGINAL_ENTRYPOINT: "/bin/sh -c " + entrypoint,
            EENV_DONT_RUN_CMD: "true"
        }
    pass


def service_collect_logging_commands(service: Service) -> dict:
    """Collect logging commands environment variables for this service"""
    environment = {}
    if "logging" in service and "commands" in service["logging"]:
        commands = service["logging"]["commands"]
        for cmdname, command in {k: commands[k] for k in sorted(commands)}.items():
            environment[EENV_COMMAND_LOG_PREFIX + cmdname] = command
    return environment


def service_collect_entrypoint_user_settings(service: Service, user, user_group, image_config) -> dict:
    environment = {}

    if not service["dont_create_user"]:
        environment[EENV_USER] = str(user)
        environment[EENV_GROUP] = str(user_group)

    if service["run_as_current_user"]:
        # Run with the current system user
        environment[EENV_RUN_MAIN_CMD_AS_USER] = "yes"
    elif "User" in image_config and image_config["User"] != "":
        # If run_as_current_user is false and an user is configured in the image config, tell the entrypoint to run
        # with this user
        environment[EENV_RUN_MAIN_CMD_AS_USER] = "yes"
        environment[EENV_USER_RUN] = image_config["User"]

    return environment


def service_collect_labels(service: Service, project_name):
    labels = {
        RIPTIDE_DOCKER_LABEL_IS_RIPTIDE: '1',
        RIPTIDE_DOCKER_LABEL_PROJECT: project_name,
        RIPTIDE_DOCKER_LABEL_SERVICE: service["$name"],
        RIPTIDE_DOCKER_LABEL_MAIN: "0"
    }
    if "roles" in service and "main" in service["roles"]:
        labels[RIPTIDE_DOCKER_LABEL_MAIN] = "1"
    return labels


def _make_abs_to_src(p):
    """Convert the given relative path to an absolute path. Relative base is /src/."""
    return str(PurePosixPath("/src").joinpath(p))
