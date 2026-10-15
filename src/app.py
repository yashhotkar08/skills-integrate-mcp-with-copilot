"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

SESSION_COOKIE = "teacher_session"
SESSION_TTL = 8 * 60 * 60
SESSION_SECRET = os.environ.get("SESSION_SECRET") or secrets.token_urlsafe(32)
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "").lower() in {"1", "true", "yes"}
TEACHERS_FILE = Path(__file__).with_name("teachers.json")


class LoginCredentials(BaseModel):
    username: str
    password: str


def load_teacher_accounts():
    if not TEACHERS_FILE.exists():
        return []
    with TEACHERS_FILE.open(encoding="utf-8") as teacher_file:
        accounts = json.load(teacher_file)
    if not isinstance(accounts, list):
        raise RuntimeError("Teacher account data must be a JSON list")
    return accounts


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    salt_text = base64.urlsafe_b64encode(salt).decode().rstrip("=")
    digest_text = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return f"pbkdf2_sha256$600000${salt_text}${digest_text}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = password_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        salt = base64.urlsafe_b64decode(salt_text + "=" * (-len(salt_text) % 4))
        expected = base64.urlsafe_b64decode(digest_text + "=" * (-len(digest_text) % 4))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except (AttributeError, ValueError, TypeError):
        return False


def _encode_session(username: str) -> str:
    payload = json.dumps({"username": username, "expires": int(time.time()) + SESSION_TTL})
    encoded_payload = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    signature = hmac.new(
        SESSION_SECRET.encode(), encoded_payload.encode(), hashlib.sha256
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{encoded_payload}.{encoded_signature}"


def _current_teacher(request: Request):
    token = request.cookies.get(SESSION_COOKIE, "")
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        signature = base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        )
        expected_signature = hmac.new(
            SESSION_SECRET.encode(), encoded_payload.encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(signature, expected_signature):
            return None
        payload = base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)
        )
        session = json.loads(payload)
        username = session.get("username")
        if session.get("expires", 0) <= time.time() or not isinstance(username, str):
            return None
        if not any(account.get("username") == username for account in load_teacher_accounts()):
            return None
        return username
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def require_teacher(request: Request):
    username = _current_teacher(request)
    if username is None:
        raise HTTPException(status_code=401, detail="Teacher login required")
    return username


@app.get("/auth/me")
def get_auth_status(request: Request):
    username = _current_teacher(request)
    return {"authenticated": username is not None, "username": username}


@app.post("/auth/login")
def login(credentials: LoginCredentials, response: Response):
    account = next(
        (item for item in load_teacher_accounts()
         if item.get("username") == credentials.username),
        None,
    )
    if account is None or not verify_password(
        credentials.password, account.get("password_hash", "")
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    response.set_cookie(
        SESSION_COOKIE,
        _encode_session(credentials.username),
        max_age=SESSION_TTL,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return {"authenticated": True, "username": credentials.username}


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )
    return {"authenticated": False}

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, _teacher: str = Depends(require_teacher)):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, _teacher: str = Depends(require_teacher)):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
