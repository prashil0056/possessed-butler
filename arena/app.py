import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from arena.schemas import (
    ArenaStatus,
    AttackRequest,
    AttackResponse,
    DefenseConfig,
    DefenseUpdateResponse,
    RoundInfo,
    StatsResponse,
)
from arena.state import arena_state


app = FastAPI(title="Possessed Butler Arena")

# Serve static files
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


# --- HTTP endpoints ---

@app.get("/")
async def index():
    """Serve the arena UI."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Arena running. UI not yet deployed — /static/index.html missing."}


@app.get("/api/status", response_model=ArenaStatus)
async def get_status():
    """Get current arena status: defense config, round info, stats."""
    return ArenaStatus(
        defense=DefenseConfig(**arena_state.defense),
        round=RoundInfo(**arena_state.round_info()),
        stats=StatsResponse(**arena_state.stats()),
    )


@app.post("/api/defense", response_model=DefenseUpdateResponse)
async def update_defense(new_defense: DefenseConfig):
    """Blue team updates defense config. Toggles, not code."""
    arena_state.save_defense(new_defense.model_dump())
    await manager.broadcast({
        "type": "defense_updated",
        "defense": new_defense.model_dump(),
    })
    return DefenseUpdateResponse(
        success=True,
        defense=new_defense,
        message="Defense updated. New attacks use this config.",
    )


@app.post("/api/attack", response_model=AttackResponse)
async def send_attack(request: AttackRequest):
    """Red team sends an attack. Runs through the current defense config."""
    # Lazy import — only load heavy modules when needed
    from harness.butler_sim import ButlerSim
    from blueteam.pipeline import DefensePipeline

    # Choose butler config based on defense toggle
    butler_config = (
        "harness/configs/butler_v2.yaml"
        if arena_state.defense.get("hardened_butler")
        else "harness/configs/butler_v1.yaml"
    )

    butler = ButlerSim(butler_config)
    pipeline = DefensePipeline("blueteam/configs/defense.yaml")

    # If input_guard is disabled in arena config, bypass it
    if not arena_state.defense.get("input_guard", True):
        pipeline.input_guard.SUSPICIOUS_PATTERNS = []

    # If output_guard is disabled, bypass it
    if not arena_state.defense.get("output_guard", True):
        pipeline.output_guard.canary_tokens = []
        pipeline.output_guard.secret_phrases = []
        pipeline.output_guard.forbidden_tools = []

    def butler_fn(wrapped):
        return butler.respond(wrapped)

    try:
        result = pipeline.protect(request.payload, butler_fn)
    except Exception as e:
        result = {
            "blocked": False,
            "block_layer": None,
            "reason": f"pipeline_error:{e}",
            "response": "",
        }

    attack_id = hashlib.sha256(
        (request.payload + datetime.now(timezone.utc).isoformat()).encode()
    ).hexdigest()[:12]
    timestamp = datetime.now(timezone.utc).isoformat()

    response_snippet = ""
    if result.get("response"):
        response_snippet = result["response"][:200]

    record = {
        "attack_id": attack_id,
        "payload": request.payload,
        "technique": request.technique,
        "blocked": result["blocked"],
        "block_layer": result.get("block_layer"),
        "reason": result["reason"],
        "response_snippet": response_snippet,
        "timestamp": timestamp,
    }

    arena_state.add_attack(record)

    response = AttackResponse(**record)

    await manager.broadcast({
        "type": "attack_result",
        "attack": record,
        "stats": arena_state.stats(),
    })

    return response


@app.post("/api/round/start")
async def start_round():
    """Start the 10-minute round timer."""
    info = arena_state.start_round()
    await manager.broadcast({"type": "round_started", "round": info})
    return {"success": True, "round": info}


@app.post("/api/round/reset")
async def reset_round():
    """Reset the round timer and clear stats."""
    arena_state.round_start = None
    arena_state.history = []
    await manager.broadcast({
        "type": "round_reset",
        "round": arena_state.round_info(),
        "stats": arena_state.stats(),
    })
    return {"success": True}


# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        # Send current state on connect
        await ws.send_json({
            "type": "initial_state",
            "defense": arena_state.defense,
            "round": arena_state.round_info(),
            "stats": arena_state.stats(),
        })

        while True:
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=1.0)
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # Periodic state push every second (for timer updates)
                await ws.send_json({
                    "type": "tick",
                    "round": arena_state.round_info(),
                    "stats": arena_state.stats(),
                })
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)
