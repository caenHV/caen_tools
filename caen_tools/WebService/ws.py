import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

from caen_setup.Tickets.TicketType import TicketType
from caen_tools.connection.client import AsyncClient

QMAXSIZE = 10
SERVADDR = "tcp://localhost:5559"

app = FastAPI()
queue = asyncio.Queue(maxsize=QMAXSIZE)


async def fifo_worker():
    print("Start queue work")
    cli = AsyncClient(SERVADDR)
    while True:
        job = await queue.get()
        print(f"Get job {job}")
        resp = await cli.query(job)
        print(f"Resp: {resp}")


@app.on_event("startup")
async def startup():
    asyncio.create_task(fifo_worker())


@app.get("/")
async def read_root():
    return FileResponse("caen_tools/WebService/index.html")


@app.get("/list_tickets")
def read_list_tickets():
    """[WS Backend API] Returns a list of available tickets"""

    data = [(t.value.type_description().__dict__) for t in TicketType]
    return data


@app.post("/set_ticket/{name}")
async def post_ticket(name: str, ticket_args: Request = None):
    """[WS Backend API] Sends ticket on the setup"""
    args_dict = await ticket_args.json() if ticket_args else {}
    tkt_json = {"name": name, "params": args_dict}
    print(f"Query ticket: {tkt_json}")
    await queue.put(tkt_json)
    return {"status": "registered"}
