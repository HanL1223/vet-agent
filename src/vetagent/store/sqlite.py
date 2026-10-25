"""SQLite store for data the app owns. Clinic records are never copied here (PR-3)."""

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS proposals (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS clinic_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS weight_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id TEXT NOT NULL,
    kg REAL NOT NULL,
    shared_with_clinic INTEGER NOT NULL,
    logged_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS consent (
    owner_id TEXT PRIMARY KEY,
    share_log INTEGER NOT NULL,
    deidentified_use INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reminders (
    gap_key TEXT PRIMARY KEY,
    sent_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS checkins (
    pet_id TEXT NOT NULL,
    week TEXT NOT NULL,
    scores TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (pet_id, week)
);
CREATE TABLE IF NOT EXISTS recaps (
    id TEXT PRIMARY KEY,
    pet_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    released_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ticks (
    pet_id TEXT NOT NULL,
    item TEXT NOT NULL,
    ticked_at TEXT NOT NULL,
    PRIMARY KEY (pet_id, item)
);
CREATE TABLE IF NOT EXISTS triage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id TEXT NOT NULL,
    symptom TEXT NOT NULL,
    hours INTEGER NOT NULL,
    level TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class Proposal:
    id: str
    owner_id: str
    kind: str  # "booking_request" | "vet_note"
    payload: dict[str, Any]
    status: str  # "pending" | "confirmed" | "dismissed"


@dataclass(frozen=True)
class Consent:
    share_log: bool
    deidentified_use: bool


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str) -> None:
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(SCHEMA)

    # Conversation -----------------------------------------------------------
    def append_message(self, owner_id: str, message: dict[str, Any]) -> None:
        self._exec(
            "INSERT INTO messages (owner_id, payload, created_at) VALUES (?, ?, ?)",
            (owner_id, json.dumps(message), _now()),
        )

    def messages(self, owner_id: str) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT payload FROM messages WHERE owner_id = ? ORDER BY id", (owner_id,)
        ).fetchall()
        return [json.loads(r["payload"]) for r in rows]

    def clear_conversation(self, conversation: str, owner_id: str, pet_id: str) -> None:
        """Drop one pet's chat and its unsent proposals; sent requests stay with the clinic."""
        self._exec("DELETE FROM messages WHERE owner_id = ?", (conversation,))
        self._exec(
            "DELETE FROM proposals WHERE owner_id = ? AND status = 'pending'"
            " AND json_extract(payload, '$.pet_id') = ?",
            (owner_id, pet_id),
        )

    # Proposals (AG-4) ---------------------------------------------------------
    def create_proposal(self, owner_id: str, kind: str, payload: dict[str, Any]) -> Proposal:
        proposal = Proposal(uuid.uuid4().hex[:12], owner_id, kind, payload, "pending")
        self._exec(
            "INSERT INTO proposals (id, owner_id, kind, payload, status, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (proposal.id, owner_id, kind, json.dumps(payload), proposal.status, _now()),
        )
        return proposal

    def proposal(self, proposal_id: str) -> Proposal | None:
        row = self._db.execute("SELECT * FROM proposals WHERE id = ?", (proposal_id,)).fetchone()
        if row is None:
            return None
        return Proposal(
            row["id"], row["owner_id"], row["kind"], json.loads(row["payload"]), row["status"]
        )

    def set_proposal_status(self, proposal_id: str, status: str) -> None:
        self._exec("UPDATE proposals SET status = ? WHERE id = ?", (status, proposal_id))

    # Requests sent to the clinic ---------------------------------------------
    def add_clinic_request(self, pet_id: str, kind: str, detail: str) -> None:
        self._exec(
            "INSERT INTO clinic_requests (pet_id, kind, detail, created_at) VALUES (?, ?, ?, ?)",
            (pet_id, kind, detail, _now()),
        )

    def clinic_requests(self) -> list[dict[str, Any]]:
        rows = self._db.execute("SELECT * FROM clinic_requests ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

    # Health log (AG-5) ---------------------------------------------------------
    def log_weight(self, pet_id: str, kg: float, shared: bool) -> None:
        self._exec(
            "INSERT INTO weight_logs (pet_id, kg, shared_with_clinic, logged_at)"
            " VALUES (?, ?, ?, ?)",
            (pet_id, kg, int(shared), _now()),
        )

    def weights(self, pet_id: str) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT kg, shared_with_clinic, logged_at FROM weight_logs WHERE pet_id = ?"
            " ORDER BY id",
            (pet_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # Consent (PR-1, PR-2) ------------------------------------------------------
    def consent(self, owner_id: str) -> Consent:
        row = self._db.execute(
            "SELECT share_log, deidentified_use FROM consent WHERE owner_id = ?", (owner_id,)
        ).fetchone()
        if row is None:
            return Consent(share_log=True, deidentified_use=False)
        return Consent(bool(row["share_log"]), bool(row["deidentified_use"]))

    def set_consent(self, owner_id: str, consent: Consent) -> None:
        self._exec(
            "INSERT INTO consent (owner_id, share_log, deidentified_use, updated_at)"
            " VALUES (?, ?, ?, ?) ON CONFLICT(owner_id) DO UPDATE SET"
            " share_log = excluded.share_log, deidentified_use = excluded.deidentified_use,"
            " updated_at = excluded.updated_at",
            (owner_id, int(consent.share_log), int(consent.deidentified_use), _now()),
        )

    # Clinic reminders (CL-4) ---------------------------------------------------
    def mark_reminded(self, gap_key: str) -> None:
        self._exec(
            "INSERT OR IGNORE INTO reminders (gap_key, sent_at) VALUES (?, ?)", (gap_key, _now())
        )

    def reminded_keys(self) -> set[str]:
        return {r["gap_key"] for r in self._db.execute("SELECT gap_key FROM reminders")}

    # Weekly check-ins (HT-1): one per pet per ISO week, the latest replaces it -----
    def save_checkin(self, pet_id: str, week: str, scores: dict[str, int]) -> None:
        self._exec(
            "INSERT INTO checkins (pet_id, week, scores, created_at) VALUES (?, ?, ?, ?)"
            " ON CONFLICT(pet_id, week) DO UPDATE SET"
            " scores = excluded.scores, created_at = excluded.created_at",
            (pet_id, week, json.dumps(scores), _now()),
        )

    def checkins(self, pet_id: str) -> list[tuple[str, dict[str, int]]]:
        rows = self._db.execute(
            "SELECT week, scores FROM checkins WHERE pet_id = ? ORDER BY week", (pet_id,)
        ).fetchall()
        return [(r["week"], json.loads(r["scores"])) for r in rows]

    # Visit recaps the clinic released to the owner (VR-1) -----------------------
    def release_recap(self, recap_id: str, pet_id: str, recap: dict[str, Any]) -> None:
        self._exec(
            "INSERT OR REPLACE INTO recaps (id, pet_id, payload, released_at) VALUES (?, ?, ?, ?)",
            (recap_id, pet_id, json.dumps(recap), _now()),
        )

    def recaps(self, pet_id: str) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT payload FROM recaps WHERE pet_id = ? ORDER BY released_at", (pet_id,)
        ).fetchall()
        return [json.loads(r["payload"]) for r in rows]

    # Things the owner ticked off: recap instructions (VR-2), new-pet steps (NP-1) ---
    def set_tick(self, pet_id: str, item: str, done: bool) -> None:
        if done:
            self._exec(
                "INSERT OR IGNORE INTO ticks (pet_id, item, ticked_at) VALUES (?, ?, ?)",
                (pet_id, item, _now()),
            )
        else:
            self._exec("DELETE FROM ticks WHERE pet_id = ? AND item = ?", (pet_id, item))

    def ticks(self, pet_id: str) -> set[str]:
        rows = self._db.execute("SELECT item FROM ticks WHERE pet_id = ?", (pet_id,))
        return {r["item"] for r in rows}

    # "Should I come in?" answers, kept for clinic insight (TR-5) -------------------
    def log_triage(self, pet_id: str, symptom: str, hours: int, level: str) -> None:
        self._exec(
            "INSERT INTO triage_log (pet_id, symptom, hours, level, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (pet_id, symptom, hours, level, _now()),
        )

    def triage_log(self, pet_id: str) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT symptom, hours, level FROM triage_log WHERE pet_id = ? ORDER BY id",
            (pet_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def _exec(self, sql: str, params: tuple) -> None:
        with self._db:
            self._db.execute(sql, params)
