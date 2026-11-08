"""Synthetic regression checks for file-only geometry preparation; no engine calls."""

import importlib.util
from pathlib import Path
import tempfile


spec = importlib.util.spec_from_file_location("runner", Path(__file__).resolve().parents[1] / "reaxkit_runner.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def main():
    prefix = "HETATM     1 Co".ljust(30)
    suffix = "    Co  0 0  0.00000"
    coordinates = (6.28853, -6.78413, 7.50395)
    original = "XTLGRF 200\nFORMAT ATOM (3f10.5)\n" + prefix + "".join(
        f"{value:10.5f}" for value in coordinates
    ) + suffix + "\nEND\n"
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "geo"
        path.write_text(original)
        rendered = runner.render_geometry(path)
        assert path.read_text() == original
        atom = rendered.splitlines()[2]
        assert atom[:30] == prefix and atom[75:] == suffix
        assert [float(atom[start:start + 15]) for start in (30, 45, 60)] == list(coordinates)
        path.write_text(rendered)
        assert runner.render_geometry(path) == rendered
        path.write_text(original + original)
        assert runner.render_geometry(path).count("HETATM") == 2
        for invalid in (
            original.replace("3f10.5", "3f12.6"),
            original.replace("FORMAT ATOM (3f10.5)\n", ""),
            original.replace("   6.28853", "       NaN"),
            "XTLGRF 200\nEND\n",
            "XTLGRF 200\nFORMAT ATOM (3f10.5)\nHETATM\n",
            original.replace("   6.28853", "-9999.0000"),
        ):
            path.write_text(invalid)
            try:
                runner.render_geometry(path)
            except ValueError:
                pass
            else:
                raise AssertionError("Invalid geometry was accepted")
    print("Geometry regression checks passed; no engine calls")


if __name__ == "__main__":
    main()
