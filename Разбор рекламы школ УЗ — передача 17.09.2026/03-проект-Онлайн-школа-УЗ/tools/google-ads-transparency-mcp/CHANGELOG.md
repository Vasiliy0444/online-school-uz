# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.3.0] - 2026-09-09

### Added
- `compare_advertisers(domains)`: active ad count per domain in one call, with
  a per-row `status` (`ok` / `absent` / `blocked` / `error`) so a rate-limit is
  never mistaken for a zero. Stops issuing requests once every egress route is
  blocked.
- `parent_entity` flag on comparison rows. Domain search returns whoever's ads
  mention the domain, which can be a parent company, a reseller or a stranger;
  the flag marks advertisers whose name shares no token with the domain.
- `advertiser_summary(advertiser, sample)`: format mix and share, last-shown
  range, de-duplicated headlines, descriptions and CTA labels, and destination
  hosts for one advertiser. Accepts an id, a domain or a name.
- `analysis` module with the pure, offline aggregation helpers behind the
  tools (`summarize_ads`, `is_parent_entity`, `normalize_domain`), exported
  from the package for library use.
- `GoogleAdsTransparency.resolve_advertiser()` for id / domain / name lookup.
- Offline test suite (`pytest`) and a CI workflow running lint and tests on
  Python 3.10 and 3.13.

### Changed
- `AdsTransparencyError` and `AdsTransparencyBlocked` are exported from the
  package root.

### Fixed
- Text ads whose preview is a `content.js` renderer (rather than an overlay
  URL) now decode headline, description and display URL. Previously they
  came back with `preview_url` only.

## [0.2.0] - 2026-09-09

### Fixed
- Pinned `mcp<2`. The 2.x SDK renamed `FastMCP`, which broke every fresh
  install of 0.1.0 with `ModuleNotFoundError`.

### Added
- `fetch_ad_creative` and `download_ad_creatives`: write the actual creative
  files to disk. Images at original resolution; videos sampled to JPEG frames
  (needs `yt-dlp` and `ffmpeg`). Bulk mode writes a `manifest.json`.
- `AdsTransparencyBlocked` is raised when Google rate-limits or CAPTCHA-gates
  the source IP, instead of silently returning an empty list.
- Request throttling with retry and backoff.
- Proxy route chain (residential → direct → tunnel), auto-detected, scoped to
  this package only, credentials scrubbed from error text.
- Exact text-ad decoding from the preview URL's protobuf overlay.
- Image and video creatives resolved through Google's renderer to the real
  asset URL or YouTube id, with on-creative headline and button label.
- Pagination past 100 creatives.
- `scripts/socks_over_ssh.py`: a loopback-only SOCKS5 proxy relayed over SSH
  exec channels, for hosts that refuse `ssh -D`.

## [0.1.0] - 2026-03-26

### Added
- Initial release: `search_advertiser_by_domain`, `search_advertisers`,
  `get_ads`, `get_ad_detail`.

[0.3.0]: https://github.com/block-town/google-ads-transparency-mcp/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/block-town/google-ads-transparency-mcp/compare/1337c36...v0.2.0
[0.1.0]: https://github.com/block-town/google-ads-transparency-mcp/commit/1337c36
