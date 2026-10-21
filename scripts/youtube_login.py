"""One-time YouTube login for the dashboard. Run on a Mac by the person who can
manage the Opsera YouTube channel:

    .venv/bin/pip install google-auth-oauthlib==1.2.1
    .venv/bin/python scripts/youtube_login.py ~/Downloads/<oauth-client-file>.json

A browser window opens. Sign in, pick the Opsera channel, and allow read-only
access. The saved login (a refresh token) goes to ~/.config/opsera-dashboard/,
never into this repo. It is then stored as the GitHub secret YOUTUBE_TOKEN.
"""
import json
import sys
from pathlib import Path

from google.auth.transport.requests import AuthorizedSession
from google_auth_oauthlib.flow import InstalledAppFlow

CHANNEL_ID = "UCpnT0NdkrOWp8v3bodeCGhQ"   # Opsera, linked from the opsera.ai footer
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
OUT = Path.home() / ".config" / "opsera-dashboard" / "youtube-token.json"


def main():
    if len(sys.argv) != 2 or not Path(sys.argv[1]).expanduser().exists():
        sys.exit("Give the path to the OAuth client file you downloaded from Google Cloud.")
    flow = InstalledAppFlow.from_client_secrets_file(str(Path(sys.argv[1]).expanduser()), SCOPES)
    creds = flow.run_local_server(port=0, prompt="select_account consent", access_type="offline",
                                  authorization_prompt_message="Opening your browser to sign in to YouTube...")
    if not creds.refresh_token:
        sys.exit("STOPPED: Google didn't return a lasting login. Run this again.")

    mine = AuthorizedSession(creds).get(
        "https://www.googleapis.com/youtube/v3/channels", params={"part": "snippet", "mine": "true"}).json()
    channels = {c["id"]: c["snippet"]["title"] for c in mine.get("items", [])}
    if CHANNEL_ID not in channels:
        sys.exit(f"STOPPED: this login can see {channels or 'no channel'}, not Opsera ({CHANNEL_ID}). "
                 "Sign in again and pick the Opsera channel.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "client_id": creds.client_id, "client_secret": creds.client_secret,
        "refresh_token": creds.refresh_token, "token_uri": creds.token_uri, "scopes": SCOPES,
    }))
    OUT.chmod(0o600)
    print(f"Signed in to the {channels[CHANNEL_ID]} channel. Login saved to {OUT}")


if __name__ == "__main__":
    main()
