import argparse
import getpass
import json
import os

from app import TEACHERS_FILE, hash_password, load_teacher_accounts


def main():
    parser = argparse.ArgumentParser(description="Manage local teacher accounts")
    parser.add_argument("username", help="username for the new teacher account")
    args = parser.parse_args()

    username = args.username.strip()
    accounts = load_teacher_accounts()
    if any(account.get("username", "").casefold() == username.casefold() for account in accounts):
        parser.error("a teacher account with that username already exists")

    password = getpass.getpass("New teacher password (minimum 12 characters): ")
    if len(password) < 12:
        parser.error("password must contain at least 12 characters")
    if password != getpass.getpass("Confirm password: "):
        parser.error("passwords do not match")

    accounts.append({"username": username, "password_hash": hash_password(password)})
    temporary_file = TEACHERS_FILE.with_suffix(".json.tmp")
    temporary_file.write_text(json.dumps(accounts, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary_file, 0o600)
    temporary_file.replace(TEACHERS_FILE)
    print(f"Teacher account '{username}' added to {TEACHERS_FILE}")


if __name__ == "__main__":
    main()