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

from .types import MigrationCallback, MigrationModule, MigrationStatement, MigrationStep


@dataclass
class MigrationCallbackPair:
    up: MigrationCallback | None
    down: MigrationCallback | None


def normalize_migration_steps(
    steps: MigrationStep | list[MigrationStep],
) -> list[MigrationCallbackPair]:
    """Convert migrations to sequence of tuple"""
    steps = _generic_steps_to_list(steps)
    return [_step_to_callback_pair(s) for s in steps]


def get_migration_name(mod: MigrationModule) -> str:
    """Extract migration name from the module"""
    return mod.__name__


def _generic_steps_to_list(steps: MigrationStep | list[MigrationStep]) -> list[MigrationStep]:
    """If steps is a single item list, convert it into the list of steps with single item"""
    if isinstance(steps, list):
        # nothing to do - list of steps
        return list(steps)
    else:
        # single step
        return [steps]


def _step_to_callback_pair(step: MigrationStep) -> MigrationCallbackPair:
    up = None
    down = None

    step_tuple = _step_to_tuple(step)

    return MigrationCallbackPair(up, down)


def _step_to_tuple(
    step: MigrationStep,
) -> tuple[MigrationStatement | None, MigrationStatement | None]:
    """Convert step to tuple format"""
    if isinstance(step, tuple):
        return step
    else:
        return step, step


def _statement_to_callback(stmt: MigrationStatement) -> MigrationCallback:
    """Check the type of the stmt. If it is the `str`, convert it into the callback"""
    if callable(stmt):
        return stmt
    else:
        return _make_callback(stmt)


def _make_callback(stmt: str) -> MigrationCallback:
    # convert text statement into the callback
    def _callback(conn: Connection):
        conn.execute(text(stmt))

    return _callback
