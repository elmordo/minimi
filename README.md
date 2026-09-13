Minimal migration library for managing database migrations in small projects where a full featured migration tool would
be overkill.

# Quick start

Create a migration module in your source directory

```
src
  +- mylib
    +- migrations
    |  +- __init__.py          <- list of migration modules
    |  +- m01_db_init.py       <- first revision
    |  +- m02_new_table.py     <- second revision
    +- other module
    +- main.py
```

```python
# __init__.py

from . import m01_db_init, m02_new_table

MIGRATIONS = [
    m01_db_init,
    m02_new_table,
]
```

```python
# m01_db_init.py

# the UP migration only
MIGRATIONS = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);
"""
```

```python
# m02_new_table.py

# the UP and DOWN migrations as tuple of two strings
MIGRATIONS = """
CREATE TABLE IF NOT EXISTS user_comments (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL
        REFERENCES users(id),
    subjects TEXT NOT NULL,
    message TEXT NOT NULL
);
""", """
DROP TABLE IF EXISTS user_comments;
"""
```

```python
# main.py

from minimi import Minimi
from sqlalchemy import create_engine
from sa_values import setup_sa_values

import mylib.migrations as migrations


def main():
    # initialize the sa_values first
    conn = create_engine("sqlite:///:memory:").connect()
    setup_sa_values(conn)
    # run the migrations
    Minimi(conn, migrations).apply()


if __name__ == "__main__":
    main()
```

# Usage

The `__init__.py` file contains a list of migration modules in the `MIGRATIONS` global variable with list of migration
modules.

Each migration module must contain the `MIGRATION` global variable with the migration.

# Buy me a ~~coffee~~ beer

If you like this library, or you want to support its development, support me by one
cold [beer](https://www.buymeacoffee.com/elmordo). The beer is tasty and full of vitamins :-)
