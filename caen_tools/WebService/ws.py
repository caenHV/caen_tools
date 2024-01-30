"""WebService code"""

import asyncio
import os
import json

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from caen_setup.Tickets.TicketType import TicketType
from caen_tools.connection.client import AsyncClient
from caen_tools.MonitorService.query import QueryMaster
from caen_tools.utils.utils import config_processor, get_time_id
from caen_tools.utils.responsedict import ResponseDict


settings = config_processor(None)

QMAXSIZE = settings.getint("webservice", "querylimit")
SERVADDR = settings.get("webservice", "proxy_address")

app = FastAPI()
queue = asyncio.Queue(maxsize=QMAXSIZE)
queue_response = ResponseDict(maxsize=50)

root = os.path.dirname(os.path.abspath(__file__))
app.mount(
    "/static", StaticFiles(directory=os.path.join(root, "build/static")), name="static"
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def fifo_worker():
    print("Start queue work")
    cli = AsyncClient(SERVADDR)
    while True:
        timeid, address, job = await queue.get()
        print(f"Get job {job}")
        resp = await cli.query(job, address)
        queue_response[timeid] = resp
        print(f"Resp: {resp}")


@app.on_event("startup")
async def startup():
    asyncio.create_task(fifo_worker())


@app.get("/")
async def read_root():
    return FileResponse("caen_tools/WebService/build/index.html")


@app.get("/list_tickets")
def read_list_tickets():
    """[WS Backend API] Returns a list of available tickets"""

    data = [(t.value.type_description().__dict__) for t in TicketType]
    return data


@app.get("/params")
async def read_parameters(time):
    """[WS Backend API] Returns Monitor information"""

    mon_tkt = QueryMaster.serialize(time)
    timeid = get_time_id()
    print(f"Query ticket: {mon_tkt}")
    await queue.put((timeid, "monitor", mon_tkt))
    res = await queue_response.popwaiting(timeid)

    # from caen_tools.MonitorService.monitor import Monitor

    # mon_db = "./monitor.db"
    # res = Monitor.get_results(mon_db, start_time=time)
    return res['body']


@app.post("/set_ticket/{name}")
async def post_ticket(name: str, ticket_args: Request = None):
    """[WS Backend API] Sends ticket on the setup"""
    args_dict = await ticket_args.json() if ticket_args else {}
    tkt_json = json.dumps({"name": name, "params": args_dict})
    timeid = get_time_id()
    print(f"Query ticket: {tkt_json}")
    await queue.put((timeid, "setup", tkt_json))
    return {"status": "registered"}
