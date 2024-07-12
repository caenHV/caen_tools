"""WebServer implementation"""

from enum import Enum
from collections import namedtuple

import os
import argparse
import logging

import uvicorn

from fastapi import FastAPI, Body, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from fastapi_utils.tasks import repeat_every

from caen_tools.connection.client import AsyncClient
from caen_tools.utils.utils import config_processor, get_timestamp, get_logging_config
from caen_tools.utils.receipt import Receipt
from caen_tools.WebService.utils import response_provider

# Initialization part
# -------------------

parser = argparse.ArgumentParser(description="CAEN Manager WebService")
parser.add_argument(
    "-c",
    "--config",
    required=False,
    type=argparse.FileType("r"),
    help="Config file",
    nargs="?",
)
console_args = parser.parse_args()
settings = config_processor(console_args.config)

get_logging_config(
    level=settings.get("ws", "loglevel"),
    filepath=settings.get("ws", "logfile"),
)

Service = namedtuple("Service", ["title", "address"])


class Services(Enum):
    """A list of microservices"""

    @property
    def title(self):
        """Returns a title of the microservice"""
        return self.value.title

    @property
    def address(self):
        """Returns an adress of the microservice"""
        return self.value.address

    DEVBACK = Service("device_backend", settings.get("ws", "device_backend"))
    MONITOR = Service("monitor", settings.get("ws", "monitor"))


tags_metadata = [
    {
        "name": Services.DEVBACK.title,
        "description": "**DeviceBackend** microservice (Direct interaction with CAEN setup)",
    },
    {
        "name": Services.MONITOR.title,
        "description": "**Monitor** microservice (Interaction with Databases and SystemCheck)",
    },
]

app = FastAPI(
    title="CAEN Manager App",
    summary="Application to run high voltage on CAEN",
    version="1.0",
)
cli = AsyncClient(
    {s.title: s.address for s in Services},
    settings.get("ws", "receive_time"),
)

root = os.path.dirname(os.path.abspath(__file__))
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(root, "frontend", "build", "static")),
    name="static",
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Schedulers part
# ---------------


@app.on_event("startup")
@repeat_every(seconds=1)
async def system_control() -> None:
    """The scheduled script for
    continious system control.

    1. Gets parameters of the system
    2. Sends them to monitor
    3. Get system check response
    4. Down voltage in case of failed check
    """

    logging.info("Start system control script")
    params = await deviceparams()  # get device parameters
    dbresp = await setparamsdb(params.response.body["params"])

    if not dbresp.response["body"]["params_ok"]:
        logging.error("Bad device parameters. Emergency DownVoltage")
        await down()

    return


@app.get("/")
async def read_root():
    """Redirect on frontend page"""
    return FileResponse(os.path.join(root, "frontend", "build", "index.html"))


# API part
# --------

# Device backend API routes


@app.get(f"/{Services.DEVBACK.title}/status", tags=[Services.DEVBACK.title])
@response_provider
async def read_parameters(sender: str = "webcli") -> Receipt:
    """[WS Backend API] Returns service status information"""

    receipt = Receipt(
        sender=sender,
        executor=Services.DEVBACK.title,
        title="status",
        params={},
    )
    resp = await cli.query(receipt)
    return resp


@app.post(f"/{Services.DEVBACK.title}/set_voltage", tags=[Services.DEVBACK.title])
@response_provider
async def set_voltage(target_voltage: float = Body(embed=True)) -> Receipt:
    """[WS Backend API] Sets voltage on CAEN setup"""
    receipt = Receipt(
        sender="webcli",
        executor=Services.DEVBACK.title,
        title="set_voltage",
        params={"target_voltage": target_voltage},
    )
    resp = await cli.query(receipt)
    return resp


@app.post(f"/{Services.DEVBACK.title}/down", tags=[Services.DEVBACK.title])
@response_provider
async def down() -> Receipt:
    """[WS Backend API] Turns off voltage from CAEN setup"""
    receipt = Receipt(
        sender="webcli",
        executor=Services.DEVBACK.title,
        title="down",
        params={},
    )
    resp = await cli.query(receipt)
    return resp


@app.get(f"/{Services.DEVBACK.title}/params", tags=[Services.DEVBACK.title])
@response_provider
async def deviceparams():
    """[WS Backend API] Gets parameters of CAEN setup"""
    receipt = Receipt(
        sender="webcli",
        executor=Services.DEVBACK.title,
        title="params",
        params={},
    )
    resp = await cli.query(receipt)
    return resp


# Monitor API routes


@app.get(f"/{Services.MONITOR.title}/status", tags=[Services.MONITOR.title])
@response_provider
async def monstatus() -> Receipt:
    """[WS Backend API] Returns a status of the Monitor service"""
    receipt_in = Receipt(
        sender="webcli",
        executor=Services.MONITOR.title,
        title="status",
        params={},
    )
    receipt_out = await cli.query(receipt_in)
    return receipt_out


@app.get(f"/{Services.MONITOR.title}/getparams", tags=[Services.MONITOR.title])
@response_provider
async def paramsdb(
    start_timestamp: int = Query(),
    stop_timestamp: int | None = Query(default=None),
) -> Receipt:
    """[WS Backend API] Returns parameters from the Monitor microservice"""
    stop_timestamp = get_timestamp() if stop_timestamp is None else stop_timestamp
    receipt = Receipt(
        sender="webcli",
        executor=Services.MONITOR.title,
        title="get_params",
        params=dict(
            start_time=start_timestamp,
            end_time=stop_timestamp,
        ),
    )
    resp = await cli.query(receipt)
    return resp


@app.post(f"/{Services.MONITOR.title}/setparams", tags=[Services.MONITOR.title])
@response_provider
async def setparamsdb(
    params: dict[str, dict[str, float]] = Body(embed=True)
) -> Receipt:
    """[WS Backend API] Sends input parameters into Monitor"""
    receipt = Receipt(
        sender="webcli",
        executor=Services.MONITOR.title,
        title="send_params",
        params={"params": params},
    )
    resp = await cli.query(receipt)
    return resp


def main():
    """Runs server"""

    # 192.168.173.217:8000
    uvicorn.run(
        "caen_tools.WebService.ws:app",
        port=settings.getint("ws", "port"),
        log_level="info",
        host=settings.get("ws", "host"),
    )


if __name__ == "__main__":
    main()
