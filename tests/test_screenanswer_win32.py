"""Guards for the Windows ctypes layer.

The tray/capture code only executes on Windows, so regular unit tests never
touch it — and a typo like `wintypes.c_uint` (it's `wintypes.UINT`) shipped
in the first `otter` release and crashed at startup. These tests lint the
ctypes layer from any OS so that class of bug cannot ship again.
"""

import pathlib
import re
import unittest
from ctypes import wintypes

SOURCE_DIR = pathlib.Path(__file__).resolve().parents[1] / "screenanswer"


class WintypesLintTests(unittest.TestCase):
    def test_every_wintypes_attribute_actually_exists(self):
        names = set()
        for path in SOURCE_DIR.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            names.update(re.findall(r"\bwt\.([A-Za-z_]\w*)", text))
        self.assertTrue(names, "expected wintypes usage in the ctypes layer")
        missing = sorted(name for name in names if not hasattr(wintypes, name))
        self.assertEqual(
            missing,
            [],
            "screenanswer references non-existent ctypes.wintypes names: %s" % missing,
        )

    def test_no_ctypes_style_names_via_wintypes(self):
        # `wt.c_uint`-style names are always wrong: wintypes uses UINT, DWORD…
        offenders = []
        for path in SOURCE_DIR.glob("*.py"):
            for match in re.finditer(r"\bwt\.(c_[A-Za-z_]\w*)", path.read_text(encoding="utf-8")):
                offenders.append("%s: wt.%s" % (path.name, match.group(1)))
        self.assertEqual(offenders, [])


class TrayModuleContractTests(unittest.TestCase):
    def test_shared_constants_and_types_are_module_level(self):
        # Methods (set_state, _show_context_menu, stop) must resolve these at
        # module scope — function-scope constants are NameErrors at click time.
        from screenanswer import tray

        for name in (
            "POINT",
            "NIM_ADD",
            "NIM_MODIFY",
            "NIM_DELETE",
            "NIF_MESSAGE",
            "NIF_ICON",
            "MF_STRING",
            "TPM_RETURNCMD",
            "TPM_RIGHTBUTTON",
            "CMD_OPEN",
            "CMD_DIAGNOSTICS",
            "WM_TRAY",
            "WM_HOTKEY",
            "WM_LBUTTONUP",
            "WM_LBUTTONDBLCLK",
            "WM_RBUTTONUP",
            "WM_CLOSE",
            "WM_DESTROY",
            "MOD_ALT",
            "MOD_CONTROL",
            "MOD_NOREPEAT",
            "WS_POPUP",
            "TRAY_UID",
            "HOTKEY_CAPTURE_ID",
            "HOTKEY_DELETE_ID",
        ):
            self.assertTrue(hasattr(tray, name), "screenanswer.tray missing module-level %s" % name)

    def test_point_is_a_shared_structure(self):
        import ctypes

        from screenanswer.tray import POINT

        self.assertTrue(hasattr(POINT, "_fields_"))
        point = POINT(1, 2)
        self.assertEqual(ctypes.sizeof(POINT), 8)  # two 32-bit LONGs

    def test_method_bodies_have_no_local_win32_constants(self):
        # Belt and braces: method sources must not redefine shared constants.
        from screenanswer import tray
        import inspect

        for name in ("set_state", "_show_context_menu", "stop"):
            source = inspect.getsource(getattr(tray.WindowsTray, name))
            for const in ("NIM_MODIFY", "MF_STRING", "CMD_OPEN", "TPM_RETURNCMD"):
                self.assertNotRegex(
                    source,
                    r"^\s*%s\s*=" % const,
                    "%s redefines %s locally" % (name, const),
                )


if __name__ == "__main__":
    unittest.main()
