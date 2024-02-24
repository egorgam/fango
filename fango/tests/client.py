from starlette.testclient import TestClient as StarletteClient

from fango.auth import create_access_token


class TestClient(StarletteClient):
    def force_authenticate(self, user):
        token = create_access_token(user)
        self.headers["Authorization"] = f"Bearer {token}"
