# Google Ads Transparency MCP Server

An MCP server that lets AI assistants look up any advertiser's Google ads. Search by domain or company name, retrieve ad creatives, and decode text ad content — all from Google's [Ads Transparency Center](https://adstransparency.google.com/).

**No API key. No paid service. No browser required.**

Google has no official API for their Ads Transparency Center. The only open-source option was an [abandoned Python package](https://github.com/faniAhmed/GoogleAdsTransparencyScraper) (last commit July 2023, broken domain search, crashed on image ads). Paid alternatives start at $75/mo. This project fixes the scraper and wraps it as an MCP server so any AI assistant can query Google's ad database directly.

## Tools

| Tool | Description |
|------|-------------|
| `search_advertiser_by_domain` | Find an advertiser by website domain (e.g. `nike.com`) |
| `search_advertisers` | Search advertisers by keyword or company name |
| `get_ads` | Get ads for an advertiser with decoded content |
| `get_ad_detail` | Get full details for a specific ad creative |
| `compare_advertisers` | Active ad count per domain across a competitor set, with a status per row |
| `advertiser_summary` | Format mix, copy sample and destination hosts for one advertiser |
| `fetch_ad_creative` | Download one creative — the image file, or video sampled to frames |
| `download_ad_creatives` | Bulk-download an advertiser's creatives into a folder with a manifest |

## Install

```bash
# With uvx (recommended)
uvx google-ads-transparency-mcp

# With pip
pip install google-ads-transparency-mcp
```

### Optional: video creatives

Downloading video ads needs [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) and
[`ffmpeg`](https://ffmpeg.org/) on your `PATH`:

```bash
brew install yt-dlp ffmpeg      # macOS
```

Everything else works without them. If they are missing, only the video download
tools fail, and they say which binary is absent.

## Configure

### Claude Code

```bash
claude mcp add google-ads-transparency -- uvx google-ads-transparency-mcp
```

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "google-ads-transparency": {
      "command": "uvx",
      "args": ["google-ads-transparency-mcp"]
    }
  }
}
```

### Cursor / VS Code

Add to your MCP settings:

```json
{
  "mcpServers": {
    "google-ads-transparency": {
      "command": "uvx",
      "args": ["google-ads-transparency-mcp"]
    }
  }
}
```

## Example Usage

Once connected, ask your AI assistant things like:

- *"What ads is nike.com running?"*
- *"Search for crypto exchange advertisers on Google"*
- *"Get the last 5 ads from Coinbase"*
- *"Look up ad details for advertiser AR05099026886533578753"*

### Example: Domain Search

```
> search_advertiser_by_domain("nike.com")

{
  "advertiser_id": "AR14188379519798214657",
  "name": "Nike, Inc.",
  "ad_count": 1842
}
```

### Example: Get Ads with Decoded Text Content

```
> get_ads("Coinbase", count=1)

[
  {
    "advertiser_id": "AR09076382774528",
    "creative_id": "CR10813648716908961793",
    "format": "text",
    "last_shown": "2025-01-15",
    "advertiser_name": "Coinbase",
    "content": {
      "preview_url": "https://ads-rendering-prod.corp.google.com/search?...",
      "headline": "Most Trusted Crypto Exchange",
      "description": "Buy, Sell & Trade Bitcoin, Ethereum & More...",
      "destination_url": "coinbase.com"
    }
  }
]
```

## How It Works

This server reverse-engineers Google's internal RPC endpoints:

| Endpoint | Purpose |
|----------|---------|
| `SearchService/SearchSuggestions` | Keyword/domain search |
| `SearchService/SearchCreatives` | Get ad creative IDs by advertiser |
| `LookupService/GetCreativeById` | Get individual ad details |

Text ads carry their copy in the `overlay` parameter of the creative preview
URL: urlsafe base64 wrapping gzip wrapping protobuf, whose named fields give the
headline, description and destination URL exactly rather than by guesswork.
Text ads rendered through `content.js` instead carry the same triple in a
`data-p` attribute, which is decoded too.

Image and video ads hand back a JavaScript renderer instead of an asset. The
server fetches it and pulls out the real `simgad` image URL, or the YouTube
video id plus the on-creative headline and button label.

### Rate limiting

Google throttles these endpoints per source IP and answers a bursty client with
an HTTP 429 and a CAPTCHA interstitial. Requests are spaced out and retried with
backoff. If your IP is already blocked the tools raise `AdsTransparencyBlocked`
rather than returning empty results, so it is obvious what happened.

An empty result never means "blocked" — that distinction is the whole point of
the exception. If you see one, the advertiser really has no ads.

Blocks are **per address, not per host**, and IPv4 and IPv6 are blocked
separately. A machine whose IPv6 is banned will still work over IPv4, which is
worth knowing before concluding a host is burned.

## Routing Around a Blocked IP

If your own IP is blocked, the scraper can borrow another machine's. Set a
proxy for this package alone:

```bash
export GOOGLE_ADS_TRANSPARENCY_PROXY=socks5h://127.0.0.1:1080
```

The `h` matters. `socks5h` resolves DNS at the proxy; `socks5` resolves it
locally. If a local resolver blocks ad hosts — NextDNS nulls out
`tpc.googlesyndication.com`, where the image creatives live — only `socks5h`
can reach them.

This variable is read *instead of* the ambient `HTTP_PROXY`/`ALL_PROXY`, on
purpose: routing an entire machine through a proxy to fix one host is both a
privacy change and a good way to break unrelated tools.

| Value | Effect |
|-------|--------|
| unset | Walk the route chain below, advancing when a route is blocked or unreachable |
| a proxy URL | Use it and nothing else |
| `direct` / `none` | Force a direct connection, skip the checks |

With the variable unset the scraper tries, in order:

1. **Residential** — a rotating residential proxy, if
   `~/.config/google-ads-transparency/residential-proxy` exists. One line, the
   full `socks5h://user:pass@host:port` URL. Every request exits from a
   different IP, so per-IP bans never stick, and the file lives outside the
   repo so it cannot be committed. Proxy credentials are scrubbed from error
   text before it is returned.
2. **Direct** — your own connection.
3. **Tunnel** — a SOCKS relay at `127.0.0.1:1080`, if something is listening
   there.

Because an unset variable auto-detects, no MCP client registration needs to
know about any of this, and nothing breaks when none of it is set up.

### Relaying through a remote host

`scripts/socks_over_ssh.py` is a local SOCKS5 proxy that relays each connection
through an SSH **exec** channel to a host you name. It exists in that shape for
hosts whose sshd sets `AllowTcpForwarding no`, which refuses `ssh -D`; exec
channels are not covered by that directive, so it needs no server-side change.

```bash
python scripts/socks_over_ssh.py --ssh-target my-box          # any ~/.ssh/config alias
curl -s --socks5-hostname 127.0.0.1:1080 https://api.ipify.org  # prints the remote IP
```

Keep it alive with whatever your OS uses (a launchd agent on macOS, a systemd
user unit on Linux) and the scraper picks it up automatically.

Security posture, since this is an unauthenticated proxy:

- **Loopback only.** The script refuses to bind anything but `127.0.0.1`, so it
  is reachable from this machine and nowhere else.
- **No agent forwarding** (`ssh -a`), so the remote host is never handed this
  machine's keys. Also no X11 (`-x`) and no pty (`-T`).
- **No server-side change.** The remote sshd config is untouched.
- **Nothing else is routed through it.** Only this package reads the variable
  that points at it.

If the tunnel is down, the tools say so rather than failing obscurely, and the
scraper moves on to the next route.

## Use as a Python Library

```python
from google_ads_transparency_mcp import GoogleAdsTransparency

client = GoogleAdsTransparency()

# Search by domain
advertiser = client.search_advertiser_by_domain("nike.com")
print(advertiser)  # {"advertiser_id": "...", "name": "Nike, Inc.", "ad_count": 1842}

# Get ads with decoded content
ads = client.get_ads("Coinbase", count=5)
for ad in ads:
    print(ad["format"], ad["content"])

# Region-specific search
client_uk = GoogleAdsTransparency(region="GB")
```

## Getting the Creatives Themselves

The ad copy is only half the story. Both download tools write real files to disk
and return their paths, so the creatives can go straight into a deck, a report,
or a vision model.

**Images are always saved at their original resolution** — the file you get back
is the creative as it ran, nothing downscaled.

**Videos are sampled into JPEG frames**, in one of two modes:

| Mode | Frames | Use |
|------|--------|-----|
| Default | 320px wide, ~12KB each | Vision analysis — cheap enough to send a batch of them |
| `full_quality=True` | Native resolution (e.g. 1080×1080) | Slides, decks, anything a person will look at |

```python
from google_ads_transparency_mcp.frames import download_image, extract_video_frames

# Full-resolution image creative
path = download_image(ad["content"]["image_url"], "out/", name=ad["creative_id"])

# Deck-quality stills from a video ad
result = extract_video_frames(
    ad["content"]["video_url"], "out/", frames=4, full_quality=True
)
print(result["frames"])    # ['out/frame_01.jpg', ...]
print(result["video_path"])  # the downloaded video itself
```

### Collecting a whole advertiser

`download_ad_creatives` pulls a batch in one call. Each creative gets its own
subfolder, and a `manifest.json` records every file alongside its decoded copy,
format and last-shown date — which is what you want when assembling examples.

```
> download_ad_creatives("Buildkite", out_dir="creatives/", count=10)

creatives/
├── manifest.json
├── CR04431036747610062849/
│   └── CR04431036747610062849.png     # 400×400, as it ran
└── CR01542648288744833025/
    ├── frame_01.jpg                   # 1080×1080 stills
    ├── frame_02.jpg
    └── video.mp4
```

One dead creative never sinks the batch — it gets an `error` field in the
manifest and the rest continue.

## Comparing and Summarising Advertisers

Two tools turn the raw lookups into the questions people actually ask.

### Who in this market is running ads, and how many?

```python
client.compare_advertisers(["nike.com", "adidas.com", "github.com"])
```

```json
[
  {"domain": "nike.com",   "status": "ok", "advertiser_name": "Nike Retail BV",      "ad_count": 100000, "parent_entity": false},
  {"domain": "adidas.com", "status": "ok", "advertiser_name": "Adidas America, Inc", "ad_count": 3000,   "parent_entity": false},
  {"domain": "github.com", "status": "ok", "advertiser_name": "TRENT SLADE",         "ad_count": 1000,   "parent_entity": true,
   "note": "resolves to 'TRENT SLADE', which shares no name token with 'github.com': ... Do not cite ad_count as this domain's own."}
]
```

Every row carries a `status`, and the distinction matters:

| Status | Meaning |
|--------|---------|
| `ok` | An advertiser was found; `ad_count` is Google's active-ads figure |
| `absent` | No advertiser is registered for that domain. **A genuine zero.** |
| `blocked` | Google rate-limited the lookup. **Not a zero.** Never cite it as one |
| `error` | Anything else; the note says what |

Once every egress route is blocked, the remaining domains are marked `blocked`
without further requests rather than hammering a ban.

**`parent_entity`** is the guard against the mistake that produces confidently
wrong numbers. Domain search returns whoever's ads mention the domain, which
can be the parent company, a reseller, or a stranger. When the advertiser name
shares no word with the domain the row is flagged and carries a note. It is a
heuristic: it flags, it does not filter. Pass `company_names={"gh.io": "GitHub"}`
to sharpen the check for domains that do not contain the company name.

### What does this advertiser's paid surface look like?

```python
client.summarize_advertiser("nike.com", sample=50)
```

```json
{
  "status": "ok", "advertiser_name": "Nike Retail BV", "active_ads": 100000,
  "sample": {
    "sampled": 50,
    "by_format": {"image": 41, "text": 6, "video": 3},
    "format_share": {"image": 0.82, "text": 0.12, "video": 0.06},
    "last_shown": {"earliest": "2026-08-30", "latest": "2026-09-09"},
    "headlines": ["..."], "descriptions": ["..."], "cta_labels": [{"label": "Shop now", "count": 4}],
    "destination_hosts": [{"host": "nike.com", "count": 6}],
    "with_video": 3, "with_image": 41
  }
}
```

`advertiser` may be an id (`AR...`), a domain, or a name. The sample is the
creatives the Transparency Center lists first, and costs roughly one to two
requests per creative. The summary is pure aggregation: it tells you the mix,
and leaves the reading of it (brand display heavy, no search presence, and so
on) to you or the model calling the tool.

The aggregation itself is importable and offline, so it works on ads you have
already fetched:

```python
from google_ads_transparency_mcp import summarize_ads, is_parent_entity

summary = summarize_ads(ads)            # ads = a list from get_ads / get_ad_detail
is_parent_entity("github.com", "Microsoft Corporation")   # True
```

## Development

```bash
uv sync --all-groups
uv run ruff check src tests
uv run pytest -q                 # offline; ADS_LIVE=1 adds one live round-trip
```

## Supported Regions

Pass a two-letter country code to filter by region. Use `"anywhere"` (default) for global results. All [240+ regions](https://adstransparency.google.com/) from Google's Ads Transparency Center are supported.

## Credits

Based on [GoogleAdsTransparencyScraper](https://github.com/faniAhmed/GoogleAdsTransparencyScraper) by Farhan Ahmed. Forked and fixed by [Sam Town](https://samuel.town) — domain search, image ad
parsing, text ad decoding, error handling, and MCP server. Later: overlay
protobuf decoding, creative asset resolution, video frame sampling, and rate
limit handling.

## License

MIT
