import sqlite3
import json
import time
from caen_setup.Tickets.Tickets import GetParams_Ticket
# from caen_setup.Tickets.TicketMaster import TicketMaster
from caen_tools.connection.client import SyncClient

SERVADDR = "tcp://localhost:5559"
DBPATH = "./monitor.db"

class Monitor:
    def __init__(self, dbpath: str):
        self.cli = SyncClient(SERVADDR)
        self.ticket = GetParams_Ticket({})
        self.tkt_json = {"name": "GetParams", "params": {}} #TicketMaster.serialize(self.ticket)

        self.con = sqlite3.connect(dbpath)
        self.con.execute("CREATE TABLE IF NOT EXISTS data (idx INTEGER PRIMARY KEY AUTOINCREMENT, channel TEXT, voltage REAL, t TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")

    @staticmethod
    def get_results(dbpath: str, num_points: int = None, start_time: int = 0):
        pass

    @staticmethod
    def __process_response(res_dict):
        res = res_dict['body']['params']
        res_list = []
        for key, val in res.items():
            k0 = json.loads(key.replace('\\', ''))
            board_address = list(k0["board_info"].keys())[0]
            conet = k0["board_info"][board_address]["conet"]
            link = k0["board_info"][board_address]["link"]
            chidx = f'{board_address}_{conet}_{link}_{k0["channel_num"]}'
            res_list.append((chidx, val['VMon']))
        return res_list


    def add_row(self):
        results = self.cli.query(self.tkt_json)
        res_dict = json.loads(results)
        res_list = Monitor.__process_response(res_dict)
        with self.con:
            self.con.executemany("INSERT INTO data(channel, voltage) VALUES(?, ?)", res_list)
        return


def main():
    m = Monitor(DBPATH)
    m.add_row()
    while True:
        try:
            m.add_row()
            time.sleep(5)
        except KeyboardInterrupt:
            break
    return

if __name__ == "__main__":
    main()
