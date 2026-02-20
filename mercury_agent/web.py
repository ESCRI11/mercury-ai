"""FastAPI web server — chat endpoint, WebSocket streaming."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import Config
from .extractor import extract_code
from .mercury_client import MercuryClient
from .metrics import extract_metrics
from .prompt import build_system_prompt
from .provider_factory import create_provider
from .state import PieceState
from .tools import TOOL_DEFINITIONS, ToolDispatcher

STATIC_DIR = Path(__file__).parent.parent / "static"


def create_app(cfg: Config) -> FastAPI:
    app = FastAPI(title="Mercury AI")

    llm = create_provider(cfg)
    mercury = MercuryClient(base_url=cfg.mercury_url)
    state = PieceState(cfg.state_file)
    dispatcher = ToolDispatcher(mercury, state)
    system_prompt = build_system_prompt(cfg)
    use_tools = llm.supports_tools()

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        index_file = STATIC_DIR / "index.html"
        return index_file.read_text(encoding="utf-8")

    @app.get("/api/status")
    async def status():
        piece = state.read()
        provider_name = getattr(llm, "provider_name", cfg.provider)
        return {
            "provider": provider_name,
            "model": llm.model,
            "tools": use_tools,
            "piece_lines": len(piece.splitlines()) if piece else 0,
            "history_len": len(llm.history),
            "mercury_ok": mercury.health_check(),
            "llm_ok": llm.is_available(),
        }

    @app.get("/api/models")
    async def models():
        return {"models": llm.list_models(), "current": llm.model}

    @app.post("/api/model")
    async def set_model(body: dict):
        name = body.get("model", "")
        if name:
            llm.set_model(name)
            nonlocal use_tools
            use_tools = llm.supports_tools()
        return {"model": llm.model, "tools": use_tools}

    @app.post("/api/chat")
    async def chat(body: dict):
        user_text = body.get("message", "")
        if not user_text:
            return JSONResponse({"error": "missing message"}, status_code=400)

        messages = _build_messages(llm, state, mercury, system_prompt, user_text)
        llm.add_message("user", user_text)
        tools = TOOL_DEFINITIONS if use_tools else None

        full_content = ""
        code_sent: str | None = None
        tool_results: list[str] = []
        metrics = ResponseMetrics()
        max_tool_rounds = 5

        for _round in range(max_tool_rounds):
            response = llm.chat(messages, tools=tools, stream=False)
            msg = response.get("message", {})
            content = msg.get("content", "") or ""
            tc_list = msg.get("tool_calls")
            full_content += content
            metrics = extract_metrics(response)

            if not tc_list:
                break

            assistant_msg: dict = {"role": "assistant"}
            if content:
                assistant_msg["content"] = content
            assistant_msg["tool_calls"] = tc_list
            messages.append(assistant_msg)
            llm.add_tool_call(tc_list)

            for tc in tc_list:
                result = dispatcher.dispatch(tc)
                tc_id = tc.get("id", "")
                llm.add_tool_result(result, tool_use_id=tc_id)
                tool_results.append(result)
                messages.append({"role": "tool", "content": result, "tool_use_id": tc_id})

            code_sent = dispatcher.last_code_sent

        if not code_sent and full_content:
            code = extract_code(full_content)
            if code:
                mercury.send_code(code)
                state.write(code)
                code_sent = code

        if full_content:
            llm.add_message("assistant", full_content)
        llm.trim_history(min(cfg.context_window // 4, 4096))

        return {
            "reply": full_content,
            "code": code_sent,
            "tool_results": tool_results,
            "metrics": metrics.to_dict(),
        }

    @app.post("/api/play")
    async def play():
        code = state.read()
        if not code:
            return {"status": "no_piece", "code": None}
        mercury.send_code(code)
        return {"status": "playing", "code": code}

    @app.post("/api/silence")
    async def silence():
        mercury.silence()
        return {"status": "silenced"}

    @app.websocket("/ws")
    async def websocket_chat(ws: WebSocket):
        await ws.accept()
        try:
            while True:
                data = await ws.receive_text()
                payload = json.loads(data)
                user_text = payload.get("message", "")
                if not user_text:
                    await ws.send_json({"error": "missing message"})
                    continue

                try:
                    messages = _build_messages(llm, state, mercury, system_prompt, user_text)
                    llm.add_message("user", user_text)
                    tools = TOOL_DEFINITIONS if use_tools else None

                    full_content = ""
                    code_sent: str | None = None
                    tool_results_log: list[str] = []
                    last_chunk: dict = {}
                    max_tool_rounds = 5

                    for _round in range(max_tool_rounds):
                        round_content = ""
                        tool_calls: list[dict] = []

                        for chunk in llm.chat(messages, tools=tools, stream=True):
                            last_chunk = chunk
                            msg = chunk.get("message", {})
                            token = msg.get("content", "")
                            if token:
                                round_content += token
                                await ws.send_json({"type": "token", "content": token})
                            if msg.get("tool_calls"):
                                tool_calls.extend(msg["tool_calls"])

                        full_content += round_content

                        if not tool_calls:
                            break

                        assistant_msg: dict = {"role": "assistant"}
                        if round_content:
                            assistant_msg["content"] = round_content
                        assistant_msg["tool_calls"] = tool_calls
                        messages.append(assistant_msg)
                        llm.add_tool_call(tool_calls)

                        for tc in tool_calls:
                            result = dispatcher.dispatch(tc)
                            tc_id = tc.get("id", "")
                            tool_results_log.append(result)
                            await ws.send_json({"type": "tool", "name": tc.get("function", {}).get("name"), "result": result})
                            llm.add_tool_result(result, tool_use_id=tc_id)
                            messages.append({"role": "tool", "content": result, "tool_use_id": tc_id})

                        code_sent = dispatcher.last_code_sent

                    if not code_sent and full_content:
                        code = extract_code(full_content)
                        if code:
                            mercury.send_code(code)
                            state.write(code)
                            code_sent = code

                    if full_content:
                        llm.add_message("assistant", full_content)
                    llm.trim_history(min(cfg.context_window // 4, 4096))

                    metrics = extract_metrics(last_chunk) if last_chunk.get("done") else None

                    await ws.send_json({
                        "type": "done",
                        "code": code_sent,
                        "tool_results": tool_results_log,
                        "metrics": metrics.to_dict() if metrics else None,
                    })

                except Exception as exc:
                    await ws.send_json({"error": str(exc)})

        except WebSocketDisconnect:
            pass

    return app


def _build_messages(
    llm,
    state: PieceState,
    mercury: MercuryClient,
    system_prompt: str,
    user_text: str,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    current = mercury.get_current_code() or state.read()
    if current:
        state.write(current)
        messages.append({
            "role": "system",
            "content": f"Currently playing piece:\n```\n{current}\n```",
        })
    messages.extend(llm.history)
    messages.append({"role": "user", "content": user_text})
    return messages
