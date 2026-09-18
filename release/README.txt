What's in your fridge? — quick start
=====================================

You don't need to know anything about code to run this. Just follow these
steps:

1. Install Docker Desktop if you don't have it yet:
   https://www.docker.com/products/docker-desktop/
   Open it once and make sure it's running (you'll see its icon in your
   menu bar / system tray).

2. Double-click:
   - macOS:   run.command
   - Windows: run.bat
   - Linux:   run.sh (from a terminal)

   The first run downloads everything, which can take a few minutes.

   macOS note: the first time you double-click run.command (or stop.command),
   macOS will likely say it's "from an unidentified developer" and refuse to
   open it. Right-click the file, choose "Open", then confirm — you only
   need to do this once per file.

3. Wait. A browser window will open automatically at
   http://127.0.0.1:8080 once the app is ready.

4. To close the app: double-click stop.command (macOS) / stop.bat (Windows)
   / run stop.sh (Linux). Your data (in the data/ folder next to this file)
   is never touched by stopping or restarting.

5. To update: when the app tells you a new version is available, just
   re-run run.command / run.bat / run.sh — it downloads the new version and
   restarts automatically. No need to download anything new unless told
   otherwise.

Everything runs entirely on your own machine — nothing is shared over the
network except pulling the app's own images and a one-off check for new
versions.
