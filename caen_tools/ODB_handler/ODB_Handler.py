import sqlite3
from datetime import datetime
import warnings


class ODB_Handler:
    def __init__(self, dbpath: str):
        self.__dbpath = dbpath
        self.con = sqlite3.connect(self.__dbpath)
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS data (idx INTEGER PRIMARY KEY AUTOINCREMENT, measurement_id INTEGER, channel TEXT, voltage REAL, current REAL, t INTEGER, status INTEGER);"
        )

        self.con.execute(
            "CREATE TABLE IF NOT EXISTS interlock (idx INTEGER PRIMARY KEY AUTOINCREMENT, state INTEGER, t INTEGER);"
        )

    def get_interlock(self):
        is_ok = True
        # with self.con:
        #     try:
        #         res = self.con.execute(
        #             "SELECT idx, state, t FROM interlock ORDER BY idx DESC LIMIT 1",
        #         ).fetchall()
        #         if len(res) < 1:
        #             is_ok = False
        #             warnings.warn("Houston! We faced problems with the Database. No interlock records!")

        #     except sqlite3.DatabaseError as e:
        #         is_ok = False
        #         warnings.warn(f"Houston! We faced problems with the Database: {e}")
                
        # res_data = [
        #     {"state": state, "time": t} for (_, state, t) in res
        # ] if is_ok else None
        
        # TODO: !!!
        res_data = [{"state": 1, "time": 1000000}]
        return res_data

    def write_params(self, results: list) -> bool:
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
        measurement_id = int(datetime.now().timestamp())
        try:
            res_list = [
                (measurement_id, chidx, v, i, ts, status)
                for (chidx, v, i, ts, status) in results
            ]
        except ValueError as e:
            is_ok = False
            warnings.warn(f"Wrong structure of results list: {e}")

        with self.con:
            try:
                self.con.executemany(
                    "INSERT INTO data(measurement_id, channel, voltage, current, t, status) VALUES(?, ?, ?, ?, ?, ?)",
                    res_list,
                )
            except sqlite3.DatabaseError:
                is_ok = False
                warnings.warn("Houston! We faced problems with a Database")

        return is_ok

    def get_params(self, start: int, end: int) -> dict | None:
        is_ok = True
        with self.con as con:
            try:
                res = con.execute(
                    "SELECT channel, voltage, current, t FROM data WHERE (t > ? AND t <= ?) ORDER BY idx DESC",
                    (start, end),
                ).fetchall()
            except sqlite3.DatabaseError:
                is_ok = False
                warnings.warn("Houston! We faced problems with a Database")

        res_data = []
        if is_ok:
            res_data = [
                {"chidx": chidx, "V": voltage, "I": current, "t": t}
                for (chidx, voltage, current, t) in res
            ]
        return res_data
