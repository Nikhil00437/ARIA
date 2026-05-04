"""
Session Manager - Handles multiple conversation tabs.
"""

import uuid
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ConversationTab:
    """Represents a single conversation tab."""
    id: str
    session_id: str
    title: str
    created_at: datetime
    last_activity: datetime
    message_count: int = 0
    is_active: bool = False
    history: List[Dict] = field(default_factory=list)
    
    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.last_activity, str):
            self.last_activity = datetime.fromisoformat(self.last_activity)


class SessionManager:
    """Manages multiple conversation tabs."""
    
    MAX_TABS = 10
    
    def __init__(self, db=None):
        self._db = db
        self._tabs: Dict[str, ConversationTab] = {}
        self._active_tab_id: Optional[str] = None
        self._tab_counter = 0
    
    def create_tab(self, session_id: Optional[str] = None, title: str = "New Chat") -> ConversationTab:
        """Create a new conversation tab."""
        if len(self._tabs) >= self.MAX_TABS:
            raise RuntimeError(f"Maximum number of tabs ({self.MAX_TABS}) reached")
        
        self._tab_counter += 1
        tab_id = f"tab_{self._tab_counter}_{uuid.uuid4().hex[:8]}"
        
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        now = datetime.now()
        tab = ConversationTab(
            id=tab_id,
            session_id=session_id,
            title=title,
            created_at=now,
            last_activity=now,
        )
        
        self._tabs[tab_id] = tab
        self.set_active_tab(tab_id)
        
        return tab
    
    def close_tab(self, tab_id: str) -> bool:
        """Close and remove a tab."""
        if tab_id not in self._tabs:
            return False
        
        # Don't close the last tab
        if len(self._tabs) == 1:
            return False
        
        del self._tabs[tab_id]
        
        # If we closed the active tab, switch to another
        if self._active_tab_id == tab_id:
            self._active_tab_id = next(iter(self._tabs.keys())) if self._tabs else None
            if self._active_tab_id:
                self._tabs[self._active_tab_id].is_active = True
        
        return True
    
    def set_active_tab(self, tab_id: str) -> bool:
        """Set the active tab."""
        if tab_id not in self._tabs:
            return False
        
        # Deactivate current active tab
        if self._active_tab_id and self._active_tab_id in self._tabs:
            self._tabs[self._active_tab_id].is_active = False
        
        # Activate new tab
        self._active_tab_id = tab_id
        self._tabs[tab_id].is_active = True
        self._tabs[tab_id].last_activity = datetime.now()
        
        return True
    
    def get_active_tab(self) -> Optional[ConversationTab]:
        """Get the currently active tab."""
        if self._active_tab_id:
            return self._tabs.get(self._active_tab_id)
        return None
    
    def get_tab(self, tab_id: str) -> Optional[ConversationTab]:
        """Get a specific tab."""
        return self._tabs.get(tab_id)
    
    def get_all_tabs(self) -> List[ConversationTab]:
        """Get all tabs in order."""
        return list(self._tabs.values())
    
    def update_tab_title(self, tab_id: str, title: str):
        """Update a tab's title."""
        if tab_id in self._tabs:
            self._tabs[tab_id].title = title
            self._tabs[tab_id].last_activity = datetime.now()
    
    def add_message_to_tab(self, tab_id: str, role: str, content: str):
        """Add a message to a tab's history."""
        if tab_id in self._tabs:
            tab = self._tabs[tab_id]
            tab.history.append({"role": role, "content": content})
            tab.message_count = len(tab.history)
            tab.last_activity = datetime.now()
            
            # Auto-update title from first user message
            if role == "user" and tab.title == "New Chat":
                title = content[:40] + ("..." if len(content) > 40 else "")
                tab.title = title
    
    def get_tab_history(self, tab_id: str) -> List[Dict]:
        """Get the message history for a tab."""
        if tab_id in self._tabs:
            return self._tabs[tab_id].history.copy()
        return []
    
    def set_tab_history(self, tab_id: str, history: List[Dict]):
        """Set the message history for a tab."""
        if tab_id in self._tabs:
            self._tabs[tab_id].history = history.copy()
            self._tabs[tab_id].message_count = len(history)
    
    def tab_count(self) -> int:
        """Get the number of open tabs."""
        return len(self._tabs)
    
    def can_create_tab(self) -> bool:
        """Check if a new tab can be created."""
        return len(self._tabs) < self.MAX_TABS
    
    def reorder_tabs(self, tab_ids: List[str]):
        """Reorder tabs (for drag-and-drop)."""
        new_tabs = {}
        for tab_id in tab_ids:
            if tab_id in self._tabs:
                new_tabs[tab_id] = self._tabs[tab_id]
        self._tabs = new_tabs


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager(db=None) -> SessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(db)
    return _session_manager