import argparse
from caen_tools.CAENLib.tickets import Tickets
from caen_tools.connection.client import SyncClient

SERVADDR = "tcp://localhost:5559"


def list_available_tickets():
    return [t.value for t in Tickets]


def jsonify_tkt(args):
    argsdict = vars(args)
    tkt_json = {"name": argsdict.pop("name"), "args": argsdict}
    return tkt_json


def main():
    parser = argparse.ArgumentParser(
        prog="Console client for tickets execution",
        description="This client can execute your ticket without WebService",
        epilog="Enjoy!",
    )
    subparsers = parser.add_subparsers(
        help="Available tickets to execute:", dest="name"
    )
    spr = dict()
    for ticket in list_available_tickets():
        name, args = ticket.description["name"], ticket.description["args"]
        spr[name] = subparsers.add_parser(name, help=ticket.__doc__.lower())
        for key, value in args.items():
            spr[name] = spr[name].add_argument(f"{key}", help=f"{key}: {value}")

    args = parser.parse_args()

    tkt_json = jsonify_tkt(args)
    cli = SyncClient(connect_addr=SERVADDR)
    resp = cli.query(tkt_json)

    print("RESPONSE", resp)
    return resp


if __name__ == "__main__":
    # python ConsoleClient/client.py --help
    main()
