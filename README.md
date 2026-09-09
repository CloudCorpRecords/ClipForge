# ClipForge

ClipForge is a Chrome extension with a private local video engine. Chrome owns the visible studio; the engine supplies FFmpeg, local Whisper transcription, URL importing, face-aware reframing, captions, and MP4 rendering.

## Normal use

1. Click ClipForge in Chrome while viewing one of your YouTube videos, or open ClipForge and upload a file.
2. Import the video.
3. Choose Local Whisper or OpenRouter in **AI & settings**.
4. Generate clips, review the suggested cuts, adjust framing and captions, then export.

The extension asks Chrome Native Messaging to start the engine automatically. No Terminal window or visible `127.0.0.1` page is needed. The engine listens only on this Mac, and the API accepts the fixed ClipForge extension origin plus its own local development origin.

## One-time installation

**Supported: macOS + Google Chrome.** Install Python 3.11+ and Node.js 22+ first.

Click **Code → Download ZIP** above and extract it to a permanent folder, or clone this repository. Read [START HERE.txt](START%20HERE.txt) for full setup details, then:

1. Double-click **Install ClipForge.command**.
2. Open `chrome://extensions`, enable Developer mode, and choose **Load unpacked**.
3. Select the `extension` folder inside your extracted project folder.

If the project folder moves, run **Install ClipForge.command** again so Chrome knows the companion's new absolute path.

## Troubleshooting

- Reload ClipForge on `chrome://extensions` after changing extension code.
- Use **Start ClipForge.command** only as a manual recovery tool.
- The engine log is `data/engine.log`.
- Native startup diagnostics are in `~/Library/Application Support/ClipForge/native-host.log`. The installer registers a launcher that uses ClipForge's exact Python environment, so startup does not depend on Chrome's `PATH`.
- Protected or authenticated streams may reject URL importing. Upload your original video file in that case.
- OpenRouter is optional. Its key and GoHighLevel credentials are stored in the ignored local `data` directory, never in the extension source.

## Uninstalling

Remove the extension in Chrome. Double-click **Uninstall ClipForge Companion.command** to move the automatic-start registration to Trash. Projects remain in `data` until you remove them yourself.

## Requirements and limits

The local companion is required for rendering; this is not a browser-only WebAssembly app. Chrome starts it automatically after installation. Internet access is needed for dependency/model downloads and URL imports. OpenRouter is optional and requires your own funded key. Local Whisper downloads its model on first use.

Recorded streams up to 4 hours / 8 GB fit the configured input limits; processing time depends on your Mac. Review generated captions and framing before publishing. Windows and Linux installers are not included.

If macOS reports a command file is not executable, open Terminal in the extracted folder and run `bash "Install ClipForge.command"`.
