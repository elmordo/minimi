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
from collections.abc import Callable
from typing import Protocol

from sqlalchemy import Connection


MigrationStatement = str | Callable[[Connection], None]
"""Single migration statement or callable with execution logic"""

MigrationStep = MigrationStatement | tuple[MigrationStatement, MigrationStatement]
"""One step of migration. One migration can contain multiple steps"""


class MigrationModule(Protocol):
    """Each migration module must contain list of migrations in the `MIGRATIONS` global variable."""

    __name__: str
    """Name of the migration module"""

    MIGRATIONS: MigrationStep | list[MigrationStep]
    """Migration step or list of migration steps. The container MUST be the `list`"""
