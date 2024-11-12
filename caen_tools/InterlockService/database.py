from collections import namedtuple
from pathlib import Path
from time import time

import logging
from tinydb import TinyDB, Query
from tinydb.table import Document
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware

from .utils import Mode, EventCode


class IlkDBMangager:
    """Implementation of interlock database manager
    that stores current state of the service"""

    Tables = namedtuple("Tables", ["events", "settings", "interlock"])

    def __init__(self, dbpath: Path, init_settings: dict):
        logging.debug("Start init Interlock Database Manager %s", init_settings)
        self._db = TinyDB(dbpath, storage=CachingMiddleware(JSONStorage), indent=4)
        self._tables = IlkDBMangager.Tables(
            events=self._db.table("events"),
            settings=self._db.table("settings"),
            interlock=self._db.table("interlock"),
        )
        self._settings_id = self.__init_settings(init_settings)
        self._interlock_id = self.__init_interlock()
        self.__push_event(EventCode.START)

    def __init_settings(self, settings: dict) -> int:
        """Initializes settings and returns doc_id"""
        setting = Query()
        doc_id = 1
        self._tables.settings.upsert(Document(settings, doc_id=doc_id))
        self._tables.settings.update({"mode": Mode.SOCKET}, ~(setting.mode.exists()))
        return doc_id

    def __init_interlock(self) -> int:
        doc_id = 1
        self._tables.interlock.upsert(
            Document(dict(value=True), doc_id=doc_id), ~(Query().value.exists())
        )
        return doc_id

    def __push_event(self, eventcode: EventCode, **kwargs):
        kwargs.update({"event": eventcode, "t": int(time())})
        self._tables.events.insert(kwargs)
        return

    @property
    def settings(self) -> dict:
        """Returns settings dictionary"""
        settings_dict = self._tables.settings.get(doc_id=self._settings_id)
        settings_dict["mode"] = Mode(settings_dict["mode"])
        return dict(settings_dict)

    @property
    def interlock(self) -> bool:
        """Returns interlock value"""
        interlock_dict = self._tables.interlock.get(doc_id=self._interlock_id)
        return bool(interlock_dict["value"])

    @interlock.setter
    def interlock(self, value: bool):
        """Sets interlock value"""
        if not isinstance(value, (bool, int)):
            raise ValueError(f"Value {value} must be bool or int (not {type(value)})")
        self._tables.interlock.update(
            {"value": bool(value)}, doc_ids=[self._interlock_id]
        )

    @property
    def mode(self) -> Mode:
        """Gets mode"""
        return self.settings["mode"]

    @mode.setter
    def mode(self, value: Mode) -> None:
        """Sets mode in the database settings"""
        self._tables.settings.update({"mode": value})

    def remove_before(self, value: int) -> None:
        """Removes rows written before current_time - value (in seconds)"""
        event = Query()
        tstart = int(time()) - value
        self._tables.events.remove((event.t < tstart))

    def close(self):
        """Closes database connection"""
        self.__push_event(EventCode.STOP)
        self._db.close()
