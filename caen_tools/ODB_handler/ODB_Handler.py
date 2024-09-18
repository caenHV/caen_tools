from datetime import datetime, timedelta
import json
from pathlib import Path
import sqlite3
import warnings
from urllib.parse import urlparse

import psycopg2


class ODB_Handler:
    def __init__(
        self, dbpath: str, interlock_db_uri: str, cleaning_frequency: int = 100
    ):
        self.__dbpath = dbpath
        parsed_uri = urlparse(interlock_db_uri)
        self.__interlock_db_credentials = {
            "dbname": parsed_uri.hostname,
            "user": parsed_uri.username,
            "password": parsed_uri.password,
            "port": parsed_uri.port,
            "host": parsed_uri.scheme,
        }

        self.con = sqlite3.connect(self.__dbpath)
        self.con.row_factory = sqlite3.Row  # to fetch dicts (not simple tuples)
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS data (idx INTEGER PRIMARY KEY AUTOINCREMENT, channel TEXT, voltage REAL, current REAL, t INTEGER, status INTEGER);"
        ).close()
        self.__records_after_delete_counter: int = 0
        self.__cleaning_frequency: int = cleaning_frequency

    def get_interlock(self):
        is_ok = True
        res = None
        try:
            conn = psycopg2.connect(**self.__interlock_db_credentials)
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT value, time from values where property = 'KMD_Interlock';"
                )
                res = cursor.fetchone()

        except Exception as e:
            is_ok = False
            warnings.warn(
                f"Houston! We faced problems with getting interlock from the SND Database: {e}."
            )
        if is_ok or res is None or len(res) != 1:
            return {"state": 1, "time": int(datetime.now().timestamp())}

        res_data = {"state": int(res[0]), "time": int(res[1].timestamp())}
        return res_data

    def __write_param_file(self, results: list, param_file_path: Path):
        tmp_path = param_file_path.with_name(param_file_path.name + "_tmp")
        cooked = {}
        for channel, voltage, current, t, status in results:
            cooked["DCV" + channel] = voltage
            cooked["DCC" + channel] = current

        with open(tmp_path, mode="w") as f:
            json.dump(cooked, f)
        tmp_path.rename(param_file_path)

    def clear_db(self):
        min_timestamp = int((datetime.now() - timedelta(days=1)).timestamp())
        try:
            cur = self.con.cursor()
            cur.execute("DELETE FROM data WHERE t < ?", (min_timestamp,))
            self.con.commit()
        except Exception as e:
            warnings.warn(f"Can not delete old records from the DB: {e}")
        finally:
            cur.close()

    def write_params(self, results: list, param_file_path: Path) -> bool:
        """Writes results to the DB.

        Parameters
        ----------
        results : list
            list of CAEN channels parameters with the following structure: list[(chidx, val["VMon"], val["IMonH"], ts, status)].

        Returns
        -------
        bool
            True if everything is ok. If something went wrong returns False.
        """
        is_ok = True
        try:
            res_list = [
                (chidx, v, i, ts, status) for (chidx, v, i, ts, status) in results
            ]
        except ValueError as e:
            is_ok = False
            warnings.warn(f"Wrong structure of results list: {e}")

        with self.con:
            try:
                self.con.executemany(
                    "INSERT INTO data(channel, voltage, current, t, status) VALUES(?, ?, ?, ?, ?)",
                    res_list,
                ).close()
                self.__records_after_delete_counter += 1
                if self.__records_after_delete_counter > self.__cleaning_frequency:
                    self.clear_db()
                    self.__records_after_delete_counter = 0

            except sqlite3.DatabaseError as e:
                is_ok = False
                warnings.warn(f"Houston! We faced problems with the Database: {e}.")
        try:
            self.__write_param_file(res_list, param_file_path)
        except Exception as e:
            warnings.warn(f"Problems with writing file for ODB: {e}")
            is_ok = False

        return is_ok

    def get_params(self, start: int, end: int) -> list | None:
        is_ok = True
        with self.con as con:
            try:
                res = con.execute(
                    "SELECT channel, voltage, current, t FROM data WHERE (t > ? AND t <= ?) ORDER BY idx DESC",
                    (start, end),
                ).fetchall()
                return [dict(row) for row in res]
            except sqlite3.DatabaseError as e:
                is_ok = False
                warnings.warn(f"Houston! We faced problems with the Database: {e}.")
        return []
