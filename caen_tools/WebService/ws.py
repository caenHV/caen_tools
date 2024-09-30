"""WebServer implementation"""

from enum import Enum
from collections import namedtuple
from typing import Annotated

import os
import asyncio
import argparse
import logging

import uvicorn

from fastapi import FastAPI, Body, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from async_lru import alru_cache
from sse_starlette.sse import EventSourceResponse

from caen_tools.connection.client import AsyncClient
from caen_tools.utils.utils import config_processor, get_timestamp, get_logging_config
from caen_tools.utils.receipt import Receipt
from caen_tools.utils.resperrs import RResponseErrors
from caen_tools.WebService.utils import response_provider, send_mail, broadcaster

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


@app.get("/energy-icon.svg", include_in_schema=False)
async def read_favicon():
    """Reads favicon for the webpage"""
    return FileResponse(os.path.join(root, "frontend", "build", "energy-icon.svg"))


# API part
# --------

# Device backend API routes


@alru_cache(ttl=1)
async def devback_status(
    sender: str = "webcli", receive_time: float | None = None
) -> Receipt:
    """Returns a status of DeviceBackend
    (cache during 1 s)
    """

    logging.debug("Start devback_status")
    receipt = Receipt(
        sender=sender,
        executor=Services.DEVBACK.title,
        title="status",
        params={},
    )
    resp = await cli.query(receipt, receive_time)
    return resp


@app.get(f"/{Services.DEVBACK.title}/status", tags=[Services.DEVBACK.title])
@response_provider
async def read_parameters(sender: str = "webcli") -> Receipt:
    """[WS Backend API]
    Returns `device_backend` status.

    Parameters
    ----------
    - **sender**: string identifier of the request sender
    """

    logging.info("Start devback status task")
    response = await devback_status(sender)
    return response


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

    logging.info("Start setting voltage task by %s: %.3f", sender, target_voltage)

    set_voltage = Receipt(
        sender=sender,
        executor=Services.DEVBACK.title,
        title="set_voltage",
        params={"target_voltage": target_voltage, "from_user": True},
    )

    # Check if autopilot is enabled
    autopilot = Receipt(
        sender=sender,
        executor=Services.SYSCHECK.title,
        title="status_autopilot",
        params={},
    )
    autopilot = await cli.query(autopilot, 1)
    if autopilot.response.statuscode == 1:
        if autopilot.response.body["interlock_follow"]:
            logging.warning("Disabled set voltage (autopilot enabled): %s", autopilot)
            set_voltage.response = RResponseErrors.ForbiddenMethod(
                msg="SetVoltage is not enabled (due to enabled autopilot)"
            )
            return set_voltage

    logging.debug("Start setting voltage %s", target_voltage)
    set_voltage = await cli.query(set_voltage)
    logging.debug("Voltage set on %s", target_voltage)
    return set_voltage


@app.post(f"/{Services.DEVBACK.title}/down", tags=[Services.DEVBACK.title])
@response_provider
async def down(sender: Annotated[str, Body(embed=True)] = "webcli") -> Receipt:
    """[WS Backend API]
    Emergency call:
      Turns off voltage from CAEN device
      and turns off autopilot (if on)

    Parameters
    ----------
    - **sender**: string identifier of the request sender
    """

    logging.info("Start down voltage task")
    down_voltage = Receipt(
        sender=sender,
        executor=Services.DEVBACK.title,
        title="down",
        params={},
    )
    down_resp = await cli.query(down_voltage)

    autopilot_off = Receipt(
        sender=sender,
        executor=Services.SYSCHECK.title,
        title="set_autopilot",
        params={"value": False, "target_voltage": 0},
    )
    autopilot_resp = await cli.query(autopilot_off, receive_time=1)

    return down_resp


@alru_cache(ttl=1)
async def device_params(sender: str = "webcli") -> Receipt:
    """[WS Backend API]
    Gets parameters of CAEN setup

    Parameters
    ----------
    - **sender**: string identifier of the request sender
    """

    logging.debug("Start get device params cached function")
    receipt = Receipt(
        sender=sender,
        executor=Services.DEVBACK.title,
        title="params",
        params={},
    )
    response = await cli.query(receipt)
    return response


@app.get(f"/{Services.DEVBACK.title}/params", tags=[Services.DEVBACK.title])
@response_provider
async def device_params_api(
    sender: Annotated[str, Query(max_length=50)] = "webcli"
) -> Receipt:
    """[WS Backend API]
    Gets parameters of CAEN setup

    Parameters
    ----------
    - **sender**: string identifier of the request sender
    """

    logging.debug("Start device_params_api")
    response = await device_params(sender)
    return response


