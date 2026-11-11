"""One transaction publishes an evaluation and all referenced object bytes."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from .blocks import BlockStore
from .legacy import ObjectStore


class Transactions:
    def __init__(self, db: sqlite3.Connection, objects: BlockStore | ObjectStore):
        self.db, self.objects = db, objects
        self.active = False

    @contextmanager
    def write(self) -> Iterator[None]:
        if self.active:
            yield
            return
        try:
            self.db.execute("BEGIN IMMEDIATE")
            self.db.execute("PRAGMA defer_foreign_keys=ON")
            self.active = True
            yield
            self.objects.flush()
            self.db.commit()
        except BaseException:
            self.db.rollback()
            self.objects.reset()
            raise
        finally:
            self.active = False
