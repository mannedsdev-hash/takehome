"""Command line entry point: python -m apprentice <command> ..."""

import argparse
import sys
from pathlib import Path

from . import config
from .memory import Skill, list_skills, read_profile


def cmd_watch(args):
    from .learner import learn_from_recording
    from .recorder import Recorder

    print(f"Recording '{args.task}'. Do the task the way you normally do it.")
    print("  F8 = add a note for the agent   F9 = pause/resume (passwords!)   F10 = stop")
    folder = Recorder(args.task, record_typing=not args.no_typing).run()
    print(f"Saved recording: {folder}")
    if args.no_learn:
        print(f'Learn from it later with: python -m apprentice learn "{args.task}" "{folder}"')
        return
    print("Learning from the demonstration...")
    learn_from_recording(args.task, folder)


def cmd_learn(args):
    from .learner import learn_from_recording

    folder = Path(args.recording)
    if not (folder / "events.jsonl").exists():
        sys.exit(f"No events.jsonl in {folder}")
    learn_from_recording(args.task, folder)


def cmd_do(args):
    from .agent import Run

    skill = Skill(args.task)
    if not skill.exists:
        print(f"No skill '{skill.slug}' yet. The agent will ask you a lot; consider `watch` first.")
    print("Starting. F9 = take over, F12 = abort, mouse into a screen corner = emergency stop.")
    Run(args.task, args.instruction).start()


def cmd_skills(_args):
    skills = list_skills()
    if not skills:
        print("No skills yet. Teach one with: python -m apprentice watch \"<task name>\"")
    for s in skills:
        m = s.meta()
        print(f"{s.slug:30} autonomy={m.get('autonomy', '?'):10} demos={m.get('demonstrations', 0):3} "
              f"runs={m.get('runs', 0):3} clean_in_a_row={m.get('clean_runs_in_a_row', 0)}")


def cmd_show(args):
    skill = Skill(args.task)
    print(skill.read() if skill.exists else f"No skill named {skill.slug}")


def cmd_autonomy(args, level):
    skill = Skill(args.task)
    if not skill.exists:
        sys.exit(f"No skill named {skill.slug}")
    skill.write(skill.body(), autonomy=level)
    print(f"{skill.slug} is now {level}.")


def main():
    p = argparse.ArgumentParser(prog="apprentice", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("watch", help="record yourself doing a task, then learn a skill from it")
    w.add_argument("task")
    w.add_argument("--no-typing", action="store_true", help="don't record what you type (only that you typed)")
    w.add_argument("--no-learn", action="store_true", help="only record; learn later")
    w.set_defaults(fn=cmd_watch)

    l = sub.add_parser("learn", help="learn (or re-learn) a skill from a saved recording")
    l.add_argument("task")
    l.add_argument("recording")
    l.set_defaults(fn=cmd_learn)

    d = sub.add_parser("do", help="let the agent do a task on your desktop")
    d.add_argument("task")
    d.add_argument("instruction", help='e.g. "Apply to the first 3 new Anthropic jobs"')
    d.set_defaults(fn=cmd_do)

    sub.add_parser("skills", help="list learned skills").set_defaults(fn=cmd_skills)
    s = sub.add_parser("show", help="print a skill file")
    s.add_argument("task")
    s.set_defaults(fn=cmd_show)
    t = sub.add_parser("trust", help="let a skill do routine submits without asking")
    t.add_argument("task")
    t.set_defaults(fn=lambda a: cmd_autonomy(a, "trusted"))
    u = sub.add_parser("supervise", help="go back to confirming every submit")
    u.add_argument("task")
    u.set_defaults(fn=lambda a: cmd_autonomy(a, "supervised"))
    sub.add_parser("profile", help="print profile.md").set_defaults(fn=lambda a: print(read_profile()))

    args = p.parse_args()
    config.MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    args.fn(args)
