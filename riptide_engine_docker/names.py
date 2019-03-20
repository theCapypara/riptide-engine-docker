import os


def get_service_container_name(project_name: str, service_name: str):
    return 'riptide__' + project_name + '__' + service_name


def get_cmd_container_name(project_name: str, command_name: str):
    return 'riptide__' + project_name + '__cmd__' + command_name + '__' + str(os.getpid())


def get_network_name(project_name: str):
    return 'riptide__' + project_name
