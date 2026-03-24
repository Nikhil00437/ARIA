import datetime
from typing import Optional
from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure
from constants import MONGO_URI, MONGO_DB, COL_SESSIONS, COL_COMMANDS, COL_SELFMOD, COL_PROFILE

class Database:
    def __init__(self):
        self._client: Optional[MongoClient] = None
        self._db = None
        self._connected = False

    def connect(self) -> bool:
        try:
            self._client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
            self._client.admin.command("ping")
            self._db = self._client[MONGO_DB]
            self._ensure_indexes()
            self._connected = True
            return True
        except ConnectionFailure as e:
            print(f"[DB] MongoDB connection failed: {e}")
            self._connected = False
            return False

    def _ensure_indexes(self):
        self._db[COL_SESSIONS].create_index([("session_id", 1)])
        self._db[COL_COMMANDS].create_index([("session_id", 1), ("timestamp", DESCENDING)])
        self._db[COL_SELFMOD].create_index([("timestamp", DESCENDING)])
        self._db[COL_PROFILE].create_index([("session_id", 1)])

    @property
    def ok(self) -> bool: return self._connected

    # Session / Chat
    def save_message(self, session_id: str, role: str, content: str):
        if not self.ok: return
        self._db[COL_SESSIONS].update_one(
            {"session_id": session_id},
            {
                "$push": {
                    "messages": {
                        "role": role,
                        "content": content,
                        "ts": datetime.datetime.utcnow(),
                    }
                },
                "$setOnInsert": {"session_id": session_id, "created": datetime.datetime.utcnow()},
            },
            upsert=True,
        )

    def get_messages(self, session_id: str, limit: int = 50) -> list:
        if not self.ok: return []
        doc = self._db[COL_SESSIONS].find_one({"session_id": session_id})
        if not doc: return []
        msgs = doc.get("messages", [])
        return msgs[-limit:]

    def list_sessions(self, limit: int = 20) -> list:
        if not self.ok: return []
        return list(
            self._db[COL_SESSIONS]
            .find({}, {"session_id": 1, "created": 1, "_id": 0})
            .sort("created", DESCENDING)
            .limit(limit)
        )
    # Command Logs
    def log_command(self, session_id: str, command: str, output: str, success: bool):
        if not self.ok: return
        self._db[COL_COMMANDS].insert_one({
            "session_id": session_id,
            "command":    command,
            "output":     output[:4096],
            "success":    success,
            "timestamp":  datetime.datetime.utcnow(),
        })

    def get_command_history(self, session_id: str, limit: int = 20) -> list:
        if not self.ok: return []
        return list(
            self._db[COL_COMMANDS]
            .find({"session_id": session_id}, {"_id": 0})
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )

    def get_nth_command(self, session_id: str, n: int) -> Optional[dict]:
        history = self.get_command_history(session_id, limit=n)
        if len(history) >= n: return history[n - 1]
        return None
    # Behavioral Profile
    def save_profile(self, session_id: str, profile: dict):
        if not self.ok: return
        self._db[COL_PROFILE].update_one(
            {"session_id": session_id},
            {"$set": {**profile, "updated": datetime.datetime.utcnow()}},
            upsert=True,
        )

    def get_profile(self, session_id: str) -> dict:
        if not self.ok: return {}
        doc = self._db[COL_PROFILE].find_one({"session_id": session_id}, {"_id": 0})
        return doc or {}

    def get_recent_interactions(self, session_id: str, n: int = 40) -> list:
        messages = self.get_messages(session_id, limit=n)
        commands = self.get_command_history(session_id, limit=n // 2)
        interactions = []
        for m in messages: interactions.append({
                "type":    "chat",
                "role":    m.get("role"),
                "content": m.get("content", "")[:300],
                "ts":      str(m.get("ts", "")),
            })
        for c in commands: interactions.append({
                "type":    "command",
                "cmd":     c.get("command", ""),
                "success": c.get("success"),
                "ts":      str(c.get("timestamp", "")),
            })
        interactions.sort(key=lambda x: x.get("ts", ""), reverse=True)
        return interactions[:n]

    # Self-Mod Ledger
    def ledger_append(self, entry: dict) -> str:
        if not self.ok: return ""
        entry["timestamp"] = datetime.datetime.utcnow()
        result = self._db[COL_SELFMOD].insert_one(entry)
        return str(result.inserted_id)

    def ledger_get_all(self, limit: int = 100) -> list:
        if not self.ok: return []
        raw = list(
            self._db[COL_SELFMOD]
            .find({})
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )
        for r in raw: r["_id"] = str(r["_id"])
        return raw

    def ledger_get_active(self) -> list:
        if not self.ok: return []
        raw = list(
            self._db[COL_SELFMOD]
            .find({"rolled_back": {"$ne": True}})
            .sort("timestamp", DESCENDING)
        )
        for r in raw: r["_id"] = str(r["_id"])
        return raw

    def ledger_mark_rolled_back(self, entry_id: str):
        from bson import ObjectId
        if not self.ok: return
        self._db[COL_SELFMOD].update_one(
            {"_id": ObjectId(entry_id)},
            {"$set": {"rolled_back": True, "rolled_back_at": datetime.datetime.utcnow()}}
        )