# Monitor API routes


@alru_cache(ttl=1)
async def monitor_status(
    sender: str = "webcli", receive_time: float | None = None
) -> Receipt:
    """Returns a status of Monitor
    (cache during 1 s)
    """

    logging.debug("Start monitor_status")
    receipt = Receipt(
        sender=sender,
        executor=Services.MONITOR.title,
        title="status",
        params={},
    )
    response = await cli.query(receipt, receive_time)
    return response


@app.get(f"/{Services.MONITOR.title}/status", tags=[Services.MONITOR.title])
@response_provider
async def monstatus(sender: Annotated[str, Query(max_length=50)] = "webcli") -> Receipt:
    """[WS Backend API]
    Returns a status of the Monitor service

    Parameters
    ----------
    - **sender**: string identifier of the request sender
    """

    logging.info("Start monitor status task")
    response = await monitor_status(sender)
    return response


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

    logging.info("Start montior/getparams task")
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

    logging.info("Start set_params_to_db task")
    receipt = Receipt(
        sender=sender,
        executor=Services.MONITOR.title,
        title="send_params",
        params={"params": params},
    )
    resp = await cli.query(receipt)
    return resp


# System check API routes


@alru_cache(ttl=1)
async def syscheck_status(
    sender: str = "webcli", receive_time: float | None = None
) -> Receipt:
    """Returns a status of System Check
    (cache during 1 s)
    """

    logging.debug("Start syscheck status")
    receipt = Receipt(
        sender=sender,
        executor=Services.SYSCHECK.title,
        title="status",
        params={},
    )
    response = await cli.query(receipt, receive_time)
    return response


@app.get(f"/{Services.SYSCHECK.title}/status", tags=[Services.SYSCHECK.title])
async def status_api(
    sender: Annotated[str, Query(max_length=50)] = "webcli"
) -> Receipt:
    """[WS Backend API]
    Gets a timestamp of the last check performed

    Parameters
    ----------
    - **sender**: string identifier of the request sender
    """

    logging.info("Start syschek status task")
    resp = await syscheck_status(sender)
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

    logging.info("Start autopilot status")
    receipt = Receipt(
        sender=sender,
        executor=Services.SYSCHECK.title,
        title="status_autopilot",
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
    target_voltage: Annotated[float, Body()],
    sender: Annotated[str, Body(max_length=50)] = "webcli",
) -> Receipt:
    """[WS Backend API]
    Sets a state of the Autopilot

    Parameters
    ----------
    - **value**: bool value to be set
    - **target_voltage**: a voltage multiplier to be maintained
    - **sender**: string identifier of the request sender
    """

    logging.info("Start set_autopilot")
    receipt = Receipt(
        sender=sender,
        executor=Services.SYSCHECK.title,
        title="set_autopilot",
        params={"value": value, "target_voltage": target_voltage},
    )
    resp = await cli.query(receipt)
    return resp


# Events stream


@app.get("/events/status", tags=["events"])
async def devback_status_broadcast() -> EventSourceResponse:
    """Broadcaster of the all system status

    Do not use different **senders** to acheive boost from cache functions
    """

    logging.debug("Start events/status")

    async def get_status(sender: str, rcv_time: float):
        async with asyncio.TaskGroup() as tg:
            devback = tg.create_task(devback_status(sender, rcv_time))
            monitor = tg.create_task(monitor_status(sender, rcv_time))
            syscheck = tg.create_task(syscheck_status(sender, rcv_time))

        response = {
            Services.DEVBACK.title: devback.result().response,
            Services.MONITOR.title: monitor.result().response,
            Services.SYSCHECK.title: syscheck.result().response,
        }
        return response

    return EventSourceResponse(
        broadcaster(1, get_status, sender="eventstream", rcv_time=1), send_timeout=5
    )


@app.get(f"/{Services.DEVBACK.title}/params_broadcast", tags=[Services.DEVBACK.title])
async def device_params_broadcast() -> EventSourceResponse:
    """Broadcaster of the device backend parameters

    Do not use sender to acheive the boost from cache function
    """

    logging.info("Start devback/params_broadcast")
    delay = 1  # in seconds
    return EventSourceResponse(
        broadcaster(delay, device_params, sender="eventstream"), send_timeout=5
    )


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
