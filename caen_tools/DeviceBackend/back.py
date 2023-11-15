from caen_setup import Handler

from caen_tools.connection.server import DeviceBackendServer
from caen_setup.Tickets.TicketMaster import TicketMaster


handler = Handler("./test_config.json", dev_mode=True)


def main():
    dbs = DeviceBackendServer("tcp://localhost:5560")
    # print("ROUTER Socket HWM", socket.get_hwm())

    while True:
        tkt_json = dbs.recv_json_str()
        print(tkt_json)

        tkt_obj = TicketMaster.deserialize(tkt_json)
        print(f"Recieved {tkt_obj}... ", end="")
        # status = tkt_obj.execute(handler)
        status = {"status": "ok"}
        print(f"and send status {status} back")
        dbs.send_json(status)


if __name__ == "__main__":
    main()
