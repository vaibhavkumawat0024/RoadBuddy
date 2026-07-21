import unittest
from datetime import datetime, timezone, timedelta
from app.services.confidence import calculate_confidence

class TestFuelDecay(unittest.TestCase):
    def test_active_ttl(self):
        # 1 hour TTL, checked after 30 minutes
        now = datetime.now(timezone.utc)
        reported_at = now - timedelta(minutes=30)
        res = calculate_confidence(
            last_reported_at=reported_at,
            source="operator",
            current_time=now,
            ttl_hours=1.0,
            reported_status="available"
        )
        self.assertEqual(res["score"], 100)
        self.assertFalse(res["is_stale"])
        self.assertTrue("Guaranteed available" in res["label"])
        self.assertTrue("30m" in res["label"])

    def test_decaying_ttl(self):
        # 1 hour TTL, checked after 2 hours (1 hour after TTL expired, which is exactly 50% decay)
        now = datetime.now(timezone.utc)
        reported_at = now - timedelta(hours=2)
        res = calculate_confidence(
            last_reported_at=reported_at,
            source="operator",
            current_time=now,
            ttl_hours=1.0,
            reported_status="available"
        )
        # 100 - (99 * 0.5) = 50.5 -> rounded to 50
        self.assertEqual(res["score"], 50)
        self.assertFalse(res["is_stale"])
        self.assertTrue("Confirmed" in res["label"])
        self.assertTrue("expired 1h" in res["label"])

    def test_expired_ttl_pinned(self):
        # 1 hour TTL, checked after 4 hours (3 hours after TTL expired)
        now = datetime.now(timezone.utc)
        reported_at = now - timedelta(hours=4)
        res = calculate_confidence(
            last_reported_at=reported_at,
            source="operator",
            current_time=now,
            ttl_hours=1.0,
            reported_status="available"
        )
        self.assertEqual(res["score"], 1)
        self.assertFalse(res["is_stale"])
        self.assertTrue("expired 3h" in res["label"])

    def test_always_available(self):
        # -1.0 TTL, checked after 100 hours
        now = datetime.now(timezone.utc)
        reported_at = now - timedelta(hours=100)
        res = calculate_confidence(
            last_reported_at=reported_at,
            source="operator",
            current_time=now,
            ttl_hours=-1.0,
            reported_status="available"
        )
        self.assertEqual(res["score"], 100)
        self.assertFalse(res["is_stale"])
        self.assertEqual(res["label"], "Available 24/7 (Guaranteed)")

if __name__ == '__main__':
    unittest.main()
