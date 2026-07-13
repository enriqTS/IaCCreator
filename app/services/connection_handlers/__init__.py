"""Connection handlers package — one handler per connection type.

Each handler implements the ConnectionHandler protocol and is registered
in the CONNECTION_HANDLER_REGISTRY by (source_service, target_service) tuple.
"""

from app.services.connection_handlers.base import (
    BaseConnectionHandler,
    ConnectionHandler,
)

__all__ = ["ConnectionHandler", "BaseConnectionHandler"]
