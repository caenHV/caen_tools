from datetime import datetime

from caen_tools.ODB_handler.ODB_Handler import ODB_Handler


class SystemCheck:
    def __init__(self, dbpath: str, interlock_db_uri: str, max_interlock_check_delta_time: int = 100):
        self.__interlock = True
        self.__last_interlock_check = int(datetime.now().timestamp())
        self.__max_interlock_check_delta_time = max_interlock_check_delta_time
        self.__are_params_ok = True
        self.__last_params_check = int(datetime.now().timestamp())
        
        self.__odb = ODB_Handler(dbpath, interlock_db_uri)
    
    def update_state(self):
        delta_time = int(datetime.now().timestamp()) - self.__last_interlock_check
        if delta_time > self.__max_interlock_check_delta_time:
            self.check_interlock()
            
    def check_interlock(self)->dict:
        interlock = self.__odb.get_interlock()
        self.__interlock = (interlock['state'] == 1)
        self.__last_interlock_check = interlock['time']
            
        response = {
            "params_ok" : self.__are_params_ok,
            "interlock" : self.__interlock,
            "interlock check timestamp" : self.__last_interlock_check,
            "params check timestamp" : self.__last_params_check
        }
        return response
    
    def check_params(self, params: dict) -> dict:
        """Check params.

        Parameters
        ----------
        params : str
            json string with key "body" where all parameters are stored (the GetParameters ticket response).

        Returns
        -------
        str
            json response:
            {
                "name" : "Monitor",
                "timestamp" : current_time,
                "is_ok" : True for ok and False if something is wrong.
            }
        """    

        # Checks that all channels are okay.
        ch_status_list = [int(bin(int(val['ChStatus']))[2:]) > 111 for _, val in params.items()]
        self.__are_params_ok = not any(ch_status_list)
        self.__last_params_check = int(datetime.now().timestamp())
        
        self.update_state()
        response = {
            "params_ok" : self.__are_params_ok,
            "interlock" : self.__interlock,
            "interlock check timestamp" : self.__last_interlock_check,
            "params check timestamp" : self.__last_params_check
        }
        return response
    
    def is_ok(self)->dict:
        self.update_state()
        response = {
            "params_ok" : self.__are_params_ok,
            "interlock" : self.__interlock,
            "interlock check timestamp" : self.__last_interlock_check,
            "params check timestamp" : self.__last_params_check
        }
        return response
        