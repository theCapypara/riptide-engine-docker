from docker.errors import NotFound
from warnings import warn

from riptide.tests.integration.engine.tester_for_engine import AbstractEngineTester
from riptide_engine_docker.labels import RIPTIDE_DOCKER_LABEL_IS_RIPTIDE
from riptide_engine_docker.service import get_container_name


class DockerEngineTester(AbstractEngineTester):

    def _get_container(self, engine_obj, project, service):
        client = engine_obj.client
        container_name = get_container_name(project["name"], service["$name"])
        return client.containers.get(container_name)

    def reset(self, engine_obj):
        client = engine_obj.client
        containers = client.containers.list(filters={'label': RIPTIDE_DOCKER_LABEL_IS_RIPTIDE})

        if len(containers) > 0:
            warnings = []
            for container in containers:
                warnings.append(container.name)
                if container.status != 'exited':
                    container.kill()
                container.remove()
            warn("DOCKER TESTER WARNING: Had to delete containers in cleanup after test...: " + ", ".join(warnings))

        networks = client.networks.list(filters={'label': RIPTIDE_DOCKER_LABEL_IS_RIPTIDE})

        for network in networks:
            network.remove()

    def assert_running(self, engine_obj, project, services):
        for service in services:
            container = self._get_container(engine_obj, project, service)
            if container.status != 'running':
                raise AssertionError('Container for service %s must be running' % service['$name'])

    def assert_not_running(self, engine_obj, project, services):
        for service in services:
            try:
                self._get_container(engine_obj, project, service)
            except NotFound:
                pass
            else:
                raise AssertionError('Container for service %s must be stopped non-present' % service['$name'])

    def get_permissions_at(self, path, engine_obj, project, service):
        container = self._get_container(engine_obj, project, service)

        exit_code, stat_data = container.exec_run(cmd='stat %s -c %%u:%%g:%%a' % path, stderr=False)
        assert exit_code == 0

        user, group, mode = tuple(stat_data.decode('utf-8').rstrip().split(':'))

        return int(user), int(group), int(mode, 8)

    def get_env(self, env, engine_obj, project, service):
        container = self._get_container(engine_obj, project, service)

        exit_code, env_return = container.exec_run(cmd='/bin/sh -c \'echo "${%s?RIPTIDE___TEST___NOT_SET}"\'' % env)
        env_return = env_return.decode('utf-8').rstrip()

        if env_return == '/bin/sh: 1: %s: RIPTIDE___TEST___NOT_SET' % env:
            return None
        return env_return
