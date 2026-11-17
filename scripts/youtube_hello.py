"""Week 0 step 0.5 pass test: list your YouTube subscriptions (read-only).

Usage:
    uv run python scripts/youtube_hello.py

Opens a browser for Google consent. The token is kept in memory only and is
never written to disk. Costs about 1 quota unit per 50 subscriptions.
"""

import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
CLIENT_SECRET = Path(
    os.environ.get("CLIENT_SECRET_PATH", "~/.podcast-recall/client_secret.json")
).expanduser()


def main() -> None:
    if not CLIENT_SECRET.exists():
        raise SystemExit(f"client secret not found at {CLIENT_SECRET}")

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    creds = flow.run_local_server(port=0)
    youtube = build("youtube", "v3", credentials=creds)

    titles: list[str] = []
    token = None
    while True:
        resp = youtube.subscriptions().list(
            part="snippet", mine=True, maxResults=50, pageToken=token
        ).execute()
        titles += [item["snippet"]["title"] for item in resp["items"]]
        token = resp.get("nextPageToken")
        if not token:
            break

    print(f"subscriptions: {len(titles)}")
    for t in titles[:10]:
        print(f"  - {t}")


if __name__ == "__main__":
    main()
