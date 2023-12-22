import sqlite3
import json
from caen_setup.Tickets.Tickets import GetParams_Ticket

# from caen_setup.Tickets.TicketMaster import TicketMaster
from caen_tools.connection.client import SyncClient


class Monitor:
    def __init__(self, dbpath: str, proxy_address: str):
        self.cli = SyncClient(proxy_address)
        self.ticket = GetParams_Ticket({})
        self.tkt_json = {
            "name": "GetParams",
            "params": {},
        }  # TicketMaster.serialize(self.ticket)

        self.con = sqlite3.connect(dbpath)
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS data (idx INTEGER PRIMARY KEY AUTOINCREMENT, channel TEXT, voltage REAL, t INTEGER);"
        )

    @staticmethod
    def get_results(dbpath: str, start_time: int = 0):
        con = sqlite3.connect(dbpath)
        res = con.execute(
            "SELECT channel, voltage, t FROM data WHERE t > ? ORDER BY idx DESC",
            (int(start_time),),
        ).fetchall()
        con.close()
        res_data = [
            {"chidx": chidx, "v": voltage, "t": t} for (chidx, voltage, t) in res
        ]
        return res_data

    @staticmethod
    def __process_response(res_dict):
        from datetime import datetime

        ts = int(datetime.now().timestamp())
        res = res_dict["body"]["params"]
        res_list = []
        for key, val in res.items():
            k0 = json.loads(key.replace("\\", ""))
            board_address = list(k0["board_info"].keys())[0]
            conet = k0["board_info"][board_address]["conet"]
            link = k0["board_info"][board_address]["link"]
            chidx = f'{board_address}_{conet}_{link}_{k0["channel_num"]}'
            res_list.append((chidx, val["VMon"], ts))
        return res_list

    def add_row(self):
        results = self.cli.query(self.tkt_json)
        res_dict = json.loads(results)
        res_list = Monitor.__process_response(res_dict)
        with self.con:
            self.con.executemany(
                "INSERT INTO data(channel, voltage, t) VALUES(?, ?, ?)", res_list
            )
        return
