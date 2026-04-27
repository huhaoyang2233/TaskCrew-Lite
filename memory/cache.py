"""
OpenAI 格式的上下文缓存数据库
模拟数据库存储，使用内存缓存
"""
import time
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class Message:
    """OpenAI 标准格式的消息"""
    role: str
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"role": self.role, "content": self.content}
        if self.name:
            result["name"] = self.name
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result


@dataclass
class Session:
    """会话数据结构"""
    session_id: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    current_thoughts: List[Dict] = field(default_factory=list)
    latest_steps_message: List[Dict] = field(default_factory=list)
    user_message: List[Dict] = field(default_factory=list)
    reflector_message: List[Dict] = field(default_factory=list)


class MemoryCache:
    """内存缓存数据库"""
    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._max_sessions = 1000
        self._session_ttl = 3600
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        if session_id is None:
            session_id = f"session_{uuid.uuid4().hex[:12]}"
        self._cleanup_expired_sessions()
        self._sessions[session_id] = Session(session_id=session_id)
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session:
            session.updated_at = time.time()
        return session
    
    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def add_message(self, session_id: str, role: str, content: str, 
                    name: Optional[str] = None,
                    tool_calls: Optional[List[Dict]] = None,
                    tool_call_id: Optional[str] = None) -> Message:
        if session_id not in self._sessions:
            self.create_session(session_id)
        
        message = Message(role=role, content=content, name=name,
                         tool_calls=tool_calls, tool_call_id=tool_call_id)
        self._sessions[session_id].messages.append(message)
        self._sessions[session_id].updated_at = time.time()
        return message
    
    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[Dict]:
        session = self._sessions.get(session_id)
        if not session:
            return []
        messages = [msg.to_dict() for msg in session.messages]
        if limit:
            messages = messages[-limit:]
        return messages
    
    def update_context(self, session_id: str, key: str, value: Any) -> bool:
        if session_id not in self._sessions:
            return False
        session = self._sessions[session_id]
        if hasattr(session, key):
            setattr(session, key, value)
            session.updated_at = time.time()
            return True
        session.metadata[key] = value
        return True
    
    def get_context(self, session_id: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if not session:
            return {}
        return {
            "current_thoughts": session.current_thoughts,
            "latest_steps_message": session.latest_steps_message,
            "user_message": session.user_message,
            "reflector_message": session.reflector_message,
            "metadata": session.metadata
        }
    
    def clear_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def _cleanup_expired_sessions(self):
        current_time = time.time()
        expired = [sid for sid, s in self._sessions.items() 
                   if current_time - s.updated_at > self._session_ttl]
        for sid in expired:
            del self._sessions[sid]
        if len(self._sessions) >= self._max_sessions:
            sorted_sessions = sorted(self._sessions.items(), key=lambda x: x[1].updated_at)
            for sid, _ in sorted_sessions[:len(sorted_sessions) - self._max_sessions + 1]:
                del self._sessions[sid]
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_sessions": len(self._sessions),
            "max_sessions": self._max_sessions,
            "session_ttl": self._session_ttl
        }


memory_cache = MemoryCache()
