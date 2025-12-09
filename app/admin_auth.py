from hashlib import sha256
from fastapi.requests import Request
from sqladmin.authentication import AuthenticationBackend
from typing import Optional

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "TN5GR0UP"
SESSION_KEY = sha256((ADMIN_USERNAME + ADMIN_PASSWORD).encode('utf-8')).hexdigest()

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        """Handles the POST request when a user submits the login form."""
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            request.session.update({SESSION_KEY: "authenticated"}) 
            return True
        
        # Login failed
        return False

    async def logout(self, request: Request) -> bool:
        """Handles the logout action."""
        # Clear the session data
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> Optional[bool]:
        """Checks if the user is authenticated on every request to the admin panel."""
        token = request.session.get(SESSION_KEY)

        # If the session key is present, the user is authenticated
        if token == "authenticated":
            return True
        
        # User is not authenticated, redirect them to the login page
        return False
