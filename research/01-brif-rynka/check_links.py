"""Check every external link in the brief before publishing.

Usage: python3 check_links.py index.html
Prints one line per URL with its final HTTP status; exits non-zero if any link is broken.
Login-walled hosts (Instagram, Facebook, Threads) are reported separately, not as broken.
"""
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
TIMEOUT_SECONDS = "20"
LOGIN_WALLED = ("instagram.com", "facebook.com", "threads.net", "linkedin.com")


def http_status(url: str) -> str:
    cmd = [
        "curl", "-s", "-o", "/dev/null", "-L", "--max-time", TIMEOUT_SECONDS,
        "-A", USER_AGENT, "-w", "%{http_code}", url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=int(TIMEOUT_SECONDS) + 5)
        return result.stdout.strip() or "000"
    except subprocess.TimeoutExpired:
        return "timeout"


def main(path: str) -> int:
    html = open(path, encoding="utf-8").read()
    urls = sorted(set(re.findall(r'href="(https?://[^"]+)"', html)))
    with ThreadPoolExecutor(max_workers=12) as pool:
        statuses = list(pool.map(http_status, urls))

    broken = []
    for url, status in zip(urls, statuses):
        walled = any(host in url for host in LOGIN_WALLED)
        ok = status.isdigit() and 200 <= int(status) < 400
        label = "OK" if ok else ("LOGIN-WALL" if walled else "BROKEN")
        print(f"{label:10} {status:8} {url}")
        if not ok and not walled:
            broken.append(url)

    print(f"\n{len(urls)} links checked, {len(broken)} broken")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
