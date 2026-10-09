#!/usr/bin/env python3
"""warden_digest.py: SessionStart hook. Once a week, one line: what gatewarden saw and how
many rules it suggests turning up. Never blocks, never prompts, always exits 0. Stdlib only.

The first run writes an explicit modes file (default watch) and starts the week; it says
nothing. Later runs speak only when seven days have passed and the log holds events.
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hooklib as hl  # noqa: E402
import warden_review as wr  # noqa: E402

WEEK = 7 * 86400.0


def main() -> None:
    try:
        hl.read_event()
        if not os.path.exists(hl.modes_path()):
            wr.save_modes({"default": "watch", "rules": {}})
        path = os.path.join(hl.state_dir(), "digest.json")
        try:
            last = float(hl.load_json(path).get("last_at", 0))
        except (OSError, ValueError, AttributeError):
            last = 0.0
        now = time.time()
        if last == 0.0:
            hl.write_json_atomic(path, {"last_at": now})
            sys.exit(0)
        if now - last < WEEK:
            sys.exit(0)
        days = (now - last) / 86400.0
        rows = wr.read_events(days)
        hl.write_json_atomic(path, {"last_at": now})
        if not rows:
            sys.exit(0)
        text = wr.report(days)
        n = text.rsplit("\n", 1)[-1].split(" ", 1)[0]
        here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "warden_review.py")
        msg = hl.note("gatewarden", "weekly", rows=[("events", len(rows)),
                                                     ("rules", len({r.get("rule") for r in rows})),
                                                     ("suggest", n), ("review", f"python \"{here}\"")])
        sys.stdout.write(json.dumps({"systemMessage": msg}) + "\n")
    except SystemExit:
        raise
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
