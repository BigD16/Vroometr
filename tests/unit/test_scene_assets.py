from pathlib import Path

_PUBLIC = Path(__file__).resolve().parents[2] / "apps" / "web" / "public"


def test_default_scene_jpegs_exist() -> None:
    for name in ("default-garage.jpg", "rides-track.jpg"):
        path = _PUBLIC / name
        assert path.is_file(), name
        assert path.read_bytes()[:3] == b"\xff\xd8\xff", name
