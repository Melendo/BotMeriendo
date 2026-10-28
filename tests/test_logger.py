import logging
from logging.handlers import RotatingFileHandler

import src.utils.logger  # noqa: F401  (configura el logging)


def test_log_rotativo():
    handlers = logging.getLogger().handlers
    rot = [h for h in handlers if isinstance(h, RotatingFileHandler)]
    assert rot, "falta el RotatingFileHandler"
    assert rot[0].maxBytes > 0 and rot[0].backupCount > 0
