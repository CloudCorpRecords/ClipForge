# ClipForge Cloud

A PHP website backed by a custom Replicate CPU worker. Your visitors need a browser; Python, FFmpeg, yt-dlp and Whisper run inside the Replicate model. The PHP host handles login, uploads, project metadata, API calls and durable downloads.

This is a private studio with one shared studio login, not a public multi-tenant subscription service. It reuses the Chrome extension's actual HTML, CSS and studio JavaScript. The same library, folders, channel browser, timeline, keyframes, transcript correction, caption controls, Saved view, Calendar and reviewed Quick Schedule connect to PHP and Replicate. Only local-engine/storage labels change to describe the website accurately. Social accounts require your own compatible GoHighLevel/Aspire integration settings.

## 1. Deploy the video engine

Install Docker and [Cog 0.16.12](https://github.com/replicate/cog/releases/tag/v0.16.12), then create a [Replicate account](https://replicate.com/signin). Add account credit if Replicate requests it.

Copy `php/config.example.json` to `php/private/config.json`. Put your Replicate API token in `replicate_token`. Keep this file private. It is excluded from Git. Run:

```sh
cog login
python3 cloud/deploy.py --owner YOUR_REPLICATE_USERNAME
```

Run the Python command from the repository root. It creates a private model, pushes the Cog image, and creates or updates a deployment using `cpu`, `min_instances: 0`, `max_instances: 1`. It saves the resulting deployment name in PHP configuration. Pin Cog 0.16.12: the newer runtime tested here embedded large file outputs in JSON. `deploy.py` disables the floating Cog base image; `COG_BIN` can point to your pinned executable. Docker and Cog are needed only for publishing updates, not on the PHP web host.

The custom-model API currently accepts `cpu` (4 CPUs, 8 GB RAM) as its lowest CPU tier: $0.0001/second ($0.36/running hour), checked September 9, 2026. The pricing page lists `cpu-small`, but both model creation and deployment creation rejected it for this account. The worker limits compute threads for modest resource use. Private deployments bill setup, active time and time waiting to scale down. Zero minimum instances avoids keeping a worker permanently warm; cold starts and slow processing are expected. See [pricing](https://replicate.com/pricing) and [deployment documentation](https://replicate.com/docs/topics/deployments/create-a-deployment).

If Docker registry uploads fail, install the official `crane` utility and add `--native-push` to the deployment command. This uploads from the host with HTTP/1.1 and normal TLS certificate verification.

## 2. Set up the website locally

Requires PHP 8.2+ with cURL and ZipArchive. Start a loopback-only setup server:

```sh
CLIPFORGE_SETUP=1 php -d upload_max_filesize=500M -d post_max_size=510M -S 127.0.0.1:8099 -t cloud/php/public
```

On Windows PowerShell, set `$env:CLIPFORGE_SETUP='1'` before running the `php` command. Open `http://127.0.0.1:8099/setup.php`, enter the API token and deployment name, and choose your studio password. The optional OpenRouter key enables AI selection using your creator/project instructions. Without it, Whisper still transcribes locally in the Replicate worker and suggestions use speech density and hook-word scoring. Tokens stay in server configuration, never browser JavaScript.

Stop the setup server and restart without `CLIPFORGE_SETUP`. Open the website root and sign in. The `registry_token` field is only useful during model publishing and can be removed from config after publishing.

## 3. Publish on PHP hosting

Upload the entire `cloud/php` directory **outside** the public web root. Configure your domain's document root to its `public` subdirectory. Never set the document root to the repository, `cloud`, or `php` directory. `private/config.json`, uploaded projects and rendered assets must not be served directly.

Give PHP write access to `php/private` (owner-only where practical). Enable HTTPS, `session.cookie_secure=1`, HttpOnly session cookies, and a long unique studio password. Keep `CLIPFORGE_DEV` and `CLIPFORGE_SETUP` unset in production. For a host that cannot change its document root, ask support to point the domain at `php/public`; do not copy secrets into `public_html`.

Set PHP upload limit 500M, post limit 510M, request and reverse-proxy timeouts up to 1500 seconds. The included `.user.ini` sets PHP limits where supported. Nginx also needs `client_max_body_size 510m` and an appropriate FastCGI timeout. Save enough disk space for sources, rendered clips and backups. A URL import can download up to 2 GB even though browser uploads are limited to 500 MB.

Add this cron job, replacing the path:

```cron
* * * * * /usr/bin/php /absolute/path/to/cloud/php/worker.php >> /absolute/private/path/clipforge-worker.log 2>&1
```

The worker polls pending jobs and saves results even when the browser is closed. Replicate API output files expire after one hour, so this worker is required for reliable persistence. The browser also polls while open. For multi-user scale, replace filesystem records with a database and use object storage/queued transfers.

## 4. Make clips

1. Create a folder and describe your channel's voice and audience in its instructions.
2. Paste a YouTube/direct video link or upload an original recording. Start with a short original recording for a quick test. Importing prepares the source; Generate clips transcribes and selects moments.
3. Pick the number and target length of clips, transcription accuracy, and creative direction. Generate clips to create the timestamped transcript.
4. Preview and edit each suggested moment. Choose framing, captions, zoom and pause trimming.
5. Save & render your edits, or use Export all. Download individual MP4s, a ZIP, the source, or the timestamped JSON.

YouTube may reject downloads from datacenter IP addresses. Uploading the original recording is the fallback; this software does not bypass login, DRM or bot challenges. Videos must be under four hours and 2 GB; render batches contain up to twelve clips of 1–180 seconds each, at 720p or 1080p. CPU transcription offers tiny English, small multilingual, and medium accuracy options. Larger models take longer. Linux may substitute available caption fonts for macOS-only families. Review captions and crop decisions before publishing. No tool guarantees viral reach.

## PHP API example

The browser calls `public/api.php`; that script calls Replicate server-side with cURL. To call the model from your own PHP backend:

```php
require '/private/path/to/cloud/php/lib.php';
$prediction = startPrediction([
    'task' => 'analyze',
    'video_url' => 'https://www.youtube.com/watch?v=_6jkAqq97T8',
    'clip_count' => 3,
    'clip_length' => 30,
    'preview_seconds' => 60,
    'render_clips' => false,
]);
// Persist $prediction['id']; later poll:
$result = replicate('GET', 'predictions/'.$prediction['id']);
```

Render with `task: render`, the previously returned source as `video`, transcript JSON as `transcript_file`, and `edits_json` containing the reviewed edits. Start/end values use source seconds. Optional `keyframes` contain clip-relative `time`, normalized `x` and `y` (0–1), and `zoom` (1–2). Keep output files on your server before they expire.

## Checks

```sh
python3 cloud/tests/test_php.py
node --check cloud/php/public/app.js
python3 cloud/tests/test_ui.py
php cloud/tests/test_social.php
cd cloud/model
cog build -t clipforge-cloud:latest --use-cog-base-image=false
cog predict -i video=@/absolute/path/to/video.mp4 -i preview_seconds=30 -i clip_count=1 -i clip_length=20 -i render_clips=true
```

`test_php.py` uses a disposable private directory and checks real HTTP login, CSRF, folder CRUD, video rename/move/delete, video byte ranges and private-file isolation. It makes no paid API calls. A local container test is not proof of a live Replicate deployment: confirm the deployment and run the sample URL/upload against it before production use.
