"""Upload a local image/video using Meta's official CLI and create a paused creative."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit

from credentials import TOKEN_PATH, load_token


META_CLI = Path.home() / ".venvs" / "meta-ads-codex" / "bin" / "meta"
REQUIRED = {"ad_account_id", "page_id", "name", "body", "title", "link_url"}
OPTIONAL = {"image", "video", "description", "call_to_action", "instagram_user_id", "url_tags"}
CALLS_TO_ACTION = {
    "APPLY_NOW", "BOOK_TRAVEL", "BUY_NOW", "CONTACT_US", "DOWNLOAD", "GET_OFFER",
    "GET_QUOTE", "LEARN_MORE", "NO_BUTTON", "OPEN_LINK", "SHOP_NOW", "SIGN_UP",
    "SUBSCRIBE", "WATCH_MORE",
}


def build_command(spec: dict[str, str], base: Path) -> list[str]:
    if not isinstance(spec, dict) or not REQUIRED <= spec.keys():
        raise ValueError("Missing required creative fields.")
    if spec.keys() - REQUIRED - OPTIONAL:
        raise ValueError("Unknown fields; status and arbitrary CLI flags are not allowed.")
    if any(not isinstance(value, str) or not value for value in spec.values()):
        raise ValueError("Every field must be a non-empty string.")
    if any(any(ord(char) < 32 and char not in "\n\t" or ord(char) == 127
               for char in value) for value in spec.values()):
        raise ValueError("Fields must not contain unsupported control characters.")
    if not re.fullmatch(r"act_\d+", spec["ad_account_id"]):
        raise ValueError("ad_account_id must use act_<digits>.")
    for field in ("page_id", "instagram_user_id"):
        if field in spec and not re.fullmatch(r"\d+", spec[field]):
            raise ValueError("Page and Instagram IDs must contain digits only.")
    if any(char.isspace() for char in spec["link_url"]):
        raise ValueError("Destination URLs must not contain whitespace.")
    target = urlsplit(spec["link_url"])
    # Accessing port validates its syntax and range before any media upload.
    target.port
    if target.scheme != "https" or not target.hostname or target.username or target.password:
        raise ValueError("Use an HTTPS destination URL without embedded credentials.")
    if "call_to_action" in spec and spec["call_to_action"] not in CALLS_TO_ACTION:
        raise ValueError("Unsupported call_to_action for the installed Meta CLI.")
    media = [field for field in ("image", "video") if field in spec]
    if len(media) != 1:
        raise ValueError("Provide exactly one local image or video.")
    kind = media[0]
    asset = (base / spec[kind]).resolve(strict=True)
    if not asset.is_file():
        raise ValueError("Media must be a regular local file.")
    suffixes = {
        "image": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"},
        "video": {".mp4", ".mov", ".avi", ".mkv", ".wmv"},
    }
    if asset.suffix.lower() not in suffixes[kind]:
        raise ValueError("Unsupported media extension.")
    command = [
        str(META_CLI), "--output=json", "--no-color", "--no-input", "ads",
        "--ad-account-id=" + spec["ad_account_id"], "creative", "create",
        "--status=PAUSED", "--" + kind + "=" + str(asset),
    ]
    for field in ("page_id", "name", "body", "title", "link_url", "description",
                  "call_to_action", "instagram_user_id", "url_tags"):
        if field in spec:
            command.append("--" + field.replace("_", "-") + "=" + spec[field])
    return command


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True, help="Creative JSON; media paths are relative to it.")
    parser.add_argument("--preview", action="store_true", help="Validate locally and print the command; no API call.")
    arguments = parser.parse_args()
    try:
        spec = json.loads(arguments.spec.read_text(encoding="utf-8"))
        command = build_command(spec, arguments.spec.resolve().parent)
        if arguments.preview:
            print(json.dumps({"command_argv": command, "external_write": False}, ensure_ascii=False, indent=2))
            return 0
        token = load_token()
        environment = os.environ.copy()
        environment["ACCESS_TOKEN"] = token
        environment["AD_ACCOUNT_ID"] = spec["ad_account_id"]
        # Run outside the project so its .env is not read by python-dotenv.
        result = subprocess.run(command, env=environment, cwd=TOKEN_PATH.parent,
                                capture_output=True, text=True, timeout=600, check=False)
        for output, stream in ((result.stdout, sys.stdout), (result.stderr, sys.stderr)):
            if output:
                print(output.replace(token, "[REDACTED]"), file=stream, end="")
        if result.returncode:
            print("Creation was not confirmed. Reconcile in Meta before retrying; partial uploads may exist.",
                  file=sys.stderr)
        return result.returncode
    except subprocess.TimeoutExpired:
        print("Meta CLI timed out. Reconcile in Meta before retrying; the write may have completed.", file=sys.stderr)
    except (OSError, UnicodeError, ValueError, TypeError):
        print("Creative preparation failed. Check the spec, local asset and saved token.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
