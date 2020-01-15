import os
import unittest

from docker.types import Mount
from unittest import mock

from unittest.mock import Mock, MagicMock

from configcrunch.tests.test_utils import YamlConfigDocumentStub
from riptide.tests.stubs import ProjectStub
from riptide_engine_docker.container_builder import ContainerBuilder, ENTRYPOINT_SH, ENTRYPOINT_CONTAINER_PATH, \
    EENV_ORIGINAL_ENTRYPOINT, EENV_DONT_RUN_CMD, EENV_COMMAND_LOG_PREFIX, EENV_USER, EENV_GROUP, \
    EENV_RUN_MAIN_CMD_AS_USER, RIPTIDE_DOCKER_LABEL_IS_RIPTIDE, RIPTIDE_DOCKER_LABEL_MAIN, RIPTIDE_DOCKER_LABEL_PROJECT, \
    RIPTIDE_DOCKER_LABEL_SERVICE, RIPTIDE_DOCKER_LABEL_HTTP_PORT, EENV_USER_RUN, DOCKER_ENGINE_HTTP_PORT_BND_START, \
    EENV_ON_LINUX, EENV_HOST_SYSTEM_HOSTNAMES

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
            '-v', '/host_path:/container_path:rw',
            '-v', '/host_path2:/container_path2:ro',
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
            '-v', '/host_path:/container_path:rw:delegated',
            '-v', '/host_path2:/container_path2:ro:delegated',
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
            '-e', EENV_ON_LINUX + '=1',
            '--label', 'riptide=1',
            '-p', '5678:1234',
            '-p', '5432:9876',
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
            '-v', expected_entrypoint_host_path + ':' + ENTRYPOINT_CONTAINER_PATH + ':ro',
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
            '-v', expected_entrypoint_host_path + ':' + ENTRYPOINT_CONTAINER_PATH + ':ro',
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
            '-v', expected_entrypoint_host_path + ':' + ENTRYPOINT_CONTAINER_PATH + ':ro',
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

        service_stub = YamlConfigDocumentStub({
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
        service_stub.collect_ports = MagicMock(return_value={
            1234: 5678,
            9876: 5432
        })
        service_stub.collect_volumes = MagicMock(return_value={
            'host1': {'bind': 'bind1', 'mode': 'ro'},
            'host2': {'bind': 'bind2', 'mode': 'rw'},
        })
        service_stub.collect_environment = MagicMock(return_value={
            'key1': 'value1',
            'key2': 'value2'
        })
        service_stub.get_project = MagicMock(return_value=ProjectStub({
            'name': 'PROJECTNAME'
        }))

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
                EENV_HOST_SYSTEM_HOSTNAMES: ' '.join(GET_LOCALHOSTS_HOSTS_RETURN)
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
            '-e', 'key1=value1',
            '-e', 'key2=value2',
            '-e', EENV_COMMAND_LOG_PREFIX + 'name1=command1',
            '-e', EENV_COMMAND_LOG_PREFIX + 'name2=command2',
            '-e', EENV_USER + '=9898',
            '-e', EENV_GROUP + '=8989',
            '-e', EENV_RUN_MAIN_CMD_AS_USER + '=yes',
            '--label', RIPTIDE_DOCKER_LABEL_IS_RIPTIDE + '=1',
            '--label', RIPTIDE_DOCKER_LABEL_PROJECT + '=PROJECTNAME',
            '--label', RIPTIDE_DOCKER_LABEL_SERVICE + '=SERVICENAME',
            '--label', RIPTIDE_DOCKER_LABEL_MAIN + '=0',
            '-p', '5678:1234',
            '-p', '5432:9876',
            '-v', expected_entrypoint_host_path + ':' + ENTRYPOINT_CONTAINER_PATH + ':ro',
            '-v', 'host1:bind1:ro',
            '-v', 'host2:bind2:rw',
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

        service_stub = YamlConfigDocumentStub({
            '$name': 'SERVICENAME',
            'roles': ['main'],
            'run_as_current_user': True,
            'dont_create_user': False
        })
        service_stub.collect_ports = MagicMock(return_value={})
        service_stub.collect_volumes = MagicMock(return_value={})
        service_stub.collect_environment = MagicMock(return_value={})
        service_stub.get_project = MagicMock(return_value=ProjectStub({
            'name': 'PROJECTNAME'
        }))

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
                EENV_HOST_SYSTEM_HOSTNAMES: ' '.join(GET_LOCALHOSTS_HOSTS_RETURN)
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
            '-e', EENV_USER + '=9898',
            '-e', EENV_GROUP + '=8989',
            '-e', EENV_RUN_MAIN_CMD_AS_USER + '=yes',
            '--label', RIPTIDE_DOCKER_LABEL_IS_RIPTIDE + '=1',
            '--label', RIPTIDE_DOCKER_LABEL_PROJECT + '=PROJECTNAME',
            '--label', RIPTIDE_DOCKER_LABEL_SERVICE + '=SERVICENAME',
            '--label', RIPTIDE_DOCKER_LABEL_MAIN + '=1',
            '-v', expected_entrypoint_host_path + ':' + ENTRYPOINT_CONTAINER_PATH + ':ro',
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

        service_stub = YamlConfigDocumentStub({
            '$name': 'SERVICENAME',
            'roles': ['main'],
            'run_as_current_user': False,
            'dont_create_user': False
        })
        service_stub.collect_ports = MagicMock(return_value={})
        service_stub.collect_volumes = MagicMock(return_value={})
        service_stub.collect_environment = MagicMock(return_value={})
        service_stub.get_project = MagicMock(return_value=ProjectStub({
            'name': 'PROJECTNAME'
        }))

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
                EENV_USER_RUN: '12345',
                EENV_GROUP: '8989',
                EENV_RUN_MAIN_CMD_AS_USER: 'yes',
                EENV_ON_LINUX: '1',
                EENV_HOST_SYSTEM_HOSTNAMES: ' '.join(GET_LOCALHOSTS_HOSTS_RETURN)
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
            '-e', EENV_USER + '=9898',
            '-e', EENV_GROUP + '=8989',
            '-e', EENV_RUN_MAIN_CMD_AS_USER + '=yes',
            '-e', EENV_USER_RUN + '=12345',
            '--label', RIPTIDE_DOCKER_LABEL_IS_RIPTIDE + '=1',
            '--label', RIPTIDE_DOCKER_LABEL_PROJECT + '=PROJECTNAME',
            '--label', RIPTIDE_DOCKER_LABEL_SERVICE + '=SERVICENAME',
            '--label', RIPTIDE_DOCKER_LABEL_MAIN + '=1',
            '-v', expected_entrypoint_host_path + ':' + ENTRYPOINT_CONTAINER_PATH + ':ro',
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

        service_stub = YamlConfigDocumentStub({
            '$name': 'SERVICENAME',
            'roles': ['main'],
            'run_as_current_user': False,
            'dont_create_user': False
        })
        service_stub.collect_ports = MagicMock(return_value={})
        service_stub.collect_volumes = MagicMock(return_value={})
        service_stub.collect_environment = MagicMock(return_value={})
        service_stub.get_project = MagicMock(return_value=ProjectStub({
            'name': 'PROJECTNAME'
        }))

        image_config_mock = {'Entrypoint': '', 'User': ''}

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
                EENV_HOST_SYSTEM_HOSTNAMES: ' '.join(GET_LOCALHOSTS_HOSTS_RETURN)
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
            '-e', EENV_USER + '=9898',
            '-e', EENV_GROUP + '=8989',
            '--label', RIPTIDE_DOCKER_LABEL_IS_RIPTIDE + '=1',
            '--label', RIPTIDE_DOCKER_LABEL_PROJECT + '=PROJECTNAME',
            '--label', RIPTIDE_DOCKER_LABEL_SERVICE + '=SERVICENAME',
            '--label', RIPTIDE_DOCKER_LABEL_MAIN + '=1',
            '-v', expected_entrypoint_host_path + ':' + ENTRYPOINT_CONTAINER_PATH + ':ro',
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

        service_stub = YamlConfigDocumentStub({
            '$name': 'SERVICENAME',
            'roles': ['main'],
            'run_as_current_user': False,
            'dont_create_user': True
        })
        service_stub.collect_ports = MagicMock(return_value={})
        service_stub.collect_volumes = MagicMock(return_value={})
        service_stub.collect_environment = MagicMock(return_value={})
        service_stub.get_project = MagicMock(return_value=ProjectStub({
            'name': 'PROJECTNAME'
        }))

        image_config_mock = {'Entrypoint': '', 'User': ''}

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
                EENV_HOST_SYSTEM_HOSTNAMES: ' '.join(GET_LOCALHOSTS_HOSTS_RETURN)
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
            '--label', RIPTIDE_DOCKER_LABEL_IS_RIPTIDE + '=1',
            '--label', RIPTIDE_DOCKER_LABEL_PROJECT + '=PROJECTNAME',
            '--label', RIPTIDE_DOCKER_LABEL_SERVICE + '=SERVICENAME',
            '--label', RIPTIDE_DOCKER_LABEL_MAIN + '=1',
            '-v', expected_entrypoint_host_path + ':' + ENTRYPOINT_CONTAINER_PATH + ':ro',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)

    @mock.patch('riptide_engine_docker.container_builder.find_open_port_starting_at',
                return_value=9876)
    def test_service_add_main_port(self, find_open_port_starting_at_mock: Mock):

        service_stub = YamlConfigDocumentStub({
            'port': 4536
        })

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
            '-e', EENV_ON_LINUX + '=1',
            '--label', RIPTIDE_DOCKER_LABEL_IS_RIPTIDE + '=1',
            '--label', RIPTIDE_DOCKER_LABEL_HTTP_PORT + '=9876',
            '-p', '9876:4536',
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

        command_stub = YamlConfigDocumentStub({
            '$name': 'COMMANDNAME'
        })
        command_stub.collect_volumes = MagicMock(return_value={
            'host1': {'bind': 'bind1', 'mode': 'ro'},
            'host2': {'bind': 'bind2', 'mode': 'rw'},
        })
        command_stub.collect_environment = MagicMock(return_value={
            'key1': 'value1',
            'key2': 'value2'
        })

        image_config_mock = {'Entrypoint': '', 'User': '12345'}

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
                EENV_HOST_SYSTEM_HOSTNAMES: ' '.join(GET_LOCALHOSTS_HOSTS_RETURN)
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
            '--label', RIPTIDE_DOCKER_LABEL_IS_RIPTIDE + '=1',
            '-v', expected_entrypoint_host_path + ':' + ENTRYPOINT_CONTAINER_PATH + ':ro',
            '-v', 'host1:bind1:ro',
            '-v', 'host2:bind2:rw',
            IMAGE_NAME, COMMAND
        ]
        actual_cli = self.fix.build_docker_cli()
        self.assertListEqual(actual_cli, expected_cli)
