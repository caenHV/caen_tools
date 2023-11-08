from fastapi import FastAPI

from CAENLib.tickets import Tickets, SetVoltage
from CAENLib.client import Client

app = FastAPI()


@app.get("/list_tickets")
def read_list_tickets():
    """[WS Backend API] Returns a list of available tickets"""

    data = [t.value.description for t in Tickets]
    return data


@app.post("/set_ticket/{name}")
def post_ticket(name):
    """[WS Backend API] Sends ticket on the setup"""
    # TODO
    return {"status": "success", "ticket": name}


def post_tickets(cli, num):
    for i in range(num, 0, -1):
        sv = SetVoltage(voltage=i).serialize()
        print(f"Send {sv}")
        resp = cli.query(sv)
        print(f"Responsed {resp}")
    return


def main():
    from random import randint

    idx = randint(0, 100)
    print(f"Send {idx} messages")

    cli = Client("tcp://localhost:5559")
    post_tickets(cli, idx)
    print("End")
    return


if __name__ == "__main__":
    main()
