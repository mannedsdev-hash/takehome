"""Markdown memory: one profile file about you, one skill file per task, one log per run.

memory/
  profile.md              facts about you the agent may reuse (name, links, standard answers)
  skills/<task>.md        how to do one task: steps, decision rules, what to ask you, pitfalls
  runs/<task>/<stamp>.md  what happened on each attempt; reflection reads these to improve the skill
"""

import re
from datetime import datetime
from pathlib import Path

from . import config

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "task"


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def read_profile() -> str:
    if config.PROFILE_PATH.exists():
        return config.PROFILE_PATH.read_text(encoding="utf-8")
    return "# Profile\n\n(empty - the agent will add facts here as it learns them)\n"


def remember_fact(fact: str, section: str = "Learned facts") -> None:
    """Append a fact under a section of profile.md, creating the section if needed."""
    text = read_profile()
    heading = f"## {section}"
    line = f"- {fact.strip()}"
    if line in text:
        return
    if heading in text:
        start = text.index(heading) + len(heading)
        nxt = text.find("\n## ", start)
        insert_at = len(text) if nxt == -1 else nxt
        body = text[:insert_at].rstrip("\n") + "\n" + line + "\n"
        text = body + ("\n" + text[insert_at:].lstrip("\n") if nxt != -1 else "")
    else:
        text = text.rstrip("\n") + f"\n\n{heading}\n\n{line}\n"
    config.PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.PROFILE_PATH.write_text(text, encoding="utf-8")


class Skill:
    """A task's markdown file. Frontmatter holds counters; the body is written by Claude."""

    def __init__(self, name: str):
        self.slug = slugify(name)
        self.path = config.SKILLS_DIR / f"{self.slug}.md"

    @property
    def exists(self) -> bool:
        return self.path.exists()

    def read(self) -> str:
        return self.path.read_text(encoding="utf-8") if self.exists else ""

    def meta(self) -> dict:
        m = FRONTMATTER.match(self.read())
        out = {}
        if m:
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    out[k.strip()] = v.strip()
        return out

    def body(self) -> str:
        return FRONTMATTER.sub("", self.read(), count=1)

    def write(self, body: str, **meta_updates) -> None:
        meta = self.meta()
        meta.setdefault("name", self.slug)
        meta.setdefault("autonomy", "supervised")
        meta.setdefault("demonstrations", "0")
        meta.setdefault("runs", "0")
        meta.setdefault("clean_runs_in_a_row", "0")
        meta["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        meta.update({k: str(v) for k, v in meta_updates.items()})
        front = "\n".join(f"{k}: {v}" for k, v in meta.items())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(f"---\n{front}\n---\n{body.strip()}\n", encoding="utf-8")

    def bump(self, key: str, by: int = 1) -> int:
        value = int(self.meta().get(key, "0")) + by
        self.write(self.body(), **{key: value})
        return value

    def run_dir(self) -> Path:
        d = config.RUNS_DIR / self.slug
        d.mkdir(parents=True, exist_ok=True)
        return d

    def recent_run_logs(self, limit: int = 3) -> list[str]:
        logs = sorted(self.run_dir().glob("*.md"))[-limit:]
        return [p.read_text(encoding="utf-8") for p in logs]


def list_skills() -> list[Skill]:
    if not config.SKILLS_DIR.exists():
        return []
    return [Skill(p.stem) for p in sorted(config.SKILLS_DIR.glob("*.md"))]
