"""V2-CONF-001: Config validation tests"""
import unittest
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfigFailFast(unittest.TestCase):
    def setUp(self):
        from maskai.config import reset_config_for_tests
        reset_config_for_tests()

    def test_missing_bot_token_raises(self):
        from maskai.config import Config
        with self.assertRaises(RuntimeError) as ctx:
            Config(BOT_TOKEN="", SUPABASE_URL="x", SUPABASE_KEY="x", DAHONO_KEY="x")
        self.assertIn("BOT_TOKEN", str(ctx.exception))

    def test_missing_supabase_url_raises(self):
        from maskai.config import Config
        with self.assertRaises(RuntimeError) as ctx:
            Config(BOT_TOKEN="x", SUPABASE_URL="", SUPABASE_KEY="x", DAHONO_KEY="x")
        self.assertIn("SUPABASE_URL", str(ctx.exception))

    def test_missing_supabase_key_raises(self):
        from maskai.config import Config
        with self.assertRaises(RuntimeError) as ctx:
            Config(BOT_TOKEN="x", SUPABASE_URL="x", SUPABASE_KEY="", DAHONO_KEY="x")
        self.assertIn("SUPABASE_KEY", str(ctx.exception))

    def test_missing_dahono_key_raises(self):
        from maskai.config import Config
        with self.assertRaises(RuntimeError) as ctx:
            Config(BOT_TOKEN="x", SUPABASE_URL="x", SUPABASE_KEY="x", DAHONO_KEY="")
        self.assertIn("DAHONO_KEY", str(ctx.exception))

    def test_all_valid_config_ok(self):
        from maskai.config import Config
        c = Config(BOT_TOKEN="t", SUPABASE_URL="u", SUPABASE_KEY="k", DAHONO_KEY="d")
        self.assertEqual(c.BOT_TOKEN, "t")

    def test_ocr_max_zero_raises(self):
        from maskai.config import Config
        with self.assertRaises(RuntimeError):
            Config(BOT_TOKEN="t", SUPABASE_URL="u", SUPABASE_KEY="k", DAHONO_KEY="d", OCR_MAX_IMAGE_BYTES=0)

    def test_ocr_max_negative_raises(self):
        from maskai.config import Config
        with self.assertRaises(RuntimeError):
            Config(BOT_TOKEN="t", SUPABASE_URL="u", SUPABASE_KEY="k", DAHONO_KEY="d", OCR_MAX_IMAGE_BYTES=-10)

    def test_ocr_max_positive_ok(self):
        from maskai.config import Config
        c = Config(BOT_TOKEN="t", SUPABASE_URL="u", SUPABASE_KEY="k", DAHONO_KEY="d", OCR_MAX_IMAGE_BYTES=8388608)
        self.assertEqual(c.OCR_MAX_IMAGE_BYTES, 8388608)

    def test_log_level_invalid_falls_back_to_info(self):
        from maskai.config import Config
        c = Config(BOT_TOKEN="t", SUPABASE_URL="u", SUPABASE_KEY="k", DAHONO_KEY="d", LOG_LEVEL="INVALID")
        self.assertEqual(c.LOG_LEVEL, "INFO")

    def test_log_level_valid_kept(self):
        from maskai.config import Config
        c = Config(BOT_TOKEN="t", SUPABASE_URL="u", SUPABASE_KEY="k", DAHONO_KEY="d", LOG_LEVEL="DEBUG")
        self.assertEqual(c.LOG_LEVEL, "DEBUG")

    def test_from_env_with_invalid_ocr_bytes_raises(self):
        from maskai.config import from_env
        import os
        os.environ["BOT_TOKEN"] = "t"
        os.environ["SUPABASE_URL"] = "u"
        os.environ["SUPABASE_KEY"] = "k"
        os.environ["DAHONO_KEY"] = "d"
        os.environ["OCR_MAX_IMAGE_BYTES"] = "abc"
        with self.assertRaises(RuntimeError):
            from_env()

    def test_singleton_returns_same_instance(self):
        """get_config() returns same instance (env already set by conftest)"""
        from maskai.config import get_config, reset_config_for_tests
        import os
        # Env already set by conftest — just verify singleton
        os.environ["BOT_TOKEN"] = "t"
        os.environ["SUPABASE_URL"] = "u"
        os.environ["SUPABASE_KEY"] = "k"
        os.environ["DAHONO_KEY"] = "d"
        reset_config_for_tests()
        c1 = get_config()
        c2 = get_config()
        self.assertIs(c1, c2)


if __name__ == "__main__":
    unittest.main()
