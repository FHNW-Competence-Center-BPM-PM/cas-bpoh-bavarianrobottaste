import hashlib
import json
import mimetypes
import os
import secrets
import smtplib
import threading
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
PENDING_REGISTRATIONS_FILE = DATA_DIR / "pending_registrations.json"
GUEST_PROFILES_FILE = DATA_DIR / "guest_profiles.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8080"))
REGISTRATION_CODE_TTL_MINUTES = int(os.environ.get("REGISTRATION_CODE_TTL_MINUTES", "15"))
PASSWORD_HASH_ITERATIONS = 200_000
DATA_LOCK = threading.Lock()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now_utc().isoformat()


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def read_json_file(path: Path, fallback):
    ensure_data_dir()
    if not path.exists():
        return fallback

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json_file(path: Path, payload) -> None:
    ensure_data_dir()
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    temp_path.replace(path)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def generate_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def smtp_settings() -> dict:
    return {
        "host": os.environ["SMTP_HOST"],
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ["SMTP_USER"],
        "password": os.environ["SMTP_PASS"],
        "mail_from": os.environ.get("MAIL_FROM", os.environ["SMTP_USER"]),
        "registration_url": os.environ.get("REGISTRATION_URL", "http://localhost:8080/register.html"),
    }


def send_messages(messages: list[EmailMessage]) -> None:
    settings = smtp_settings()

    with smtplib.SMTP(settings["host"], settings["port"], timeout=20) as smtp:
        smtp.starttls()
        smtp.login(settings["user"], settings["password"])
        for message in messages:
            smtp.send_message(message)


def build_thank_you_message(first_name: str, registration_url: str) -> str:
    return (
        f"Hallo {first_name}\n\n"
        "vielen Dank für deine Nachricht an Bavarian RoboTaste.\n\n"
        "Wir haben deine Anfrage erhalten und leiten sie intern weiter. "
        "Unser Team meldet sich so schnell wie möglich bei dir.\n\n"
        "Wenn du dich schon jetzt registrierst, können wir deine künftigen "
        "Besuche besser begleiten. Außerdem wartet bei jedem Restaurantbesuch "
        "eine kleine Überraschung auf dich.\n\n"
        f"Hier kannst du dich registrieren:\n{registration_url}\n\n"
        "Beste Grüße\n"
        "Bavarian RoboTaste\n"
    )


def build_registration_code_message(first_name: str, code: str) -> str:
    return (
        f"Hallo {first_name}\n\n"
        "dein Bestätigungscode für die Registrierung bei Bavarian RoboTaste lautet:\n\n"
        f"{code}\n\n"
        f"Der Code ist {REGISTRATION_CODE_TTL_MINUTES} Minuten gültig.\n\n"
        "Falls du diese Registrierung nicht angefordert hast, kannst du diese E-Mail ignorieren.\n\n"
        "Beste Grüße\n"
        "Bavarian RoboTaste\n"
    )


def build_registration_success_message(first_name: str, registration_url: str) -> str:
    return (
        f"Hallo {first_name}\n\n"
        "deine Registrierung bei Bavarian RoboTaste ist jetzt abgeschlossen.\n\n"
        "Ab sofort können wir deine künftigen Besuche, Reservierungen und besondere Überraschungen "
        "besser auf dich abstimmen.\n\n"
        f"Hier findest du deine Registrierungsseite erneut:\n{registration_url}\n\n"
        "Bis bald bei Bavarian RoboTaste\n"
        "Bavarian RoboTaste\n"
    )


def build_contact_messages(payload: dict) -> list[EmailMessage]:
    settings = smtp_settings()
    name = payload["name"].strip()
    first_name = name.split()[0]
    sender_email = payload["email"].strip()
    topic = payload["topic"].strip()
    message = payload["message"].strip()

    internal_message = EmailMessage()
    internal_message["Subject"] = f"Neue Kontaktanfrage: {topic}"
    internal_message["From"] = settings["mail_from"]
    internal_message["To"] = settings["user"]
    internal_message["Reply-To"] = sender_email
    internal_message.set_content(
        "Neue Nachricht über das Kontaktformular\n\n"
        f"Name: {name}\n"
        f"E-Mail: {sender_email}\n"
        f"Thema: {topic}\n\n"
        f"Nachricht:\n{message}\n"
    )

    thank_you_message = EmailMessage()
    thank_you_message["Subject"] = "Danke für deine Nachricht an Bavarian RoboTaste"
    thank_you_message["From"] = settings["mail_from"]
    thank_you_message["To"] = sender_email
    thank_you_message.set_content(build_thank_you_message(first_name, settings["registration_url"]))

    return [internal_message, thank_you_message]


