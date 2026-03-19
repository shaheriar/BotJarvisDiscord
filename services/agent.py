"""Agent runner for iterative tool-calling execution."""
from __future__ import annotations

import json
import logging
import time
from typing import Awaitable, Callable

from openai import AsyncOpenAI

import config

logger = logging.getLogger(__name__)

ToolExecutor = Callable[[str, dict], Awaitable[tuple[str, str]]]
ProgressCallback = Callable[[str], Awaitable[None]]


def _tool_status_text(tool_name: str) -> str:
    mapping = {
        "web_search": "Searching the web for recent information...",
        "web_search_deep": "Digging deeper across multiple web sources...",
        "web_fetch": "Reading the source page for details...",
        "browser_visit": "Loading the page in browser mode...",
        "get_news": "Gathering the latest headlines and reports...",
        "get_weather": "Checking weather data and conditions...",
        "get_stock": "Analyzing stock market data and trends...",
        "get_crypto": "Analyzing crypto market data and trends...",
        "wikipedia_lookup": "Looking up background context...",
        "translate_text": "Translating the requested text...",
        "music_play_youtube": "Queueing your track...",
    }
    return mapping.get(tool_name, f"Using tool: `{tool_name}`...")


class AgentRunner:
    """Run a bounded planner/executor loop around OpenAI tool calls."""

    def __init__(
        self,
        *,
        client: AsyncOpenAI,
        tools: list[dict],
        model: str,
        tool_executor: ToolExecutor,
    ) -> None:
        self._client = client
        self._tools = tools
        self._model = model
        self._tool_executor = tool_executor

    async def run(
        self,
        *,
        msg_list: list,
        initial_assistant_msg,
        initial_tool_calls: list,
        progress_callback: ProgressCallback | None = None,
    ) -> tuple[object, list[str], dict]:
        """Return (assistant_message, used_sources, telemetry)."""

        used_sources: list[str] = []
        tool_calls = initial_tool_calls
        assistant_msg = initial_assistant_msg
        iteration_count = 0
        total_tool_payload_chars = 0
        tool_count = 0

        if progress_callback:
            await progress_callback("Planning next steps...")

        while tool_calls and iteration_count < max(1, config.JARVIS_MAX_AGENT_ITERATIONS):
            iteration_count += 1
            msg_list.append(assistant_msg)
            if progress_callback:
                await progress_callback(
                    f"Research step {iteration_count}/{max(1, config.JARVIS_MAX_AGENT_ITERATIONS)}..."
                )

            for tc in tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except Exception:
                    args = {}

                started = time.monotonic()
                if progress_callback:
                    await progress_callback(_tool_status_text(name))
                result_text, source_label = await self._tool_executor(name, args)
                elapsed_ms = int((time.monotonic() - started) * 1000)
                tool_count += 1

                if source_label and source_label not in used_sources:
                    used_sources.append(source_label)

                tool_payload = {
                    "type": "tool_result",
                    "trusted": False,
                    "source": source_label or "",
                    "data": result_text,
                }
                serialized = json.dumps(tool_payload, ensure_ascii=False)
                total_tool_payload_chars += len(serialized)
                msg_list.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": "[TOOL_RESULT_DATA ONLY]\n" + serialized + "\n[/TOOL_RESULT]",
                    }
                )

                logger.info(
                    "agent_tool_call",
                    extra={
                        "tool_name": name,
                        "latency_ms": elapsed_ms,
                        "iteration": iteration_count,
                    },
                )

                # Hard stop on tool payload growth to keep cost bounded.
                if total_tool_payload_chars > config.JARVIS_MAX_RESEARCH_CHARS:
                    logger.warning(
                        "agent_budget_reached",
                        extra={
                            "reason": "max_research_chars",
                            "max_research_chars": config.JARVIS_MAX_RESEARCH_CHARS,
                        },
                    )
                    tool_calls = []
                    break

            if not tool_calls:
                break

            response_obj = await self._client.chat.completions.create(
                model=self._model,
                messages=msg_list,
                tools=self._tools,
                tool_choice="auto",
                temperature=config.JARVIS_RESPONSE_TEMPERATURE,
                max_tokens=config.JARVIS_TOOL_REQUERY_MAX_TOKENS,
            )
            choice = response_obj.choices[0]
            assistant_msg = choice.message
            tool_calls = getattr(assistant_msg, "tool_calls", None) or []

        # Optional post-answer self-critique for deeper research quality.
        if (
            config.JARVIS_SELF_CRITIQUE
            and iteration_count < max(1, config.JARVIS_MAX_AGENT_ITERATIONS)
            and not tool_calls
        ):
            if progress_callback:
                await progress_callback("Reviewing answer quality...")
            msg_list.append(assistant_msg)
            critique_prompt = (
                "Check the draft answer for gaps. "
                "If any factual claim lacks support, call tools. "
                "If complete and well-supported, return the final answer directly."
            )
            msg_list.append({"role": "user", "content": critique_prompt})
            critique_obj = await self._client.chat.completions.create(
                model=self._model,
                messages=msg_list,
                tools=self._tools,
                tool_choice="auto",
                temperature=0.2,
                max_tokens=config.JARVIS_TOOL_REQUERY_MAX_TOKENS,
            )
            critique_choice = critique_obj.choices[0]
            critique_msg = critique_choice.message
            critique_calls = getattr(critique_msg, "tool_calls", None) or []
            if critique_calls:
                msg_list.pop()  # remove critique prompt
                msg_list.pop()  # remove appended assistant message
                return await self.run(
                    msg_list=msg_list,
                    initial_assistant_msg=critique_msg,
                    initial_tool_calls=critique_calls,
                    progress_callback=progress_callback,
                )
            assistant_msg = critique_msg

        if progress_callback:
            await progress_callback("Finalizing response...")

        telemetry = {
            "iterations": iteration_count,
            "tools_called": tool_count,
            "used_sources": used_sources,
        }
        logger.info("agent_run_complete", extra=telemetry)
        return assistant_msg, used_sources, telemetry
