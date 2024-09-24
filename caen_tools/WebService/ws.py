"""WebServer implementation"""

from enum import Enum
from collections import namedtuple
from typing import Annotated

import os
import argparse
import logging

import uvicorn

from fastapi import FastAPI, Body, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from fastapi_utils.tasks import repeat_every

from caen_tools.connection.client import AsyncClient
from caen_tools.connection.websockpub import WSPubManager
from caen_tools.utils.utils import config_processor, get_timestamp, get_logging_config
from caen_tools.utils.receipt import Receipt
from caen_tools.WebService.utils import response_provider, send_mail

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
settings.add_section("global_pars")
settings.set("global_pars", "last_target_voltage", "0.0")
settings.set("global_pars", "is_interlock", "True")

get_logging_config(
    level=settings.get("ws", "loglevel"),
    filepath=settings.get("ws", "logfile"),
)
logging.info(
    "Successfuly started WebService with arguments %s",
    dict(settings.items("ws")),
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
    SYSCHECK = Service("system_check", settings.get("ws", "system_check"))


tags_metadata = [
    {
        "name": Services.DEVBACK.title,
        "description": "**DeviceBackend** microservice (Direct interaction with CAEN setup)",
    },
    {
        "name": Services.MONITOR.title,
        "description": "**Monitor** microservice (Interaction with Databases and SystemCheck)",
    },
    {
        "name": Services.SYSCHECK.title,
        "description": "**System check** (parameter control and interlock following)",
    },
]

INTERLOCK_VAL = settings.get("ws", "interlock_follow")

app = FastAPI(
    title="CAEN Manager App",
    summary="Application to run high voltage on CAEN",
    version="1.0",
)
cli = AsyncClient(
    {s.title: s.address for s in Services},
    settings.get("ws", "receive_time"),
)
wspub = WSPubManager()

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
    continious broadcasting system state.

    1. Gets parameters of the system
    2. Broadcast them to subscribers
    """

    SRV_NAME = "broadcaster"
    logging.info("Broadcasting time")
    params = await deviceparams(SRV_NAME)  # get device parameters
    wspayload = {"body": params.response.body, "timestamp": params.response.timestamp}
    await wspub.broadcast(wspayload)  # Broadcast parameters via websocket connection
    return


@app.on_event("shutdown")
async def last_scream() -> None:
    """Actions on shutdown server"""

    logging.info("Start server shutdown actions")

    subslist = list(
        filter(lambda x: ("@" in x), settings.get("ws", "subscribers").split("\n"))
    )
    logging.info("Send shutdown info emails to %s", subslist)
    send_mail(subslist, "CAEN WebServer shutdown", "Hello! WebServer shutdown.")
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
    """[WS Backend API]
    Returns `device_backend` status.

    Parameters
    ----------
    - **sender**: string identifier of the request sender
    """

    receipt = Receipt(
        sender=sender,
        executor=Services.DEVBACK.title,
        title="status",
        params={},
    )
    resp = await cli.query(receipt)
    return resp


@app.get(f"/{Services.DEVBACK.title}/user_permissions", tags=[Services.DEVBACK.title])
@response_provider
async def get_user_permission(sender: str = "webcli") -> Receipt:
    """[WS Backend API]
    Returns user permissions for setting voltaget.

    Parameters
    ----------
    - **sender**: string identifier of the request sender
    """

    receipt = Receipt(
        sender=sender,
        executor=Services.DEVBACK.title,
        title="get_user_permission",
        params={},
    )
    resp = await cli.query(receipt)
    return resp


@app.post(f"/{Services.DEVBACK.title}/set_voltage", tags=[Services.DEVBACK.title])
@response_provider
async def set_voltage(
    target_voltage: Annotated[float, Body()], sender: Annotated[str, Body()] = "webcli"
) -> Receipt:
    """[WS Backend API]
    Sets voltage on CAEN setup

    Parameters
    ----------
    - **target_voltage**: float value of the voltage to be set
    - **sender**: string identifier of the request sender
    """
    receipt = Receipt(
        sender=sender,
        executor=Services.DEVBACK.title,
        title="set_voltage",
        params={"target_voltage": target_voltage, "from_user": True},
    )
    logging.debug("Start setting voltage %s", target_voltage)
    resp = await cli.query(receipt)
    logging.debug("Voltage set on %s", target_voltage)
    return resp


@app.post(f"/{Services.DEVBACK.title}/down", tags=[Services.DEVBACK.title])
@response_provider
async def down(sender: Annotated[str, Body(embed=True)] = "webcli") -> Receipt:
    """[WS Backend API]
    Turns off voltage from CAEN setup

    Parameters
    ----------
    - **sender**: string identifier of the request sender
    """
    receipt = Receipt(
        sender=sender,
        executor=Services.DEVBACK.title,
        title="down",
        params={},
    )
    resp = await cli.query(receipt)
    return resp


@app.get(f"/{Services.DEVBACK.title}/params", tags=[Services.DEVBACK.title])
@response_provider
async def deviceparams(
    sender: Annotated[str, Query(max_length=50)] = "webcli"
) -> Receipt:
    """[WS Backend API]
    Gets parameters of CAEN setup

    Parameters
    ----------
    - **sender**: string identifier of the request sender
    """
    receipt = Receipt(
        sender=sender,
        executor=Services.DEVBACK.title,
        title="params",
        params={},
    )
    resp = await cli.query(receipt)
    return resp


@app.websocket(f"/{Services.DEVBACK.title}/ws")
async def websocket_endpoint(websocket: WebSocket):
    """[WS Backend API] Websocket endpoint
    to get CAEN setup parameters every second"""
    await wspub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        wspub.disconnect(websocket)
    return


# Monitor API routes


@app.get(f"/{Services.MONITOR.title}/status", tags=[Services.MONITOR.title])
@response_provider
async def monstatus(sender: Annotated[str, Query(max_length=50)] = "webcli") -> Receipt:
    """[WS Backend API]
    Returns a status of the Monitor service

    Parameters
    ----------
    - **sender**: string identifier of the request sender
    """
    receipt_in = Receipt(
        sender=sender,
        executor=Services.MONITOR.title,
        title="status",
        params={},
    )
    receipt_out = await cli.query(receipt_in)
    return receipt_out


@app.get(f"/{Services.MONITOR.title}/getparams", tags=[Services.MONITOR.title])
@response_provider
async def paramsdb(
    start_timestamp: Annotated[int, Query()],
    stop_timestamp: Annotated[int | None, Query()] = None,
    sender: Annotated[str, Query(max_length=50)] = "webcli",
) -> Receipt:
    """[WS Backend API]
    Returns parameters from the `monitor` microservice

    Parameters
    ----------
    - **start_timestamp**: start timestamp for data retrieval (in seconds)
    - **stop_timestamp**: stop timestamp for data retrieval  (in seconds)
    - **sender**: string identifier of the request sender
    """
    stop_timestamp = get_timestamp() if stop_timestamp is None else stop_timestamp
    receipt = Receipt(
        sender=sender,
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
    params: Annotated[dict[str, dict[str, float]], Body(embed=True)],
    sender: Annotated[str, Query(max_length=50)] = "webcli",
) -> Receipt:
    """[WS Backend API]
    Sends input parameters into `monitor`

    Parameters
    ----------
    - **params**: dictionary of the parameters to be set in monitor
    - **sender**: string identifier of the request sender
    """

    receipt = Receipt(
        sender=sender,
        executor=Services.MONITOR.title,
        title="send_params",
        params={"params": params},
    )
    resp = await cli.query(receipt)
    return resp


# System check API routes


@app.get(f"/{Services.SYSCHECK.title}/last_check", tags=[Services.SYSCHECK.title])
async def last_check(
    sender: Annotated[str, Query(max_length=50)] = "webcli"
) -> Receipt:
    """[WS Backend API]
    Gets a timestamp of the last check performed

    Parameters
    ----------
    - **sender**: string identifier of the request sender
    """

    receipt = Receipt(
        sender=sender,
        executor=Services.SYSCHECK.title,
        title="last_check",
        params={},
    )
    resp = await cli.query(receipt)
    return resp


@app.get(
    f"/{Services.SYSCHECK.title}/is_interlock_follow", tags=[Services.SYSCHECK.title]
)
@response_provider
async def is_interlock_follow(
    sender: Annotated[str, Query(max_length=50)] = "webcli"
) -> Receipt:
    """[WS Backend API]
    Gets a state of the interlock following

    Parameters
    ----------
    - **sender**: string identifier of the request sender
    """

    receipt = Receipt(
        sender=sender,
        executor=Services.SYSCHECK.title,
        title="follow_ilock",
        params={},
    )
    resp = await cli.query(receipt)
    return resp


@app.post(
    f"/{Services.SYSCHECK.title}/set_interlock_follow", tags=[Services.SYSCHECK.title]
)
@response_provider
async def set_interlock_follow(
    value: Annotated[bool, Body()],
    sender: Annotated[str, Body(max_length=50)] = "webcli",
) -> Receipt:
    """[WS Backend API]
    Sets a state of the interlock following

    Parameters
    ----------
    - **value**: bool value to be set
    - **sender**: string identifier of the request sender
    """

    receipt = Receipt(
        sender=sender,
        executor=Services.SYSCHECK.title,
        title="set_follow_ilock",
        params={"value": value},
    )
    resp = await cli.query(receipt)
    return resp


def main():
    """Runs server"""

    # 192.168.173.217:8000
    uvicorn.run(
        "caen_tools.WebService.ws:app",
        port=settings.getint("ws", "port"),
        host=settings.get("ws", "host"),
        log_config=None,
        # workers=1,
    )


if __name__ == "__main__":
    main()
