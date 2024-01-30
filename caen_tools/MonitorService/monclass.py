import json
import logging
from typing import Optional, List

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from caen_tools.MonitorService.database import DataRows, Base

from caen_tools.utils.utils import get_default_logger


class MonitorDB:
    """Class to manipulate Monitor DataBase"""

    def __init__(self, dbpath: str, logger: Optional[logging.Logger] = None):
        self.logger = (
            logger if logger is not None else get_default_logger(logging.DEBUG)
        )
        self.logger.debug("Init MonitorDB class")

        self.engine = create_engine(f"sqlite://{dbpath}", echo=False)
        Base.metadata.create_all(self.engine)
        self.logger.debug("Create DB engine sqlite://%s", dbpath)

    def store_data(self, data_obj: object):
        """Stores data_obj in database

        Parameters
        ----------
        data_obj : object
            python object as a getparams ticket response to store in database
        """
        res_list = MonitorDB.__process_response(data_obj)

        with Session(self.engine) as session:
            session.add_all(res_list)
            session.commit()
        self.logger.debug("Updated DB. Stored new data")
        return

    def get_db_data(self, tkt: dict) -> str:
        """Returns data from database

        Parameters
        ----------
        tkt : dict
            dictionary containing arguments for selection

        Returns
        -------
        str
            string from json object
        """
        ts = int(tkt["timestamp"])
        selection = select(DataRows).where(DataRows.timestamp >= ts)
        res_data = list()
        with Session(self.engine) as session:
            for row in session.execute(selection):
                # print(row)
                datarow = {
                    "chidx": row[0].channel,
                    "voltage": row[0].voltage,
                    "t": row[0].timestamp,
                }
                res_data.append(datarow)
        res_data_str = json.dumps({"status": "ok", "body": res_data})
        return res_data_str

    @staticmethod
    def __process_response(res_dict) -> List[DataRows]:
        """Returns a list of DataRows

        Parameters
        ----------
        res_dict : dict
            json dict response

        Returns
        -------
        List[DataRows]
            list of DataRows
        """

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
            item = DataRows(
                channel=chidx, timestamp=ts, current=val["IMonL"], voltage=val["VMon"]
            )
            res_list.append(item)

        return res_list
