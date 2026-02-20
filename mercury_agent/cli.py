"""Interactive CLI for the Ollama-Mercury orchestrator."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.theme import Theme

from .config import Config
from .extractor import extract_code
from .mercury_client import MercuryClient
from .metrics import ResponseMetrics, extract_metrics
from .prompt import build_system_prompt
from .provider_factory import create_provider
from .state import PieceState
from .tools import TOOL_DEFINITIONS, ToolDispatcher

_THEME = Theme({"info": "dim cyan", "warning": "bold yellow", "error": "bold red"})

HELP_TEXT = """\
[bold]Commands:[/bold]
  /play             Resend current piece (resume after silence)
  /silence          Stop all sound
  /model <name>     Switch model
  /models           List available models
  /status           Show current status
  /clear            Clear conversation history
  /help             Show this help
  /quit             Exit
"""


class _TimedSpinner:
    """A renderable that shows a spinner with a live elapsed-time counter."""

    _FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, t0: float) -> None:
        self._t0 = t0
        self._idx = 0

    def __rich_console__(self, console, options):
        elapsed = time.time() - self._t0
        frame = self._FRAMES[self._idx % len(self._FRAMES)]
        self._idx += 1
        yield Text(f"  {frame} thinking... ({elapsed:.0f}s)", style="dim")


class CLI:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.console = Console(theme=_THEME)
        self.llm = create_provider(cfg)
        self.mercury = MercuryClient(base_url=cfg.mercury_url)
        self.state = PieceState(cfg.state_file)
        self.dispatcher = ToolDispatcher(self.mercury, self.state)
        self.system_prompt = ""
        self.use_tools = False

    # -- startup --------------------------------------------------------------

    def _boot(self) -> bool:
        provider_name = getattr(self.llm, "provider_name", self.cfg.provider)
        self.console.print(f"\n[bold cyan]Mercury × LLM[/bold cyan]", justify="center")
        self.console.print(f"[dim]LLM-driven live coding ({provider_name})[/dim]\n", justify="center")

        # Check LLM provider
        self.console.print(f"[info]Checking {provider_name}...[/info]", end=" ")
        if not self.llm.is_available():
            self.console.print(f"[error]Not reachable. Check your {provider_name} configuration.[/error]")
            if self.cfg.provider == "ollama":
                self.console.print(f"[info]  Host: {self.cfg.ollama_host}[/info]")
            elif not self.cfg.api_key:
                self.console.print(f"[info]  No API key set. Use --api-key or set it in .env[/info]")
            return False

        models = self.llm.list_models()
        self.console.print(f"[green]OK[/green] ({len(models)} models)")

        # Validate model (only for Ollama where models must be pulled)
        if self.cfg.provider == "ollama" and models and self.llm.model not in models:
            self.console.print(f"[error]Model '{self.llm.model}' not found in Ollama.[/error]")
            self.console.print(f"[info]Available models:[/info]")
            for m in models:
                self.console.print(f"  {m}")
            self.console.print(f"\n[info]Pull it with:[/info] ollama pull {self.llm.model}")
            self.console.print(f"[info]Or use --model with one of the above.[/info]")
            return False

        # Check Mercury
        self.console.print("[info]Checking Mercury...[/info]", end=" ")
        if not self.mercury.health_check():
            self.console.print("[warning]Mercury not reachable at {0} (start it first)[/warning]".format(self.cfg.mercury_url))
        else:
            self.console.print("[green]OK[/green]")

        # Build system prompt
        self.console.print("[info]Building system prompt...[/info]", end=" ")
        self.system_prompt = build_system_prompt(self.cfg)
        token_est = len(self.system_prompt) // 4
        self.console.print(f"[green]OK[/green] (~{token_est} tokens)")

        # Probe tool-calling
        self.console.print(f"[info]Model:[/info] {self.llm.model}", end=" ")
        self.use_tools = self.llm.supports_tools()
        if self.use_tools:
            self.console.print("[green](tool-calling enabled)[/green]")
        else:
            self.console.print("[dim](code-extraction fallback)[/dim]")

        self.console.print(f"\nType [bold]/help[/bold] for commands.\n")
        return True

    # -- message handling -----------------------------------------------------

    def _build_messages(self, user_text: str) -> list[dict[str, Any]]:
        messages = [{"role": "system", "content": self.system_prompt}]
        current = self.mercury.get_current_code() or self.state.read()
        if current:
            self.state.write(current)
            messages.append({
                "role": "system",
                "content": f"Currently playing piece:\n```\n{current}\n```",
            })
        messages.extend(self.llm.history)
        messages.append({"role": "user", "content": user_text})
        return messages

    def _handle_streaming_response(self, user_text: str) -> str:
        messages = self._build_messages(user_text)
        self.llm.add_message("user", user_text)
        self.dispatcher.last_code_sent = None
        tools = TOOL_DEFINITIONS if self.use_tools else None
        max_tool_rounds = 5

        full_content = ""
        metrics = ResponseMetrics()
        started_printing = False

        t0 = time.time()
        spinner = _TimedSpinner(t0)
        live = Live(spinner, console=self.console, refresh_per_second=10, transient=True)
        live.start()

        try:
            for _round in range(max_tool_rounds):
                round_content = ""
                tool_calls: list[dict] = []
                last_chunk: dict[str, Any] = {}

                for chunk in self.llm.chat(messages, tools=tools, stream=True):
                    last_chunk = chunk
                    msg = chunk.get("message", {})

                    if msg.get("tool_calls"):
                        tool_calls.extend(msg["tool_calls"])

                    token = msg.get("content", "")
                    if token:
                        if not started_printing:
                            if live.is_started:
                                live.stop()
                            self.console.print()
                            started_printing = True
                        self.console.print(token, end="", highlight=False)
                        round_content += token

                full_content += round_content

                if last_chunk.get("done"):
                    metrics = extract_metrics(last_chunk)

                if not tool_calls:
                    if _round > 0 and not round_content and not self.dispatcher.last_code_sent:
                        self.console.print("  [dim yellow]⚠ Model returned empty after tool call (retrying may help)[/dim yellow]")
                    break

                assistant_msg: dict[str, Any] = {"role": "assistant"}
                if round_content:
                    assistant_msg["content"] = round_content
                assistant_msg["tool_calls"] = tool_calls
                messages.append(assistant_msg)
                self.llm.add_tool_call(tool_calls)

                for tc in tool_calls:
                    result = self.dispatcher.dispatch(tc)
                    tc_id = tc.get("id", "")
                    fn_name = tc.get("function", {}).get("name", "?")
                    if live.is_started:
                        live.stop()
                    preview = result.replace("\n", " ")[:80]
                    self.console.print(f"  [dim]tool:{fn_name} → {preview}[/dim]")

                    self.llm.add_tool_result(result, tool_use_id=tc_id)
                    messages.append({"role": "tool", "content": result, "tool_use_id": tc_id})

                if self.dispatcher.last_code_sent:
                    self._show_code(self.dispatcher.last_code_sent)

                t0 = time.time()
                spinner = _TimedSpinner(t0)
                live = Live(spinner, console=self.console, refresh_per_second=10, transient=True)
                live.start()
        finally:
            if live.is_started:
                live.stop()

        if started_printing:
            self.console.print()

        if self.dispatcher.last_code_sent:
            if full_content:
                self.llm.add_message("assistant", full_content)
            self._show_metrics(metrics)
            return full_content

        if full_content:
            self.llm.add_message("assistant", full_content)
            code = extract_code(full_content)
            if code:
                self.mercury.send_code(code)
                self.state.write(code)
                self._show_code(code)
                self.console.print("  [dim]→ Sent to Mercury[/dim]")

        self._show_metrics(metrics)
        return full_content

    def _show_metrics(self, metrics: ResponseMetrics) -> None:
        if metrics.generated_tokens > 0:
            self.console.print(f"  [dim]{metrics.format_compact()}[/dim]")

    def _show_code(self, code: str) -> None:
        syntax = Syntax(code, "text", theme="monokai", line_numbers=True)
        self.console.print(Panel(syntax, title="Mercury Code", border_style="cyan"))

    # -- slash commands -------------------------------------------------------

    def _handle_command(self, cmd: str) -> bool:
        parts = cmd.strip().split(maxsplit=1)
        verb = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if verb == "/quit":
            return False

        if verb == "/help":
            self.console.print(HELP_TEXT)
            return True

        if verb == "/play":
            code = self.state.read()
            if code:
                self.mercury.send_code(code)
                self.console.print(f"[info]Playing ({len(code.splitlines())} lines).[/info]")
            else:
                self.console.print("[warning]No piece to play.[/warning]")
            return True

        if verb == "/silence":
            self.mercury.silence()
            self.console.print("[info]Silenced.[/info]")
            return True

        if verb == "/model":
            if not arg:
                self.console.print(f"[info]Current model: {self.llm.model}[/info]")
                return True
            self.llm.set_model(arg.strip())
            self.use_tools = self.llm.supports_tools()
            tool_status = "tool-calling" if self.use_tools else "code-extraction"
            self.console.print(f"[info]Switched to {self.llm.model} ({tool_status})[/info]")
            return True

        if verb == "/models":
            models = self.llm.list_models()
            if models:
                for m in models:
                    marker = " [bold cyan]←[/bold cyan]" if m == self.llm.model else ""
                    self.console.print(f"  {m}{marker}")
            else:
                self.console.print("[warning]No models found[/warning]")
            return True

        if verb == "/status":
            piece = self.state.read()
            provider_name = getattr(self.llm, "provider_name", self.cfg.provider)
            self.console.print(
                f"  Provider: {provider_name}\n"
                f"  Model: {self.llm.model}\n"
                f"  Tools: {'yes' if self.use_tools else 'no'}\n"
                f"  Piece: {len(piece.splitlines())} lines\n"
                f"  History: {len(self.llm.history)} messages"
            )
            return True

        if verb == "/clear":
            self.llm.clear_history()
            self.console.print("[info]History cleared.[/info]")
            return True

        self.console.print(f"[warning]Unknown command: {verb}[/warning]")
        return True

    # -- main loop ------------------------------------------------------------

    async def run_async(self) -> None:
        if not self._boot():
            return

        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.console.input("[bold green]> [/bold green]")
                )
            except (EOFError, KeyboardInterrupt):
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            if user_input.startswith("/"):
                if not self._handle_command(user_input):
                    break
                continue

            try:
                self.llm.trim_history(min(self.cfg.context_window // 4, 4096))
                self._handle_streaming_response(user_input)
            except KeyboardInterrupt:
                self.console.print("\n[dim]Interrupted.[/dim]")
            except Exception as e:
                self.console.print(f"[error]Error: {e}[/error]")

        self.console.print("\n[dim]Goodbye.[/dim]")

    def run(self) -> None:
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            self.console.print("\n[dim]Goodbye.[/dim]")
