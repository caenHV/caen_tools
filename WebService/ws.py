from fastapi import FastAPI
from CAENLib.tickets import Tickets

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
