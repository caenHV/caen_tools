import asyncio
import os

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


from caen_setup.Tickets.TicketType import TicketType
from caen_tools.connection.client import AsyncClient
from caen_tools.utils.utils import config_processor, get_timestamp
from caen_tools.utils.receipt import (
    Receipt,
    ReceiptJSONEncoder,
    ReceiptJSONDecoder,
    ReceiptResponse,
)


settings = config_processor(None)

SERVADDR = settings.get("ws", "proxy_address")
RECTIME = settings.get("ws", "receive_time")

app = FastAPI()
cli = AsyncClient(SERVADDR, RECTIME)

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


@app.on_event("startup")
async def startup():
    pass
    # asyncio.create_task(fifo_worker())


@app.get("/")
async def read_root():
    return FileResponse("caen_tools/WebService/build/index.html")


@app.get("/list_tickets")
def read_list_tickets():
    """[WS Backend API] Returns a list of available tickets"""

    data = [(t.value.type_description().__dict__) for t in TicketType]
    return data


# Device backend API routes

@app.get("/device_backend/status")
async def read_parameters(sender: str = "webcli"):
    """[WS Backend API] Returns Monitor information"""
    import random

    receipt = Receipt(
        sender=sender,
        executor="device_backend",
        title="status",
        params={"voltage": random.randint(0, 1000)},
    )
    print("query", receipt)
    resp = await cli.query(receipt)
    print("Response", resp)
    return resp

@app.post("/device_backend/set_voltage")
async def set_voltage(target_voltage: float):
    """[WS Backend API] Sets voltage on CAEN setup"""
    receipt = Receipt(
        sender="webcli",
        executor="device_backend",
        title="set_voltage",
        params={"target_voltage": target_voltage},
    )
    resp = await cli.query(receipt)
    return resp

@app.post("/device_backend/down")
async def down():
    """[WS Backend API] Turns off voltage from CAEN setup"""
    receipt = Receipt(
        sender="webcli",
        executor="device_backend",
        title="down",
        params={},
    )
    resp = await cli.query(receipt)
    return resp

@app.get("/device_backend/params")
async def params():
    """[WS Backend API] Gets parameters of CAEN setup"""
    receipt = Receipt(
        sender="webcli",
        executor="device_backend",
        title="params",
        params={},
    )
    resp = await cli.query(receipt)
    return resp
