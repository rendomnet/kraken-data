#!/usr/bin/env python3
"""Reject malformed catalogues before they reach the CDN."""
import json
import pathlib
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

if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)

print("all catalogues valid")
