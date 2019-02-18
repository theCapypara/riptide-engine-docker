from riptide.tests.integration.engine.tester_for_engine import AbstractEngineTester
from riptide_engine_docker.labels import RIPTIDE_DOCKER_LABEL_IS_RIPTIDE


class DockerEngineTester(AbstractEngineTester):
    def reset(self, engine_obj):
        client = engine_obj.client
        containers = client.containers.list(filters={'label': RIPTIDE_DOCKER_LABEL_IS_RIPTIDE})

        if len(containers) > 0:
            print("DOCKER TESTER WARNING: Had to delete containers in cleanup after test... List follows.")
            for container in containers:
                print(container.name)
                if container.status != 'exited':
                    container.kill()
                container.remove()

        networks = client.networks.list(filters={'label': RIPTIDE_DOCKER_LABEL_IS_RIPTIDE})

        for network in networks:
            network.remove()
