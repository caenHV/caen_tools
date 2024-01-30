import argparse
import getpass
import socket
import json

# from caen_tools.CAENLib.tickets import Tickets
from caen_setup import TicketType
from caen_tools.connection.client import SyncClient
from caen_tools.ConsoleClient.listen import listen

SERVADDR = "tcp://localhost:5559"


def list_available_tickets() -> list:
    # return [t.value for t in Tickets]
    return [t.value for t in TicketType]


def jsonify_tkt(args):
    argsdict = vars(args).copy()
    argsdict.pop("address")
    tkt_json = {"name": argsdict.pop("name"), "params": argsdict}
    return tkt_json


def main():
    user, host = getpass.getuser(), socket.gethostname()
    parser = argparse.ArgumentParser(
        prog="Console client for tickets execution",
        description="This client can execute your ticket without WebService",
        epilog="Enjoy!",
    )
    parser.add_argument(
        "-a",
        "--address",
        nargs="?",
        default=SERVADDR,
        help=f"proxy address (default {SERVADDR})",
    )
    subparsers = parser.add_subparsers(
        help="Available tickets to execute:",
        dest="name",
        required=True,
    )
    spr = dict()
    for ticket in list_available_tickets():
        name, args = ticket.type_description().name, ticket.type_description().params
        spr[name] = subparsers.add_parser(name, help=ticket.__doc__)
        for key, value in args.items():
            # print(key)
            min_val, max_val, desc = value['min_value'], value['max_value'], value['description']
            spr[name].add_argument(f"{key}", help=f"{key}: {min_val} - {max_val}, Description: {desc}")

    spr["Listener"] = subparsers.add_parser("Listener", help="listen proxy")

    args = parser.parse_args()

    if args.name == "Listener":
        listen()
        return
    else:
        tkt_json = jsonify_tkt(args)
        cli = SyncClient(connect_addr=args.address)
        resp = cli.query(json.dumps(tkt_json), "setup")
        # import json
        # resp = cli.query(json.dumps({'name': 'MonitorQuery', 'timestamp': 100}), 'monitor')

    print("RESPONSE", resp)
    return resp


if __name__ == "__main__":
    # python ConsoleClient/client.py --help
    main()
