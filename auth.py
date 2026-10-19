import os
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


class AuthError(Exception):
    pass


def get_service(interactive=False):
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            creds = None

    if not creds or not creds.valid:
        if not interactive:
            raise AuthError("Login expired. Run gmail-automation.py by hand to log in again.")
        flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
        creds = flow.run_local_server(port=0)

    with open("token.json", "w") as f:
        f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)