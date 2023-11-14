from caen_setup import Handler

from caen_tools.CAENLib.tickets import Tickets
from caen_tools.connection.server import DeviceBackendServer


handler = Handler("./test_config.json", dev_mode=True)


def main():
    dbs = DeviceBackendServer("tcp://localhost:5560")
    # print("ROUTER Socket HWM", socket.get_hwm())

    while True:
        tkt_json = dbs.recv_json()
        tkt_obj = Tickets.deserialize(tkt_json)
        print(f"Recieved {tkt_obj}... ", end="")
        status = tkt_obj.execute(handler)
        print(f"and send status {status} back")
        dbs.send_json(status)


if __name__ == "__main__":
    main()
