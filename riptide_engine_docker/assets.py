import atexit
import importlib.resources

from contextlib import ExitStack


def riptide_engine_docker_assets_dir():
    file_manager = ExitStack()
    atexit.register(file_manager.close)
    package_name = __name__.split(".")[0]
    ref = importlib.resources.files(package_name) / 'assets'
    path = file_manager.enter_context(importlib.resources.as_file(ref))
    return path
