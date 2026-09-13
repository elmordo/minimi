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
import pytest
from sqlalchemy import inspect, text

from minimi import Minimi
from minimi.exceptions import InvalidModuleStructureError, MigrationFailedError


def test_apply_migrations(db_connection, db_migrations):
    """Tests applying valid migration modules to the database.

    Expected result: Creates database schema elements (e.g. 'users' table and columns)
    and records all migration names as applied in the tracking table.
    """
    minimi = Minimi(db_connection, db_migrations.success)
    minimi.apply()

    inspector = inspect(db_connection)
    tables = inspector.get_table_names()
    assert "users" in tables

    columns = [col["name"] for col in inspector.get_columns("users")]
    assert "id" in columns
    assert "name" in columns
    assert "email" in columns

    applied = minimi._applied_migrations.get_all()
    assert len(applied) == 2


def test_apply_migrations_idempotent(db_connection, db_migrations):
    """Tests applying migrations repeatedly in succession.

    Expected result: Second application has no effect on database schema and applied
    migrations list remains unchanged without duplicate execution.
    """
    minimi = Minimi(db_connection, db_migrations.success)
    minimi.apply()
    minimi.apply()

    inspector = inspect(db_connection)
    assert "users" in inspector.get_table_names()
    applied = minimi._applied_migrations.get_all()
    assert len(applied) == 2


def test_apply_invalid_migrations(db_connection, db_migrations):
    """Tests applying migrations containing a failing step/statement.

    Expected result: Raises `MigrationFailedError`, records only successful migrations
    prior to failure, and does not record the failed migration.
    """
    minimi = Minimi(db_connection, db_migrations.failure)
    with pytest.raises(MigrationFailedError):
        minimi.apply()

    # Verify that the failed migration (m03F) was not recorded as applied
    applied = minimi._applied_migrations.get_all()
    # m01 and m02 succeeded and were recorded before m03 failed
    assert len(applied) == 2


def test_rollback_migrations(db_connection, db_migrations):
    """Tests rolling back previously applied migrations.

    Expected result: Reverts database schema modifications (e.g. drops 'users' table)
    and clears recorded migrations from the tracking table in reverse order.
    """
    minimi = Minimi(db_connection, db_migrations.success)
    minimi.apply()

    inspector = inspect(db_connection)
    assert "users" in inspector.get_table_names()

    minimi.rollback()

    inspector = inspect(db_connection)
    assert "users" not in inspector.get_table_names()
    applied = minimi._applied_migrations.get_all()
    assert len(applied) == 0


def test_rollback_unapplied_migrations(db_connection, db_migrations):
    """Tests calling rollback on a database where migrations have not been applied.

    Expected result: Operates safely as a no-op without errors or schema changes,
    leaving applied migrations empty.
    """
    minimi = Minimi(db_connection, db_migrations.success)
    minimi.rollback()

    inspector = inspect(db_connection)
    assert "users" not in inspector.get_table_names()
    assert len(minimi._applied_migrations.get_all()) == 0


def test_partial_apply_and_subsequent_apply(db_connection, db_migrations):
    """Tests applying a subset of migrations followed by applying the full list.

    Expected result: First application applies only the initial migration, and subsequent
    application applies remaining unapplied migrations incrementally.
    """
    first_migration = [db_migrations.success[0]]
    all_migrations = db_migrations.success

    minimi_first = Minimi(db_connection, first_migration)
    minimi_first.apply()

    inspector = inspect(db_connection)
    assert "users" in inspector.get_table_names()
    columns = [col["name"] for col in inspector.get_columns("users")]
    assert "id" in columns
    assert "name" in columns
    assert "email" not in columns

    minimi_all = Minimi(db_connection, all_migrations)
    minimi_all.apply()

    inspector = inspect(db_connection)
    columns_after = [col["name"] for col in inspector.get_columns("users")]
    assert "email" in columns_after


def test_rollback_partial_applied(db_connection, db_migrations):
    """Tests rolling back when only a subset of migrations was previously applied.

    Expected result: Reverts only the applied subset and cleans up tracking records
    without attempting to roll back unapplied migrations.
    """
    first_migration = [db_migrations.success[0]]
    all_migrations = db_migrations.success

    minimi_first = Minimi(db_connection, first_migration)
    minimi_first.apply()

    minimi_all = Minimi(db_connection, all_migrations)
    minimi_all.rollback()

    inspector = inspect(db_connection)
    assert "users" not in inspector.get_table_names()
    assert len(minimi_all._applied_migrations.get_all()) == 0


def test_apply_step_failure_rolls_back_previous_steps(db_connection):
    """Tests intra-migration step failure during forward application.

    Expected result: Raises `MigrationFailedError` and reverts steps already executed within
    the same migration module, leaving schema clean and migration unrecorded.
    """

    class StepFailMigration:
        __name__ = "step_fail_migration"
        MIGRATIONS = [
            (
                "CREATE TABLE step_rollback_test (id INTEGER PRIMARY KEY);",
                "DROP TABLE step_rollback_test;",
            ),
            "INVALID SQL STATEMENT;",
        ]

    minimi = Minimi(db_connection, [StepFailMigration])
    with pytest.raises(MigrationFailedError):
        minimi.apply()

    inspector = inspect(db_connection)
    assert "step_rollback_test" not in inspector.get_table_names()
    assert len(minimi._applied_migrations.get_all()) == 0


