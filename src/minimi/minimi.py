# MIT License
#
# Copyright (c) 2026 Authors and contributors listed in the AUTHORS file
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

from sa_values import SaValues
from sqlalchemy import Connection
from sqlalchemy.exc import DBAPIError

from .exceptions import InvalidModuleStructureError, MigrationFailedError
from .migrations import get_migration_name, MigrationCallbackPair, normalize_migration_steps
from .types import MigrationCallback, MigrationModule


class Minimi:
    """Apply or roll back migrations"""

    SA_VALUE_MIGRATION_KEY = "minimi.migration"

    def __init__(
        self,
        connection: Connection,
        migrations: list[MigrationModule],
        migration_value_key: str = SA_VALUE_MIGRATION_KEY,
    ):
        self.connection = connection
        self.migrations = migrations
        self._applied_migrations = SaValues(self.connection).multi_value_key(
            migration_value_key,
        )

    def apply(self):
        """Apply all unapplied migrations"""
        applied_migrations = set(self._applied_migrations.get_all())
        for mod in self.migrations:
            migration_name = get_migration_name(mod)
            if migration_name in applied_migrations:
                continue
            self._apply_migration(mod)

            try:
                self._applied_migrations.add(migration_name)
            except Exception:
                try:
                    self._rollback_migration(mod)
                except Exception:  # noqa
                    # TODO: log error and better exception catching
                    pass

                raise

    def rollback(self):
        """Roll back all migrations"""
        applied_migrations = set(self._applied_migrations.get_all())

        for m in reversed(self.migrations):
            migration_name = get_migration_name(m)
            if migration_name not in applied_migrations:
                continue
            self._rollback_migration(m)
            self._applied_migrations.delete(migration_name)

    def _apply_migration(self, mod: MigrationModule) -> None:
        """Apply a single migration module"""
        steps = self._get_normalized_steps(mod)
        applied_steps = []
        for step in steps:
            try:
                self._call_callback(step.up)
            except MigrationFailedError:
                for revert_step in reversed(applied_steps):
                    try:
                        self._call_callback(revert_step.down)
                    except MigrationFailedError:
                        # stop on rollback failure
                        break
                raise
            applied_steps.append(step)

    def _rollback_migration(self, mod: MigrationModule) -> None:
        """Roll back a single migration module"""
        steps = self._get_normalized_steps(mod)
        for step in reversed(steps):
            self._call_callback(step.down)

    def _call_callback(self, cbk: MigrationCallback | None):
        """Call the migration callback and handle DB related errors."""
        if cbk is None:
            return

        try:
            cbk(self.connection)
        except DBAPIError as err:
            raise MigrationFailedError from err

    @staticmethod
    def _get_normalized_steps(mod) -> list[MigrationCallbackPair]:
        try:
            return normalize_migration_steps(mod.MIGRATIONS)
        except AttributeError:
            raise InvalidModuleStructureError(
                f"Module {mod.__name__} does not have a MIGRATIONS attribute",
            )
