"""Turns demonstrations and run logs into skill markdown. This is the self-improvement loop:

  watch (you demo)  -> learn_from_recording -> skills/<task>.md
  do (agent tries)  -> runs/<task>/<stamp>.md -> reflect_on_run -> skills/<task>.md (revised)
"""

import re
from pathlib import Path

from . import config, llm
from .memory import Skill, read_profile, remember_fact
from .recorder import load_recording
from .screen import image_block

SKILL_FORMAT = """\
A skill file is the agent's playbook for one recurring task on the user's computer. Write it in
markdown with exactly these sections:

# <Task name>
## Goal
One or two sentences: what "done" looks like.
## When to use / inputs
What the user gives at the start (e.g. "a job URL") and anything to check first.
## Apps and places
Websites, apps, tabs, folders, and chat sessions involved, and how to recognise each on screen.
## Steps
Numbered, concrete steps. Name the visible labels to click, where things are, and what to wait for.
Sub-steps for loops ("for each job on the list ...").
## Decision rules
When to do what. Which fields the agent fills by itself and from which source (profile.md, a
previous output, a document), and which fields it must ALWAYS ask the user about.
## Ask the human
Exactly which questions to bring to the user and when. Prefer asking over guessing for anything
personal, legal (visa, sponsorship, demographics), or not seen in a demonstration.
## Confirm before
Irreversible actions that need the user's yes first (submit, send, pay, delete, accept terms).
## Pitfalls
Things that went wrong or nearly went wrong, and how to avoid them.
## Change log
Dated one-line entries for each revision: what was learned and from which demo or run.

Write rules that generalise across repetitions (e.g. "for each job"), not a transcript of one
session. Never put passwords, one-time codes, or payment details in the skill. Keep personal
facts out of the skill; they go in the facts block described below."""

FACTS_HEADER = "## Facts about the user"

LEARN_SYSTEM = f"""You are the learning module of a desktop agent that learns tasks by watching its user.
You get a recording of the user doing a task: an event log (clicks, typed text, copy/paste with
clipboard contents, notes the user typed for you) interleaved with screenshots. Clicks are marked
with a red ring on the screenshot taken just after them.

Infer what the user was doing and why, then write or update the skill file. If a skill file already
exists, merge: keep what is still true, add what this demonstration teaches, and fix what it
contradicts. User notes are the strongest signal; follow them.

{SKILL_FORMAT}

After the skill, add a final section titled exactly "{FACTS_HEADER}" with one bullet per reusable
fact about the user seen in the demo (name, email, phone, links, location, work authorisation,
answers they typed to standard questions). Leave out anything already in the profile and anything
secret. Write "- none" if there is nothing new. Output only the markdown."""

REFLECT_SYSTEM = f"""You are the reflection module of a desktop agent. The agent just attempted a task
using its skill file. You get the current skill, the run log (the agent's actions and notes, the
questions it asked and the user's answers, confirmations given or refused, and any stretch where
the user took over and did it themselves, with screenshots), and the profile.

Revise the skill so the next run goes better:
- Turn each user answer into a rule: either "fill X from profile/previous output" (if the answer is
  reusable) or "always ask the user about X" (if it is personal per occurrence).
- Turn every takeover or refused confirmation into a corrected step or a pitfall.
- Remove steps that turned out to be wrong; tighten steps that were slow.
Do not invent steps nobody performed.

{SKILL_FORMAT}

After the skill, add the "{FACTS_HEADER}" section as described: new reusable facts from the user's
answers, or "- none". Output only the markdown."""


def _split_facts(markdown: str) -> tuple[str, list[str]]:
    if FACTS_HEADER not in markdown:
        return markdown, []
    skill_md, facts_md = markdown.split(FACTS_HEADER, 1)
    facts = [m.strip() for m in re.findall(r"^\s*[-*]\s+(.+)$", facts_md, re.M)]
    return skill_md.strip(), [f for f in facts if f.lower() not in ("none", "none.")]


def _save(skill: Skill, markdown: str, **meta) -> list[str]:
    body, facts = _split_facts(markdown)
    skill.write(body, **meta)
    for fact in facts:
        remember_fact(fact)
    return facts


def recording_to_content(folder: Path, max_frames: int | None = None) -> list[dict]:
    """Interleave event lines and screenshots into Claude content blocks."""
    events = load_recording(folder)
    max_frames = max_frames or config.MAX_LEARN_FRAMES
    framed = [i for i, e in enumerate(events) if e.get("frame")]
    must = {i for i in framed if events[i]["kind"] in ("note", "start", "stop", "paste")}
    rest = [i for i in framed if i not in must]
    budget = max(0, max_frames - len(must))
    step = max(1, -(-len(rest) // budget)) if budget else len(rest) + 1
    keep = must | set(rest[::step])

    t0 = events[0]["t"] if events else 0
    content, lines = [], []
    for i, e in enumerate(events):
        desc = {k: v for k, v in e.items() if k not in ("t", "kind", "frame")}
        lines.append(f"[+{e['t'] - t0:6.1f}s] {e['kind']} {desc if desc else ''}".rstrip())
        if i in keep:
            content.append({"type": "text", "text": "\n".join(lines)})
            lines = []
            content.append(image_block(_load(folder / e["frame"]), "JPEG"))
    if lines:
        content.append({"type": "text", "text": "\n".join(lines)})
    return content


def _load(path: Path):
    from PIL import Image

    return Image.open(path).convert("RGB")


def learn_from_recording(task: str, folder: Path) -> Skill:
    skill = Skill(task)
    content = [
        {"type": "text", "text": f"Task name: {task}\n\nCurrent profile.md:\n{read_profile()}"},
        {"type": "text", "text": f"Current skill file:\n{skill.body() if skill.exists else '(none yet)'}"},
        {"type": "text", "text": "Recording of the user doing the task:"},
        *recording_to_content(folder),
    ]
    markdown = llm.write_markdown(LEARN_SYSTEM, content)
    demos = int(skill.meta().get("demonstrations", "0")) + 1
    facts = _save(skill, markdown, demonstrations=demos)
    print(f"Skill saved: {skill.path}  (demonstrations: {demos})")
    if facts:
        print(f"Added {len(facts)} fact(s) to {config.PROFILE_PATH}")
    return skill


def reflect_on_run(skill: Skill, run_log: Path, takeover_folders: list[Path], had_corrections: bool) -> None:
    content = [
        {"type": "text", "text": f"Current profile.md:\n{read_profile()}"},
        {"type": "text", "text": f"Current skill file:\n{skill.body()}"},
        {"type": "text", "text": f"Run log:\n{run_log.read_text(encoding='utf-8')}"},
    ]
    for i, folder in enumerate(takeover_folders, 1):
        content.append({"type": "text", "text": f"Takeover {i}: the user did this part themselves:"})
        content.extend(recording_to_content(folder, max_frames=20))
    markdown = llm.write_markdown(REFLECT_SYSTEM, content)

    meta = skill.meta()
    runs = int(meta.get("runs", "0")) + 1
    clean = 0 if had_corrections else int(meta.get("clean_runs_in_a_row", "0")) + 1
    _save(skill, markdown, runs=runs, clean_runs_in_a_row=clean)
    print(f"Skill revised from this run: {skill.path}")
    if meta.get("autonomy") != "trusted" and clean >= config.TRUST_AFTER_CLEAN_RUNS:
        print(
            f"{clean} runs in a row without corrections. If you are happy, promote it with:\n"
            f"  python -m apprentice trust \"{skill.slug}\""
        )
