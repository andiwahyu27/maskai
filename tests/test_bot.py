"""MASKAI Bot - Baseline test infrastructure"""
import unittest
import sys, os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestBaseline(unittest.TestCase):
    """Minimal tests to validate bot can be loaded"""
    
    def test_bot_compiles(self):
        """bot.py must be syntactically valid"""
        import py_compile
        bot_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot.py")
        py_compile.compile(bot_path, doraise=True)
    
    def test_schema_readable(self):
        """schema.sql must exist and be readable"""
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schema.sql")
        self.assertTrue(os.path.exists(schema_path))
        with open(schema_path) as f:
            content = f.read()
        self.assertIn("CREATE TABLE", content.upper())
        self.assertIn("maskai_transactions", content.lower())

if __name__ == "__main__":
    unittest.main()
