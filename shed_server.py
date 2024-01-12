import asyncio
import json
import logging
import time
from typing import Dict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

# Set up logging
logging.basicConfig(level=logging.INFO)
# Initialise FastAPI
app = FastAPI()

PING_INTERVAL = 30


async def heartbeat(player_name: str, lobby_name: str, interval: float = PING_INTERVAL):
    while True:
        await asyncio.sleep(interval)
        await lobbies[lobby_name].message_player(player_name, "ping")
        logging.info("ping")


def parse_action(message: str):
    try:
        data = json.loads(message)
        if 'type' in data:
            return data
        raise ValueError("Message does not contain an action type")
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON message")


async def handle_action(action, lobby_name, player_name):
    if action['type'] == ActionTypes.READY:
        lobbies[lobby_name].players[player_name].ready = True
        message = {
            "type": StateTypes.READY_STATE,
            "player": player_name,
            "is_ready": action['is_ready']
        }
        await lobbies[lobby_name].broadcast(message, [player_name])
        if all(player.ready for player in lobbies[lobby_name].players.values()):
            message = {
                "type": StateTypes.ALL_READY,
                "all_ready": True
            }
            await lobbies[lobby_name].broadcast(message)


class Player:
    def __init__(self, websocket):
        self.websocket = websocket
        self.ready = False
        self.last_pong = 0
        self.connected = True

    def is_alive(self):
        return time.time() - self.last_pong <= PING_INTERVAL + 3


class Lobby:
    def __init__(self, name: str):
        self.name = name
        self.players: Dict[str, Player] = {}
        self.lock = asyncio.Lock()

    async def reset_ready_states(self):
        async with self.lock:
            for player in self.players.values():
                player.ready = False

    async def add_player(self, player_name: str, websocket: WebSocket):
        async with self.lock:
            self.players[player_name] = Player(websocket)

    async def remove_player(self, player_name: str, close_websocket: bool = False):
        async with self.lock:
            if close_websocket:
                await self.players[player_name].websocket.close()
            del self.players[player_name]

    async def message_player(self, player_name: str, message: str | dict):
        async with self.lock:
            if not self.players[player_name].is_alive():
                await self.players[player_name].websocket.close()
            json_string = message if isinstance(message, str) else json.dumps(message)
            await self.players[player_name].websocket.send_text(json_string)

    async def broadcast(self, message: str | dict, excluded_players: list = None):
        if excluded_players is None:
            excluded_players = []
        json_string = message if isinstance(message, str) else json.dumps(message)
        for player_name, player in self.players.items():
            if player_name not in excluded_players:
                try:
                    await self.message_player(player_name, json_string)
                except Exception as e:
                    logging.error(f"Error broadcasting to player {player_name}: {e}")


class ActionTypes:
    READY = 'ready'


class StateTypes:
    READY_STATE = 'ready_state'
    ALL_READY = 'all_ready'


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
    return {'lobbies': [{'lobby_name': name, 'player_count': len(lobby.players)} for name, lobby in lobbies.items()]}


@app.websocket("/join_lobby/{lobby_name}/{player_name}")
async def join_lobby(websocket: WebSocket, lobby_name: str, player_name: str):
    if lobby_name not in lobbies:
        await websocket.close()
        raise HTTPException(status_code=404, detail=f"Lobby '{lobby_name}' not found")
    if player_name in lobbies[lobby_name].players:
        await websocket.close()
        raise HTTPException(status_code=400, detail=f"Player '{player_name}' is already in the lobby '{lobby_name}'")
    await websocket.accept()

    await lobbies[lobby_name].add_player(player_name, websocket)
    heartbeat_task = asyncio.create_task(heartbeat(player_name, lobby_name))
    lobbies[lobby_name].players[player_name].last_pong = time.time()

    try:
        while True:
            data = await websocket.receive_text()
            if data == "pong":
                lobbies[lobby_name].players[player_name].last_pong = time.time()
                continue
            action = parse_action(data)
            await handle_action(action, lobby_name, player_name)
    except WebSocketDisconnect:
        await lobbies[lobby_name].remove_player(player_name)
        if all(player.ready for player in lobbies[lobby_name].players.values()):
            message = {
                "type": StateTypes.ALL_READY,
                "all_ready": False
            }
            await lobbies[lobby_name].broadcast(message)
            await lobbies[lobby_name].reset_ready_states()
        if not lobbies[lobby_name].players:
            del lobbies[lobby_name]
    finally:
        heartbeat_task.cancel()