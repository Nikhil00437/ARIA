import json
import datetime
import threading
from typing import Optional, Any
from logger import get_logger
from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.errors import ConnectionFailure
from bson import ObjectId
from constants import (
    MONGO_URI, MONGO_DB, COL_SESSIONS, COL_MESSAGES,
    COL_COMMANDS, COL_SELFMOD, COL_PROFILE, COL_USAGE,
    COL_REACTIONS, COL_AGENT_TASKS, COL_AGENT_STEPS, COL_INSIGHTS,
)

logger = get_logger(__name__)

class _MemoryStore:
    """In-memory store used as fallback when MongoDB is unavailable."""

    def __init__(self) -> None:
        self.sessions: dict[str, dict] = {}
        self.messages: list[dict] = []
        self.commands: list[dict] = []
        self.selfmod: list[dict] = []
        self.reactions: list[dict] = {}
        self.app_meta: dict[str, str] = {}
        self._msg_seq: dict[str, int] = {}
        self._seq_lock = threading.Lock()
        self.agent_tasks: dict[str, dict] = {}
        self.agent_steps: list[dict] = []
        self._agent_step_seq: dict[str, int] = {}
        # Self-mod insight feed (Phase 9)
        self.insights: list[dict] = []
        self._insight_seq: int = 0
        self._insight_lock = threading.Lock()
        self.agent_tasks: dict[str, dict] = {}
        self.agent_steps: list[dict] = []
        self._agent_step_seq: dict[str, int] = {}

    def _next_seq(self, session_id: str) -> int:
        with self._seq_lock:
            seq = self._msg_seq.get(session_id, 0)
            self._msg_seq[session_id] = seq + 1
            return seq

    def save_message(self, session_id: str, role: str, content: str) -> None:
        now = datetime.datetime.utcnow()
        seq = self._next_seq(session_id)
        self.messages.append({
            "session_id": session_id, "role": role, "content": content,
            "ts": now, "seq": seq,
        })
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "session_id": session_id, "created": now,
                "message_count": 0, "last_activity": now, "title": "",
            }
        self.sessions[session_id]["last_activity"] = now
        self.sessions[session_id]["message_count"] = self.sessions[session_id].get("message_count", 0) + 1

    def get_messages(self, session_id: str, limit: int = 50, skip: int = 0) -> list:
        msgs = [m for m in self.messages if m.get("session_id") == session_id]
        msgs.sort(key=lambda x: x.get("seq", 0))
        return msgs[skip:skip + limit]

    def count_messages(self, session_id: str) -> int:
        return sum(1 for m in self.messages if m.get("session_id") == session_id)

    def list_sessions(self, limit: int = 100) -> list:
        sessions = sorted(
            self.sessions.values(),
            key=lambda x: x.get("last_activity", datetime.datetime.min),
            reverse=True,
        )
        return [
            {
                "session_id": s.get("session_id"),
                "created": s.get("created"),
                "title": s.get("title", ""),
                "message_count": s.get("message_count", 0),
                "last_activity": s.get("last_activity"),
            }
            for s in sessions[:limit]
        ]

    def save_session_title(self, session_id: str, title: str) -> None:
        if session_id not in self.sessions:
            self.sessions[session_id] = {"session_id": session_id, "created": datetime.datetime.utcnow()}
        self.sessions[session_id]["title"] = title
        self.sessions[session_id]["last_activity"] = datetime.datetime.utcnow()

    def generate_session_title(self, session_id: str) -> str:
        if session_id in self.sessions and self.sessions[session_id].get("title"):
            return self.sessions[session_id]["title"]
        msgs = self.get_messages(session_id, limit=1)
        for m in msgs:
            if m.get("role") == "user":
                content = m.get("content", "").strip()
                return content[:57] + "..." if len(content) > 60 else content
        return "New Session"

    def delete_session(self, session_id: str) -> bool:
        self.messages = [m for m in self.messages if m.get("session_id") != session_id]
        self.commands = [c for c in self.commands if c.get("session_id") != session_id]
        self.reactions = [r for r in self.reactions if r.get("session_id") != session_id]
        existed = session_id in self.sessions
        self.sessions.pop(session_id, None)
        return existed

    def log_command(self, session_id: str, command: str, output: str, success: bool) -> None:
        self.commands.append({
            "session_id": session_id, "command": command,
            "output": output[:4096], "success": success,
            "timestamp": datetime.datetime.utcnow(),
        })

    def get_command_history(self, session_id: str, limit: int = 20) -> list:
        cmds = [c for c in self.commands if c.get("session_id") == session_id]
        cmds.sort(key=lambda x: x.get("timestamp", datetime.datetime.min), reverse=True)
        return cmds[:limit]

    def save_reaction(self, session_id: str, message_seq: int, reaction: str) -> bool:
        for r in self.reactions:
            if (r["session_id"] == session_id and r["message_seq"] == message_seq
                    and r["reaction"] == reaction):
                self.reactions.remove(r)
                return False
        self.reactions.append({
            "session_id": session_id, "message_seq": message_seq,
            "reaction": reaction, "ts": datetime.datetime.utcnow(),
        })
        return True

    def get_reactions(self, session_id: str, message_seq: int) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self.reactions:
            if r["session_id"] == session_id and r["message_seq"] == message_seq:
                counts[r["reaction"]] = counts.get(r["reaction"], 0) + 1
        return counts

    def save_profile(self, session_id: str, profile: dict) -> None:
        pass  # Profile persistence is non-critical; skip in memory fallback

    def track_usage(self, session_id: str, usage_type: str, **kwargs: Any) -> None:
        pass  # Usage analytics are non-critical in fallback mode

    def save_last_session(self, session_id: str) -> None:
        self.app_meta["last_session_id"] = session_id

    def get_last_session(self) -> Optional[str]:
        return self.app_meta.get("last_session_id")

    # ── Agent tasks (Phase 2) ───────────────────────────────────────────────

    def _next_agent_step_seq(self, task_id: str) -> int:
        seq = self._agent_step_seq.get(task_id, 0)
        self._agent_step_seq[task_id] = seq + 1
        return seq

    def create_agent_task(self, task_id: str, session_id: str, goal: str,
                           mode: str, parent_task_id: Optional[str] = None) -> dict:
        now = datetime.datetime.utcnow()
        doc = {
            "task_id": task_id, "session_id": session_id, "goal": goal,
            "mode": mode, "status": "running", "plan": "", "summary": "",
            "parent_task_id": parent_task_id,
            "created": now, "updated": now, "total_tokens": 0,
        }
        self.agent_tasks[task_id] = doc
        return doc

    def update_agent_task(self, task_id: str, **kwargs) -> None:
        doc = self.agent_tasks.get(task_id)
        if not doc:
            return
        for k, v in kwargs.items():
            doc[k] = v
        doc["updated"] = datetime.datetime.utcnow()

    def get_agent_task(self, task_id: str) -> Optional[dict]:
        return self.agent_tasks.get(task_id)

    def list_agent_tasks(self, session_id: Optional[str] = None, limit: int = 50) -> list:
        tasks = list(self.agent_tasks.values())
        if session_id:
            tasks = [t for t in tasks if t.get("session_id") == session_id]
        tasks.sort(key=lambda t: t.get("created", datetime.datetime.min), reverse=True)
        return tasks[:limit]

    def cancel_agent_task(self, task_id: str) -> bool:
        doc = self.agent_tasks.get(task_id)
        if not doc or doc.get("status") not in ("running", "queued"):
            return False
        doc["status"] = "cancelled"
        doc["updated"] = datetime.datetime.utcnow()
        return True

    def save_agent_step(self, step: dict) -> None:
        task_id = step.get("task_id", "")
        seq = self._next_agent_step_seq(task_id)
        step["seq"] = seq
        step["ts"] = step.get("ts", datetime.datetime.utcnow())
        self.agent_steps.append(step)

    def get_agent_steps(self, task_id: str, limit: int = 200) -> list:
        steps = [s for s in self.agent_steps if s.get("task_id") == task_id]
        steps.sort(key=lambda s: s.get("seq", 0))
        return steps[:limit]

    # ── Self-mod insights (Phase 9) ─────────────────────────────────────────

    def save_insight(self, insight: dict) -> str:
        with self._insight_lock:
            self._insight_seq += 1
            insight_id = f"ins_{self._insight_seq}"
            insight["id"] = insight_id
            insight.setdefault("ts", datetime.datetime.utcnow())
            insight.setdefault("status", "noticed")
            self.insights.append(insight)
            # FIFO cap at 500 records
            if len(self.insights) > 500:
                self.insights = self.insights[-500:]
        return insight_id

    def get_insights(self, limit: int = 200, status: Optional[str] = None) -> list:
        items = self.insights
        if status:
            items = [i for i in items if i.get("status") == status]
        items.sort(key=lambda i: i.get("ts", datetime.datetime.min), reverse=True)
        return items[:limit]

    def update_insight_status(self, insight_id: str, status: str, proposal_id: Optional[str] = None) -> None:
        with self._insight_lock:
            for i in self.insights:
                if i.get("id") == insight_id:
                    i["status"] = status
                    if proposal_id:
                        i["proposal_id"] = proposal_id
                    break

    def export_session_markdown(self, session_id: str) -> str:
        title = self.generate_session_title(session_id)
        msgs = self.get_messages(session_id, limit=10000)
        md = f"# {title}\n\n_Session ID: {session_id}_\n\n---\n\n"
        for msg in msgs:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prefix = "**You:**" if role == "user" else "**ARIA:**"
            md += f"{prefix}\n{content}\n\n---\n\n"
        return md

    def export_session_json(self, session_id: str) -> str:
        session = self.sessions.get(session_id)
        msgs = self.get_messages(session_id, limit=10000)
        cmds = self.get_command_history(session_id, limit=1000)
        return json.dumps({
            "session": session, "messages": msgs, "commands": cmds,
            "exported_at": datetime.datetime.utcnow().isoformat(),
        }, indent=2, default=str)


