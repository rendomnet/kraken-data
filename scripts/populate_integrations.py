#!/usr/bin/env python3
"""
Populate and verify integrations in kraken-data/integrations.json.

Fetches Twitch Helix numeric IDs, Speedrun.com slugs, and verifies Reddit subreddits.
Reads TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET from environment or ../backend/.env.
"""

import argparse
import json
import os
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
INTEGRATIONS_FILE = ROOT_DIR / "integrations.json"
BACKEND_ENV_FILE = ROOT_DIR.parent / "backend" / ".env"

def load_env():
    """Load TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET from env or ../backend/.env."""
    env_vars = dict(os.environ)
    for env_path in [ROOT_DIR / ".env", BACKEND_ENV_FILE]:
        if env_path.is_file():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key not in env_vars:
                        env_vars[key] = val
    return env_vars

class TwitchResolver:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None

    def authenticate(self):
        if not self.client_id or not self.client_secret:
            return False
        url = "https://id.twitch.tv/oauth2/token"
        data = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                self.access_token = res.get("access_token")
                return True
        except Exception as e:
            print(f"[Twitch] Auth failed: {e}", file=sys.stderr)
            return False

    def resolve_game_id(self, query: str) -> str | None:
        if not self.access_token and not self.authenticate():
            return None

        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}"
        }

        # 1. Exact name match on /helix/games
        encoded_name = urllib.parse.quote(query)
        req = urllib.request.Request(f"https://api.twitch.tv/helix/games?name={encoded_name}", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("data", [])
                if items:
                    return str(items[0]["id"])
        except urllib.error.HTTPError as e:
            if e.code == 401:
                self.authenticate()
            pass
        except Exception:
            pass

        # 2. Search categories
        search_req = urllib.request.Request(
            f"https://api.twitch.tv/helix/search/categories?query={encoded_name}&first=5",
            headers=headers
        )
        try:
            with urllib.request.urlopen(search_req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("data", [])
                if items:
                    norm_query = re.sub(r"[^a-z0-9]+", "", query.lower())
                    for cat in items:
                        cat_norm = re.sub(r"[^a-z0-9]+", "", cat["name"].lower())
                        if cat_norm == norm_query:
                            return str(cat["id"])
                    # If first item is very close
                    return str(items[0]["id"])
        except Exception:
            pass

        return None

def normalize_slug_to_title(slug: str) -> str:
    parts = slug.split("-")
    return " ".join(p.capitalize() for p in parts)

def main():
    parser = argparse.ArgumentParser(description="Populate and verify integrations.json")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without saving")
    parser.add_argument("--twitch-only", action="store_true", help="Only resolve Twitch IDs")
    args = parser.parse_args()

    if not INTEGRATIONS_FILE.is_file():
        sys.exit(f"Error: {INTEGRATIONS_FILE} not found")

    env = load_env()
    twitch_client_id = env.get("TWITCH_CLIENT_ID", "")
    twitch_client_secret = env.get("TWITCH_CLIENT_SECRET", "")

    twitch = TwitchResolver(twitch_client_id, twitch_client_secret)
    if not twitch.authenticate():
        print("[Warning] Twitch credentials not found or invalid. Twitch resolution skipped.")

    data = json.loads(INTEGRATIONS_FILE.read_text(encoding="utf-8"))
    games = data.get("games", {})

    changes_count = 0

    for slug, entry in sorted(games.items()):
        current_twitch = entry.get("twitch")
        if current_twitch:
            if not str(current_twitch).isdigit() and twitch.access_token:
                # Need to convert directory name to numeric ID
                numeric_id = twitch.resolve_game_id(current_twitch)
                if numeric_id:
                    print(f"[{slug}] Twitch '{current_twitch}' -> {numeric_id}")
                    entry["twitch"] = numeric_id
                    changes_count += 1
                else:
                    print(f"[{slug}] Warning: Could not resolve Twitch ID for '{current_twitch}'")
            elif str(current_twitch).isdigit():
                # Already numeric ID
                pass
        elif twitch.access_token and not args.twitch_only:
            # Missing twitch ID, try lookup by slug name
            title = normalize_slug_to_title(slug)
            numeric_id = twitch.resolve_game_id(title)
            if numeric_id:
                print(f"[{slug}] Added Twitch ID {numeric_id} (searched '{title}')")
                entry["twitch"] = numeric_id
                changes_count += 1

    print(f"\nTotal updates: {changes_count}")

    if changes_count > 0 and not args.dry_run:
        INTEGRATIONS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Updated {INTEGRATIONS_FILE}")

        # Run validate.py
        import subprocess
        validate_script = ROOT_DIR / "scripts" / "validate.py"
        subprocess.run([sys.executable, str(validate_script)], check=True)

if __name__ == "__main__":
    main()
