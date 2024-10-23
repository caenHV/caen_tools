from datetime import datetime, timedelta
import json
from pathlib import Path
import sqlite3
import logging


class ODB_Handler:
    def __init__(self, dbpath: str, cleaning_frequency: int = 100):
        self.__dbpath = dbpath

        self.con = sqlite3.connect(self.__dbpath)
        self.con.row_factory = sqlite3.Row  # to fetch dicts (not simple tuples)
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS data (idx INTEGER PRIMARY KEY AUTOINCREMENT, channel TEXT, voltage REAL, current REAL, t INTEGER, status INTEGER);"
        ).close()
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS status (idx INTEGER PRIMARY KEY AUTOINCREMENT, is_ok BOOLEAN , description TEXT, t INTEGER);"
        ).close()
        self.__records_after_delete_counter: int = 0
        self.__cleaning_frequency: int = cleaning_frequency

    def __write_param_file(self, results: list, param_file_path: Path):
        tmp_path = param_file_path.with_name(param_file_path.name + "_tmp")
        cooked = {}
        for channel, voltage, current, _, _ in results:
            cooked["DCV" + channel] = voltage
            cooked["DCC" + channel] = current

        with open(tmp_path, mode="w", encoding="utf-8") as f:
            json.dump(cooked, f)
        tmp_path.rename(param_file_path)

    def __write_status_file(
        self, is_ok: bool, description: str, timestamp: int, status_file_path: Path
    ):
        tmp_path = status_file_path.with_name(status_file_path.name + "_tmp")
        cooked = {"is_ok": is_ok, "description": description, "timestamp": timestamp}

        with open(tmp_path, mode="w", encoding="utf-8") as f:
            json.dump(cooked, f)
        tmp_path.rename(status_file_path)

    def clear_db(self):
        min_timestamp = int((datetime.now() - timedelta(days=1)).timestamp())
        try:
            cur = self.con.cursor()
            cur.execute("DELETE FROM data WHERE t < ?", (min_timestamp,))
            self.con.commit()
        except Exception as e:
            logging.warning(f"Can not delete old records from the DB: {e}")
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
            logging.warning(f"Wrong structure of results list: {e}")

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
                logging.warning(f"Houston! We faced problems with the Database: {e}.")
        try:
            self.__write_param_file(res_list, param_file_path)
        except Exception as e:
            logging.warning(f"Problems with writing file for ODB: {e}")
            is_ok = False

        return is_ok

    def write_status(
        self, is_ok: bool, description: str, timestamp: int, status_file_path: Path
    ) -> bool:
        """Writes the hardware status to the DB.

        Parameters
        ----------
        is_ok : bool
            True if yes False otherwise. Pretty obvious!
        description : str
            Explanation of the status. Meaningful only if is_ok == False
        timestamp : int
            time from the epoch of the status issue.
        status_file_path: Path
            Path to the file that is listened by the ODB connector (Anisyonkov program)

        Returns
        -------
        bool
            True if everything is ok. If something went wrong returns False.
        """
        with self.con:
            try:
                self.con.execute(
                    "INSERT INTO status(is_ok, description, t) VALUES(?, ?, ?)",
                    (is_ok, description, timestamp),
                ).close()
                self.__records_after_delete_counter += 1
                if self.__records_after_delete_counter > self.__cleaning_frequency:
                    self.clear_db()
                    self.__records_after_delete_counter = 0

            except sqlite3.DatabaseError as e:
                is_ok = False
                logging.warning(
                    f"Houston! We faced problems with the Status Database: {e}."
                )
        try:
            self.__write_status_file(is_ok, description, timestamp, status_file_path)
        except Exception as e:
            logging.warning(f"Problems with writing file for the ODB: {e}")
            is_ok = False

        return is_ok

    def get_params(self, start: int, end: int) -> list[dict] | None:
        with self.con as con:
            try:
                res = con.execute(
                    "SELECT channel, voltage, current, t FROM data WHERE (t > ? AND t <= ?) ORDER BY idx DESC",
                    (start, end),
                ).fetchall()
                # return [dict(row) for row in res]
                return [
                    {
                        "t": row["t"],
                        "V": row["voltage"],
                        "I": row["current"],
                        "chidx": row["channel"],
                    }
                    for row in res
                ]
            except sqlite3.DatabaseError as e:
                logging.warning(f"Houston! We faced problems with the Database: {e}.")
        return []

    def get_status(self, start: int, end: int) -> list[dict] | None:
        with self.con as con:
            try:
                res = con.execute(
                    "SELECT is_ok, description, t FROM status WHERE (t > ? AND t <= ?) ORDER BY idx DESC",
                    (start, end),
                ).fetchall()
                # return [dict(row) for row in res]
                return [
                    {
                        "t": row["t"],
                        "is_ok": row["is_ok"],
                        "description": row["description"],
                    }
                    for row in res
                ]
            except sqlite3.DatabaseError as e:
                logging.warning(
                    f"Houston! We faced problems with the Status Database: {e}."
                )
        return []
