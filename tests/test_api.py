"""Integration tests for the Flask API (app.py).

These tests use Flask's built-in test client and do NOT need a real database.
A fake psycopg2 module is injected so no DB connection is needed.

Run (after pip install -r requirements.txt):
    python -m unittest tests.test_api -v
"""
import json
import sys
import os
import unittest
from unittest.mock import MagicMock

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Dependency check: skip entire module if Flask/bcrypt missing ──────────────
try:
    import flask   # noqa: F401
    import bcrypt  # noqa: F401
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

_SKIP_MSG = "Flask/bcrypt not installed — run: pip install -r requirements.txt"


def _inject_fake_psycopg2():
    """Inject a mock psycopg2 so app.py can be imported without a real DB."""
    if "psycopg2" not in sys.modules:
        fake = MagicMock()
        fake.connect.return_value = MagicMock()
        fake.extras = MagicMock()
        fake.extras.RealDictCursor = dict
        fake.errors = MagicMock()
        fake.errors.UniqueViolation = Exception
        sys.modules["psycopg2"]        = fake
        sys.modules["psycopg2.extras"] = fake.extras
        sys.modules["psycopg2.errors"] = fake.errors


def _make_app():
    """Import the Flask app with all external dependencies stubbed out."""
    _inject_fake_psycopg2()
    import app as flask_app
    flask_app.app.config["TESTING"]          = True
    flask_app.app.config["SECRET_KEY"]       = "test"
    flask_app.app.config["WTF_CSRF_ENABLED"] = False
    return flask_app.app


@unittest.skipUnless(HAS_FLASK, _SKIP_MSG)
class TestAuthRoutes(unittest.TestCase):

    def setUp(self):
        self.app    = _make_app()
        self.client = self.app.test_client()

    def test_root_redirects_to_login(self):
        rv = self.client.get("/", follow_redirects=False)
        self.assertIn(rv.status_code, (301, 302))
        self.assertIn("login", rv.headers.get("Location", ""))

    def test_login_page_returns_200(self):
        rv = self.client.get("/login")
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b"Sign in", rv.data)

    def test_login_bad_credentials(self):
        with self.app.app_context():
            with unittest.mock.patch("app.query", return_value=None):
                rv = self.client.post("/login",
                                      data={"email": "x@y.com", "password": "bad"},
                                      follow_redirects=True)
        self.assertIn(b"Invalid email or password", rv.data)

    def test_logout_redirects_to_login(self):
        rv = self.client.get("/logout", follow_redirects=False)
        self.assertIn(rv.status_code, (301, 302))

    def test_protected_route_redirects_unauthenticated(self):
        rv = self.client.get("/dashboard", follow_redirects=False)
        self.assertIn(rv.status_code, (301, 302))

    def test_register_page_returns_200(self):
        rv = self.client.get("/register")
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b"Create Account", rv.data)

    def test_register_password_mismatch(self):
        rv = self.client.post("/register",
                              data={"name": "Test User", "email": "test@test.com", "role": "student",
                                    "password": "password123", "confirm_password": "differentpassword"},
                              follow_redirects=True)
        self.assertIn(b"Passwords do not match", rv.data)

    def test_register_short_password(self):
        rv = self.client.post("/register",
                              data={"name": "Test User", "email": "test@test.com", "role": "student",
                                    "password": "123", "confirm_password": "123"},
                              follow_redirects=True)
        self.assertIn(b"at least 6 characters", rv.data)

    def test_register_success(self):
        with self.app.app_context():
            with unittest.mock.patch("app.query", side_effect=[None, {"id": 99, "name": "New User", "email": "new@user.com", "role": "student"}, None]):
                with unittest.mock.patch("app.execute"):
                    rv = self.client.post("/register",
                                          data={"name": "New User", "email": "new@user.com", "role": "student",
                                                "password": "password123", "confirm_password": "password123"},
                                          follow_redirects=False)
                    self.assertIn(rv.status_code, (301, 302))
                    self.assertIn("dashboard", rv.headers.get("Location", ""))

    def test_404_handler(self):
        rv = self.client.get("/this-route-does-not-exist-xyz")
        self.assertEqual(rv.status_code, 404)


@unittest.skipUnless(HAS_FLASK, _SKIP_MSG)
class TestAdminRoutes(unittest.TestCase):

    def setUp(self):
        self.app    = _make_app()
        self.client = self.app.test_client()

    def _login_admin(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["role"]    = "admin"
            sess["name"]    = "Admin"

    def test_branches_page_requires_login(self):
        rv = self.client.get("/branches", follow_redirects=False)
        self.assertIn(rv.status_code, (301, 302))

    def test_branches_page_accessible_as_admin(self):
        self._login_admin()
        import unittest.mock
        mock_row = {"n": 1}
        with unittest.mock.patch("app.query", return_value=[]):
            rv = self.client.get("/branches")
        self.assertEqual(rv.status_code, 200)

    def test_generate_page_accessible_as_admin(self):
        self._login_admin()
        rv = self.client.get("/generate")
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b"Generate", rv.data)

    def test_runs_page_accessible_as_admin(self):
        self._login_admin()
        import unittest.mock
        with unittest.mock.patch("app.query", return_value=[]):
            rv = self.client.get("/runs")
        self.assertEqual(rv.status_code, 200)


@unittest.skipUnless(HAS_FLASK, _SKIP_MSG)
class TestApiStats(unittest.TestCase):

    def setUp(self):
        self.app    = _make_app()
        self.client = self.app.test_client()

    def _login(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["role"]    = "admin"
            sess["name"]    = "Admin"

    def test_api_stats_requires_login(self):
        rv = self.client.get("/api/stats")
        self.assertIn(rv.status_code, (302, 401, 403))

    def test_api_stats_returns_json(self):
        self._login()
        import unittest.mock
        mock_row = {"n": 3}
        with unittest.mock.patch("app.query", return_value=mock_row):
            rv = self.client.get("/api/stats")
        self.assertEqual(rv.status_code, 200)
        data = json.loads(rv.data)
        self.assertIn("branches", data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
