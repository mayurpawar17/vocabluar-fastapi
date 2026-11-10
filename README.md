# AI Conversation API

This folder contains the FastAPI backend for the Flutter app's AI
conversation feature. The API:

- Verifies the Firebase Authentication ID token sent by the signed-in app.
- Calls Gemini using a key stored only on the backend.
- Saves conversations and messages in the signed-in user's Firestore data.
- Returns optional grammar corrections, vocabulary tips, and a session
  summary.

The local development setup runs the API on your computer. It does not
require Cloud Run or `gcloud auth application-default login`.

## Requirements

- Python 3.11 or newer.
- Flutter and the project dependencies installed.
- A Firebase project configured for this app, with Authentication and
  Cloud Firestore enabled.
- A Gemini API key.
- A Firebase service-account JSON file with permission to access this
  project's Firestore.

## 1. Prepare Firebase and Gemini credentials

1. In Firebase Console, confirm that the Firebase project is the same one
   configured in `lib/firebase_options.dart`.
2. Enable the sign-in provider you use in the app under Firebase
   Authentication, and create a test user if needed.
3. Ensure Cloud Firestore is created for the project.
4. Create a service-account key in Firebase Console under **Project
   settings → Service accounts**. Store the downloaded JSON file outside
   this repository, for example in a private folder under your home
   directory. Do not commit or share the file.
5. Create a Gemini API key in Google AI Studio. Do not put this key in
   Flutter code, screenshots, or source control.

The service account is used by the backend process to access Firestore.
It is separate from the Firebase ID token that Flutter sends to identify
the app user. Grant the service account only the access it needs.

## 2. Create and configure the Python environment

Open a terminal at the repository root, then:

```sh
cd backend
python3.12 --version
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
touch .env
```

If `python3.12` is not installed, install Python 3.12 or newer and use
that version's command to create the virtual environment. Do not reuse a
virtual environment created with Python 3.9; remove or rename that
environment and recreate it with the newer interpreter.

Edit `backend/.env` and add your local values:

```dotenv
FIREBASE_PROJECT_ID=your-firebase-project-id
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
DAILY_MESSAGE_LIMIT=50
MAX_MESSAGE_LENGTH=500
CORS_ORIGINS=
```

The `.env` file is ignored by Git and is the only settings file used for
local configuration. Keep the Firebase service-account JSON
outside the repository and point the Firebase Admin SDK to its full path
in the same terminal:

```sh
export GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/your-service-account.json"
```

`GOOGLE_APPLICATION_CREDENTIALS` must point to the JSON file itself, not
just the directory containing it. These credentials are for local
development only.

## 3. Start and check FastAPI

From the `backend/` directory, with `.venv` active and the credentials
environment variable set:

```sh
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Keep this terminal open while using the app. Verify that the server is
running by opening:

- Health check: <http://localhost:8080/health> — should return
  `{"status":"ok"}`.
- Interactive API documentation: <http://localhost:8080/docs>.

To stop the API, press **Ctrl+C** in its terminal. To leave the Python
virtual environment, run `deactivate`.

## 4. Run Flutter against the local API

Open a second terminal at the repository root. Set
`CONVERSATION_API_BASE_URL` to an address reachable from the device that
runs the app:

### Android emulator

The Android emulator reaches the host computer using `10.0.2.2`:

```sh
flutter run --dart-define=CONVERSATION_API_BASE_URL=http://10.0.2.2:8080
```

This is also the Flutter app's default API URL.

### iOS simulator

```sh
flutter run --dart-define=CONVERSATION_API_BASE_URL=http://localhost:8080
```

### Physical Android or iOS device

Use your computer's private LAN IP address, not `localhost`. The phone
and computer must be on the same network, and the computer firewall must
allow inbound connections on port `8080`.

```sh
flutter run --dart-define=CONVERSATION_API_BASE_URL=http://YOUR_COMPUTER_LAN_IP:8080
```

Replace `YOUR_COMPUTER_LAN_IP` with the computer's current LAN address.
If you change the API URL, stop and rerun Flutter because this value is
provided at build time.

## 5. Try the conversation

1. Start the FastAPI server and leave it running.
2. Start the Flutter app with the correct API URL.
3. Sign in with a Firebase Authentication account.
4. Open the vocabulary feed and tap **AI conversation**.
5. Choose a topic and English level, then start chatting.
6. End the conversation to see its learning summary.

The backend sends conversation data to Gemini and stores it in Firestore.
Make sure your privacy notices and data handling are appropriate before
using real personal conversations.

## API endpoints

All conversation endpoints require this header:

```http
Authorization: Bearer <Firebase ID token>
```

- `POST /v1/conversations` — create a conversation. Example body:
  `{"topic":"daily_life","level":"beginner"}`.
- `POST /v1/conversations/{conversationId}/messages` — send a message.
  Example body: `{"text":"Yesterday I went to the market."}`.
- `POST /v1/conversations/{conversationId}/end` — finish the session and
  return its summary.

The supported topics are `daily_life`, `work`, `travel`, `shopping`,
`interview`, and `free_conversation`. Levels are `beginner`,
`intermediate`, and `advanced`.

## Troubleshooting

- **Python version warnings or `| None` type errors:** Check
  `python --version` after activating `.venv`. Recreate the environment
  with Python 3.11 or newer if it was made with Python 3.9.
- **Firebase credential or permission errors:** Confirm
  `GOOGLE_APPLICATION_CREDENTIALS` points to the service-account JSON
  file, the project ID matches the app, and the service account can
  access Firestore.
- **401 / sign-in error:** Sign in to the Flutter app and confirm the
  Firebase Authentication project matches `FIREBASE_PROJECT_ID`.
- **Gemini unavailable / invalid API key:** Check `GEMINI_API_KEY`, model
  availability, and Gemini API quota in the backend terminal and Google
  AI Studio.
- **Connection refused:** Confirm Uvicorn is running on port `8080` and
  the Flutter app is using the correct device-specific base URL.
- **Physical device cannot connect:** Use the computer's LAN IP, ensure
  both devices are on the same network, and check firewall settings.

## Security notes

- Never commit `.env`, Gemini credentials, or service-account JSON keys.
- The backend currently verifies Firebase Authentication ID tokens, but
  does not yet verify Firebase App Check tokens. Do not expose this
  development API publicly until App Check verification and production
  abuse protections are configured.
- The local HTTP URLs above are for development. Use HTTPS for any
  deployed service.

## Deployment

For deployment, build this directory as a Cloud Run service, assign a
dedicated service account the minimum required Firestore permissions,
and provide the Gemini key through Google Secret Manager. Set
`CONVERSATION_API_BASE_URL` to the deployed HTTPS service URL in the
Flutter build.
