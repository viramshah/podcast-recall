# Podcast Recall: Mission

## Intent
Ask a question in plain English from any MCP client (for example Claude Desktop) and get an answer drawn from the podcasts in my YouTube library. Every answer names the episode, gives the exact quote and timestamp, and links to the episode at that moment.

## North star
Every useful answer can be saved as a finding and exported to Markdown/Notion, Google Docs or Apple Notes, so it is on my phone when I need it.

## Quality bar
At least 90% of answers are grounded in the user's podcasts, measured against the rubric in the requirements doc (section 1.4). At most 2% of answers contain a critical failure. Fabricated citations never reach the user.

## Budget
$0 in new spend. Everything runs locally on an Apple Silicon Mac.

## Users (v1)
The owner plus up to 4 testers, each with their own Google account added as an OAuth test user.

## In scope (v1)
- YouTube library: subscriptions, own playlists, Liked videos.
- Transcripts from the publisher's RSS audio (found through Podcast Index), transcribed locally.
- Cited answers, local verifier, exports, evaluation harness.

## Out of scope (v1)
- Spotify (v1.1; needs Premium for Dev Mode and has an AI-content policy to check).
- Apple Podcasts and YouTube Music (v2).
- In-app audio playback, mobile app, public sign-up, video or visual content, auto-summaries of every episode.
- Watch history (no API exposes it).
