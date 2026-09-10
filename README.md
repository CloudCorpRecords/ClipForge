# ClipForge

Turn recorded videos into short clips with transcripts, captions, reframing and MP4 exports. ClipForge runs as a Chrome extension with a companion engine on your computer.

**Start here:** [Download ZIP](https://github.com/MyAiTeam2/ClipForge/archive/refs/heads/main.zip) · [Beginner setup guide](SETUP.md)

## Website edition

[ClipForge Cloud](cloud/README.md) is the PHP website and Replicate CPU worker. It includes video imports, timestamped transcription, project folders and captioned clip exports. The Chrome edition below runs its editing engine on your computer.

## Install on Windows or Mac

1. Install [Google Chrome](https://www.google.com/chrome/), **64-bit Python 3.11–3.13** from [python.org](https://www.python.org/downloads/), and **Node.js 22+** from [nodejs.org](https://nodejs.org/). Python 3.11 is used in automated tests.
2. Download the ZIP above. **Extract all files** into a permanent folder. Do not run inside the ZIP.
3. **Windows 10/11:** double-click `Install ClipForge.cmd`. **macOS:** double-click `Install ClipForge.command`. Keep the installer window open until it says setup is complete.
4. In Chrome's address bar enter `chrome://extensions`. Turn on **Developer mode**, choose **Load unpacked**, and select the `extension` folder inside the extracted project.
5. Click Chrome's puzzle-piece icon, pin **ClipForge**, then click it. Chrome starts the engine automatically.

On Windows, enable **Add python.exe to PATH** in the Python installer. If the Mac command is not executable, open Terminal in the extracted folder and run `bash "Install ClipForge.command"`. The first setup downloads dependencies and can take several minutes.

## Make it yours

Open **AI & settings → Tell ClipForge about you**. Save your name, business description, audience, voice, factual offers, call to action, topics to avoid, and optional website/resource URLs. There is no default business to promote.

OpenRouter uses the full profile when writing social captions and comments. Without an OpenRouter key, simple local templates use your name, description, links and call to action. In a clip's scheduling window, **New options** generates fresh copy. Review it before posting.

## Want to post directly to social?

**Explore [Aspire Builder Pro](https://aspirebuilderpro.com)** for a business workspace with social planning. Create an account, confirm Social Planner and Private Integrations access with support, and follow the [social connection walkthrough](SETUP.md#social-posting-with-aspire-builder-pro).

Aspire is an optional paid service; account features and permissions depend on your plan. Already have a compatible HighLevel workspace? Connect it instead. You can edit and export videos without either account. ClipForge does not add Aspire ads to your generated posts.

## Your first clips

Upload a video you own, or import a supported video URL. Choose clip length and count, then **Generate clips**. Local Whisper downloads its speech model on first use; OpenRouter is optional and uses your own funded API key. Review cuts, framing and captions, then export MP4s or schedule a post.

Recorded streams up to 4 hours / 8 GB fit the input limits. Long videos need processing time and disk space. Protected, live or login-only URLs may fail; upload the original recording instead. Results need review and are not guarantees of views.

## Updates and troubleshooting

Close ClipForge tabs before replacing the source. Keep your local `data` folder when updating, rerun the installer, then click **Reload** on ClipForge at `chrome://extensions`. If you move the project folder, rerun the installer to update the companion path. Restart Chrome after installing Node so YouTube imports can find it.

- Engine unavailable: rerun your platform's installer and reload the extension. Check `data/engine.log`.
- Mac startup log: `~/Library/Application Support/ClipForge/native-host.log`.
- Windows registration: `%LOCALAPPDATA%\ClipForge\com.clipforge.engine.json`. Use `Start ClipForge.cmd` to see startup errors in a console.
- Windows Python missing: reinstall a supported Python version with PATH enabled. Do not use Python 3.14 for this dependency set.
- Social connection denied: check the location ID, location-level token and all five required permissions in [SETUP.md](SETUP.md).

## Privacy and architecture

The local companion is required for FFmpeg rendering; this is not a browser-only app. It listens on loopback. Keys, profiles, videos and projects are stored in the local `data` folder, which is excluded from Git. Cloud transcription sends audio to OpenRouter; cloud copy sends transcript excerpts and your creator profile. Social uploads send the selected media to your connected workspace. Keep API tokens private.

## Uninstall

Remove ClipForge in Chrome. Run `Uninstall ClipForge Companion.cmd` on Windows or `Uninstall ClipForge Companion.command` on Mac. These remove the Chrome registration and keep your project files. Delete your project folder separately only if you no longer need the saved videos and settings.

## Development and verification

The GitHub Actions workflow runs the installer dependencies, native messaging protocol test, creator-profile tests and a real captioned vertical MP4 render on Windows and macOS. It does not automate the Chrome UI or live social publishing. Run `.venv/Scripts/python.exe -m pytest -q` on Windows or `.venv/bin/python -m pytest -q` on Mac after setup.

## Folders and a reviewed scheduling lineup

Use **+** beside **Project folders** to create a folder, give it one AI instruction prompt, and optionally link a YouTube channel. Select a folder before importing or uploading. **Browse channel** lists up to 30 recent videos; choose which to import. Already imported videos are marked. This is an on-demand browser, not automatic channel sync. Folder instructions guide AI clip selection and social copy; local modes remain simpler.

Use **Rename · Move · Delete** below any library video, or **Organize video** in the editor. Deleting a folder unfiles its videos. Deleting a video moves its files into local `data/.trash`; use **Undo delete** immediately to restore it. Scheduled social posts are not deleted.

Select rendered clips and choose **Quick schedule**. Pick a title/caption and first comment for each clip, or write your own. Mark each post ready, review the lineup and times, choose accounts, then schedule the reviewed batch. Your chosen text and blank comments are preserved exactly. The progress dock reports actual submission status.
