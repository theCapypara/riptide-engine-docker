import os


def riptide_engine_docker_assets_dir():
    this_folder = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(this_folder, '..', 'assets')
