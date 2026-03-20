"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
import sqlite3

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

DB_PATH = current_dir / "activities.db"

INITIAL_ACTIVITIES = {
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


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS registrations (
                activity_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (activity_id, user_id),
                FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )


def seed_initial_data() -> None:
    with get_connection() as connection:
        activity_count = connection.execute(
            "SELECT COUNT(*) AS count FROM activities"
        ).fetchone()["count"]

        if activity_count > 0:
            return

        for activity_name, details in INITIAL_ACTIVITIES.items():
            cursor = connection.execute(
                """
                INSERT INTO activities (name, description, schedule, max_participants)
                VALUES (?, ?, ?, ?)
                """,
                (
                    activity_name,
                    details["description"],
                    details["schedule"],
                    details["max_participants"],
                ),
            )
            activity_id = cursor.lastrowid

            for email in details["participants"]:
                connection.execute(
                    "INSERT OR IGNORE INTO users (email) VALUES (?)",
                    (email,),
                )
                user_id = connection.execute(
                    "SELECT id FROM users WHERE email = ?",
                    (email,),
                ).fetchone()["id"]
                connection.execute(
                    """
                    INSERT OR IGNORE INTO registrations (activity_id, user_id)
                    VALUES (?, ?)
                    """,
                    (activity_id, user_id),
                )


def fetch_activities() -> dict:
    with get_connection() as connection:
        activity_rows = connection.execute(
            """
            SELECT id, name, description, schedule, max_participants
            FROM activities
            WHERE archived = 0
            ORDER BY name
            """
        ).fetchall()

        activities = {
            row["name"]: {
                "description": row["description"],
                "schedule": row["schedule"],
                "max_participants": row["max_participants"],
                "participants": [],
            }
            for row in activity_rows
        }

        registration_rows = connection.execute(
            """
            SELECT a.name AS activity_name, u.email AS email
            FROM registrations r
            JOIN activities a ON a.id = r.activity_id
            JOIN users u ON u.id = r.user_id
            WHERE a.archived = 0
            ORDER BY a.name, r.created_at
            """
        ).fetchall()

        for row in registration_rows:
            activities[row["activity_name"]]["participants"].append(row["email"])

    return activities


def get_activity_id(connection: sqlite3.Connection, activity_name: str):
    activity_row = connection.execute(
        "SELECT id FROM activities WHERE name = ? AND archived = 0",
        (activity_name,),
    ).fetchone()
    if activity_row is None:
        return None
    return activity_row["id"]


@app.on_event("startup")
def startup() -> None:
    init_db()
    seed_initial_data()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return fetch_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    with get_connection() as connection:
        activity_id = get_activity_id(connection, activity_name)
        if activity_id is None:
            raise HTTPException(status_code=404, detail="Activity not found")

        connection.execute(
            "INSERT OR IGNORE INTO users (email) VALUES (?)",
            (email,),
        )
        user_id = connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()["id"]

        existing_registration = connection.execute(
            """
            SELECT 1
            FROM registrations
            WHERE activity_id = ? AND user_id = ?
            """,
            (activity_id, user_id),
        ).fetchone()

        if existing_registration is not None:
            raise HTTPException(
                status_code=400,
                detail="Student is already signed up"
            )

        connection.execute(
            """
            INSERT INTO registrations (activity_id, user_id)
            VALUES (?, ?)
            """,
            (activity_id, user_id),
        )

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    with get_connection() as connection:
        activity_id = get_activity_id(connection, activity_name)
        if activity_id is None:
            raise HTTPException(status_code=404, detail="Activity not found")

        user_row = connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        if user_row is None:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity"
            )

        deleted_rows = connection.execute(
            """
            DELETE FROM registrations
            WHERE activity_id = ? AND user_id = ?
            """,
            (activity_id, user_row["id"]),
        ).rowcount

        if deleted_rows == 0:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity"
            )

    return {"message": f"Unregistered {email} from {activity_name}"}
