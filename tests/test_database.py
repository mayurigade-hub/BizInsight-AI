import os
import tempfile
import unittest

import database


class TestDatabaseUserLookup(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.original_db_name = database.DB_NAME
        database.DB_NAME = self.temp_db.name
        database.initialize_database()

    def tearDown(self):
        database.DB_NAME = self.original_db_name
        try:
            os.remove(self.temp_db.name)
        except OSError:
            pass

    def test_get_user_by_username_returns_user(self):
        result = database.create_user("testuser", "test@example.com", "Password123!")
        self.assertIs(result, True)

        user = database.get_user_by_username("testuser")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "testuser")
        self.assertEqual(user["email"], "test@example.com")
        self.assertTrue(database.verify_password("Password123!", user["password_hash"]))

    def test_get_user_by_username_returns_none_for_unknown_username(self):
        self.assertIsNone(database.get_user_by_username("missing"))

    def test_get_user_by_username_returns_none_for_blank_username(self):
        self.assertIsNone(database.get_user_by_username("  "))

    def test_clear_data_removes_feedback_with_aspect_sentiment(self):
        database.create_user("aspectuser", "aspect@example.com", "Password123!")
        user = database.get_user_by_username("aspectuser")
        user_id = user["id"]

        database.insert_feedback_bulk_with_aspects(
            [
                (
                    "Delivery was late but packaging was great",
                    0.1,
                    {"Delivery": "Negative", "Packaging": "Positive"},
                )
            ],
            user_id,
        )

        # Sanity check: aspect rows exist before clearing.
        self.assertTrue(len(database.fetch_aspect_sentiment(user_id)) > 0)
        self.assertTrue(len(database.fetch_feedback(user_id)) > 0)

        result = database.clear_data(user_id)
        self.assertIs(result, True)

        self.assertEqual(database.fetch_feedback(user_id), [])
        self.assertEqual(database.fetch_aspect_sentiment(user_id), [])

    def test_clear_data_with_no_feedback_does_not_raise(self):
        database.create_user("emptyuser", "empty@example.com", "Password123!")
        user = database.get_user_by_username("emptyuser")
        user_id = user["id"]

        result = database.clear_data(user_id)
        self.assertIs(result, True)


if __name__ == "__main__":
    unittest.main()