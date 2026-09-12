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
from unittest.mock import MagicMock

from sqlalchemy import Connection, text

from minimi.migrations import _noop, MigrationCallbackPair, normalize_migration_steps


def test_normalize_empty_list():
    result = normalize_migration_steps([])
    assert result == []


def test_normalize_single_string_step():
    stmt = "CREATE TABLE users (id INTEGER PRIMARY KEY)"
    result = normalize_migration_steps(stmt)

    assert len(result) == 1
    pair = result[0]
    assert isinstance(pair, MigrationCallbackPair)
    assert callable(pair.up)
    assert callable(pair.down)

    conn = MagicMock(spec=Connection)
    pair.up(conn)
    assert conn.execute.call_count == 1
    assert str(conn.execute.call_args[0][0]) == str(text(stmt))

    conn.reset_mock()
    assert pair.down
    pair.down(conn)
    assert conn.execute.call_count == 0


def test_normalize_single_callback_step():
    mock_callback = MagicMock()
    result = normalize_migration_steps(mock_callback)

    assert len(result) == 1
    pair = result[0]
    assert pair.up is mock_callback
    assert pair.down is _noop

    conn = MagicMock(spec=Connection)
    pair.up(conn)
    mock_callback.assert_called_with(conn)


def test_normalize_single_none_step():
    result = normalize_migration_steps(None)

    assert len(result) == 1
    pair = result[0]
    assert callable(pair.up)
    assert callable(pair.down)

    conn = MagicMock(spec=Connection)
    pair.up(conn)
    pair.down(conn)
    conn.execute.assert_not_called()


def test_normalize_tuple_with_strings():
    up_stmt = "CREATE TABLE users (id INTEGER PRIMARY KEY)"
    down_stmt = "DROP TABLE users"
    result = normalize_migration_steps((up_stmt, down_stmt))

    assert len(result) == 1
    pair = result[0]
    assert callable(pair.up)
    assert callable(pair.down)

    conn = MagicMock(spec=Connection)
    pair.up(conn)
    assert conn.execute.call_count == 1
    assert str(conn.execute.call_args[0][0]) == str(text(up_stmt))

    conn.reset_mock()
    pair.down(conn)
    assert conn.execute.call_count == 1
    assert str(conn.execute.call_args[0][0]) == str(text(down_stmt))


def test_normalize_tuple_with_callbacks():
    mock_up = MagicMock()
    mock_down = MagicMock()
    result = normalize_migration_steps((mock_up, mock_down))

    assert len(result) == 1
    pair = result[0]
    assert pair.up is mock_up
    assert pair.down is mock_down

    conn = MagicMock(spec=Connection)
    pair.up(conn)
    mock_up.assert_called_once_with(conn)
    mock_down.assert_not_called()

    pair.down(conn)
    mock_down.assert_called_once_with(conn)


def test_normalize_tuple_with_none():
    mock_up = MagicMock()
    result = normalize_migration_steps((mock_up, None))

    assert len(result) == 1
    pair = result[0]
    assert pair.up is mock_up
    assert callable(pair.down)

    conn = MagicMock(spec=Connection)
    pair.down(conn)
    conn.execute.assert_not_called()

    # Opposite: None up, string down
    down_stmt = "DROP TABLE users"
    result_none_up = normalize_migration_steps((None, down_stmt))
    assert len(result_none_up) == 1
    pair_none_up = result_none_up[0]

    conn.reset_mock()
    pair_none_up.up(conn)
    conn.execute.assert_not_called()

    pair_none_up.down(conn)
    assert conn.execute.call_count == 1
    assert str(conn.execute.call_args[0][0]) == str(text(down_stmt))

    # Both None in tuple
    result_both_none = normalize_migration_steps((None, None))
    assert len(result_both_none) == 1
    conn.reset_mock()
    result_both_none[0].up(conn)
    result_both_none[0].down(conn)
    conn.execute.assert_not_called()


def test_normalize_list_of_multiple_steps():
    mock_callback = MagicMock()
    steps = [
        "CREATE TABLE t1 (id INT)",
        ("CREATE TABLE t2 (id INT)", "DROP TABLE t2"),
        (mock_callback, None),
        None,
    ]

    result = normalize_migration_steps(steps)

    assert len(result) == 4
    for pair in result:
        assert isinstance(pair, MigrationCallbackPair)

    conn = MagicMock(spec=Connection)

    # Step 0: string statement
    result[0].up(conn)
    assert str(conn.execute.call_args[0][0]) == str(text("CREATE TABLE t1 (id INT)"))
    conn.reset_mock()
    result[0].down(conn)
    conn.execute.assert_not_called()

    # Step 1: tuple of string statements
    conn.reset_mock()
    result[1].up(conn)
    assert str(conn.execute.call_args[0][0]) == str(text("CREATE TABLE t2 (id INT)"))
    conn.reset_mock()
    result[1].down(conn)
    assert str(conn.execute.call_args[0][0]) == str(text("DROP TABLE t2"))

    # Step 2: callback and None
    result[2].up(conn)
    mock_callback.assert_called_once_with(conn)
    conn.reset_mock()
    result[2].down(conn)
    conn.execute.assert_not_called()

    # Step 3: None
    conn.reset_mock()
    result[3].up(conn)
    result[3].down(conn)
    conn.execute.assert_not_called()
