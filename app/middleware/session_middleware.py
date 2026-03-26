"""Session middleware that resolves or creates anonymous sessions on every request."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.session_manager import SessionManager

COOKIE_NAME = "session_id"
COOKIE_MAX_AGE = 2592000  # 30 days


class SessionMiddleware(BaseHTTPMiddleware):
    """Attach a session_id to every request via cookies.

    - If the request carries a valid session cookie, resolve it and touch the session.
    - If the cookie is missing or references a non-existent session, create a new one
      and set the cookie on the response.
    """

    def __init__(self, app, session_manager: SessionManager) -> None:  # noqa: ANN001
        super().__init__(app)
        self.session_manager = session_manager

    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        cookie_value = request.cookies.get(COOKIE_NAME)
        new_session = False

        if cookie_value:
            user = self.session_manager.resolve_session(cookie_value)
            if user is not None:
                # Valid existing session
                self.session_manager.touch_session(cookie_value)
                request.state.session_id = cookie_value
            else:
                # Cookie references a session that no longer exists — treat as new
                new_session = True
        else:
            new_session = True

        if new_session:
            session_id = self.session_manager.create_session()
            request.state.session_id = session_id

        response = await call_next(request)

        if new_session:
            response.set_cookie(
                key=COOKIE_NAME,
                value=request.state.session_id,
                httponly=True,
                samesite="lax",
                path="/",
                max_age=COOKIE_MAX_AGE,
            )

        return response
