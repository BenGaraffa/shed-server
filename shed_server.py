from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from typing import Dict
import time
import asyncio
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

class Player:
    def __init__(self, webSocket):
        self.webSocket = webSocket
        self.ready = False
        self.last_pong = 0
        self.connected = True

    def is_alive(self):
        return not time.time() - self.last_pong > 10

class Lobby:
    def __init__(self, name: str):
        self.name = name
        self.players: Dict[str, Player] = {}
        self.lock = asyncio.Lock()

    async def reset_ready_states(self):
        async with self.lock:
            # Set reset player ready states
            for player in self.players:
                player.ready = False
        
    async def add_player(self, player_name: str, webSocket: WebSocket):
        async with self.lock:
            try:
                self.players[player_name] = Player(webSocket)
            # change exception type in future
            except Exception as e:
                return e
            
    async def remove_player(self, player_name: str, close_webSocket: bool = False):
        async with self.lock:
            try:
                if close_webSocket:
                    await self.players[player_name].webSocket.close()
                del self.players[player_name]
            except Exception as e:
                return e
    
    async def messagePlayer(self, player_name: str, message: str | dict):
        async with self.lock:
            if not self.players[player_name].is_alive():
                await self.players[player_name].webSocket.close()
            json_string = message if type(message) == str else json.dumps(message)
            await self.players[player_name].webSocket.send_text(json_string)
            
    async def broadcast(self, message: str | dict, excluded_players: list = []):
        json_string = message if type(message) == str else json.dumps(message)
        for player_name in list(self.players.keys()):  # Use list to avoid runtime dictionary size change
            if player_name in excluded_players:
                continue
            try:
                await self.messagePlayer(player_name, json_string)
            except Exception as e:
                logging.error(f"Error broadcasting to player {player_name}: {e}")


class ActionTypes:
    READY = 'ready'

class StateTypes:
    READY_STATE = 'ready_state'
    ALL_READY   = 'all_ready'

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

# WebSocket connection for real-time communication
@app.websocket("/join_lobby/{lobby_name}/{player_name}")
async def join_lobby(webSocket: WebSocket, lobby_name: str, player_name: str):
    # Lobby connection validation
    if lobby_name not in lobbies:
        await webSocket.close()
        raise HTTPException(status_code=404, detail=f"Lobby '{lobby_name}' not found")
    if player_name in lobbies[lobby_name].players.keys():
        await webSocket.close()
        raise HTTPException(status_code=400, detail=f"Player '{player_name}' is already in the lobby '{lobby_name}'")
    await webSocket.accept()

    # Add player to lobby
    await lobbies[lobby_name].add_player(player_name, webSocket)

    try:
        # Heart beat setup
        heartbeat_task = asyncio.create_task(heartbeat(player_name, lobby_name))
        lobbies[lobby_name].players[player_name].last_pong = time.time()

        while True: # Websocket watch dog
            data = await webSocket.receive_text()

            # Ping pong heartbeat catch
            if data == "pong":
                lobbies[lobby_name].players[player_name].last_pong = time.time()
                continue  # Ignore the pong message and wait for the next message

            logging.info(data)
            try:
                # Handle incoming data
                action = parse_action(data)
                await handle_action(action, lobby_name, player_name)
                # ...
            except ValueError as err:
                # webSocket.send_json type: error, value: err
                logging.error(f"Action Value Error: {err}")

    except WebSocketDisconnect:
        await lobbies[lobby_name].remove_player(player_name)
        logging.info(f"Player '{player_name}' removed from lobby '{lobby_name}'") 

        # Make sure to unready all players if someone disconnects
        if all([player.ready for _, player in lobbies[lobby_name].players.items()]):
            # Broadcast ALL_READY as false
            message = {
                "type": StateTypes.ALL_READY,
                "all_ready": False
            }
            await lobbies[lobby_name].broadcast(message)
            await lobbies[lobby_name].reset_ready_states()
            
        # Reconnect attempt needed first?
        if not lobbies[lobby_name].players:
            del lobbies[lobby_name]  # Delete lobby if empty
    
    finally:
        heartbeat_task.cancel()

async def heartbeat(player_name: str, lobby_name: str, interval: float = 5.0):
    while True:
        await asyncio.sleep(interval)
        await lobbies[lobby_name].messagePlayer(player_name, "ping")

def parse_action(message: str):
    try:
        data = json.loads(message)
        if 'type' in data:
            return data
        else:
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

        if all([player.ready for _, player in lobbies[lobby_name].players.items()]):
            message = {
                "type": StateTypes.ALL_READY,
                "all_ready": True
            }
            await lobbies[lobby_name].broadcast(message)