import datetime, uuid
from typing import Optional
from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from bson import ObjectId
from constants import (
    MONGO_URI, MONGO_DB, COL_SESSIONS, COL_MESSAGES,
    COL_COMMANDS, COL_SELFMOD, COL_PROFILE, COL_USAGE,
)

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
        # Drop conflicting non-unique indexes before creating unique ones
        for coll_name, idx_name in [(COL_SESSIONS, "session_id_1"), (COL_PROFILE, "session_id_1")]:
            try:
                coll = self._db[coll_name]
                info = coll.index_information()
                if idx_name in info and not info[idx_name].get("unique", False):
                    coll.drop_index(idx_name)
            except Exception:
                pass

        self._db[COL_SESSIONS].create_index([("session_id", 1)], unique=True)
        self._db[COL_SESSIONS].create_index([("last_activity", DESCENDING)])
        self._db[COL_SESSIONS].create_index([("title", "text")])
        self._db[COL_MESSAGES].create_index([("session_id", 1), ("seq", ASCENDING)])
        self._db[COL_MESSAGES].create_index([("session_id", 1), ("role", 1)])
        self._db[COL_MESSAGES].create_index([("ts", DESCENDING)])
        self._db[COL_MESSAGES].create_index([("content", "text")])
        self._db[COL_COMMANDS].create_index([("session_id", 1), ("timestamp", DESCENDING)])
        self._db[COL_COMMANDS].create_index([("command", "text")])
        self._db[COL_SELFMOD].create_index([("timestamp", DESCENDING)])
        self._db[COL_PROFILE].create_index([("session_id", 1)], unique=True)
        self._db[COL_USAGE].create_index([("date", 1)])
        self._db[COL_USAGE].create_index([("session_id", 1)])
        self._db["app_meta"].create_index([("key", 1)], unique=True)

    @property
    def ok(self) -> bool: return self._connected

    # ── Session / Chat ──────────────────────────────────────────────

    def save_message(self, session_id: str, role: str, content: str):
        if not self.ok: return
        now = datetime.datetime.utcnow()
        self._db[COL_MESSAGES].insert_one({
            "session_id": session_id,
            "role":       role,
            "content":    content,
            "ts":         now,
            "seq":        self._next_seq(session_id),
        })
        self._db[COL_SESSIONS].update_one(
            {"session_id": session_id},
            {
                "$set":  {"last_activity": now},
                "$inc":  {"message_count": 1},
                "$setOnInsert": {"session_id": session_id, "created": now},
            },
            upsert=True,
        )

    def save_messages_batch(self, session_id: str, messages: list[dict]):
        if not self.ok or not messages: return
        now = datetime.datetime.utcnow()
        base_seq = self._next_seq(session_id)
        docs = []
        for i, m in enumerate(messages):
            docs.append({
                "session_id": session_id,
                "role":       m.get("role", "user"),
                "content":    m.get("content", ""),
                "ts":         m.get("ts", now),
                "seq":        base_seq + i,
            })
        if docs:
            self._db[COL_MESSAGES].insert_many(docs)
        self._db[COL_SESSIONS].update_one(
            {"session_id": session_id},
            {
                "$set":  {"last_activity": now},
                "$inc":  {"message_count": len(docs)},
                "$setOnInsert": {"session_id": session_id, "created": now},
            },
            upsert=True,
        )

    def get_messages(self, session_id: str, limit: int = 50, skip: int = 0) -> list:
        if not self.ok: return []
        return list(
            self._db[COL_MESSAGES]
            .find({"session_id": session_id}, {"_id": 0})
            .sort("seq", DESCENDING)
            .skip(skip)
            .limit(limit)
        )[::-1]

    def count_messages(self, session_id: str) -> int:
        if not self.ok: return 0
        return self._db[COL_MESSAGES].count_documents({"session_id": session_id})

    def search_messages(self, query: str, session_id: Optional[str] = None, limit: int = 20) -> list:
        if not self.ok: return []
        criteria = {"$text": {"$search": query}}
        if session_id:
            criteria["session_id"] = session_id
        return list(
            self._db[COL_MESSAGES]
            .find(criteria, {"_id": 0, "session_id": 1, "role": 1, "content": 1, "ts": 1})
            .sort("ts", DESCENDING)
            .limit(limit)
        )

    def list_sessions(self, limit: int = 100) -> list:
        if not self.ok: return []
        return list(
            self._db[COL_SESSIONS]
            .find({}, {"_id": 0, "session_id": 1, "created": 1, "title": 1,
                       "message_count": 1, "last_activity": 1})
            .sort("last_activity", DESCENDING)
            .limit(limit)
        )

    def save_session_title(self, session_id: str, title: str):
        if not self.ok: return
        self._db[COL_SESSIONS].update_one(
            {"session_id": session_id},
            {"$set": {"title": title}},
        )

    def generate_session_title(self, session_id: str) -> str:
        if not self.ok: return ""
        doc = self._db[COL_SESSIONS].find_one(
            {"session_id": session_id}, {"title": 1}
        )
        if doc and doc.get("title"):
            return doc["title"]
        first = self._db[COL_MESSAGES].find_one(
            {"session_id": session_id, "role": "user"},
            {"content": 1},
            sort=[("seq", ASCENDING)],
        )
        if first:
            content = first.get("content", "").strip()
            if len(content) > 60:
                return content[:57] + "..."
            return content
        return "New Session"

    def get_session_stats(self, session_id: str) -> dict:
        if not self.ok: return {}
        session = self._db[COL_SESSIONS].find_one(
            {"session_id": session_id},
            {"_id": 0, "session_id": 1, "created": 1, "title": 1,
             "message_count": 1, "last_activity": 1},
        )
        if not session: return {}
        msg_count = self._db[COL_MESSAGES].count_documents({"session_id": session_id})
        cmd_count = self._db[COL_COMMANDS].count_documents({"session_id": session_id})
        intent_counts = list(
            self._db[COL_USAGE].aggregate([
                {"$match": {"session_id": session_id, "type": "intent"}},
                {"$group": {"_id": "$intent", "count": {"$sum": 1}}},
                {"$sort": {"count": DESCENDING}},
            ])
        )
        session["total_messages"] = msg_count
        session["total_commands"] = cmd_count
        session["intent_breakdown"] = {i["_id"]: i["count"] for i in intent_counts}
        created = session.get("created")
        last = session.get("last_activity")
        if created and last:
            delta = last - created
            session["duration_minutes"] = round(delta.total_seconds() / 60, 1)
        return session

    def delete_session(self, session_id: str) -> bool:
        if not self.ok: return False
        self._db[COL_MESSAGES].delete_many({"session_id": session_id})
        self._db[COL_COMMANDS].delete_many({"session_id": session_id})
        self._db[COL_PROFILE].delete_one({"session_id": session_id})
        self._db[COL_USAGE].delete_many({"session_id": session_id})
        result = self._db[COL_SESSIONS].delete_one({"session_id": session_id})
        return result.deleted_count > 0

    def delete_old_sessions(self, days: int = 90) -> int:
        if not self.ok: return 0
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        old_sessions = list(
            self._db[COL_SESSIONS]
            .find({"last_activity": {"$lt": cutoff}}, {"session_id": 1})
        )
        count = 0
        for s in old_sessions:
            sid = s["session_id"]
            self._db[COL_MESSAGES].delete_many({"session_id": sid})
            self._db[COL_COMMANDS].delete_many({"session_id": sid})
            self._db[COL_PROFILE].delete_one({"session_id": sid})
            self._db[COL_USAGE].delete_many({"session_id": sid})
            count += 1
        if old_sessions:
            self._db[COL_SESSIONS].delete_many({
                "session_id": {"$in": [s["session_id"] for s in old_sessions]}
            })
        return count

    def save_last_session(self, session_id: str):
        if not self.ok: return
        self._db["app_meta"].update_one(
            {"key": "last_session_id"},
            {"$set": {"value": session_id, "updated": datetime.datetime.utcnow()}},
            upsert=True,
        )

    def get_last_session(self) -> Optional[str]:
        if not self.ok: return None
        doc = self._db["app_meta"].find_one({"key": "last_session_id"})
        if doc:
            return doc.get("value")
        return None

    # ── Usage Analytics ─────────────────────────────────────────────

    def track_usage(self, session_id: str, usage_type: str, **kwargs):
        if not self.ok: return
        entry = {
            "session_id": session_id,
            "type":       usage_type,
            "date":       datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
            "ts":         datetime.datetime.utcnow(),
        }
        entry.update(kwargs)
        self._db[COL_USAGE].insert_one(entry)

    def get_usage_stats(self, days: int = 30) -> dict:
        if not self.ok: return {}
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        pipeline = [
            {"$match": {"date": {"$gte": cutoff}}},
            {"$group": {
                "_id": "$type",
                "count": {"$sum": 1},
                "sessions": {"$addToSet": "$session_id"},
            }},
        ]
        results = list(self._db[COL_USAGE].aggregate(pipeline))
        stats = {}
        for r in results:
            stats[r["_id"]] = {
                "count": r["count"],
                "unique_sessions": len(r["sessions"]),
            }
        intent_pipeline = [
            {"$match": {"date": {"$gte": cutoff}, "type": "intent"}},
            {"$group": {"_id": "$intent", "count": {"$sum": 1}}},
            {"$sort": {"count": DESCENDING}},
        ]
        stats["intents"] = {i["_id"]: i["count"] for i in self._db[COL_USAGE].aggregate(intent_pipeline)}
        stats["period_days"] = days
        return stats

    # ── Command Logs ────────────────────────────────────────────────

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

    def search_commands(self, query: str, session_id: Optional[str] = None, limit: int = 20) -> list:
        if not self.ok: return []
        criteria = {"$text": {"$search": query}}
        if session_id:
            criteria["session_id"] = session_id
        return list(
            self._db[COL_COMMANDS]
            .find(criteria, {"_id": 0, "session_id": 1, "command": 1, "success": 1, "timestamp": 1})
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )

    # ── Behavioral Profile ──────────────────────────────────────────

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
        if not self.ok: return []
        messages = self.get_messages(session_id, limit=n)
        commands = self.get_command_history(session_id, limit=n // 2)
        interactions = []
        for m in messages:
            interactions.append({
                "type":    "chat",
                "role":    m.get("role"),
                "content": m.get("content", "")[:300],
                "ts":      m.get("ts", datetime.datetime.min),
            })
        for c in commands:
            interactions.append({
                "type":    "command",
                "cmd":     c.get("command", ""),
                "success": c.get("success"),
                "ts":      c.get("timestamp", datetime.datetime.min),
            })
        interactions.sort(key=lambda x: x.get("ts", datetime.datetime.min), reverse=True)
        return interactions[:n]

    # ── Self-Mod Ledger ─────────────────────────────────────────────

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
        if not self.ok: return
        self._db[COL_SELFMOD].update_one(
            {"_id": ObjectId(entry_id)},
            {"$set": {"rolled_back": True, "rolled_back_at": datetime.datetime.utcnow()}}
        )

    # ── Internal ────────────────────────────────────────────────────

    def _next_seq(self, session_id: str) -> int:
        result = self._db[COL_MESSAGES].find_one(
            {"session_id": session_id},
            {"seq": 1},
            sort=[("seq", DESCENDING)],
        )
        return (result.get("seq", 0) + 1) if result else 0

    # ── Export ───────────────────────────────────────────────────

    def export_session_json(self, session_id: str) -> str:
        """Export a session as JSON."""
        import json
        session = self._db[COL_SESSIONS].find_one({"session_id": session_id})
        messages = self.get_messages(session_id, limit=10000)
        commands = self.get_command_history(session_id, limit=1000)
        
        export_data = {
            "session": session,
            "messages": messages,
            "commands": commands,
            "exported_at": datetime.datetime.utcnow().isoformat(),
        }
        
        return json.dumps(export_data, indent=2, default=str)

    def export_session_markdown(self, session_id: str) -> str:
        """Export a session as Markdown."""
        session = self._db[COL_SESSIONS].find_one({"session_id": session_id})
        title = session.get("title", "Untitled Session") if session else "Untitled"
        messages = self.get_messages(session_id, limit=10000)
        
        md = f"# {title}\n\n"
        md += f"_Session ID: {session_id}_\n\n"
        
        if session and session.get("created"):
            md += f"Created: {session['created']}\n\n"
        
        md += "---\n\n"
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                md += f"**You:**\n{content}\n\n"
            else:
                md += f"**ARIA:**\n{content}\n\n"
            md += "---\n\n"
        
        return md
