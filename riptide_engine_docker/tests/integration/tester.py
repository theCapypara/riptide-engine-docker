from time import sleep


from docker.errors import NotFound
from warnings import warn

from riptide.tests.integration.engine.tester_for_engine import AbstractEngineTester
from riptide_engine_docker.container_builder import get_service_container_name, RIPTIDE_DOCKER_LABEL_IS_RIPTIDE


class DockerEngineTester(AbstractEngineTester):
    def _get_container(self, engine_obj, project, service):
        client = engine_obj.client
        container_name = get_service_container_name(project["name"], service["$name"])
        return client.containers.get(container_name)

    def reset(self, engine_obj):
        client = engine_obj.client

        containers = client.containers.list(filters={"label": RIPTIDE_DOCKER_LABEL_IS_RIPTIDE})
        if len(containers) > 0:
            warnings = []
            for container in containers:
                warnings.append(container.name)
                if container.status != "exited":
                    container.kill()
                container.remove()
            warn("DOCKER TESTER WARNING: Had to delete containers in cleanup after test...: " + ", ".join(warnings))

        volumes = client.volumes.list(filters={"label": RIPTIDE_DOCKER_LABEL_IS_RIPTIDE})
        if len(volumes) > 0:
            warnings = []
            for volume in volumes:
                warnings.append(volume.name)
                volume.remove()
            warn("DOCKER TESTER WARNING: Had to delete volumes in cleanup after test...: " + ", ".join(warnings))

        networks = client.networks.list(filters={"label": RIPTIDE_DOCKER_LABEL_IS_RIPTIDE})
        for network in networks:
            network.remove()

    def assert_running(self, engine_obj, project, services):
        for service in services:
            try:
                container = self._get_container(engine_obj, project, service)
                if container.status == "created":
                    self.__wait_until_not_in_created_state(engine_obj, project, service)
                if container.status != "running":
                    raise AssertionError(
                        f"Container for service {service['$name']} must be running. Was: {container.status}"
                    )
            except NotFound as err:
                raise AssertionError(
                    f"Container for service {service['$name']} must be running. Was: Not Found"
                ) from err

    def assert_not_running(self, engine_obj, project, services):
        for service in services:
            try:
                self._get_container(engine_obj, project, service)
            except NotFound:
                pass
            else:
                raise AssertionError(f"Container for service {service['$name']} must be stopped non-present")

    def get_permissions_at(self, path, engine_obj, project, service, write_check=True, is_directory=True, as_user=0):
        container = self._get_container(engine_obj, project, service)

        exit_code, stat_data = container.exec_run(cmd="stat %s -c %%u:%%g:%%a" % path, stderr=False)
        assert exit_code == 0

        user, group, mode = tuple(stat_data.decode("utf-8").rstrip().split(":"))

        write_check_result = False
        if write_check and is_directory:
            exit_code, _ = container.exec_run(cmd=f"touch {path.rstrip('/')}/__write_check ", user=str(as_user))
            write_check_result = exit_code == 0
        if write_check and not is_directory:
            exit_code, _ = container.exec_run(cmd=f"sh -c 'echo \"test line\" >> {path}'", user=str(as_user))
            write_check_result = exit_code == 0

        return int(user), int(group), int(mode, 8), write_check_result

    def get_env(self, env, engine_obj, project, service):
        container = self._get_container(engine_obj, project, service)

        exit_code, env_return = container.exec_run(cmd="/bin/sh -c 'echo \"${%s?RIPTIDE___TEST___NOT_SET}\"'" % env)
        env_return = env_return.decode("utf-8").rstrip()

        if env_return == f"/bin/sh: 1: {env}: RIPTIDE___TEST___NOT_SET":
            return None
        return env_return

    def get_file(self, file, engine, project, service) -> str | None:
        container = self._get_container(engine, project, service)

        exit_code, env_return = container.exec_run(cmd=f"cat {file}", stderr=False)
        assert exit_code == 0 or exit_code == 1
        if exit_code == 1:
            return None  # File not found
        return env_return.decode("utf-8")

    def assert_file_exists(self, file, engine, project, service, type="both"):
        container = self._get_container(engine, project, service)

        if type == "file":
            flag = "f"
        elif type == "directory":
            flag = "d"
        else:
            flag = "e"

        exit_code, env_return = container.exec_run(
            cmd=f"/bin/sh -c '[ -{flag} \"{file}\" ] && echo 1 || echo 0'", stderr=False
        )
        assert exit_code == 0

        if env_return.decode("utf-8").rstrip() != "1":
            raise AssertionError(f"File {file} does not exist in container")

    def create_file(self, path, engine, project, service, as_user=0):
        container = self._get_container(engine, project, service)

        exit_code, env_return = container.exec_run(cmd=f"touch {path}", stderr=False, user=str(as_user))
        assert exit_code == 0

    def assert_named_volume(self, engine, name):
        try:
            engine.client.volumes.get(name)
        except NotFound as err:
            raise AssertionError(f"The volume {name} must exist.") from err

    def __wait_until_not_in_created_state(self, engine_obj, project, service):
        """Sometimes it takes a while for Docker to start a container. Wait until Docker is done."""
        sleep(1)
        container = self._get_container(engine_obj, project, service)
        if container.status == "created":
            self.__wait_until_not_in_created_state(engine_obj, project, service)
