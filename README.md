# Apprentice

A desktop agent that **learns your tasks by watching you**, writes down what it learned as a
markdown file per task, then **does the task with you**. It asks about anything it doesn't know
and gets better after every run.

It runs on your own computer. It sees the screen through screenshots and uses the real mouse and
keyboard, driven by Claude's computer-use toolset.

```
 watch            learn                 do                     reflect
 you do it  ──▶  skills/<task>.md  ──▶  agent does it,   ──▶  skill rewritten from
 (recorded)       (steps, rules,        asks you when          your answers, refusals
                   what to ask)         unsure, you can        and takeovers
                                        take over (F9)               │
                       ▲─────────────────────────────────────────────┘
```

## How it learns (no prompt engineering needed)

| You do this | It learns |
|---|---|
| `watch` a task once or twice | Steps, apps/tabs involved, where to click, what you copy and paste where |
| Press **F8** while recording and type a note | Rules: "I always write this answer myself", "skip roles needing 5+ yrs" |
| Answer its questions during a run | Reusable answers go to `profile.md`; one-off ones become "always ask about X" |
| Say **No** at a confirmation | The step gets corrected, and a pitfall is added |
| Press **F9** and do a part yourself | Your actions are recorded and folded into the skill |
| Let it finish 5 runs without corrections | It suggests `trust`, so routine submits happen without asking |

All memory is plain markdown you can read and edit:

```
memory/
  profile.md               facts about you (name, links, standard answers)
  skills/apply-job.md      one file per task: goal, steps, decision rules, what to ask, pitfalls
  runs/apply-job/*.md      a log of every attempt, used for reflection
recordings/                raw screen recordings (stay on your computer, git-ignored)
```

## Setup

Requires Python 3.10+ and an Anthropic API key.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...  # Windows: set ANTHROPIC_API_KEY=...
```

Platform notes:
- **macOS**: allow your terminal under System Settings → Privacy & Security → **Screen Recording**
  and **Accessibility** (needed to see the screen and control the mouse).
- **Linux**: needs X11 (not Wayland) and `sudo apt install python3-tk`.
- **Windows**: works as is.

Fill in `memory/profile.md` with your basics first. It saves a lot of questions.

## Usage: your job-application workflow

**1. Teach it once.** Start recording, then do one application exactly as you did this morning:
copy the job description from Anthropic careers, paste it into your "Resume agent" chat in the
Claude tab, download the resume, upload it, fill the form, take the "Why Anthropic?" question to
the same chat, paste the answer back, and submit.

```bash
python -m apprentice watch "apply job"
#   F8  add a note   F9  pause/resume (do this before typing passwords)   F10  stop
```

When you press F10 it sends the recording to Claude and writes `memory/skills/apply-job.md`.
Open the file and check it. Repeat `watch` for a second or third job if anything was missed.
Each demo is merged into the same file. A starter `apply-job.md` based on your description is
already included.

**2. Do it together.**

```bash
python -m apprentice do "apply job" "Apply to the 3 newest Anthropic jobs on the careers page in the open Chrome window"
```

Keep your hands off the mouse while it works. A pop-up appears when it needs you:
- a **question** (visa status, salary expectations, anything not in your profile)
- a **confirmation** before it clicks Submit, showing what it filled in

Controls during a run:
- **F9**: take over. The agent pauses and records you. Press **F10** to hand control back.
- **F12**: stop the run.
- **Move the mouse into any screen corner**: emergency stop.

After every run it reflects on the run and rewrites the skill file.

**3. Let it go faster.** After several clean runs:

```bash
python -m apprentice trust "apply job"       # routine submits without asking
python -m apprentice supervise "apply job"   # back to asking every time
```

Other commands: `skills` (list skills and their stats), `show "<task>"`, `profile`,
`learn "<task>" <recording-folder>` (re-learn from a saved recording),
`watch "<task>" --no-typing` (record that you typed, not what you typed).

## Safety and privacy

- The agent controls your real mouse and keyboard. Close anything you don't want it to touch,
  and stay near the computer.
- It never types passwords or payment details. It hands logins and captchas to you.
- Screenshots and recordings are sent to the Anthropic API when it learns and acts. Pause
  recording (F9) for anything private. Recordings are saved under `recordings/` and are git-ignored.
- In `supervised` mode, every submit/send/pay/delete needs your yes. Payments and deletions
  always need it, even when trusted.
- Text on web pages is treated as data, not instructions.
- Read a job site's terms before automating applications there. You are responsible for what
  gets submitted in your name, so read the summary before you confirm.

## Configuration

Environment variables (see `apprentice/config.py`):

| Variable | Default | Meaning |
|---|---|---|
| `APPRENTICE_MODEL` | `claude-opus-5-5` | Model for acting and learning |
| `APPRENTICE_ACT_EFFORT` | `high` | Effort level for the desktop loop (`low` is cheaper/faster) |
| `APPRENTICE_MAX_STEPS` | `200` | Max model turns per run |
| `APPRENTICE_MAX_LONG_EDGE` | `1920` | Screenshot size sent to Claude |
| `APPRENTICE_MAX_LEARN_FRAMES` | `60` | Frames from a recording used for learning |
| `APPRENTICE_TRUST_AFTER` | `5` | Clean runs before it suggests `trust` |
| `APPRENTICE_HOME` | repo folder | Where `memory/` and `recordings/` live |

Learning and reflection calls use server-side refusal fallbacks (`fallbacks: "default"`), so a
safety-classifier decline is retried on Anthropic's recommended fallback model instead of failing.
The desktop loop doesn't use them, because a fallback model may not support the computer-use
toolset. If Claude declines there, the run stops and the reason is logged.

## Code map

| File | What it does |
|---|---|
| `apprentice/recorder.py` | Watches you: screenshots on click, typed text, copy/paste contents, notes |
| `apprentice/learner.py` | Turns recordings and run logs into skill markdown (learn + reflect) |
| `apprentice/agent.py` | The run loop: computer toolset plus ask/confirm/hand-over/remember tools |
| `apprentice/computer.py` | Executes Claude's mouse/keyboard actions with pyautogui |
| `apprentice/screen.py` | Screenshots and coordinate scaling (HiDPI-safe) |
| `apprentice/memory.py` | profile.md, skill files with counters, run logs |
| `apprentice/human.py` | Pop-up questions and confirmations |
