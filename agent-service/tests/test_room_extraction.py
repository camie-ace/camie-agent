"""
Test room extraction functionality
"""

import unittest
from utils.room_extractor import extract_phone_number, extract_room_name


class TestRoomExtraction(unittest.TestCase):
    def test_phone_number_extraction(self):
        # Test Twilio format
        self.assertEqual(
            "+33644644937",
            extract_phone_number(
                "twilio-+33644644937-21f2636a-011f-47f0-9c14-0d1f1e0e8982-_0046_XiDmiKxErBXz")
        )

        # Test direct phone number
        self.assertEqual(
            "+33644644937",
            extract_phone_number("some-prefix-+33644644937-some-suffix")
        )

        # Test number without plus
        number = extract_phone_number("some-prefix-33644644937-some-suffix")
        self.assertTrue(number == "+33644644937" or number == "33644644937",
                        f"Expected +33644644937 or 33644644937, got {number}")

        # Test unknown
        self.assertIsNone(extract_phone_number("unknown"))

        # Test None
        self.assertIsNone(extract_phone_number(None))

    def test_room_name_extraction(self):
        # We need to mock a JobContext object for these tests
        class MockJobRequest:
            def __init__(self, room_name):
                self.room_name = room_name

        class MockJob:
            def __init__(self, room_name=None):
                self.id = "AJ_test123"
                if room_name:
                    self.request = MockJobRequest(room_name)

            def __str__(self):
                return f"MockJob(id=AJ_test123, room_name=test-room-name)"

        class MockRoom:
            def __init__(self, name):
                self.name = name

        class MockContext:
            def __init__(self, job=None, room=None):
                self.job = job
                self.room = room

            def __str__(self):
                return "MockContext(room_name=context-room-name)"

        # Test standard API path
        ctx = MockContext(job=MockJob(room_name="standard-api-room"))
        self.assertEqual("standard-api-room", extract_room_name(ctx))

        # Test fallback to context string - our implementation uses this path
        ctx = MockContext(job=MockJob())  # No request
        self.assertEqual("context-room-name", extract_room_name(ctx))

        # Test context with null job
        ctx = MockContext()  # Empty context
        ctx.job = None
        ctx.room = None
        # With our current implementation, this still extracts from context string
        self.assertEqual("context-room-name", extract_room_name(ctx))


if __name__ == "__main__":
    unittest.main()
