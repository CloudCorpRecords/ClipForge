# ClipForge: the beginner walkthrough

## 1. Put the app on your computer

A ZIP is a compressed folder. Download it from the repository's green **Code → Download ZIP** button. On Windows, right-click it and choose **Extract All**. On Mac, double-click the ZIP. Move the extracted folder somewhere permanent, such as Documents. The folder contains `extension`, `server`, and the install files.

Install Google Chrome, Python 3.11–3.13 (64-bit), and Node.js 22 or newer first. Use the official download links in the README. On Windows tick **Add python.exe to PATH** during Python setup. Close and reopen Chrome after installing Node.

Double-click **Install ClipForge.cmd** on Windows or **Install ClipForge.command** on Mac. This creates ClipForge's Python environment, downloads its video tools and registers the automatic engine with Chrome for your user account. Wait for the success message. If it fails, read the last error in the window and the troubleshooting section in README; rerun after fixing it.

## 2. Add it to Chrome

1. Open Chrome. Type `chrome://extensions` in the address bar and press Enter.
2. Turn on **Developer mode** in the upper right.
3. Click **Load unpacked**. Open your extracted ClipForge folder, select its **extension** folder, and confirm.
4. Click the puzzle-piece icon beside Chrome's address bar. Pin ClipForge.
5. Click ClipForge to open the editor. It should say **Local service connected**.

Keep the extracted folder; Chrome loads the app from there. This is a manually installed extension, not a Chrome Web Store download. After an update, rerun the installer and reload the extension.

## 3. Tell it about yourself

Open **AI & settings**. Under **Tell ClipForge about you**, fill in what you want the caption writer to know. Example:

- Name: Jamie's Garden Studio
- What you do: I teach balcony gardening in small spaces.
- Audience: Beginners growing their first herbs.
- Voice: Friendly, practical, no hype.
- Offers and facts: My beginner guide costs $15.
- Call to action: Get my beginner guide.
- Things to avoid: No guarantees; don't mention competitors.
- Website and resource: Your actual links, or leave them blank.

Click **Save settings**. Your profile is personal to this installation. You can replace or clear it at any time. For the full tone/audience/offer controls, add your own funded OpenRouter key. Local mode uses simpler templates. Changing your profile does not rewrite already scheduled posts.

## 4. Make your first clip

Upload a short recording first so you can learn quickly. Pick **Local Whisper** and **Local suggestions** to start without API keys. Choose the number and approximate length of clips, then **Generate clips**. The speech model downloads on first use. Review each clip, adjust the start/end and framing, and render. Click **MP4** to save it to your computer.

OpenRouter is a separate optional AI service. Its key goes in **OpenRouter API key**, never in the social integration field. Cloud modes use your API credits. You can leave all cloud services disconnected and still edit/export locally.

## Social posting with Aspire Builder Pro

### A. Get a workspace

Visit **[Aspire Builder Pro](https://aspirebuilderpro.com)** and follow its signup steps. It offers a business platform with social planning; check current plans and confirm Social Planner plus Private Integrations access before purchasing. If unsure, ask support: “I want to connect ClipForge to Social Planner using a location-level Private Integration token. Can you enable that for my business?”

Already have a compatible HighLevel workspace? Use that. An Aspire subscription is optional for ClipForge editing and downloading.

### B. Connect your actual social channels

Sign in to your business workspace. Open **Marketing → Social Planner** and use its connect-account controls. Log in to each social service you want to use and select the pages/channels you manage. Complete the authorization prompts. If Social Planner is missing, ask your administrator/support for access. ClipForge reads these connected accounts; it does not need your Facebook, YouTube or other social passwords.

### C. Create the social token

In the **business/location workspace**, open **Settings → Private Integrations → Create new Integration**. Name it **ClipForge**. A “scope” means a permission. Select these five permissions:

```
socialplanner/account.readonly
socialplanner/post.readonly
socialplanner/post.write
medias.write
users.readonly
```

Create the integration and copy its generated token. Paste it into ClipForge's **Private integration token** field. Use a location/sub-account token, not an agency-wide token or an old API v1 key. If Private Integrations is missing, ask your administrator/support to create it with these permissions. Do not email or post your token publicly.

### D. Copy your location ID

While inside your business workspace, look at the browser address. It may look like `https://app.aspirebuilderpro.com/v2/location/ABC123.../dashboard`. Copy only the text after `/location/` and before the next `/`. That is the location ID. Paste it into **Location ID** in ClipForge.

### E. Test and save

Click **Test connection**. A successful check reports how many accounts and staff were found. Select your staff identity under **Posting as**, then **Save settings**. Zero accounts means you still need to connect channels in Social Planner. A permission error usually means a missing scope, the wrong location ID or the wrong type of token.

### F. Schedule your first post

Render a clip, click **Schedule**, select a connected account, and choose your post type. Pick a generated caption or write one yourself. **New options** rewrites using your saved creator profile. Review the first comment too; support varies by social network and post type. Pick a future day/time and click **Schedule post**. Check **Calendar** and your workspace's Social Planner for the resulting status. Scheduling acceptance does not guarantee that the social network will publish successfully.

## Helpful references

- [Aspire Builder Pro plans](https://aspirebuilderpro.com/pricing)
- [HighLevel Private Integrations documentation](https://marketplace.gohighlevel.com/docs/Authorization/PrivateIntegrationsToken/index.html)
- [HighLevel Social Posting API: location token support](https://marketplace.gohighlevel.com/docs/2023-02-21/ghl/social-planner/social-media-posting-api/)
- [Chrome native messaging setup](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging)
