"""MASKAI Bot - Security tests"""
import unittest
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bot as bot_module

class TestAuthorization(unittest.TestCase):
    
    def test_admin_authorized(self):
        self.assertTrue(bot_module.is_authorized(1367356347))
    
    def test_unknown_rejected(self):
        self.assertFalse(bot_module.is_authorized(999999999))
        self.assertFalse(bot_module.is_authorized(0))
    
    def test_admin_ids_is_list(self):
        self.assertIsInstance(bot_module.ADMIN_IDS, list)
        self.assertGreater(len(bot_module.ADMIN_IDS), 0)

if __name__ == "__main__":
    unittest.main()
