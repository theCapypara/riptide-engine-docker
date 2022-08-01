import os
import unittest

from docker.types import Mount
from unittest import mock

from unittest.mock import Mock, MagicMock

from riptide.tests.configcrunch_test_utils import YamlConfigDocumentStub
from riptide.tests.stubs import ProjectStub
from riptide_engine_docker.container_builder import ContainerBuilder, ENTRYPOINT_SH, ENTRYPOINT_CONTAINER_PATH, \
    EENV_ORIGINAL_ENTRYPOINT, EENV_DONT_RUN_CMD, EENV_COMMAND_LOG_PREFIX, EENV_USER, EENV_GROUP, \
    EENV_RUN_MAIN_CMD_AS_USER, RIPTIDE_DOCKER_LABEL_IS_RIPTIDE, RIPTIDE_DOCKER_LABEL_MAIN, RIPTIDE_DOCKER_LABEL_PROJECT, \
    RIPTIDE_DOCKER_LABEL_SERVICE, RIPTIDE_DOCKER_LABEL_HTTP_PORT, EENV_USER_RUN, DOCKER_ENGINE_HTTP_PORT_BND_START, \
    EENV_ON_LINUX, EENV_HOST_SYSTEM_HOSTNAMES, EENV_OVERLAY_TARGETS, EENV_NAMED_VOLUMES

IMAGE_NAME = 'unit/testimage'
COMMAND = 'test_command'
EADMOCK = '__riptide_engine_docker_assets_dir'
GET_LOCALHOSTS_HOSTS_RETURN = ['dummy1', 'dummy2']


