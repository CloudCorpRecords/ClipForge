# Verification — September 9, 2026

- Website CSS is byte-for-byte identical to the installed Chrome extension. Automated checks compare the original HTML element, ID and class structure as well.
- Live PHP → Replicate → PHP render succeeded with the published CPU worker. A timestamped transcript from a 60-second excerpt of the requested YouTube video produced a captioned vertical clip. The reviewed title, timing and keyframe were preserved; browser playback verified 1080 × 1920 and 10.871 seconds.
- The full requested YouTube source (`_6jkAqq97T8`) was imported through PHP and Replicate: 3355.562 seconds, 1280 × 720, 593,762,296 bytes saved on the website. Browser media metadata confirmed the full source loads. The full 55-minute transcript was not generated in this test; transcription/render verification used the excerpt above.
- Finished clip saved to the studio library. Its download ZIP was created successfully.
- PHP HTTP tests cover authentication, CSRF, folder/video changes, transcript/clip data, private file isolation and byte-range media delivery. Worker validation and social payload tests pass.
- Social payload checks preserve reviewed captions and first comments, including intentionally blank comments. No live social posts were sent.
- Deployment uses `cpu`, minimum zero and maximum one instance. Model and deployment IDs are in `deployment.json`.

This verifies a private single-studio website, not production hosting or multi-tenant billing. A PHP hosting destination and studio password still need to be configured. YouTube availability varies; upload original recordings when a URL cannot be downloaded.
