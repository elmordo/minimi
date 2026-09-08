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
from typing import cast

from sa_values import SaValues
from sa_values.values import MultiValueKey
from sqlalchemy import Connection

from .types import MigrationModule, MigrationStep


class Minimi:
    """Apply or roll back migrations"""

    SA_VALUE_MIGRATION_KEY = "minimi.migration"

    def __init__(self, connection: Connection, migrations: list[MigrationModule]):
        self.connection = connection
        self.migrations = migrations

    def apply(self):
        """Apply all unapplied migrations"""
        applied_migrations = self._get_applied_migrations()
        mv = self._get_multi_value()
        applied = []
        for m in self.migrations:
            migration_name = self._get_migration_name(m)
            if migration_name not in applied_migrations:
                self._apply_migration(m)
                try:
                    mv.add(migration_name)
                except Exception:
                    for to_revert in reversed(applied):
                        try:
                            self._rollback_migration(to_revert)
                        except Exception:  # noqa
                            # TODO: log error and better exception catching
                            pass

                    raise
                applied.append(migration_name)

    def rollback(self):
        """Rollback all migrations"""
        applied_migrations = self._get_applied_migrations()
        mv = self._get_multi_value()
        for m in self.migrations:
            migration_name = self._get_migration_name(m)
            if migration_name in applied_migrations:
                self._rollback_migration(m)
                mv.delete(migration_name)

    def _get_applied_migrations(self) -> list[str]:
        """Get a list of applied migrations"""
        return self._get_multi_value().get_all()

    def _get_multi_value(self) -> MultiValueKey:
        return SaValues(self.connection).multi_value_key(self.SA_VALUE_MIGRATION_KEY)

    def _get_migration_name(self, mod: MigrationModule) -> str:
        """Get migration module name"""
        return mod.__name__

    def _apply_migration(self, mod: MigrationModule) -> None:
        raise NotImplementedError

    def _rollback_migration(self, mod: MigrationModule) -> None:
        raise NotImplementedError

    def _extract_miration_steps(self, mod: MigrationModule) -> list[MigrationStep]:
        """Extract migration steps from migration module"""
        if type(mod.MIGRATIONS) is list:
            # migration step list is returned as-is
            return cast(list[MigrationStep], mod.MIGRATIONS)
        else:
            # single migration step is wrapped in a list
            return [cast(MigrationStep, mod.MIGRATIONS)]
