#!/usr/bin/env python3
"""Reject malformed catalogues and integrations before they reach the CDN."""
import json
import pathlib
import re
import sys

REQUIRED_GAME_FIELDS = ("productCode", "name")
errors = []
catalogues = sorted(pathlib.Path(".").glob("*/catalogue.json"))

if not catalogues:
    sys.exit("no catalogue.json files found")

for path in catalogues:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path}: invalid JSON — {exc}")
        continue

    if not isinstance(data.get("games"), list) or not data["games"]:
        errors.append(f"{path}: 'games' must be a non-empty list")
        continue

    seen = set()
    for index, game in enumerate(data["games"]):
        label = f"{path}: games[{index}]"
        if not isinstance(game, dict):
            errors.append(f"{label}: must be an object")
            continue
        for field in REQUIRED_GAME_FIELDS:
            if not str(game.get(field, "")).strip():
                errors.append(f"{label}: missing '{field}'")
        code = game.get("productCode")
        if code in seen:
            errors.append(f"{label}: duplicate productCode '{code}'")
        seen.add(code)

    print(f"{path}: {len(data['games'])} games")

# integrations.json: games keyed by Kraken slug, each claiming source ids.
SLUG_KEY = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
integrations = pathlib.Path("integrations.json")
try:
    data = json.loads(integrations.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    errors.append(f"{integrations}: unreadable — {exc}")
    data = None

if data is not None:
    games = data.get("games")
    if not isinstance(games, dict) or not games:
        errors.append(f"{integrations}: 'games' must be a non-empty object")
        games = {}

    claimed = {}
    for slug, entry in games.items():
        label = f"{integrations}: games['{slug}']"
        if not SLUG_KEY.match(slug):
            errors.append(f"{label}: key must be a lowercase hyphenated Kraken slug")
        if not isinstance(entry, dict):
            errors.append(f"{label}: must be an object")
            continue
        for key, value in entry.items():
            if key != "sources" and (not isinstance(value, str) or not value.strip()):
                errors.append(f"{label}: '{key}' must be a non-empty string")
        sources = entry.get("sources", {})
        if not isinstance(sources, dict):
            errors.append(f"{label}: 'sources' must be an object")
            continue
        for source, ids in sources.items():
            if not isinstance(ids, list) or not ids:
                errors.append(f"{label}: sources.{source} must be a non-empty list")
                continue
            for source_id in ids:
                if not isinstance(source_id, str) or not source_id.strip():
                    errors.append(f"{label}: sources.{source} has an empty or non-string id")
                    continue
                uid = f"{source}@{source_id}"
                if uid in claimed:
                    errors.append(f"{label}: {uid} is already claimed by '{claimed[uid]}'")
                claimed.setdefault(uid, slug)

    print(f"{integrations}: {len(games)} games")

if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)

print("all files valid")
