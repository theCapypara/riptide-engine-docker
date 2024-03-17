import atexit
import sys

if sys.version_info < (3, 11):
    import pkg_resources
else:
    import importlib.resources

from contextlib import ExitStack


def riptide_engine_docker_assets_dir():
    if sys.version_info < (3, 11):
        return pkg_resources.resource_filename(__name__, 'assets')
    else:
        file_manager = ExitStack()
        atexit.register(file_manager.close)
        package_name = __name__.split(".")[0]
        ref = importlib.resources.files(package_name) / 'assets'
        path = file_manager.enter_context(importlib.resources.as_file(ref))
        return path
