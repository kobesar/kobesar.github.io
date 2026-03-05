# Swing Scout — AI Golf Swing Analyzer

A single-file static web app that analyzes your golf swing from a photo using Claude's vision capabilities and returns structured coaching feedback.

## Setup

1. The app lives at `index.html` — no build step required
2. Deploy to GitHub Pages or open the file directly in a browser
3. Enter your [Anthropic API key](https://console.anthropic.com/settings/keys) when prompted
4. Upload a photo of a golf swing and get instant AI coaching feedback

## How it works

Upload a swing photo, and Claude analyzes your stance, grip, backswing, downswing, posture, and balance — returning scores and actionable tips for each.

## Direct browser access

This app calls the Anthropic API directly from the browser using the `anthropic-dangerous-direct-browser-access` header. This means your API key is sent from the client side. This is fine for personal use, but for a production app with multiple users you'd want a backend proxy so your API key isn't exposed in network requests.

## Cost

Each analysis costs approximately **$0.01** depending on image size (uses `claude-sonnet-4-20250514` with a 1,000 token max output).
