# MIT License
#
# Copyright (c) [YEAR] [COPYRIGHT HOLDER]
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from dataclasses import dataclass

from sqlalchemy import Connection, text

from .exceptions import InvalidModuleStructureError
from .types import MigrationCallback, MigrationModule, MigrationStatement, MigrationStep


@dataclass
class MigrationCallbackPair:
    up: MigrationCallback
    down: MigrationCallback


def normalize_migration_steps(
    steps: MigrationStep | list[MigrationStep],
) -> list[MigrationCallbackPair]:
    """Convert migrations to sequence of tuple"""
    steps = _generic_steps_to_list(steps)
    return [_step_to_callback_pair(s) for s in steps]


def get_migration_name(mod: MigrationModule) -> str:
    """Extract migration name from the module

    Raises:
        InvalidModuleStructureError: If module does not have the `__name__` attribute
    """
    try:
        return mod.__name__
    except AttributeError:
        raise InvalidModuleStructureError(
            f"Module {mod} does not have __name__ attribute. "
            "Make sure that module is a valid Python module."
        )


def _generic_steps_to_list(steps: MigrationStep | list[MigrationStep]) -> list[MigrationStep]:
    """If steps is a single item list, convert it into the list of steps with single item"""
    if isinstance(steps, list):
        # nothing to do - list of steps
        return list(steps)
    else:
        # single step
        return [steps]


def _step_to_callback_pair(step: MigrationStep | None) -> MigrationCallbackPair:
    step_tuple = _step_to_tuple(step)
    up = _statement_to_callback(step_tuple[0])
    down = _statement_to_callback(step_tuple[1])
    return MigrationCallbackPair(up, down)


def _step_to_tuple(
    step: MigrationStep | None,
) -> tuple[MigrationStatement | None, MigrationStatement | None]:
    """Convert step to tuple format"""
    if step is None:
        return None, None
    elif isinstance(step, tuple):
        return step
    else:
        return step, None


def _statement_to_callback(stmt: MigrationStatement | None) -> MigrationCallback:
    """Check the type of the stmt. If it is the `str`, convert it into the callback"""

    if stmt is None:
        return _noop
    if callable(stmt):
        return stmt
    else:
        return _make_callback(stmt)


def _noop(_conn: Connection):
    pass


def _make_callback(stmt: str) -> MigrationCallback:
    # convert text statement into the callback
    def _callback(conn: Connection):
        conn.execute(text(stmt))

    return _callback
