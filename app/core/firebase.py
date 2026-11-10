import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore import Client


def get_firebase_app() -> firebase_admin.App:
    try:
        return firebase_admin.get_app()
    except ValueError:
        options = {}
        from .config import get_settings

        if project_id := get_settings().firebase_project_id:
            options["projectId"] = project_id
        return firebase_admin.initialize_app(options=options or None)


def get_firestore_client() -> Client:
    return firestore.client(app=get_firebase_app())
