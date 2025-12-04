import unittest

from core.utils.phone import normalize_phone


class TestCoreUtils(unittest.TestCase):
    def test_normalize_phone(self):
        dirty_phone_number = '+7 (999) 999-99-99'
        norm_phone_number = '79999999999'

        result = normalize_phone(dirty_phone_number)
        self.assertEqual(result, norm_phone_number)