from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from typing import List, Dict
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

class Lobby:
    def __init__(self, name: str):
        self.name = name
        self.players: Dict[str, WebSocket] = {}
        self.ready = Dict[str, bool] = {}

lobbies: Dict[str, Lobby] = {}

@app.post("/create_lobby")
def create_lobby(lobby_name: str):
    if lobby_name in lobbies:
        raise HTTPException(status_code=400, detail=f"Lobby '{lobby_name}' already exists")
    lobbies[lobby_name] = Lobby(name=lobby_name)
    return {"message": f"Lobby '{lobby_name}' created"}

@app.delete("/delete_lobby")
def delete_lobby(lobby_name: str):
    if lobby_name not in lobbies:
        raise HTTPException(status_code=404, detail=f"Lobby '{lobby_name}' doesn't exist")
    del lobbies[lobby_name]
    return {"message": f"Lobby '{lobby_name}' deleted"}

@app.get("/lobbies")
def list_lobbies():
    # return {name: {"playerCount": len(lobby.players)} for name, lobby in lobbies.items()}
    return {'lobbies': [{'lobby_name': name, 'player_count': len(lobby.players)} for name, lobby in lobbies.items()]}

# WebSocket connection for real-time communication
@app.websocket("/join_lobby/{lobby_name}/{player_name}")
async def join_lobby(websocket: WebSocket, lobby_name: str, player_name: str):
    if lobby_name not in lobbies:
        await websocket.close()
        raise HTTPException(status_code=404, detail=f"Lobby '{lobby_name}' not found")
    if player_name in lobbies[lobby_name].players:
        await websocket.close()
        raise HTTPException(status_code=400, detail=f"Player '{player_name}' is already in the lobby '{lobby_name}'")
    await websocket.accept()
    try:
        lobbies[lobby_name].players[player_name] = websocket
        lobbies[lobby_name].ready[player_name] = False
        while True:
            data = await websocket.receive_text()
            logging.info(data)
            try:
                # Handle incoming data
                action = parse_action(data)
                await handle_action(action, websocket, lobby_name, player_name)
                # ...
            except ValueError as err:
                # websocket.send_json type: error, value: err
                print(f"Action Value Error: {err}")
    except WebSocketDisconnect:
        del lobbies[lobby_name].players[player_name] # Remove disconnected player
        del lobbies[lobby_name].ready[player_name]
        # Reconnect attempt needed first?
        if not lobbies[lobby_name].players:
            del lobbies[lobby_name]  # Delete lobby if empty

def parse_action(message: str):
    try:
        data = json.loads(message)
        if 'type' in data:
            return data
        else:
            raise ValueError("Message does not contain an action type")
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON message")

async def handle_action(action, websocket, lobby_name, player_name):
    if action['type'] == "ready_up":
        lobbies[lobby_name].ready[player_name] = True
        message = {
            "type": "ready_status",
            "player": player_name,
            "is_ready": True
        }
        await broadcast_message(lobby_name, player_name, message)
    elif action['type'] == "ready_down":
        lobbies[lobby_name].ready[player_name] = True
        message = {
            "type": "ready_status",
            "player": player_name,
            "is_ready": False
        }
        await broadcast_message(lobby_name, player_name, message)

async def broadcast_message(lobby_name: str, player_name: str, message: dict):
    if lobby_name in lobbies:
        json_string = json.dumps(message)
        for player, websocket in lobbies[lobby_name].players.items():
            if player != player_name:
                await websocket.send_text(json_string)