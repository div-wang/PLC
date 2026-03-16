'''
Author: Div gh110827@gmail.com
Date: 2026-03-16 15:12:14
LastEditors: Div gh110827@gmail.com
LastEditTime: 2026-03-16 15:12:15
Description: 
Copyright (c) 2026 by ${git_name_email}, All Rights Reserved. 
'''
import unittest

from connectors.jy500_modbus import decode_float32, decode_int32, encode_float32, encode_int32


class TestJY500Codec(unittest.TestCase):
    def test_float32_example_100(self):
        hi, lo = encode_float32(100.0, "ABCD")
        self.assertEqual(hi, 0x42C8)
        self.assertEqual(lo, 0x0000)
        self.assertAlmostEqual(decode_float32([hi, lo], "ABCD"), 100.0, places=6)

    def test_int32_example_10000(self):
        hi, lo = encode_int32(10000, "ABCD")
        self.assertEqual(hi, 0x0000)
        self.assertEqual(lo, 0x2710)
        self.assertEqual(decode_int32([hi, lo], "ABCD"), 10000)


if __name__ == "__main__":
    unittest.main()