def build_registration_code_email(first_name: str, email: str, code: str) -> EmailMessage:
    settings = smtp_settings()
    message = EmailMessage()
    message["Subject"] = "Dein Bestätigungscode für Bavarian RoboTaste"
    message["From"] = settings["mail_from"]
    message["To"] = email
    message.set_content(build_registration_code_message(first_name, code))
    return message


def build_registration_success_email(first_name: str, email: str) -> EmailMessage:
    settings = smtp_settings()
    message = EmailMessage()
    message["Subject"] = "Deine Registrierung bei Bavarian RoboTaste ist abgeschlossen"
    message["From"] = settings["mail_from"]
    message["To"] = email
    message.set_content(build_registration_success_message(first_name, settings["registration_url"]))
    return message


def create_password_hash(password: str) -> dict:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS)
    return {
        "algorithm": "pbkdf2_sha256",
        "iterations": PASSWORD_HASH_ITERATIONS,
        "salt": salt.hex(),
        "hash": derived_key.hex(),
    }


def verify_password_hash(password: str, password_state: dict) -> bool:
    if not password_state:
        return False

    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(password_state["salt"]),
        int(password_state["iterations"]),
    )
    return secrets.compare_digest(derived_key.hex(), password_state["hash"])


def guest_profiles() -> list[dict]:
    profiles = read_json_file(GUEST_PROFILES_FILE, [])
    return profiles if isinstance(profiles, list) else []


def pending_registrations() -> dict:
    registrations = read_json_file(PENDING_REGISTRATIONS_FILE, {})
    return registrations if isinstance(registrations, dict) else {}


def sessions() -> dict:
    auth_sessions = read_json_file(SESSIONS_FILE, {})
    return auth_sessions if isinstance(auth_sessions, dict) else {}


def public_profile(profile: dict) -> dict:
    return {
        "id": profile["id"],
        "firstName": profile["firstName"],
        "email": profile["email"],
        "phone": profile.get("phone", ""),
        "createdAt": profile.get("createdAt", ""),
    }


def find_profile_by_email(email: str) -> dict | None:
    normalized_email = normalize_email(email)
    return next((profile for profile in guest_profiles() if normalize_email(profile["email"]) == normalized_email), None)


def find_profile_by_id(profile_id: str) -> dict | None:
    return next((profile for profile in guest_profiles() if profile["id"] == profile_id), None)


def is_code_expired(expires_at: str) -> bool:
    return datetime.fromisoformat(expires_at) < now_utc()


def create_session(profile_id: str) -> str:
    with DATA_LOCK:
        auth_sessions = sessions()
        token = secrets.token_urlsafe(32)
        auth_sessions[token] = {
            "guestProfileId": profile_id,
            "createdAt": now_iso(),
        }
        write_json_file(SESSIONS_FILE, auth_sessions)
    return token


def delete_session(token: str) -> None:
    with DATA_LOCK:
        auth_sessions = sessions()
        auth_sessions.pop(token, None)
        write_json_file(SESSIONS_FILE, auth_sessions)


def profile_for_token(token: str) -> dict | None:
    auth_sessions = sessions()
    session = auth_sessions.get(token)
    if not session:
        return None
    return find_profile_by_id(session["guestProfileId"])


def request_registration_code(payload: dict) -> None:
    email = normalize_email(payload["email"])

    with DATA_LOCK:
        if find_profile_by_email(email):
            raise ValueError("Für diese E-Mail-Adresse existiert bereits ein Gastprofil.")

        registrations = pending_registrations()
        code = generate_verification_code()
        registrations[email] = {
            "firstName": payload["firstName"].strip(),
            "email": email,
            "phone": payload.get("phone", "").strip(),
            "verificationCode": code,
            "requestedAt": now_iso(),
            "expiresAt": (now_utc() + timedelta(minutes=REGISTRATION_CODE_TTL_MINUTES)).isoformat(),
            "verifiedAt": None,
        }
        write_json_file(PENDING_REGISTRATIONS_FILE, registrations)

    send_messages([build_registration_code_email(payload["firstName"].strip(), email, code)])


def verify_registration_code(payload: dict) -> None:
    email = normalize_email(payload["email"])
    code = str(payload.get("verificationCode", "")).strip()

    with DATA_LOCK:
        registrations = pending_registrations()
        registration = registrations.get(email)
        if not registration:
            raise ValueError("Für diese E-Mail-Adresse gibt es keine offene Registrierung.")
        if is_code_expired(registration["expiresAt"]):
            registrations.pop(email, None)
            write_json_file(PENDING_REGISTRATIONS_FILE, registrations)
            raise ValueError("Der Bestätigungscode ist abgelaufen. Bitte fordere einen neuen Code an.")
        if not code or registration["verificationCode"] != code:
            raise ValueError("Der eingegebene Bestätigungscode ist nicht korrekt.")

        registration["verifiedAt"] = now_iso()
        registrations[email] = registration
        write_json_file(PENDING_REGISTRATIONS_FILE, registrations)


