from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

from CAENLib.tickets import Tickets, SetVoltage
from CAENLib.client import Client, AsyncClient

app = FastAPI()
cli = AsyncClient("tcp://localhost:5559", 20)


@app.get("/")
async def read_root():
    return FileResponse("WebService/index.html")


@app.get("/list_tickets")
def read_list_tickets():
    """[WS Backend API] Returns a list of available tickets"""

    data = [t.value.description for t in Tickets]
    return data


@app.post("/set_ticket/{name}")
async def post_ticket(name: str, ticket_args: Request = None):
    """[WS Backend API] Sends ticket on the setup"""
    args_dict = await ticket_args.json() if ticket_args else {}
    tkt = {"name": name, "args": args_dict}
    print(f"Query ticket: {tkt}")
    resp = await cli.query(tkt)
    return resp


def post_tickets(cli, num):
    for i in range(num, 0, -1):
        sv = SetVoltage(voltage=i).serialize()
        print(f"Send {sv}")
        resp = cli.query(sv)
        print(f"Responsed {resp}")
    return


def main():
    from random import randint

    idx = randint(1, 100)
    print(f"Send {idx} messages")

    cli = Client("tcp://localhost:5559")
    post_tickets(cli, idx)
    print("End")
    return


if __name__ == "__main__":
    main()