class ContainerBuilderTest(unittest.TestCase):

    def setUp(self) -> None:
        self.fix = ContainerBuilder(image=IMAGE_NAME, command=COMMAND)
        self.expected_api_base = {
            'image': IMAGE_NAME,
            'command': COMMAND,
            'environment': {EENV_ON_LINUX: '1'},
            'mounts': [],
            'ports': {},
            'labels': {'riptide': '1'}
        }
        self.expected_cli_base = ["docker", "run", "--rm", "-it"]

    def test_simple(self):
        """Test only with values from constructor"""
        # Test API build
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '-e', EENV_ON_LINUX + '=1', '--label', 'riptide=1', IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    def test_command_list(self):
        test_obj = ContainerBuilder(image=IMAGE_NAME, command=[COMMAND, 'elem2'])
        # Test API build
        self.expected_api_base.update({
            'command': [COMMAND, 'elem2']
        })
        actual_api = test_obj.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '-e', EENV_ON_LINUX + '=1', '--label', 'riptide=1', IMAGE_NAME, COMMAND + ' "elem2"'
        ]
        actual_cli = test_obj.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    def test_command_none(self):
        test_obj = ContainerBuilder(image=IMAGE_NAME, command=None)
        # Test API build
        self.expected_api_base.update({
            'command': None
        })
        actual_api = test_obj.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '-e', EENV_ON_LINUX + '=1', '--label', 'riptide=1', IMAGE_NAME, ''
        ]
        actual_cli = test_obj.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    def test_command_list_spaces(self):
        test_obj = ContainerBuilder(image=IMAGE_NAME, command=[COMMAND, 'elem2 elem3'])
        # Test API build
        self.expected_api_base.update({
            'command': [COMMAND, '"elem2 elem3"']
        })
        actual_api = test_obj.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '-e', EENV_ON_LINUX + '=1', '--label', 'riptide=1', IMAGE_NAME, COMMAND + ' "elem2 elem3"'
        ]
        actual_cli = test_obj.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    def test_command_str_spaces_in_first_part_of_command(self):
        test_obj = ContainerBuilder(image=IMAGE_NAME, command='elem1 elem2 elem3 "elem4a elem4b" \'elem5a elem5b\'')
        # Test API build
        self.expected_api_base.update({
            'command': 'elem1 elem2 elem3 "elem4a elem4b" \'elem5a elem5b\''
        })
        actual_api = test_obj.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '-e', EENV_ON_LINUX + '=1', '--label', 'riptide=1', IMAGE_NAME, 'elem1 elem2 elem3 "elem4a elem4b" \'elem5a elem5b\''
        ]
        actual_cli = test_obj.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    def test_set_env(self):
        self.fix.set_env('test_key', 'test_value')

        # Test API build
        self.expected_api_base.update({
            'environment': {'test_key': 'test_value', EENV_ON_LINUX: '1'}
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '-e', EENV_ON_LINUX + '=1', '-e', 'test_key=test_value',
            '--label', 'riptide=1', IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    def test_set_label(self):
        self.fix.set_label('test_key', 'test_value')

        # Test API build
        self.expected_api_base.update({
            'labels': {
                'riptide': '1',
                'test_key': 'test_value'
            }
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '-e', EENV_ON_LINUX + '=1',
            '--label', 'riptide=1',
            '--label', 'test_key=test_value', IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    @mock.patch('platform.system', return_value='Linux')
    def test_set_mount_not_mac(self, system_mock: Mock):
        self.fix.set_mount('/host_path', '/container_path')
        self.fix.set_mount('/host_path2', '/container_path2', 'ro')

        # Test API build
        self.expected_api_base.update({
            'mounts': [
                Mount(
                    target='/container_path',
                    source='/host_path',
                    type='bind',
                    read_only=False,
                    consistency='delegated'
                ),
                Mount(
                    target='/container_path2',
                    source='/host_path2',
                    type='bind',
                    read_only=True,
                    consistency='delegated'
                )
            ]
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '-e', EENV_ON_LINUX + '=1',
            '--label', 'riptide=1',
            '--mount', 'type=bind,dst=/container_path,src=/host_path,ro=0',
            '--mount', 'type=bind,dst=/container_path2,src=/host_path2,ro=1',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    @mock.patch('platform.system', return_value='MacOS')
    def test_set_mount_mac(self, system_mock: Mock):
        self.fix.set_mount('/host_path', '/container_path')
        self.fix.set_mount('/host_path2', '/container_path2', 'ro')

        # Test API build
        self.expected_api_base.update({
            'mounts': [
                Mount(
                    target='/container_path',
                    source='/host_path',
                    type='bind',
                    read_only=False,
                    consistency='delegated'
                ),
                Mount(
                    target='/container_path2',
                    source='/host_path2',
                    type='bind',
                    read_only=True,
                    consistency='delegated'
                )
            ]
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '-e', EENV_ON_LINUX + '=1',
            '--label', 'riptide=1',
            '--mount', 'type=bind,dst=/container_path,src=/host_path,ro=0,consistency=delegated',
            '--mount', 'type=bind,dst=/container_path2,src=/host_path2,ro=1,consistency=delegated',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    @mock.patch('platform.system', return_value='Linux')
    def test_set_named_volume_mount(self, system_mock: Mock):
        self.fix.set_named_volume_mount('name', '/container_path')
        self.fix.set_named_volume_mount('name2', '/container_path2', 'ro')

        # Test API build
        self.expected_api_base.update({
            'mounts': [
                Mount(
                    target='/container_path',
                    source='riptide__name',
                    type='volume',
                    read_only=False,
                    labels={RIPTIDE_DOCKER_LABEL_IS_RIPTIDE: "1"}
                ),
                Mount(
                    target='/container_path2',
                    source='riptide__name2',
                    type='volume',
                    read_only=True,
                    labels={RIPTIDE_DOCKER_LABEL_IS_RIPTIDE: "1"}
                )
            ],
            'environment': {
                EENV_ON_LINUX: '1',
                EENV_NAMED_VOLUMES: '/container_path:/container_path2'
            }
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '-e', EENV_ON_LINUX + '=1',
            '-e', EENV_NAMED_VOLUMES + '=/container_path:/container_path2',
            '--label', 'riptide=1',
            '--mount', 'type=volume,target=/container_path,src=riptide__name,ro=0,volume-label=riptide=1',
            '--mount', 'type=volume,target=/container_path2,src=riptide__name2,ro=1,volume-label=riptide=1',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    def test_set_port(self):
        self.fix.set_port(1234, 5678)
        self.fix.set_port(9876, 5432)

        # Test API build
        self.expected_api_base.update({
            'ports': {1234: 5678, 9876: 5432}
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '-p', '5678:1234',
            '-p', '5432:9876',
            '-e', EENV_ON_LINUX + '=1',
            '--label', 'riptide=1',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    def test_set_network(self):
        self.fix.set_network('name')

        # Test API build
        self.expected_api_base.update({
            'network': 'name'
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '--network', 'name',
            '-e', EENV_ON_LINUX + '=1',
            '--label', 'riptide=1',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    def test_set_use_host_network(self):
        self.fix.set_network('name')
        self.fix.set_use_host_network(True)

        # Test API build
        self.expected_api_base.update({
            'network_mode': 'host'
        })
        del self.expected_api_base['ports']
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '--network', 'host',
            '-e', EENV_ON_LINUX + '=1',
            '--label', 'riptide=1',
            IMAGE_NAME, COMMAND
        ]

        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    def test_set_name(self):
        self.fix.set_name('blubbeldiblub')

        # Test API build
        self.expected_api_base.update({
            'name': 'blubbeldiblub'
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '--name', 'blubbeldiblub',
            '-e', EENV_ON_LINUX + '=1',
            '--label', 'riptide=1',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    def test_set_entrypoint(self):
        self.fix.set_entrypoint('/usr/bin/very-important-script')

        # Test API build
        self.expected_api_base.update({
            'entrypoint': ['/usr/bin/very-important-script']
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '--entrypoint', '/usr/bin/very-important-script',
            '-e', EENV_ON_LINUX + '=1',
            '--label', 'riptide=1',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    def test_set_args(self):
        self.fix.set_args(['arg1', 'arg2', 'arg3'])

        # Test API build
        self.expected_api_base.update({
            'command': COMMAND + ' "arg1" "arg2" "arg3"'
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '-e', EENV_ON_LINUX + '=1',
            '--label', 'riptide=1',
            IMAGE_NAME, COMMAND + ' "arg1" "arg2" "arg3"'
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    def test_set_args_command_is_list(self):
        fix = ContainerBuilder(image=IMAGE_NAME, command=[COMMAND, "arg0"])
        fix.set_args(['arg1', 'arg2', 'arg3'])

        # Test API build
        self.expected_api_base.update({
            'command': [COMMAND, 'arg0', 'arg1', 'arg2', 'arg3']
        })
        actual_api = fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '-e', EENV_ON_LINUX + '=1',
            '--label', 'riptide=1',
            IMAGE_NAME, COMMAND + ' "arg0" "arg1" "arg2" "arg3"'
        ]
        actual_cli = fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    def test_set_hostname(self):
        self.fix.set_hostname('dubdub')

        # Test API build
        self.expected_api_base.update({
            'hostname': 'dubdub'
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '--hostname', 'dubdub',
            '-e', EENV_ON_LINUX + '=1',
            '--label', 'riptide=1',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    def test_set_workdir(self):
        self.fix.set_workdir('/tmp/blubbel')

        # Test API build
        self.expected_api_base.update({
            'working_dir': '/tmp/blubbel'
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '-w', '/tmp/blubbel',
            '-e', EENV_ON_LINUX + '=1',
            '--label', 'riptide=1',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    @mock.patch('riptide_engine_docker.container_builder.riptide_engine_docker_assets_dir',
                return_value=EADMOCK)
    @mock.patch('platform.system', return_value='Linux')
    def test_enable_riptide_entrypoint_orig_is_list(self, sys_mock: Mock, ead_mock: Mock):
        self.maxDiff = None

        image_config_mock = {'Entrypoint': ['cmd', 'arg1', 'arg2 with space']}
        self.fix.enable_riptide_entrypoint(image_config_mock)

        expected_entrypoint_host_path = os.path.join(EADMOCK, ENTRYPOINT_SH)
        # Test API build
        self.expected_api_base.update({
            'user': 0,
            'entrypoint': [ENTRYPOINT_CONTAINER_PATH],
            'mounts': [
                Mount(
                    target=ENTRYPOINT_CONTAINER_PATH,
                    source=expected_entrypoint_host_path,
                    type='bind',
                    read_only=True,
                    consistency='delegated'
                )],
            'environment': {
                EENV_ORIGINAL_ENTRYPOINT: 'cmd "arg1" "arg2 with space"',
                EENV_ON_LINUX: '1'
            }
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '--entrypoint', ENTRYPOINT_CONTAINER_PATH,
            '-u', '0',
            '-e', EENV_ON_LINUX + '=1',
            '-e', EENV_ORIGINAL_ENTRYPOINT + '=cmd "arg1" "arg2 with space"',
            '--label', 'riptide=1',
            '--mount', f'type=bind,dst={ENTRYPOINT_CONTAINER_PATH},src={expected_entrypoint_host_path},ro=1',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    @mock.patch('riptide_engine_docker.container_builder.riptide_engine_docker_assets_dir',
                return_value=EADMOCK)
    @mock.patch('platform.system', return_value='Linux')
    def test_enable_riptide_entrypoint_orig_is_string(self, sys_mock: Mock, ead_mock: Mock):
        self.maxDiff = None

        expected_sh = '/bin/sh -c '
        ep_value = 'entrypoint is a string'
        image_config_mock = {'Entrypoint': ep_value}
        self.fix.enable_riptide_entrypoint(image_config_mock)

        expected_entrypoint_host_path = os.path.join(EADMOCK, ENTRYPOINT_SH)
        # Test API build
        self.expected_api_base.update({
            'user': 0,
            'entrypoint': [ENTRYPOINT_CONTAINER_PATH],
            'mounts': [
                Mount(
                    target=ENTRYPOINT_CONTAINER_PATH,
                    source=expected_entrypoint_host_path,
                    type='bind',
                    read_only=True,
                    consistency='delegated'
                )],
            'environment': {
                EENV_ORIGINAL_ENTRYPOINT: expected_sh + ep_value,
                EENV_DONT_RUN_CMD: 'true',
                EENV_ON_LINUX: '1'
            }
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '--entrypoint', ENTRYPOINT_CONTAINER_PATH,
            '-u', '0',
            '-e', EENV_ON_LINUX + '=1',
            '-e', EENV_ORIGINAL_ENTRYPOINT + '=' + expected_sh + ep_value,
            '-e', EENV_DONT_RUN_CMD + '=true',
            '--label', 'riptide=1',
            '--mount', f'type=bind,dst={ENTRYPOINT_CONTAINER_PATH},src={expected_entrypoint_host_path},ro=1',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    @mock.patch('riptide_engine_docker.container_builder.riptide_engine_docker_assets_dir',
                return_value=EADMOCK)
    @mock.patch('platform.system', return_value='Linux')
    def test_enable_riptide_entrypoint_orig_no(self, sys_mock: Mock, ead_mock: Mock):
        self.maxDiff = None

        image_config_mock = {'Entrypoint': None}
        self.fix.enable_riptide_entrypoint(image_config_mock)

        expected_entrypoint_host_path = os.path.join(EADMOCK, ENTRYPOINT_SH)
        # Test API build
        self.expected_api_base.update({
            'user': 0,
            'entrypoint': [ENTRYPOINT_CONTAINER_PATH],
            'mounts': [
                Mount(
                    target=ENTRYPOINT_CONTAINER_PATH,
                    source=expected_entrypoint_host_path,
                    type='bind',
                    read_only=True,
                    consistency='delegated'
                )],
            'environment': {
                EENV_ORIGINAL_ENTRYPOINT: '',
                EENV_ON_LINUX: '1'
            }
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '--entrypoint', ENTRYPOINT_CONTAINER_PATH,
            '-u', '0',
            '-e', EENV_ON_LINUX + '=1',
            '-e', EENV_ORIGINAL_ENTRYPOINT + '=',
            '--label', 'riptide=1',
            '--mount', f'type=bind,dst={ENTRYPOINT_CONTAINER_PATH},src={expected_entrypoint_host_path},ro=1',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    @mock.patch('riptide_engine_docker.container_builder.riptide_engine_docker_assets_dir',
                return_value=EADMOCK)
    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('riptide_engine_docker.container_builder.getuid', return_value=9898)
    @mock.patch('riptide_engine_docker.container_builder.getgid', return_value=8989)
    @mock.patch('riptide_engine_docker.container_builder.get_localhost_hosts', return_value=GET_LOCALHOSTS_HOSTS_RETURN)
    def test_init_from_service_current_user(self, *args, **kwargs):
        self.maxDiff = None

        service_stub = YamlConfigDocumentStub.make({
            '$name': 'SERVICENAME',
            'roles': [],
            'run_as_current_user': True,
            'dont_create_user': False,
            'logging': {
                'commands': {
                    'name1': 'command1',
                    'name2': 'command2'
                }
            }
        })
        config_stub = YamlConfigDocumentStub.make({
            'performance': {
                'dont_sync_named_volumes_with_host': False,
                'dont_sync_unimportant_src': False
            }
        })
        project_stub = ProjectStub.make({
            'name': 'PROJECTNAME'
        }, parent=config_stub)

        service_stub.collect_ports = MagicMock(return_value={
            1234: 5678,
            9876: 5432
        })
        service_stub.collect_volumes = MagicMock(return_value={
            'host1': {'bind': 'bind1', 'mode': 'ro', 'name': 'namedvolume'},
            'host2': {'bind': 'bind2', 'mode': 'rw'},
        })
        service_stub.collect_environment = MagicMock(return_value={
            'key1': 'value1',
            'key2': 'value2'
        })
        service_stub.get_project = MagicMock(return_value=project_stub)
        config_stub.freeze()
        project_stub.freeze()
        service_stub.freeze()

        image_config_mock = {'Entrypoint': '', 'User': '12345'}

        self.fix.init_from_service(service_stub, image_config_mock)

        expected_entrypoint_host_path = os.path.join(EADMOCK, ENTRYPOINT_SH)
        # Test API build
        self.expected_api_base.update({
            'user': 0,
            'entrypoint': [ENTRYPOINT_CONTAINER_PATH],
            'ports': {
                1234: 5678,
                9876: 5432
            },
            'mounts': [
                Mount(
                    target=ENTRYPOINT_CONTAINER_PATH,
                    source=expected_entrypoint_host_path,
                    type='bind',
                    read_only=True,
                    consistency='delegated'
                ),
                Mount(
                    target='bind1',
                    source='host1',
                    type='bind',
                    read_only=True,
                    consistency='delegated'
                ),
                Mount(
                    target='bind2',
                    source='host2',
                    type='bind',
                    read_only=False,
                    consistency='delegated'
                )
            ],
            'environment': {
                EENV_ORIGINAL_ENTRYPOINT: '',
                EENV_COMMAND_LOG_PREFIX + 'name1': 'command1',
                EENV_COMMAND_LOG_PREFIX + 'name2': 'command2',
                EENV_USER: '9898',
                EENV_GROUP: '8989',
                EENV_RUN_MAIN_CMD_AS_USER: 'yes',
                'key1': 'value1',
                'key2': 'value2',
                EENV_ON_LINUX: '1',
                EENV_HOST_SYSTEM_HOSTNAMES: ' '.join(GET_LOCALHOSTS_HOSTS_RETURN),
                EENV_OVERLAY_TARGETS: ''
            },
            'labels': {
                RIPTIDE_DOCKER_LABEL_IS_RIPTIDE: '1',
                RIPTIDE_DOCKER_LABEL_MAIN: '0',
                RIPTIDE_DOCKER_LABEL_PROJECT: 'PROJECTNAME',
                RIPTIDE_DOCKER_LABEL_SERVICE: 'SERVICENAME'
            }
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '-p', '5678:1234',
            '-p', '5432:9876',
            '--entrypoint', ENTRYPOINT_CONTAINER_PATH,
            '-u', '0',
            '-e', EENV_ON_LINUX + '=1',
            '-e', EENV_ORIGINAL_ENTRYPOINT + '=',
            '-e', EENV_HOST_SYSTEM_HOSTNAMES + '=' + ' '.join(GET_LOCALHOSTS_HOSTS_RETURN),
            '-e', 'key1=value1',
            '-e', 'key2=value2',
            '-e', EENV_OVERLAY_TARGETS + '=',
            '-e', EENV_COMMAND_LOG_PREFIX + 'name1=command1',
            '-e', EENV_COMMAND_LOG_PREFIX + 'name2=command2',
            '-e', EENV_USER + '=9898',
            '-e', EENV_GROUP + '=8989',
            '-e', EENV_RUN_MAIN_CMD_AS_USER + '=yes',
            '--label', RIPTIDE_DOCKER_LABEL_IS_RIPTIDE + '=1',
            '--label', RIPTIDE_DOCKER_LABEL_PROJECT + '=PROJECTNAME',
            '--label', RIPTIDE_DOCKER_LABEL_SERVICE + '=SERVICENAME',
            '--label', RIPTIDE_DOCKER_LABEL_MAIN + '=0',
            '--mount', f'type=bind,dst={ENTRYPOINT_CONTAINER_PATH},src={expected_entrypoint_host_path},ro=1',
            '--mount', f'type=bind,dst=bind1,src=host1,ro=1',
            '--mount', f'type=bind,dst=bind2,src=host2,ro=0',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    @mock.patch('riptide_engine_docker.container_builder.riptide_engine_docker_assets_dir',
                return_value=EADMOCK)
    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('riptide_engine_docker.container_builder.getuid', return_value=9898)
    @mock.patch('riptide_engine_docker.container_builder.getgid', return_value=8989)
    @mock.patch('riptide_engine_docker.container_builder.get_localhost_hosts', return_value=GET_LOCALHOSTS_HOSTS_RETURN)
    def test_init_from_service_current_user_main_service(self, *args, **kwargs):
        self.maxDiff = None

        service_stub = YamlConfigDocumentStub.make({
            '$name': 'SERVICENAME',
            'roles': ['main'],
            'run_as_current_user': True,
            'dont_create_user': False
        })
        config_stub = YamlConfigDocumentStub.make({
            'performance': {
                'dont_sync_named_volumes_with_host': False,
                'dont_sync_unimportant_src': False
            }
        })
        project_stub = ProjectStub.make({
            'name': 'PROJECTNAME'
        }, parent=config_stub)

        service_stub.collect_ports = MagicMock(return_value={})
        service_stub.collect_volumes = MagicMock(return_value={})
        service_stub.collect_environment = MagicMock(return_value={})
        service_stub.get_project = MagicMock(return_value=project_stub)
        config_stub.freeze()
        project_stub.freeze()
        service_stub.freeze()

        image_config_mock = {'Entrypoint': '', 'User': '12345'}

        self.fix.init_from_service(service_stub, image_config_mock)

        expected_entrypoint_host_path = os.path.join(EADMOCK, ENTRYPOINT_SH)
        # Test API build
        self.expected_api_base.update({
            'user': 0,
            'entrypoint': [ENTRYPOINT_CONTAINER_PATH],
            'mounts': [
                Mount(
                    target=ENTRYPOINT_CONTAINER_PATH,
                    source=expected_entrypoint_host_path,
                    type='bind',
                    read_only=True,
                    consistency='delegated'
                )
            ],
            'environment': {
                EENV_ORIGINAL_ENTRYPOINT: '',
                EENV_USER: '9898',
                EENV_GROUP: '8989',
                EENV_RUN_MAIN_CMD_AS_USER: 'yes',
                EENV_ON_LINUX: '1',
                EENV_HOST_SYSTEM_HOSTNAMES: ' '.join(GET_LOCALHOSTS_HOSTS_RETURN),
                EENV_OVERLAY_TARGETS: '',
            },
            'labels': {
                RIPTIDE_DOCKER_LABEL_IS_RIPTIDE: '1',
                RIPTIDE_DOCKER_LABEL_MAIN: '1',
                RIPTIDE_DOCKER_LABEL_PROJECT: 'PROJECTNAME',
                RIPTIDE_DOCKER_LABEL_SERVICE: 'SERVICENAME'
            }
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '--entrypoint', ENTRYPOINT_CONTAINER_PATH,
            '-u', '0',
            '-e', EENV_ON_LINUX + '=1',
            '-e', EENV_ORIGINAL_ENTRYPOINT + '=',
            '-e', EENV_HOST_SYSTEM_HOSTNAMES + '=' + ' '.join(GET_LOCALHOSTS_HOSTS_RETURN),
            '-e', EENV_OVERLAY_TARGETS + '=',
            '-e', EENV_USER + '=9898',
            '-e', EENV_GROUP + '=8989',
            '-e', EENV_RUN_MAIN_CMD_AS_USER + '=yes',
            '--label', RIPTIDE_DOCKER_LABEL_IS_RIPTIDE + '=1',
            '--label', RIPTIDE_DOCKER_LABEL_PROJECT + '=PROJECTNAME',
            '--label', RIPTIDE_DOCKER_LABEL_SERVICE + '=SERVICENAME',
            '--label', RIPTIDE_DOCKER_LABEL_MAIN + '=1',
            '--mount', f'type=bind,dst={ENTRYPOINT_CONTAINER_PATH},src={expected_entrypoint_host_path},ro=1',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    @mock.patch('riptide_engine_docker.container_builder.riptide_engine_docker_assets_dir',
                return_value=EADMOCK)
    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('riptide_engine_docker.container_builder.getuid', return_value=9898)
    @mock.patch('riptide_engine_docker.container_builder.getgid', return_value=8989)
    @mock.patch('riptide_engine_docker.container_builder.get_localhost_hosts', return_value=GET_LOCALHOSTS_HOSTS_RETURN)
    def test_init_from_service_no_current_user_but_set(self, *args, **kwargs):
        self.maxDiff = None

        service_stub = YamlConfigDocumentStub.make({
            '$name': 'SERVICENAME',
            'roles': ['main'],
            'run_as_current_user': False,
            'dont_create_user': False
        })
        config_stub = YamlConfigDocumentStub.make({
            'performance': {
                'dont_sync_named_volumes_with_host': False,
                'dont_sync_unimportant_src': False
            }
        })
        project_stub = ProjectStub.make({
            'name': 'PROJECTNAME'
        }, parent=config_stub)

        service_stub.collect_ports = MagicMock(return_value={})
        service_stub.collect_volumes = MagicMock(return_value={})
        service_stub.collect_environment = MagicMock(return_value={})
        service_stub.get_project = MagicMock(return_value=project_stub)

        image_config_mock = {'Entrypoint': '', 'User': '12345'}

        config_stub.freeze()
        project_stub.freeze()
        service_stub.freeze()

        self.fix.init_from_service(service_stub, image_config_mock)

        expected_entrypoint_host_path = os.path.join(EADMOCK, ENTRYPOINT_SH)
        # Test API build
        self.expected_api_base.update({
            'user': 0,
            'entrypoint': [ENTRYPOINT_CONTAINER_PATH],
            'mounts': [
                Mount(
                    target=ENTRYPOINT_CONTAINER_PATH,
                    source=expected_entrypoint_host_path,
                    type='bind',
                    read_only=True,
                    consistency='delegated'
                )
            ],
            'environment': {
                EENV_ORIGINAL_ENTRYPOINT: '',
                EENV_USER: '9898',
                EENV_USER_RUN: '12345',
                EENV_GROUP: '8989',
                EENV_RUN_MAIN_CMD_AS_USER: 'yes',
                EENV_ON_LINUX: '1',
                EENV_HOST_SYSTEM_HOSTNAMES: ' '.join(GET_LOCALHOSTS_HOSTS_RETURN),
                EENV_OVERLAY_TARGETS: ''
            },
            'labels': {
                RIPTIDE_DOCKER_LABEL_IS_RIPTIDE: '1',
                RIPTIDE_DOCKER_LABEL_MAIN: '1',
                RIPTIDE_DOCKER_LABEL_PROJECT: 'PROJECTNAME',
                RIPTIDE_DOCKER_LABEL_SERVICE: 'SERVICENAME'
            }
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '--entrypoint', ENTRYPOINT_CONTAINER_PATH,
            '-u', '0',
            '-e', EENV_ON_LINUX + '=1',
            '-e', EENV_ORIGINAL_ENTRYPOINT + '=',
            '-e', EENV_HOST_SYSTEM_HOSTNAMES + '=' + ' '.join(GET_LOCALHOSTS_HOSTS_RETURN),
            '-e', EENV_OVERLAY_TARGETS + '=',
            '-e', EENV_USER + '=9898',
            '-e', EENV_GROUP + '=8989',
            '-e', EENV_RUN_MAIN_CMD_AS_USER + '=yes',
            '-e', EENV_USER_RUN + '=12345',
            '--label', RIPTIDE_DOCKER_LABEL_IS_RIPTIDE + '=1',
            '--label', RIPTIDE_DOCKER_LABEL_PROJECT + '=PROJECTNAME',
            '--label', RIPTIDE_DOCKER_LABEL_SERVICE + '=SERVICENAME',
            '--label', RIPTIDE_DOCKER_LABEL_MAIN + '=1',
            '--mount', f'type=bind,dst={ENTRYPOINT_CONTAINER_PATH},src={expected_entrypoint_host_path},ro=1',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    @mock.patch('riptide_engine_docker.container_builder.riptide_engine_docker_assets_dir',
                return_value=EADMOCK)
    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('riptide_engine_docker.container_builder.getuid', return_value=9898)
    @mock.patch('riptide_engine_docker.container_builder.getgid', return_value=8989)
    @mock.patch('riptide_engine_docker.container_builder.get_localhost_hosts', return_value=GET_LOCALHOSTS_HOSTS_RETURN)
    def test_init_from_service_no_current_user_root(self, *args, **kwargs):
        self.maxDiff = None

        service_stub = YamlConfigDocumentStub.make({
            '$name': 'SERVICENAME',
            'roles': ['main'],
            'run_as_current_user': False,
            'dont_create_user': False
        })
        config_stub = YamlConfigDocumentStub.make({
            'performance': {
                'dont_sync_named_volumes_with_host': False,
                'dont_sync_unimportant_src': False
            }
        })
        project_stub = ProjectStub.make({
            'name': 'PROJECTNAME'
        }, parent=config_stub)

        service_stub.collect_ports = MagicMock(return_value={})
        service_stub.collect_volumes = MagicMock(return_value={})
        service_stub.collect_environment = MagicMock(return_value={})
        service_stub.get_project = MagicMock(return_value=project_stub)

        image_config_mock = {'Entrypoint': '', 'User': ''}

        config_stub.freeze()
        project_stub.freeze()
        service_stub.freeze()

        self.fix.init_from_service(service_stub, image_config_mock)

        expected_entrypoint_host_path = os.path.join(EADMOCK, ENTRYPOINT_SH)
        # Test API build
        self.expected_api_base.update({
            'user': 0,
            'entrypoint': [ENTRYPOINT_CONTAINER_PATH],
            'mounts': [
                Mount(
                    target=ENTRYPOINT_CONTAINER_PATH,
                    source=expected_entrypoint_host_path,
                    type='bind',
                    read_only=True,
                    consistency='delegated'
                )
            ],
            'environment': {
                EENV_ORIGINAL_ENTRYPOINT: '',
                EENV_USER: '9898',
                EENV_GROUP: '8989',
                EENV_ON_LINUX: '1',
                EENV_HOST_SYSTEM_HOSTNAMES: ' '.join(GET_LOCALHOSTS_HOSTS_RETURN),
                EENV_OVERLAY_TARGETS: ''
            },
            'labels': {
                RIPTIDE_DOCKER_LABEL_IS_RIPTIDE: '1',
                RIPTIDE_DOCKER_LABEL_MAIN: '1',
                RIPTIDE_DOCKER_LABEL_PROJECT: 'PROJECTNAME',
                RIPTIDE_DOCKER_LABEL_SERVICE: 'SERVICENAME'
            }
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '--entrypoint', ENTRYPOINT_CONTAINER_PATH,
            '-u', '0',
            '-e', EENV_ON_LINUX + '=1',
            '-e', EENV_ORIGINAL_ENTRYPOINT + '=',
            '-e', EENV_HOST_SYSTEM_HOSTNAMES + '=' + ' '.join(GET_LOCALHOSTS_HOSTS_RETURN),
            '-e', EENV_OVERLAY_TARGETS + '=',
            '-e', EENV_USER + '=9898',
            '-e', EENV_GROUP + '=8989',
            '--label', RIPTIDE_DOCKER_LABEL_IS_RIPTIDE + '=1',
            '--label', RIPTIDE_DOCKER_LABEL_PROJECT + '=PROJECTNAME',
            '--label', RIPTIDE_DOCKER_LABEL_SERVICE + '=SERVICENAME',
            '--label', RIPTIDE_DOCKER_LABEL_MAIN + '=1',
            '--mount', f'type=bind,dst={ENTRYPOINT_CONTAINER_PATH},src={expected_entrypoint_host_path},ro=1',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    @mock.patch('riptide_engine_docker.container_builder.riptide_engine_docker_assets_dir',
                return_value=EADMOCK)
    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('riptide_engine_docker.container_builder.getuid', return_value=9898)
    @mock.patch('riptide_engine_docker.container_builder.getgid', return_value=8989)
    @mock.patch('riptide_engine_docker.container_builder.get_localhost_hosts', return_value=GET_LOCALHOSTS_HOSTS_RETURN)
    def test_init_from_service_no_current_user_dont_create(self, *args, **kwargs):
        self.maxDiff = None

        service_stub = YamlConfigDocumentStub.make({
            '$name': 'SERVICENAME',
            'roles': ['main'],
            'run_as_current_user': False,
            'dont_create_user': True
        })
        config_stub = YamlConfigDocumentStub.make({
            'performance': {
                'dont_sync_named_volumes_with_host': False,
                'dont_sync_unimportant_src': False
            }
        })
        project_stub = ProjectStub.make({
            'name': 'PROJECTNAME'
        }, parent=config_stub)

        service_stub.collect_ports = MagicMock(return_value={})
        service_stub.collect_volumes = MagicMock(return_value={})
        service_stub.collect_environment = MagicMock(return_value={})
        service_stub.get_project = MagicMock(return_value=project_stub)

        image_config_mock = {'Entrypoint': '', 'User': ''}

        config_stub.freeze()
        project_stub.freeze()
        service_stub.freeze()

        self.fix.init_from_service(service_stub, image_config_mock)

        expected_entrypoint_host_path = os.path.join(EADMOCK, ENTRYPOINT_SH)
        # Test API build
        self.expected_api_base.update({
            'user': 0,
            'entrypoint': [ENTRYPOINT_CONTAINER_PATH],
            'mounts': [
                Mount(
                    target=ENTRYPOINT_CONTAINER_PATH,
                    source=expected_entrypoint_host_path,
                    type='bind',
                    read_only=True,
                    consistency='delegated'
                )
            ],
            'environment': {
                EENV_ORIGINAL_ENTRYPOINT: '',
                EENV_ON_LINUX: '1',
                EENV_HOST_SYSTEM_HOSTNAMES: ' '.join(GET_LOCALHOSTS_HOSTS_RETURN),
                EENV_OVERLAY_TARGETS: ''
            },
            'labels': {
                RIPTIDE_DOCKER_LABEL_IS_RIPTIDE: '1',
                RIPTIDE_DOCKER_LABEL_MAIN: '1',
                RIPTIDE_DOCKER_LABEL_PROJECT: 'PROJECTNAME',
                RIPTIDE_DOCKER_LABEL_SERVICE: 'SERVICENAME'
            }
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '--entrypoint', ENTRYPOINT_CONTAINER_PATH,
            '-u', '0',
            '-e', EENV_ON_LINUX + '=1',
            '-e', EENV_ORIGINAL_ENTRYPOINT + '=',
            '-e', EENV_HOST_SYSTEM_HOSTNAMES + '=' + ' '.join(GET_LOCALHOSTS_HOSTS_RETURN),
            '-e', EENV_OVERLAY_TARGETS + '=',
            '--label', RIPTIDE_DOCKER_LABEL_IS_RIPTIDE + '=1',
            '--label', RIPTIDE_DOCKER_LABEL_PROJECT + '=PROJECTNAME',
            '--label', RIPTIDE_DOCKER_LABEL_SERVICE + '=SERVICENAME',
            '--label', RIPTIDE_DOCKER_LABEL_MAIN + '=1',
            '--mount', f'type=bind,dst={ENTRYPOINT_CONTAINER_PATH},src={expected_entrypoint_host_path},ro=1',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    @mock.patch('riptide_engine_docker.container_builder.riptide_engine_docker_assets_dir',
                return_value=EADMOCK)
    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('riptide_engine_docker.container_builder.getuid', return_value=9898)
    @mock.patch('riptide_engine_docker.container_builder.getgid', return_value=8989)
    @mock.patch('riptide_engine_docker.container_builder.get_localhost_hosts', return_value=GET_LOCALHOSTS_HOSTS_RETURN)
    def test_init_from_service_named_volume_perf_options(self, *args, **kwargs):
        self.maxDiff = None

        service_stub = YamlConfigDocumentStub.make({
            '$name': 'SERVICENAME',
            'roles': [],
            'run_as_current_user': True,
            'dont_create_user': False
        })
        config_stub = YamlConfigDocumentStub.make({
            'performance': {
                # ENABLE FOR THIS TEST
                'dont_sync_named_volumes_with_host': True,
                'dont_sync_unimportant_src': False
            }
        })
        project_stub = ProjectStub.make({
            'name': 'PROJECTNAME'
        }, parent=config_stub)

        service_stub.collect_ports = MagicMock(return_value={})
        service_stub.collect_volumes = MagicMock(return_value={
            'host1': {'bind': 'bind1', 'mode': 'ro', 'name': 'namedvolume'},
            'host2': {'bind': 'bind2', 'mode': 'rw'},
        })
        service_stub.collect_environment = MagicMock(return_value={})
        service_stub.get_project = MagicMock(return_value=project_stub)

        image_config_mock = {'Entrypoint': '', 'User': '12345'}

        config_stub.freeze()
        project_stub.freeze()
        service_stub.freeze()

        self.fix.init_from_service(service_stub, image_config_mock)

        expected_entrypoint_host_path = os.path.join(EADMOCK, ENTRYPOINT_SH)
        # Test API build
        self.expected_api_base.update({
            'user': 0,
            'entrypoint': [ENTRYPOINT_CONTAINER_PATH],
            'ports': {},
            'mounts': [
                Mount(
                    target=ENTRYPOINT_CONTAINER_PATH,
                    source=expected_entrypoint_host_path,
                    type='bind',
                    read_only=True,
                    consistency='delegated'
                ),
                Mount(
                    target='bind1',
                    source='riptide__namedvolume',
                    type='volume',
                    read_only=True,
                    labels={'riptide' : '1'}
                ),
                Mount(
                    target='bind2',
                    source='host2',
                    type='bind',
                    read_only=False,
                    consistency='delegated'
                )
            ],
            'environment': {
                EENV_ORIGINAL_ENTRYPOINT: '',
                EENV_USER: '9898',
                EENV_GROUP: '8989',
                EENV_RUN_MAIN_CMD_AS_USER: 'yes',
                EENV_ON_LINUX: '1',
                EENV_HOST_SYSTEM_HOSTNAMES: ' '.join(GET_LOCALHOSTS_HOSTS_RETURN),
                EENV_OVERLAY_TARGETS: '',
                EENV_NAMED_VOLUMES: 'bind1'
            },
            'labels': {
                RIPTIDE_DOCKER_LABEL_IS_RIPTIDE: '1',
                RIPTIDE_DOCKER_LABEL_MAIN: '0',
                RIPTIDE_DOCKER_LABEL_PROJECT: 'PROJECTNAME',
                RIPTIDE_DOCKER_LABEL_SERVICE: 'SERVICENAME'
            }
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '--entrypoint', ENTRYPOINT_CONTAINER_PATH,
            '-u', '0',
            '-e', EENV_ON_LINUX + '=1',
            '-e', EENV_ORIGINAL_ENTRYPOINT + '=',
            '-e', EENV_HOST_SYSTEM_HOSTNAMES + '=' + ' '.join(GET_LOCALHOSTS_HOSTS_RETURN),
            '-e', EENV_OVERLAY_TARGETS + '=',
            '-e', EENV_USER + '=9898',
            '-e', EENV_GROUP + '=8989',
            '-e', EENV_RUN_MAIN_CMD_AS_USER + '=yes',
            '-e', EENV_NAMED_VOLUMES + '=bind1',
            '--label', RIPTIDE_DOCKER_LABEL_IS_RIPTIDE + '=1',
            '--label', RIPTIDE_DOCKER_LABEL_PROJECT + '=PROJECTNAME',
            '--label', RIPTIDE_DOCKER_LABEL_SERVICE + '=SERVICENAME',
            '--label', RIPTIDE_DOCKER_LABEL_MAIN + '=0',
            '--mount', f'type=bind,dst={ENTRYPOINT_CONTAINER_PATH},src={expected_entrypoint_host_path},ro=1',
            '--mount', 'type=volume,target=bind1,src=riptide__namedvolume,ro=1,volume-label=riptide=1',
            '--mount', f'type=bind,dst=bind2,src=host2,ro=0',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    @mock.patch('riptide_engine_docker.container_builder.find_open_port_starting_at',
                return_value=9876)
    def test_service_add_main_port(self, find_open_port_starting_at_mock: Mock):

        service_stub = YamlConfigDocumentStub.make({
            'port': 4536
        })

        service_stub.freeze()

        self.fix.service_add_main_port(service_stub)

        find_open_port_starting_at_mock.assert_called_once_with(DOCKER_ENGINE_HTTP_PORT_BND_START)

        # Test API build
        self.expected_api_base.update({
            'ports': {
                4536: 9876
            },
            'labels': {
                RIPTIDE_DOCKER_LABEL_IS_RIPTIDE: '1',
                RIPTIDE_DOCKER_LABEL_HTTP_PORT: '9876',
            }
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '-p', '9876:4536',
            '-e', EENV_ON_LINUX + '=1',
            '--label', RIPTIDE_DOCKER_LABEL_IS_RIPTIDE + '=1',
            '--label', RIPTIDE_DOCKER_LABEL_HTTP_PORT + '=9876',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    @mock.patch('riptide_engine_docker.container_builder.riptide_engine_docker_assets_dir',
                return_value=EADMOCK)
    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('riptide_engine_docker.container_builder.get_localhost_hosts', return_value=GET_LOCALHOSTS_HOSTS_RETURN)
    def test_init_from_command(self, *args, **kwargs):
        self.maxDiff = None

        config_stub = YamlConfigDocumentStub.make({
            'performance': {
                'dont_sync_named_volumes_with_host': False,
                'dont_sync_unimportant_src': False
            }
        })
        project_stub = YamlConfigDocumentStub.make({}, parent=config_stub)
        command_stub = YamlConfigDocumentStub.make({
            '$name': 'COMMANDNAME'
        })
        command_stub.get_project = MagicMock(return_value=project_stub)
        command_stub.collect_volumes = MagicMock(return_value={
            'host1': {'bind': 'bind1', 'mode': 'ro', 'name': 'namedvolume'},
            'host2': {'bind': 'bind2', 'mode': 'rw'},
        })
        command_stub.collect_environment = MagicMock(return_value={
            'key1': 'value1',
            'key2': 'value2'
        })

        image_config_mock = {'Entrypoint': '', 'User': '12345'}
        config_stub.freeze()
        project_stub.freeze()
        command_stub.freeze()

        self.fix.init_from_command(command_stub, image_config_mock)

        expected_entrypoint_host_path = os.path.join(EADMOCK, ENTRYPOINT_SH)
        # Test API build
        self.expected_api_base.update({
            'user': 0,
            'entrypoint': [ENTRYPOINT_CONTAINER_PATH],
            'mounts': [
                Mount(
                    target=ENTRYPOINT_CONTAINER_PATH,
                    source=expected_entrypoint_host_path,
                    type='bind',
                    read_only=True,
                    consistency='delegated'
                ),
                Mount(
                    target='bind1',
                    source='host1',
                    type='bind',
                    read_only=True,
                    consistency='delegated'
                ),
                Mount(
                    target='bind2',
                    source='host2',
                    type='bind',
                    read_only=False,
                    consistency='delegated'
                )
            ],
            'environment': {
                EENV_ORIGINAL_ENTRYPOINT: '',
                'key1': 'value1',
                'key2': 'value2',
                EENV_ON_LINUX: '1',
                EENV_HOST_SYSTEM_HOSTNAMES: ' '.join(GET_LOCALHOSTS_HOSTS_RETURN),
                EENV_OVERLAY_TARGETS: ''
            }
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '--entrypoint', ENTRYPOINT_CONTAINER_PATH,
            '-u', '0',
            '-e', EENV_ON_LINUX + '=1',
            '-e', EENV_ORIGINAL_ENTRYPOINT + '=',
            '-e', EENV_HOST_SYSTEM_HOSTNAMES + '=' + ' '.join(GET_LOCALHOSTS_HOSTS_RETURN),
            '-e', 'key1=value1',
            '-e', 'key2=value2',
            '-e', EENV_OVERLAY_TARGETS + '=',
            '--label', RIPTIDE_DOCKER_LABEL_IS_RIPTIDE + '=1',
            '--mount', f'type=bind,dst={ENTRYPOINT_CONTAINER_PATH},src={expected_entrypoint_host_path},ro=1',
            '--mount', f'type=bind,dst=bind1,src=host1,ro=1',
            '--mount', f'type=bind,dst=bind2,src=host2,ro=0',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    @mock.patch('riptide_engine_docker.container_builder.riptide_engine_docker_assets_dir',
                return_value=EADMOCK)
    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('riptide_engine_docker.container_builder.get_localhost_hosts', return_value=GET_LOCALHOSTS_HOSTS_RETURN)
    def test_init_from_command_named_volume_perf_options(self, *args, **kwargs):
        self.maxDiff = None

        config_stub = YamlConfigDocumentStub.make({
            'performance': {
                # ENABLED FOR THIS TEST:
                'dont_sync_named_volumes_with_host': True,
                'dont_sync_unimportant_src': False
            }
        })
        project_stub = YamlConfigDocumentStub.make({}, parent=config_stub)
        command_stub = YamlConfigDocumentStub.make({
            '$name': 'COMMANDNAME'
        })
        command_stub.get_project = MagicMock(return_value=project_stub)
        command_stub.collect_volumes = MagicMock(return_value={
            'host1': {'bind': 'bind1', 'mode': 'ro', 'name': 'namedvolume'},
            'host2': {'bind': 'bind2', 'mode': 'rw'},
        })
        command_stub.collect_environment = MagicMock(return_value={})
        image_config_mock = {'Entrypoint': '', 'User': '12345'}
        config_stub.freeze()
        project_stub.freeze()
        command_stub.freeze()

        self.fix.init_from_command(command_stub, image_config_mock)

        expected_entrypoint_host_path = os.path.join(EADMOCK, ENTRYPOINT_SH)
        # Test API build
        self.expected_api_base.update({
            'user': 0,
            'entrypoint': [ENTRYPOINT_CONTAINER_PATH],
            'mounts': [
                Mount(
                    target=ENTRYPOINT_CONTAINER_PATH,
                    source=expected_entrypoint_host_path,
                    type='bind',
                    read_only=True,
                    consistency='delegated'
                ),
                Mount(
                    target='bind1',
                    source='riptide__namedvolume',
                    type='volume',
                    read_only=True,
                    labels={'riptide': '1'}
                ),
                Mount(
                    target='bind2',
                    source='host2',
                    type='bind',
                    read_only=False,
                    consistency='delegated'
                )
            ],
            'environment': {
                EENV_ORIGINAL_ENTRYPOINT: '',
                EENV_ON_LINUX: '1',
                EENV_HOST_SYSTEM_HOSTNAMES: ' '.join(GET_LOCALHOSTS_HOSTS_RETURN),
                EENV_NAMED_VOLUMES: 'bind1',
                EENV_OVERLAY_TARGETS: ''
            }
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '--entrypoint', ENTRYPOINT_CONTAINER_PATH,
            '-u', '0',
            '-e', EENV_ON_LINUX + '=1',
            '-e', EENV_ORIGINAL_ENTRYPOINT + '=',
            '-e', EENV_HOST_SYSTEM_HOSTNAMES + '=' + ' '.join(GET_LOCALHOSTS_HOSTS_RETURN),
            '-e', EENV_OVERLAY_TARGETS + '=',
            '-e', EENV_NAMED_VOLUMES + '=' + 'bind1',
            '--label', RIPTIDE_DOCKER_LABEL_IS_RIPTIDE + '=1',
            '--mount', f'type=bind,dst={ENTRYPOINT_CONTAINER_PATH},src={expected_entrypoint_host_path},ro=1',
            '--mount', 'type=volume,target=bind1,src=riptide__namedvolume,ro=1,volume-label=riptide=1',
            '--mount', f'type=bind,dst=bind2,src=host2,ro=0',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    @mock.patch('riptide_engine_docker.container_builder.riptide_engine_docker_assets_dir',
                return_value=EADMOCK)
    @mock.patch('platform.system', return_value='Linux')
    @mock.patch('riptide_engine_docker.container_builder.get_localhost_hosts', return_value=GET_LOCALHOSTS_HOSTS_RETURN)
    def test_init_from_command_unimportant_paths(self, *args, **kwargs):
        self.maxDiff = None

        config_stub = YamlConfigDocumentStub.make({
            'performance': {
                'dont_sync_named_volumes_with_host': False,
                # ENABLED FOR THIS TEST:
                'dont_sync_unimportant_src': True
            }
        })
        project_stub = YamlConfigDocumentStub.make({}, parent=config_stub)
        app_stub = YamlConfigDocumentStub.make({
            'unimportant_paths': [
                'unimportant_1', 'unimportant_2/subpath'
            ]
        }, parent=project_stub)
        command_stub = YamlConfigDocumentStub.make({
            '$name': 'COMMANDNAME'
        })
        command_stub.get_project = MagicMock(return_value=project_stub)
        command_stub.parent = MagicMock(return_value=app_stub)
        command_stub.collect_volumes = MagicMock(return_value={})
        command_stub.collect_environment = MagicMock(return_value={})
        image_config_mock = {'Entrypoint': '', 'User': '12345'}
        config_stub.freeze()
        project_stub.freeze()
        command_stub.freeze()
        app_stub.freeze()

        self.fix.init_from_command(command_stub, image_config_mock)

        expected_entrypoint_host_path = os.path.join(EADMOCK, ENTRYPOINT_SH)
        # Test API build
        self.expected_api_base.update({
            'cap_add': ['SYS_ADMIN'],
            'security_opt': ['apparmor:unconfined'],
            'user': 0,
            'entrypoint': [ENTRYPOINT_CONTAINER_PATH],
            'mounts': [
                Mount(
                    target=ENTRYPOINT_CONTAINER_PATH,
                    source=expected_entrypoint_host_path,
                    type='bind',
                    read_only=True,
                    consistency='delegated'
                )
            ],
            'environment': {
                EENV_ORIGINAL_ENTRYPOINT: '',
                EENV_ON_LINUX: '1',
                EENV_HOST_SYSTEM_HOSTNAMES: ' '.join(GET_LOCALHOSTS_HOSTS_RETURN),
                EENV_OVERLAY_TARGETS: '/src/unimportant_1:/src/unimportant_2/subpath'
            }
        })
        actual_api = self.fix.build_docker_api()
        self.assertDictEqual(actual_api, self.expected_api_base)

        # Test CLI build
        expected_cli = self.expected_cli_base + [
            '--entrypoint', ENTRYPOINT_CONTAINER_PATH,
            '-u', '0',
            '-e', EENV_ON_LINUX + '=1',
            '-e', EENV_ORIGINAL_ENTRYPOINT + '=',
            '-e', EENV_HOST_SYSTEM_HOSTNAMES + '=' + ' '.join(GET_LOCALHOSTS_HOSTS_RETURN),
            '-e', EENV_OVERLAY_TARGETS + '=/src/unimportant_1:/src/unimportant_2/subpath',
            '--label', RIPTIDE_DOCKER_LABEL_IS_RIPTIDE + '=1',
            '--mount', f'type=bind,dst={ENTRYPOINT_CONTAINER_PATH},src={expected_entrypoint_host_path},ro=1',
            '--cap-add=SYS_ADMIN',
            '--security-opt', 'apparmor:unconfined',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)
