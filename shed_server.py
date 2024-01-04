from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from typing import List, Dict
from pydantic import BaseModel
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

class Lobby(BaseModel):
    name: str
    players: Dict[str, WebSocket] = {}

lobbies: Dict[str, Lobby] = {}

@app.post("/create_lobby")
def create_lobby(lobby: Lobby):
    if lobby.name in lobbies:
        raise HTTPException(status_code=400, detail=f"Lobby '{lobby.name}' already exists")
    lobbies[lobby.name] = lobby
    return {"message": f"Lobby '{lobby.name}' created"}

@app.delete("/delete_lobby")
def delete_lobby(lobby_name: str):
    if lobby_name not in lobbies:
        raise HTTPException(status_code=404, detail=f"Lobby '{lobby_name}' doesn't exist")
    del lobbies[lobby_name]
    return {"message": f"Lobby '{lobby_name}' deleted"}

# @app.get("/can_join_lobby/{lobby_name}")
# def can_join_lobby(lobby_name: str, player_name: str):
#     if lobby_name not in lobbies:
#         raise HTTPException(status_code=404, detail=f"Lobby '{lobby_name}' not found")
#     if player_name in lobbies[lobby_name].players:
#         raise HTTPException(status_code=400, detail=f"Player '{player_name}' is already in the lobby '{lobby_name}'")
#     return {"message": f"Player '{player_name}' can join lobby '{lobby_name}'"}

@app.get("/lobbies")
def list_lobbies():
    return lobbies

# WebSocket connection for real-time communication
@app.websocket("/join_lobby/{lobby_name}/{player_name}")
async def join_lobby(websocket: WebSocket, lobby_name: str, player_name: str):
    if lobby_name not in lobbies:
        raise HTTPException(status_code=404, detail=f"Lobby '{lobby_name}' not found")
    if player_name in lobbies[lobby_name].players:
        raise HTTPException(status_code=400, detail=f"Player '{player_name}' is already in the lobby '{lobby_name}'")
    await websocket.accept()
    try:
        lobbies[lobby_name].players.append(player_name)
        while True:
            data = await websocket.receive_text()
            # Handle incoming data
            # ...
    except WebSocketDisconnect:
        lobbies[lobby_name].players.remove(player_name)
        if not lobbies[lobby_name].players:
            del lobbies[lobby_name]  # Delete lobby if empty