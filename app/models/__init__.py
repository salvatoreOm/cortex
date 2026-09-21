"""Import every model here so Base.metadata knows about all tables.

Anything that imports app.db.base (the app itself, Alembic, tests) ends up
importing this package too, which is what makes autogenerate and
`Base.metadata.create_all` see every table below.
"""

from app.models.chat_session import ChatSession
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.message import Message
from app.models.user import User

__all__ = ["User", "Document", "Chunk", "ChatSession", "Message"]
