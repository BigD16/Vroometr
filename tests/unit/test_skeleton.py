from vroometr import __version__


def test_shared_package_version() -> None:
    assert __version__ == "0.1.0"
