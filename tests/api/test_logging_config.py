import logging

from staylong.api import app as api_app


def test_runtime_logging_emits_info_records_to_existing_root_handlers(caplog) -> None:
    """Protects the Cloud Run timing signal from Python's WARNING default."""
    root_logger = logging.getLogger()
    original_level = root_logger.level
    root_logger.setLevel(logging.WARNING)

    try:
        configure_runtime_logging = getattr(api_app, "configure_runtime_logging", None)
        assert callable(configure_runtime_logging)
        configure_runtime_logging()
        logging.getLogger("staylong.services.taskmaster").info("timing signal")
    finally:
        root_logger.setLevel(original_level)

    assert "timing signal" in caplog.messages
