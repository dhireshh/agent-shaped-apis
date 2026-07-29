# Taking this into Claude Code and up to GitHub

You don't need to write or edit any code. Follow these steps in order.

## 1. Download the project from this chat

Below this file, there should be a way to download the whole
`partly-agent-api-experiment` folder (or a zip of it). Save it somewhere
easy to find, like your Desktop.

If you only see individual files rather than a folder/zip, ask me and
I'll package it as a single zip file for you.

## 2. Open Claude Code

Open the Claude Code app (desktop or however you normally launch it).

## 3. Point Claude Code at the folder you downloaded

- If Claude Code asks you to open or select a project folder, choose the
  `partly-agent-api-experiment` folder you just downloaded (unzip it
  first if it came as a zip).
- If it opens to an empty/different project, look for an "Open Folder"
  or "Open Project" option and select it there.

## 4. Ask Claude Code to create the GitHub repo for you

Once it's open, just type into Claude Code, in plain English:

> "Create a new public GitHub repo called `agent-shaped-apis` from this
> folder, and push it."

Claude Code will:
- notice you're not yet in a git repo and initialize one
- ask you to authenticate with GitHub the first time (it'll open a
  browser login — this is normal, just approve it)
- create the repo under your GitHub account
- commit the files and push them up

You'll get a confirmation with the repo URL when it's done.

## 5. Double check it landed

Go to `github.com/<your-username>` in a browser and confirm you see the
new repo with all the files (`README.md`, `src/`, `results/`, etc.).

## 6. If anything goes sideways

- **"Claude Code says git isn't installed"** — tell it to install git,
  or install Xcode Command Line Tools (Mac) / Git for Windows first,
  then retry the same request.
- **"It created the repo but the push failed"** — just say "try the
  push again" — this is almost always a one-off auth hiccup.
- **"I want it private, not public"** — say "make it a private repo"
  instead in step 4.

## After it's live

Update the `[link]` placeholder in `WRITEUP.md` with your real GitHub
URL before you post it anywhere.
