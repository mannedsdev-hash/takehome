"""Text-only Claude calls used for learning and reflection (the desktop loop lives in agent.py)."""

import anthropic

from . import config

client = anthropic.Anthropic()


def write_markdown(system: str, content: list[dict], effort: str | None = None) -> str:
    """Ask Claude for a markdown document. Streams so long outputs don't hit HTTP timeouts.

    Server-side refusal fallbacks are on: if the request is declined by a safety classifier,
    the API re-runs it on Anthropic's recommended fallback model instead of failing.
    """
    with client.beta.messages.stream(
        model=config.MODEL,
        max_tokens=32000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=system,
        output_config={"effort": effort or config.LEARN_EFFORT},
        messages=[{"role": "user", "content": content}],
    ) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        raise RuntimeError("Claude declined this request; nothing was written.")
    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    if msg.stop_reason == "max_tokens":
        raise RuntimeError("Output was cut off at max_tokens; nothing was written.")
    # Accept either raw markdown or a single fenced block.
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return text.strip()
