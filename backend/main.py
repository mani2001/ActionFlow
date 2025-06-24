import os
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from pathlib import Path

app = FastAPI()

# Session middleware for login sessions
app.add_middleware(SessionMiddleware, secret_key="very-long-secret-key-actionflow-project-1234567890")

# Serve frontend and static files
frontend_path = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_path / "static"), name="static")

@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_path = frontend_path / "index.html"
    return HTMLResponse(index_path.read_text(encoding="utf-8"))

# ==== Google Auth Config ====
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CLIENT_SECRETS_FILE = str(Path(__file__).parent / "credentials.json")
REDIRECT_URI = "http://localhost:8000/auth/callback"

# ==== Google Drive Auth Routes ====

@app.get("/auth")
def login(request: Request):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    request.session["state"] = state
    return RedirectResponse(auth_url)

@app.get("/auth/callback")
def auth_callback(request: Request):
    state = request.session.get("state")
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI,
    )
    flow.fetch_token(authorization_response=str(request.url))
    creds = flow.credentials
    # Save credentials in session
    request.session["credentials"] = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }
    return RedirectResponse("/")

@app.get("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return JSONResponse({"success": True})

@app.get("/auth/status")
def auth_status(request: Request):
    creds_dict = request.session.get("credentials")
    if creds_dict:
        return {"connected": True}
    return {"connected": False}

# ==== List Meet Recordings Transcripts ====

@app.get("/drive/meet-transcripts")
def get_meet_transcripts(request: Request):
    creds_dict = request.session.get("credentials")
    if not creds_dict:
        return JSONResponse({"error": "not_connected"}, status_code=401)
    creds = Credentials(**creds_dict)
    drive_service = build('drive', 'v3', credentials=creds)

    # Find "Meet Recordings" folder
    results = drive_service.files().list(
        q="mimeType='application/vnd.google-apps.folder' and name='Meet Recordings' and trashed=false",
        fields="files(id, name)").execute()
    folders = results.get('files', [])
    if not folders:
        return JSONResponse({"error": "no_folder"})
    folder_id = folders[0]['id']

    # List transcript files in that folder, sorted by most recent
    transcript_results = drive_service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        orderBy="modifiedTime desc",
        pageSize=5,
        fields="files(id, name, modifiedTime)").execute()
    transcripts = transcript_results.get('files', [])
    if not transcripts:
        return JSONResponse({"error": "no_transcripts"})
    return JSONResponse({
        "transcripts": [
            {
                "id": f["id"],
                "name": f["name"],
                "modifiedTime": f["modifiedTime"]
            }
            for f in transcripts
        ]
    })

def extract_text_from_google_doc(doc):
    text = ""
    for idx, element in enumerate(doc.get("body", {}).get("content", [])):
        if "paragraph" in element:
            para_text = ""
            for p_elem in element["paragraph"].get("elements", []):
                if "textRun" in p_elem and "content" in p_elem["textRun"]:
                    para_text += p_elem["textRun"]["content"]
            text += para_text + "\n"
    return text


@app.get("/api/transcript/{meeting_id}")
def get_transcript(request: Request, meeting_id: str):
    creds_dict = request.session.get("credentials")
    if not creds_dict:
        return Response("Not authorized", status_code=401)
    creds = Credentials(**creds_dict)
    drive_service = build('drive', 'v3', credentials=creds)
    docs_service = build('docs', 'v1', credentials=creds)

    # Find "Meet Recordings" folder
    folders = drive_service.files().list(
        q="mimeType='application/vnd.google-apps.folder' and name='Meet Recordings' and trashed=false",
        fields="files(id)").execute().get('files', [])
    if not folders:
        return Response("Meet Recordings folder not found.", status_code=404)
    folder_id = folders[0]['id']

    # Search for the file by name (assuming meeting_id is the name)
    query = (
        f"'{folder_id}' in parents and "
        f"mimeType='application/vnd.google-apps.document' and "
        f"name contains '{meeting_id}' and trashed=false"
    )
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    if not files:
        return Response("Transcript not found.", status_code=404)
    
    # Use the first matching file (can refine as needed)
    file_id = files[0]['id']
    doc = docs_service.documents().get(documentId=file_id).execute()
    text = extract_text_from_google_doc(doc)
    # Convert the content to plain text
    print("=== Transcript extracted ===")
    print(text)
    print("=== End of transcript ===")
    return Response(text, media_type="text/plain")
# Optional: healthcheck route
@app.get("/ping")
def ping():
    return {"pong": True}

# Run: uvicorn backend.main:app --reload
