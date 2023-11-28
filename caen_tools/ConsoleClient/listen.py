from caen_tools.connection.listener import Listener


def listen() -> None:
    """Listen the publisher"""

    lsn = Listener(connect_addr="tcp://localhost:5561")
    resp = ""
    while True:
        try:
            resp = lsn.recv_msg()
            print(resp)
        except KeyboardInterrupt:
            print("\nGoodbye!")
            return
    return
