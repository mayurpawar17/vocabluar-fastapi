import logging
import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client

logger = logging.getLogger("uvicorn.error")
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)


def get_firebase_app() -> firebase_admin.App:
    try:
        return firebase_admin.get_app()
    except ValueError:
        options = {}
        from .config import get_settings

        settings = get_settings()
        if project_id := settings.firebase_project_id:
            options["projectId"] = project_id

        cred = None
        cred_path = (
            settings.google_application_credentials
            or settings.firebase_credentials_path
            or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        )

        # Auto-detect service account json file in project root if not explicitly set
        if not cred_path:
            for candidate in Path(".").glob("*service*account*.json"):
                if candidate.is_file():
                    cred_path = str(candidate)
                    break

        if cred_path:
            path_obj = Path(cred_path).expanduser().resolve()
            if path_obj.is_file():
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(path_obj)
                cred = credentials.Certificate(str(path_obj))
                logger.info(
                    "Firebase service account file loaded successfully from: %s",
                    path_obj,
                )
            else:
                logger.warning(
                    "Configured Firebase service account file was not found at: %s",
                    cred_path,
                )
        else:
            logger.info(
                "No explicit service account JSON path specified. Using Google Application Default Credentials.",
            )

        app = firebase_admin.initialize_app(credential=cred, options=options or None)
        logger.info(
            "Firebase Admin initialized successfully (project: %s)",
            options.get("projectId") or app.project_id,
        )
        return app


def get_firestore_client() -> Client:
    return firestore.client(app=get_firebase_app())