def complete_registration(payload: dict) -> tuple[dict, str]:
    email = normalize_email(payload["email"])
    password = payload["password"]

    with DATA_LOCK:
        registrations = pending_registrations()
        registration = registrations.get(email)
        if not registration:
            raise ValueError("Für diese E-Mail-Adresse gibt es keine offene Registrierung.")
        if is_code_expired(registration["expiresAt"]):
            registrations.pop(email, None)
            write_json_file(PENDING_REGISTRATIONS_FILE, registrations)
            raise ValueError("Der Bestätigungscode ist abgelaufen. Bitte fordere einen neuen Code an.")
        if not registration.get("verifiedAt"):
            raise ValueError("Bitte bestätige zuerst deinen E-Mail-Code.")
        if find_profile_by_email(email):
            raise ValueError("Für diese E-Mail-Adresse existiert bereits ein Gastprofil.")

        guest_profile = {
            "id": f"guest_{secrets.token_hex(8)}",
            "firstName": registration["firstName"],
            "email": registration["email"],
            "phone": registration["phone"],
            "createdAt": now_iso(),
            "registrationSource": "website",
            "password": create_password_hash(password),
        }

        profiles = guest_profiles()
        profiles.append(guest_profile)
        write_json_file(GUEST_PROFILES_FILE, profiles)

        registrations.pop(email, None)
        write_json_file(PENDING_REGISTRATIONS_FILE, registrations)

    send_messages([build_registration_success_email(guest_profile["firstName"], guest_profile["email"])])
    token = create_session(guest_profile["id"])
    return guest_profile, token


def login_user(email: str, password: str) -> tuple[dict, str]:
    profile = find_profile_by_email(email)
    if not profile or not verify_password_hash(password, profile.get("password", {})):
        raise ValueError("E-Mail oder Passwort ist nicht korrekt.")

    token = create_session(profile["id"])
    return profile, token


def update_profile(profile_id: str, payload: dict) -> dict:
    with DATA_LOCK:
        profiles = guest_profiles()
        profile = next((item for item in profiles if item["id"] == profile_id), None)
        if not profile:
            raise ValueError("Das Gastprofil wurde nicht gefunden.")

        first_name = str(payload.get("firstName", "")).strip()
        if not first_name:
            raise ValueError("Bitte gib einen Vornamen an.")

        profile["firstName"] = first_name
        profile["phone"] = str(payload.get("phone", "")).strip()
        write_json_file(GUEST_PROFILES_FILE, profiles)
        return profile


def change_password(profile_id: str, current_password: str, new_password: str) -> None:
    with DATA_LOCK:
        profiles = guest_profiles()
        profile = next((item for item in profiles if item["id"] == profile_id), None)
        if not profile:
            raise ValueError("Das Gastprofil wurde nicht gefunden.")
        if not verify_password_hash(current_password, profile.get("password", {})):
            raise ValueError("Das aktuelle Passwort ist nicht korrekt.")

        profile["password"] = create_password_hash(new_password)
        write_json_file(GUEST_PROFILES_FILE, profiles)


def parse_json_body(handler) -> dict:
    content_length = int(handler.headers.get("Content-Length", "0"))
    raw_body = handler.rfile.read(content_length)
    return json.loads(raw_body.decode("utf-8"))


