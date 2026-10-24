"""Small offline staged-file guard. Reports paths only, never matched content.

This is a baseline credential check, not a guarantee of secret-free content.
"""

import re
import subprocess
import sys
from pathlib import PurePosixPath

PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    re.compile(rb"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(
        rb"(?i)(?:api[_-]?key|secret|password|access[_-]?token)"
        rb"\s*[:=]\s*['\"][A-Za-z0-9+/=_-]{16,}['\"]"
    ),
]


def suspicious(path: str, content: bytes) -> bool:
    name = PurePosixPath(path).name.lower()
    return (
        name.startswith(".env")
        or PurePosixPath(name).suffix in {".pem", ".key", ".p12", ".pfx"}
        or any(pattern.search(content) is not None for pattern in PATTERNS)
    )


def main() -> int:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
        check=True,
        capture_output=True,
    )
    flagged = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        path = raw.decode("utf-8")
        content = subprocess.run(
            ["git", "show", ":" + path], check=True, capture_output=True
        ).stdout
        if suspicious(path, content):
            flagged.append(path)
    if flagged:
        print("Potential credentials detected in staged files:", file=sys.stderr)
        for path in flagged:
            print(path, file=sys.stderr)
        return 1
    print("Staged credential scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
