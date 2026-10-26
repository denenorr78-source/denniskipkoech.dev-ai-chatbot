import tempfile
import unittest
import hashlib
import hmac
import json
from pathlib import Path
from unittest.mock import Mock

from app.intake import IntakeAssistant
from app.models import IncomingMessage
from app.security import verify_meta_signature, verify_tiktok_signature
from app.store import Store


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.store = Store(str(Path(self.tempdir.name) / "test.sqlite3"))
        self.bot = IntakeAssistant(self.store, "Denniskipkoech.dev AI Chatbot")

    def tearDown(self):
        self.tempdir.cleanup()

    def send(self, text):
        return self.bot.handle(IncomingMessage("instagram", "sender-1", text))

    def test_greeting_starts_intake(self):
        result = self.send("Hi")
        self.assertIn("What are you looking to build", result.reply)
        self.assertIsNone(result.lead)

    def test_collects_project_timeline_budget_and_contact(self):
        self.send("I need a booking website with payments")
        self.assertIn("budget range", self.send("About two months").reply.lower())
        self.assertIn("what name and email", self.send("KES 100,000-150,000").reply.lower())
        result = self.send("Alex, alex@example.com")
        self.assertIsNotNone(result.lead)
        self.assertEqual(result.lead["budget"], "KES 100,000-150,000")
        self.assertEqual(result.lead["contact"], "Alex, alex@example.com")

    def test_duplicate_event_is_ignored(self):
        self.assertFalse(self.store.is_processed("whatsapp", "wamid-1"))
        self.store.mark_processed("whatsapp", "wamid-1")
        self.assertTrue(self.store.is_processed("whatsapp", "wamid-1"))

    def test_pending_event_is_reused_until_delivery_succeeds(self):
        result = {"reply": "What are you looking to build?", "lead": None}
        self.store.save_pending_event("whatsapp", "wamid-1", result)

        self.assertEqual(self.store.load_pending_event("whatsapp", "wamid-1"), result)
        self.assertFalse(self.store.is_processed("whatsapp", "wamid-1"))

        self.store.mark_processed("whatsapp", "wamid-1")
        self.assertTrue(self.store.is_processed("whatsapp", "wamid-1"))
        self.assertIsNone(self.store.load_pending_event("whatsapp", "wamid-1"))

    def test_database_health_check(self):
        self.store.check()

    def test_rejects_unsupported_database_url(self):
        with self.assertRaisesRegex(ValueError, "must use PostgreSQL"):
            Store("mysql://localhost/chatbot")

    def test_postgres_queries_use_psycopg_placeholders(self):
        store = Store.__new__(Store)
        store.is_postgres = True
        connection = Mock()

        store._execute(
            connection,
            "SELECT state_json FROM conversations WHERE sender_id=?",
            ("sender-1",),
        )

        connection.execute.assert_called_once_with(
            "SELECT state_json FROM conversations WHERE sender_id=%s",
            ("sender-1",),
        )

    def test_meta_signature(self):
        secret = "test-secret"
        body = b'{"object":"page"}'
        digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        self.assertTrue(verify_meta_signature(body, f"sha256={digest}", secret))
        self.assertFalse(verify_meta_signature(body, "sha256=bad", secret))

    def test_tiktok_signature(self):
        secret = "test-secret"
        timestamp = "1700000000"
        body = {"event": "im_receive_msg", "content": "{\"text\":{\"body\":\"Hi\"}}"}
        canonical = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        signed = f"{timestamp}.{canonical}".encode()
        digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        signature = f"t={timestamp},s={digest}"
        self.assertTrue(verify_tiktok_signature(
            canonical.encode(), signature, secret, max_skew_seconds=10, now=1700000000
        ))
        self.assertFalse(verify_tiktok_signature(
            canonical.encode(), signature, secret, max_skew_seconds=10, now=1700001000
        ))


if __name__ == "__main__":
    unittest.main()
