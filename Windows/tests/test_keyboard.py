import unittest
from fotoswipe.keyboard import blocks_shortcut


class KeyboardTests(unittest.TestCase):
    def test_windows_lock_states_do_not_block_arrows(self):
        for locks in (0, 0x2, 0x8, 0x20, 0x2A):
            for extended in (0, 0x40000):
                with self.subTest(locks=locks, extended=extended):
                    self.assertFalse(blocks_shortcut(locks | extended, 'win32'))

    def test_windows_control_and_alt_still_block_sorting(self):
        for state in (0x4, 0x20000, 0x20004, 0x2002C):
            self.assertTrue(blocks_shortcut(state, 'win32'))

    def test_x11_modifier_mapping_remains_separate(self):
        self.assertTrue(blocks_shortcut(0x8, 'x11'))
        self.assertTrue(blocks_shortcut(0x4, 'x11'))
        self.assertFalse(blocks_shortcut(0x12, 'x11'))
