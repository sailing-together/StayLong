"""Smoke tests for the initial package."""


def test_package_imports() -> None:
    import staylong

    assert staylong.__doc__ is not None
