from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Dict
from pydantic import BaseModel

app = FastAPI()

class Lobby(BaseModel):
    name: str
    players: List[str] = []

lobbies: Dict[str, Lobby] = {}

@app.post("/create_lobby")
def create_lobby(lobby: Lobby):
    if lobby.name in lobbies:
        raise HTTPException(status_code=400, detail="Lobby already exists")
    lobbies[lobby.name] = lobby
    return {"message": f"Lobby '{lobby.name}' created"}

@app.post("/join_lobby/{lobby_name}")
def join_lobby(lobby_name: str, player_name: str):
    
    if lobby_name not in lobbies:
        raise HTTPException(status_code=404, detail="Lobby not found")
    if player_name in lobbies[lobby_name].players:
        raise HTTPException(status_code=400, detail="Player already in the lobby")
    return {"message": f"Player '{player_name}' can join lobby '{lobby_name}'"}

@app.get("/lobbies")
def list_lobbies():
    return lobbies

# WebSocket connection for real-time communication
@app.websocket("/ws/{lobby_name}/{player_name}")
async def websocket_endpoint(websocket: WebSocket, lobby_name: str, player_name: str):
    await websocket.accept()
    try:
        if lobby_name not in lobbies:
            await websocket.close(code=1001)
            return
        lobbies[lobby_name].players.append(player_name)
        while True:
            data = await websocket.receive_text()
            # Handle incoming data
            # ...
    except WebSocketDisconnect:
        lobbies[lobby_name].players.remove(player_name)
        if not lobbies[lobby_name].players:
            del lobbies[lobby_name]  # Delete lobby if empty