class Database:
    """Data access layer with automatic in-memory fallback when MongoDB is offline."""

    def __init__(self):
        self._client: Optional[MongoClient] = None
        self._db = None
        self._connected = False
        self._mem = _MemoryStore()

    def connect(self) -> bool:
        try:
            self._client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
            self._client.admin.command("ping")
            self._db = self._client[MONGO_DB]
            self._ensure_indexes()
            self._connected = True
            return True
        except ConnectionFailure as e:
            logger.warning("MongoDB connection failed — using in-memory store: %s", e)
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
        # Agent harness (Phase 2)
        self._db[COL_AGENT_TASKS].create_index([("task_id", 1)], unique=True)
        self._db[COL_AGENT_TASKS].create_index([("session_id", 1), ("created", DESCENDING)])
        self._db[COL_AGENT_STEPS].create_index([("task_id", 1), ("seq", ASCENDING)])
        self._db[COL_AGENT_STEPS].create_index([("task_id", 1)])
        # Phase 9: self-mod insights
        self._db[COL_INSIGHTS].create_index([("ts", DESCENDING)])
        self._db[COL_INSIGHTS].create_index([("status", 1)])

    @property
    def ok(self) -> bool: return self._connected

    # ── Session / Chat ──────────────────────────────────────────────

    def save_message(self, session_id: str, role: str, content: str):
        if self._connected:
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
        else:
            self._mem.save_message(session_id, role, content)

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
        if not self._connected:
            return self._mem.get_messages(session_id, limit, skip)
        return list(
            self._db[COL_MESSAGES]
            .find({"session_id": session_id}, {"_id": 0})
            .sort("seq", DESCENDING)
            .skip(skip)
            .limit(limit)
        )[::-1]

    def count_messages(self, session_id: str) -> int:
        if not self._connected:
            return self._mem.count_messages(session_id)
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
        if not self._connected:
            return self._mem.list_sessions(limit)
        return list(
            self._db[COL_SESSIONS]
            .find({}, {"_id": 0, "session_id": 1, "created": 1, "title": 1,
                       "message_count": 1, "last_activity": 1})
            .sort("last_activity", DESCENDING)
            .limit(limit)
        )

    def save_session_title(self, session_id: str, title: str):
        if self._connected:
            self._db[COL_SESSIONS].update_one(
                {"session_id": session_id},
                {"$set": {"title": title}},
            )
        else:
            self._mem.save_session_title(session_id, title)

    def generate_session_title(self, session_id: str) -> str:
        if not self._connected:
            return self._mem.generate_session_title(session_id)
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
        if not self._connected:
            return self._mem.delete_session(session_id)
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
        if self._connected:
            self._db["app_meta"].update_one(
                {"key": "last_session_id"},
                {"$set": {"value": session_id, "updated": datetime.datetime.utcnow()}},
                upsert=True,
            )
        else:
            self._mem.save_last_session(session_id)

    def get_last_session(self) -> Optional[str]:
        if not self._connected:
            return self._mem.get_last_session()
        doc = self._db["app_meta"].find_one({"key": "last_session_id"})
        if doc:
            return doc.get("value")
        return None

    # ── Usage Analytics ─────────────────────────────────────────────

    def track_usage(self, session_id: str, usage_type: str, **kwargs: Any) -> None:
        if self._connected:
            entry: dict[str, Any] = {
                "session_id": session_id,
                "type":       usage_type,
                "date":       datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
                "ts":         datetime.datetime.utcnow(),
            }
            entry.update(kwargs)
            self._db[COL_USAGE].insert_one(entry)
        # Usage analytics are non-critical in fallback mode — skip

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
        if self._connected:
            self._db[COL_COMMANDS].insert_one({
                "session_id": session_id,
                "command":    command,
                "output":     output[:4096],
                "success":    success,
                "timestamp":  datetime.datetime.utcnow(),
            })
        else:
            self._mem.log_command(session_id, command, output, success)

    def get_command_history(self, session_id: str, limit: int = 20) -> list:
        if not self._connected:
            return self._mem.get_command_history(session_id, limit)
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
        if self._connected:
            self._db[COL_PROFILE].update_one(
                {"session_id": session_id},
                {"$set": {**profile, "updated": datetime.datetime.utcnow()}},
                upsert=True,
            )
        # Profile is non-critical in fallback mode — skip

    def get_profile(self, session_id: str) -> dict:
        if not self.ok: return {}
        doc = self._db[COL_PROFILE].find_one({"session_id": session_id}, {"_id": 0})
        return doc or {}

    def get_recent_interactions(self, session_id: str, n: int = 40) -> list:
        if not self._connected:
            messages = self._mem.get_messages(session_id, limit=n)
            commands = self._mem.get_command_history(session_id, limit=n // 2)
        else:
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

    # ── Agent tasks (Phase 2) ───────────────────────────────────────────────

    def create_agent_task(self, task_id: str, session_id: str, goal: str,
                          mode: str, parent_task_id: Optional[str] = None) -> dict:
        now = datetime.datetime.utcnow()
        doc = {
            "task_id": task_id, "session_id": session_id, "goal": goal,
            "mode": mode, "status": "running", "plan": "", "summary": "",
            "parent_task_id": parent_task_id,
            "created": now, "updated": now, "total_tokens": 0,
        }
        if self._connected:
            self._db[COL_AGENT_TASKS].insert_one(doc)
        else:
            self._mem.create_agent_task(task_id, session_id, goal, mode, parent_task_id)
        return doc

    def update_agent_task(self, task_id: str, **kwargs) -> None:
        if self._connected and kwargs:
            self._db[COL_AGENT_TASKS].update_one(
                {"task_id": task_id},
                {"$set": {**kwargs, "updated": datetime.datetime.utcnow()}},
            )
        else:
            self._mem.update_agent_task(task_id, **kwargs)

    def get_agent_task(self, task_id: str) -> Optional[dict]:
        if self._connected:
            doc = self._db[COL_AGENT_TASKS].find_one(
                {"task_id": task_id}, {"_id": 0}
            )
            return doc
        return self._mem.get_agent_task(task_id)

    def list_agent_tasks(self, session_id: Optional[str] = None, limit: int = 50) -> list:
        if self._connected:
            criteria = {}
            if session_id:
                criteria["session_id"] = session_id
            return list(
                self._db[COL_AGENT_TASKS]
                .find(criteria, {"_id": 0})
                .sort("created", DESCENDING)
                .limit(limit)
            )
        return self._mem.list_agent_tasks(session_id, limit)

    def cancel_agent_task(self, task_id: str) -> bool:
        if self._connected:
            result = self._db[COL_AGENT_TASKS].update_one(
                {"task_id": task_id, "status": {"$in": ["running", "queued"]}},
                {"$set": {"status": "cancelled", "updated": datetime.datetime.utcnow()}},
            )
            return result.modified_count > 0
        return self._mem.cancel_agent_task(task_id)

    def save_agent_step(self, step: dict) -> None:
        if self._connected:
            step.setdefault("ts", datetime.datetime.utcnow())
            self._db[COL_AGENT_STEPS].insert_one(step)
        else:
            self._mem.save_agent_step(step)

    def get_agent_steps(self, task_id: str, limit: int = 200) -> list:
        if self._connected:
            return list(
                self._db[COL_AGENT_STEPS]
                .find({"task_id": task_id}, {"_id": 0})
                .sort("seq", ASCENDING)
                .limit(limit)
            )
        return self._mem.get_agent_steps(task_id, limit)

    # ── Self-mod insights (Phase 9) ─────────────────────────────────────────

    def save_insight(self, insight: dict) -> str:
        if self._connected:
            insight.setdefault("ts", datetime.datetime.utcnow())
            insight.setdefault("status", "noticed")
            res = self._db[COL_INSIGHTS].insert_one(dict(insight))
            insight["_id"] = res.inserted_id
            # No pre-allocated id in Mongo path — return a generated one.
            return insight.get("id") or str(res.inserted_id)
        return self._mem.save_insight(insight)

    def get_insights(self, limit: int = 200, status: Optional[str] = None) -> list:
        if self._connected:
            criteria = {}
            if status:
                criteria["status"] = status
            return list(
                self._db[COL_INSIGHTS]
                .find(criteria, {"_id": 0})
                .sort("ts", DESCENDING)
                .limit(limit)
            )
        return self._mem.get_insights(limit, status)

    def update_insight_status(self, insight_id: str, status: str, proposal_id: Optional[str] = None) -> None:
        if self._connected:
            update = {"$set": {"status": status}}
            if proposal_id:
                update["$set"]["proposal_id"] = proposal_id
            self._db[COL_INSIGHTS].update_one({"id": insight_id}, update)
        else:
            self._mem.update_insight_status(insight_id, status, proposal_id)

    # ── Internal ────────────────────────────────────────────────────

    def _next_seq(self, session_id: str) -> int:
        """Atomically allocate the next message seq for a session.

        Previously this did a find-max-then-insert, which races when two
        threads (e.g. concurrent agent loops) write to the same session.
        Now both backends resolve the seq through a single atomic step:
        an atomic `find_one_and_update` on a `counters` document (Mongo)
        or the locked in-memory counter (`_MemoryStore._next_seq`).
        """
        if self._connected:
            doc = self._db["counters"].find_one_and_update(
                {"_id": f"msg_seq:{session_id}"},
                {"$inc": {"seq": 1}},
                upsert=True,
                return_document=True,  # pymongo ReturnDocument.AFTER == True
            )
            return int(doc.get("seq", 1))
        return self._mem._next_seq(session_id)

    # ── Reactions ────────────────────────────────────────────────

    def save_reaction(self, session_id: str, message_seq: int, reaction: str) -> bool:
        """Save a reaction to a specific message. Returns True if new, False if toggled off."""
        if not self._connected:
            return self._mem.save_reaction(session_id, message_seq, reaction)
        existing = self._db[COL_REACTIONS].find_one({
            "session_id": session_id,
            "message_seq": message_seq,
            "reaction": reaction,
        })
        if existing:
            self._db[COL_REACTIONS].delete_one({"_id": existing["_id"]})
            return False
        self._db[COL_REACTIONS].insert_one({
            "session_id": session_id,
            "message_seq": message_seq,
            "reaction": reaction,
            "ts": datetime.datetime.utcnow(),
        })
        return True

    def get_reactions(self, session_id: str, message_seq: int) -> dict[str, int]:
        """Get reaction counts for a message, keyed by reaction symbol."""
        if not self._connected:
            return self._mem.get_reactions(session_id, message_seq)
        pipeline = [
            {"$match": {"session_id": session_id, "message_seq": message_seq}},
            {"$group": {"_id": "$reaction", "count": {"$sum": 1}}},
        ]
        results = self._db[COL_REACTIONS].aggregate(pipeline)
        return {r["_id"]: r["count"] for r in results}

    def count_all_reactions(self, session_id: str) -> list[dict]:
        """Get all reactions across all messages in a session."""
        if not self.ok:
            return []
        pipeline = [
            {"$match": {"session_id": session_id}},
            {"$group": {
                "_id": {"message_seq": "$message_seq", "reaction": "$reaction"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"_id.message_seq": 1}},
        ]
        return list(self._db[COL_REACTIONS].aggregate(pipeline))

    # ── Export ───────────────────────────────────────────────────

    def export_session_json(self, session_id: str) -> str:
        """Export a session as JSON."""
        if not self._connected:
            return self._mem.export_session_json(session_id)
        session = self._db[COL_SESSIONS].find_one({"session_id": session_id})
        messages = self.get_messages(session_id, limit=10000)
        commands = self.get_command_history(session_id, limit=1000)

        return json.dumps({
            "session": session,
            "messages": messages,
            "commands": commands,
            "exported_at": datetime.datetime.utcnow().isoformat(),
        }, indent=2, default=str)

    def export_session_markdown(self, session_id: str) -> str:
        """Export a session as Markdown."""
        if not self._connected:
            return self._mem.export_session_markdown(session_id)
        session = self._db[COL_SESSIONS].find_one({"session_id": session_id})
        title = session.get("title", "Untitled Session") if session else "Untitled"
        messages = self.get_messages(session_id, limit=10000)

        md = f"# {title}\n\n_Session ID: {session_id}_\n\n"
        if session and session.get("created"):
            md += f"Created: {session['created']}\n\n"
        md += "---\n\n"

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prefix = "**You:**" if role == "user" else "**ARIA:**"
            md += f"{prefix}\n{content}\n\n---\n\n"
        return md
