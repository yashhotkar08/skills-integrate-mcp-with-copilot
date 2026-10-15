# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Teacher login to register and unregister students
- Public activity and participant-list viewing

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Create a local teacher account. Passwords are stored as salted hashes in the ignored `teachers.json` file:

   ```
   cd src
   python manage_teachers.py teacher
   ```

3. Set a stable session signing key and run the application:

   ```
   export SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
   uvicorn app:app --reload
   ```

   Set `COOKIE_SECURE=true` when serving over HTTPS. Without `SESSION_SECRET`, the app uses a temporary key and active logins expire on restart.

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| GET    | `/auth/me`                                                        | Check whether the current browser has a teacher session              |
| POST   | `/auth/login`                                                     | Log in with a teacher username and password                         |
| POST   | `/auth/logout`                                                    | End the current teacher session                                     |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Register a student (teacher session required)                       |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teacher session required)                  |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as the identifier in activity participant lists.

3. **Teachers** - Local accounts are provisioned with `manage_teachers.py`; only salted password hashes are written to `teachers.json`, which is ignored by Git.

Activity and participant data is stored in memory and resets when the server restarts. Teacher accounts remain in the local JSON file.
