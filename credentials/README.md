# YouTube Data API v3 Setup Guide

To enable automated uploads to your YouTube channel, set up an OAuth 2.0 Client ID:

### 1. Google Cloud Console Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g. `Game-Automation-Pipeline`).
3. In the sidebar, navigate to **APIs & Services** > **Library**.
4. Search for **YouTube Data API v3** and click **Enable**.

### 2. Configure OAuth Consent Screen
1. Navigate to **APIs & Services** > **OAuth consent screen**.
2. Select **External** (or Internal if using Google Workspace).
3. Fill in App Name (e.g. `Game Uploader`), User support email, and Developer contact email.
4. In **Scopes**, add `https://www.googleapis.com/auth/youtube.upload`.
5. Under **Test users**, add your own Google / YouTube account email.

### 3. Create Credentials
1. Navigate to **APIs & Services** > **Credentials**.
2. Click **+ CREATE CREDENTIALS** -> **OAuth client ID**.
3. Select **Desktop app** as the Application type.
4. Name it `Game Pipeline Client` and click **Create**.
5. Click **Download JSON** and save the file to this directory as:
   `credentials/client_secret.json`

### 4. First Run Authentication
Run:
```cmd
.venv\Scripts\python.exe main.py --test-youtube
```
A browser window will open asking you to sign in to your Google account and grant upload permissions. Once approved:
- A `token.json` file is automatically generated in `credentials/`.
- Future pipeline runs will upload silently in the background without asking for authorization again!

