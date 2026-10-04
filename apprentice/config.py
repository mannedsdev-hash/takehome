"""Paths and tunables. Override any of them with environment variables."""

import os
from pathlib import Path

ROOT = Path(os.environ.get("APPRENTICE_HOME", Path(__file__).resolve().parent.parent))
MEMORY_DIR = ROOT / "memory"
SKILLS_DIR = MEMORY_DIR / "skills"
RUNS_DIR = MEMORY_DIR / "runs"
PROFILE_PATH = MEMORY_DIR / "profile.md"
RECORDINGS_DIR = ROOT / "recordings"

MODEL = os.environ.get("APPRENTICE_MODEL", "claude-opus-5-5")
# Effort for the hands-on desktop loop and for learning/reflecting.
ACT_EFFORT = os.environ.get("APPRENTICE_ACT_EFFORT", "high")
LEARN_EFFORT = os.environ.get("APPRENTICE_LEARN_EFFORT", "high")

# Screenshots sent to Claude are downscaled to fit these limits (1080p-class is a good cost/accuracy balance).
SCREENSHOT_MAX_LONG_EDGE = int(os.environ.get("APPRENTICE_MAX_LONG_EDGE", "1920"))
SCREENSHOT_MAX_PIXELS = 3_750_000

MAX_AGENT_STEPS = int(os.environ.get("APPRENTICE_MAX_STEPS", "200"))
# Frames from a demonstration that are sent to Claude when learning (sampled evenly if more were captured).
MAX_LEARN_FRAMES = int(os.environ.get("APPRENTICE_MAX_LEARN_FRAMES", "60"))
# A skill is suggested for "trusted" mode after this many runs in a row with no human corrections.
TRUST_AFTER_CLEAN_RUNS = int(os.environ.get("APPRENTICE_TRUST_AFTER", "5"))
