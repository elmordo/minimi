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
import sqlalchemy
from sa_values import setup_sa_values

from .shared import MigrationModulePair


@pytest.fixture()
def db_migrations(db_type) -> MigrationModulePair:
    if db_type == "sqlite":
        from ._migrations.sqlite import fail, success
    else:
        raise NotImplementedError

    return MigrationModulePair(
        success=success.MIGRATIONS,
        failure=fail.MIGRATIONS,
    )


@pytest.fixture(autouse=True)
def _sa_setup(db_connection):
    setup_sa_values(db_connection)


@pytest.fixture()
def db_connection(db_engine) -> sqlalchemy.engine.Connection:
    return db_engine.connect()


@pytest.fixture()
def db_engine(db_uri) -> sqlalchemy.engine.Engine:
    return sqlalchemy.create_engine(db_uri)


@pytest.fixture()
def db_uri(db_type) -> str:
    if db_type == "sqlite":
        return "sqlite:///:memory:"
    raise NotImplementedError


@pytest.fixture(params=["sqlite"])
def db_type(request: pytest.FixtureRequest) -> str:
    return request.param