def test_apply_step_failure_when_revert_step_also_fails(db_connection):
    """Tests intra-migration step failure where the revert step itself fails.

    Expected result: Raises `MigrationFailedError` while handling internal revert exception safely.
    """

    class RevertFailMigration:
        __name__ = "revert_fail_migration"
        MIGRATIONS = [
            (
                "CREATE TABLE step_revert_fail (id INTEGER PRIMARY KEY);",
                "INVALID REVERT SQL;",
            ),
            "INVALID SQL STATEMENT;",
        ]

    minimi = Minimi(db_connection, [RevertFailMigration])
    with pytest.raises(MigrationFailedError):
        minimi.apply()


def test_apply_and_rollback_with_callable_steps(db_connection):
    """Tests applying and rolling back migrations defined with custom Python functions.

    Expected result: Executes `up` callable on apply to modify schema, and executes
    `down` callable on rollback to revert schema changes.
    """
    called = {"up": False, "down": False}

    def up_func(conn):
        called["up"] = True
        conn.execute(text("CREATE TABLE callable_test (id INT);"))

    def down_func(conn):
        called["down"] = True
        conn.execute(text("DROP TABLE callable_test;"))

    class CallableMigration:
        __name__ = "callable_migration"
        MIGRATIONS = [(up_func, down_func)]

    minimi = Minimi(db_connection, [CallableMigration])
    minimi.apply()
    assert called["up"] is True
    inspector = inspect(db_connection)
    assert "callable_test" in inspector.get_table_names()

    minimi.rollback()
    assert called["down"] is True
    inspector = inspect(db_connection)
    assert "callable_test" not in inspector.get_table_names()


def test_apply_and_rollback_with_none_callback(db_connection):
    """Tests applying and rolling back a migration whose `MIGRATIONS` is `None`.

    Expected result: Records migration as applied without error on apply, and removes
    from applied migrations on rollback without modifying database schema.
    """

    class NoneCallbackMigration:
        MIGRATIONS = None

    minimi = Minimi(db_connection, [NoneCallbackMigration])
    minimi.apply()
    assert "NoneCallbackMigration" in minimi._applied_migrations.get_all()

    minimi.rollback()
    assert "NoneCallbackMigration" not in minimi._applied_migrations.get_all()


def test_apply_missing_migrations_attribute(db_connection):
    """Tests applying a migration module that lacks the required `MIGRATIONS` attribute.

    Expected result: Raises `InvalidModuleStructureError` before executing migrations.
    """

    class InvalidModule:
        pass

    minimi = Minimi(db_connection, [InvalidModule])
    with pytest.raises(InvalidModuleStructureError, match="does not have a MIGRATIONS attribute"):
        minimi.apply()


def test_apply_missing_name_attribute(db_connection):
    """Tests applying a migration object that lacks the `__name__` attribute.

    Expected result: Raises `InvalidModuleStructureError` during name validation.
    """

    class ObjectWithoutName:
        MIGRATIONS = "CREATE TABLE no_name (id INT);"

    minimi = Minimi(db_connection, [ObjectWithoutName()])
    with pytest.raises(InvalidModuleStructureError, match="does not have __name__ attribute"):
        minimi.apply()


def test_rollback_missing_migrations_attribute(db_connection):
    """Tests rolling back a migration module that lacks the required `MIGRATIONS` attribute.

    Expected result: Raises `InvalidModuleStructureError` when resolving rollback steps.
    """

    class InvalidModule:
        pass

    minimi = Minimi(db_connection, [InvalidModule])
    minimi._applied_migrations.add("InvalidModule")

    with pytest.raises(InvalidModuleStructureError, match="does not have a MIGRATIONS attribute"):
        minimi.rollback()


def test_rollback_missing_name_attribute(db_connection):
    """Tests rolling back a migration object that lacks the `__name__` attribute.

    Expected result: Raises `InvalidModuleStructureError` during name validation.
    """

    class NoNameModule:
        pass

    minimi = Minimi(db_connection, [NoNameModule()])
    with pytest.raises(InvalidModuleStructureError, match="does not have __name__ attribute"):
        minimi.rollback()


def test_apply_rolls_back_when_record_fails(db_connection):
    """Tests failure when recording an applied migration into the tracking table.

    Expected result: Raises error from tracking failure, rolls back executed migration
    steps, and leaves database schema clean.
    """

    class SingleMigration:
        __name__ = "record_fail_migration"
        MIGRATIONS = (
            "CREATE TABLE record_fail_test (id INT);",
            "DROP TABLE record_fail_test;",
        )

    minimi = Minimi(db_connection, [SingleMigration])
    original_add = minimi._applied_migrations.add

    def mock_add(name):
        raise RuntimeError("Failed to record migration in DB")

    minimi._applied_migrations.add = mock_add

    with pytest.raises(RuntimeError, match="Failed to record migration in DB"):
        minimi.apply()

    inspector = inspect(db_connection)
    assert "record_fail_test" not in inspector.get_table_names()