def bearer_token(handler) -> str | None:
    authorization = handler.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    return authorization.removeprefix("Bearer ").strip()


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        if self.path == "/api/auth/me":
            self.handle_auth_me()
            return
        super().do_GET()

    def do_POST(self):
        routes = {
            "/api/contact": self.handle_contact,
            "/api/register/request-code": self.handle_register_request_code,
            "/api/register/verify-code": self.handle_register_verify_code,
            "/api/register/complete": self.handle_register_complete,
            "/api/auth/login": self.handle_auth_login,
            "/api/auth/logout": self.handle_auth_logout,
            "/api/profile": self.handle_profile_update,
            "/api/profile/change-password": self.handle_profile_change_password,
        }

        handler = routes.get(self.path)
        if not handler:
            self.send_error(404, "Not found")
            return

        try:
            payload = parse_json_body(self)
        except json.JSONDecodeError:
            self.respond_json(400, {"ok": False, "error": "invalid_json"})
            return

        handler(payload)

    def authenticated_profile(self) -> tuple[str | None, dict | None]:
        token = bearer_token(self)
        if not token:
            return None, None
        return token, profile_for_token(token)

    def handle_auth_me(self):
        _, profile = self.authenticated_profile()
        if not profile:
            self.respond_json(401, {"ok": False, "error": "unauthorized"})
            return

        self.respond_json(200, {"ok": True, "guestProfile": public_profile(profile)})

    def handle_contact(self, payload: dict):
        required_fields = ["name", "email", "topic", "message"]
        missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
        if missing:
            self.respond_json(400, {"ok": False, "error": "missing_fields", "fields": missing})
            return

        try:
            send_messages(build_contact_messages(payload))
        except Exception as exc:
            self.respond_json(500, {"ok": False, "error": "mail_send_failed", "detail": str(exc)})
            return

        self.respond_json(200, {"ok": True})

    def handle_register_request_code(self, payload: dict):
        required_fields = ["firstName", "email"]
        missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
        if missing:
            self.respond_json(400, {"ok": False, "error": "missing_fields", "fields": missing})
            return

        try:
            request_registration_code(payload)
        except ValueError as exc:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": str(exc)})
            return
        except Exception as exc:
            self.respond_json(500, {"ok": False, "error": "mail_send_failed", "detail": str(exc)})
            return

        self.respond_json(200, {"ok": True})

    def handle_register_verify_code(self, payload: dict):
        required_fields = ["email", "verificationCode"]
        missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
        if missing:
            self.respond_json(400, {"ok": False, "error": "missing_fields", "fields": missing})
            return

        try:
            verify_registration_code(payload)
        except ValueError as exc:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": str(exc)})
            return

        self.respond_json(200, {"ok": True})

    def handle_register_complete(self, payload: dict):
        required_fields = ["email", "password", "passwordConfirm"]
        missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
        if missing:
            self.respond_json(400, {"ok": False, "error": "missing_fields", "fields": missing})
            return

        if payload["password"] != payload["passwordConfirm"]:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": "Die Passwörter stimmen nicht überein."})
            return

        if len(payload["password"]) < 8:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": "Das Passwort muss mindestens 8 Zeichen lang sein."})
            return

        try:
            guest_profile, token = complete_registration(payload)
        except ValueError as exc:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": str(exc)})
            return
        except Exception as exc:
            self.respond_json(500, {"ok": False, "error": "registration_failed", "detail": str(exc)})
            return

        self.respond_json(
            200,
            {
                "ok": True,
                "token": token,
                "guestProfile": public_profile(guest_profile),
            },
        )

    def handle_auth_login(self, payload: dict):
        required_fields = ["email", "password"]
        missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
        if missing:
            self.respond_json(400, {"ok": False, "error": "missing_fields", "fields": missing})
            return

        try:
            profile, token = login_user(payload["email"], payload["password"])
        except ValueError as exc:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": str(exc)})
            return

        self.respond_json(200, {"ok": True, "token": token, "guestProfile": public_profile(profile)})

    def handle_auth_logout(self, payload: dict):
        token, _ = self.authenticated_profile()
        if token:
            delete_session(token)
        self.respond_json(200, {"ok": True})

    def handle_profile_update(self, payload: dict):
        _, profile = self.authenticated_profile()
        if not profile:
            self.respond_json(401, {"ok": False, "error": "unauthorized"})
            return

        try:
            updated_profile = update_profile(profile["id"], payload)
        except ValueError as exc:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": str(exc)})
            return

        self.respond_json(200, {"ok": True, "guestProfile": public_profile(updated_profile)})

    def handle_profile_change_password(self, payload: dict):
        _, profile = self.authenticated_profile()
        if not profile:
            self.respond_json(401, {"ok": False, "error": "unauthorized"})
            return

        required_fields = ["currentPassword", "newPassword", "newPasswordConfirm"]
        missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
        if missing:
            self.respond_json(400, {"ok": False, "error": "missing_fields", "fields": missing})
            return

        if payload["newPassword"] != payload["newPasswordConfirm"]:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": "Die neuen Passwörter stimmen nicht überein."})
            return

        if len(payload["newPassword"]) < 8:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": "Das neue Passwort muss mindestens 8 Zeichen lang sein."})
            return

        try:
            change_password(profile["id"], payload["currentPassword"], payload["newPassword"])
        except ValueError as exc:
            self.respond_json(400, {"ok": False, "error": "validation_error", "detail": str(exc)})
            return

        self.respond_json(200, {"ok": True})

    def guess_type(self, path):
        if str(path).endswith(".js"):
            return "application/javascript"
        return mimetypes.guess_type(path)[0] or "application/octet-stream"

    def respond_json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ensure_data_dir()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Serving Bavarian RoboTaste on http://{HOST}:{PORT}")
    server.serve_forever()
