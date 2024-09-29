import logging
import socket


class MChSWorker:
    """A class for working with MChS"""

    @staticmethod
    def send(udp_ip: str, udp_port: str, client_id: str, ack: bool):
        """Sends UDP datagram to the MChS Controller.
        For details read this: https://cmd.inp.nsk.su/wiki/pub/CMD3/Diplom2018/Зубакин_АС.pdf

        Parameters
        ----------
        udp_ip : str
            MChS controller host address
        udp_port : str
            Port listened by MChS controller
        client_id : str
            Id of Caen_HV registered in MChS controller
        ack : bool
            True == everything is ok, False == lock Triggers
        """

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        logging.debug(
            "Opened send_UDP_to_MChS_Controller socket. Start sending UDP package to MChS Controller."
        )

        try:
            udp_port = int(udp_port)  # type: ignore
            sock.sendto(
                str.encode(f"{'ACK' if ack else 'NACK'} {client_id}"),
                (udp_ip, udp_port),
            )
            logging.debug(
                "Sent UDP package to MChS Controller with status code %s",
                ("ACK" if ack else "NACK"),
            )
        except Exception as e:
            logging.error(
                "MChS_Controler sending problems: %s, %s", type(e).__name__, e
            )

        sock.close()
        logging.debug("Closed send_UDP_to_MChS_Controller socket.")

        return

    def __init__(self, udp_ip: str, udp_port: str, client_id: str):
        self.udp_ip = udp_ip
        self.udp_port = udp_port
        self.client_id = client_id
        self.__state = dict()

    @property
    def isack(self) -> bool:
        """Checks the total acknowledge"""
        logging.debug("Get total ack from mchs worker")
        return all(self.__state.values())

    def set_state(self, **kwargs):
        """Sets an acknowledge"""
        logging.debug("Set state for mchs worker")
        self.__state.update(kwargs)

    def pop_keystate(self, key) -> bool | None:
        """Pops a key from state"""
        return self.__state.pop(key, None)

    def send_state(self):
        """Sends an acknowledge status to the server"""
        logging.info("Send %s to MChS", "ACK" if self.isack else "NACK")
        logging.debug("MChS dict state %s", self.__state)
        MChSWorker.send(self.udp_ip, self.udp_port, self.client_id, self.isack)
        return
