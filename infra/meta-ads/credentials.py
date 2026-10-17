"""Supply a locally stored token to the official Meta MCP without chat exposure."""

from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path
import stat
import sys
import tempfile


TOKEN_PATH = Path.home() / ".config" / "meta-ads-codex" / "access-token"


def validate_token(value: str) -> str:
    value = value.strip()
    if not value or len(value) > 16384:
        raise ValueError("Token is empty or too long.")
    if any(ord(char) < 33 or ord(char) > 126 for char in value):
        raise ValueError("Token must be a single line without whitespace.")
    return value


def check_private_directory(directory: Path) -> None:
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError("Token directory must be an owned directory, not a symlink.")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError("Token directory permissions must exclude other users.")


def load_token(path: Path = TOKEN_PATH) -> str:
    check_private_directory(path.parent)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "r", encoding="ascii") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError("Token must be an owned regular file.")
        if stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError("Token file permissions must exclude other users.")
        return validate_token(stream.read(16385))


def store_token(value: str, path: Path = TOKEN_PATH) -> None:
    value = validate_token(value)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    check_private_directory(path.parent)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".token-")
    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["store", "status", "headers"])
    arguments = parser.parse_args()
    try:
        if arguments.action == "store":
            if not sys.stdin.isatty():
                raise ValueError("Use an interactive terminal; token input is hidden.")
            store_token(getpass.getpass("Meta employee system-user token (hidden): "))
            print("Token saved locally. Its validity has not yet been checked by Meta.")
        elif arguments.action == "status":
            load_token()
            print("Local token is present and private. Meta authorization is unverified.")
        else:
            # This stdout is read by Codex's http_headers_helper, not by the chat.
            print(json.dumps({"Authorization": "Bearer " + load_token()}))
    except (OSError, UnicodeError, ValueError, EOFError) as error:
        # Do not interpolate the token or exception values from third-party code.
        print("Meta credentials unavailable: " + type(error).__name__, file=sys.stderr)
        print("Save the token using credentials.py store in your terminal.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
