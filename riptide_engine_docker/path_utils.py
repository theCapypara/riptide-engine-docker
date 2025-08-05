from __future__ import annotations

import os

from riptide.config.document.command import Command
from riptide.config.document.project import Project
from riptide.config.files import path_in_project
from riptide.engine.abstract import ExecError

IMAGE = "alpine"
# TODO: Since permissions are always mapped to user->root under Windows, there won't be permission
#       problems under windows. We could probably just use the AbstractEngine implementation there.


def rm(engine, path, project: Project):
    """
    Removes path from the hosts file system using a Docker container running root.
    See AbstractEngine.path_rm for general usage.
    """
    # TODO: Safety checks, this function is potentially really dangerous right now
    if not path_in_project(path, project):
        raise PermissionError(f"Tried to delete a file/directory that is not within the project: {path}")
    if not os.path.exists(path):
        return
    name_of_file = os.path.basename(path)
    file_dir = os.path.abspath(os.path.join(path, ".."))
    command = Command(
        {
            "image": IMAGE,
            "command": f"rm -rf /cmd_target/{name_of_file}",
            "additional_volumes": {"target": {"host": file_dir, "container": "/cmd_target", "mode": "rw"}},
        }
    )
    command.validate()
    command.freeze()
    (exit_code, output) = engine.cmd_detached(project, command, run_as_root=True)
    if exit_code != 0:
        raise ExecError(f"Error removing the path ({str(exit_code)}) {path}: {output}")


def copy(engine, fromm, to, project: Project):
    """
    Copy files from the hosts file system using a Docker container running root.
    See AbstractEngine.path_copy for general usage.
    """
    if not path_in_project(to, project):
        raise PermissionError(f"Tried to copy into a path that is not within the project: {fromm} -> {to}")
    if not os.path.exists(fromm):
        raise OSError(f"Tried to copy a directory/file that does not exist: {fromm}")
    if not os.path.exists(os.path.dirname(to)):
        raise OSError(f"Tried to copy into a path that does not exist: {to}")
    command = Command(
        {
            "image": IMAGE,
            "command": "cp -a /copy_from/. /copy_to/",
            "additional_volumes": {
                "fromm": {"host": fromm, "container": "/copy_from", "mode": "ro"},
                "to": {"host": to, "container": "/copy_to", "mode": "rw"},
            },
        }
    )
    command.validate()
    command.freeze()
    (exit_code, output) = engine.cmd_detached(project, command, run_as_root=True)
    if exit_code != 0:
        raise ExecError(f"Error copying the directory ({str(exit_code)}) {fromm} -> {to}: {output}")
