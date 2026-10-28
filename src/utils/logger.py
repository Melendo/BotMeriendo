import logging
from logging.handlers import RotatingFileHandler

LOG_FILE = 'bot.log'
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB por archivo
LOG_BACKUPS = 3                  # bot.log + 3 copias = 20 MB como máximo


def setup_logging():
    # Eliminar handlers existentes para evitar duplicados si se llama varias veces
    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.handlers = []

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)-8s %(name)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            RotatingFileHandler(
                LOG_FILE,
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUPS,
                encoding='utf-8',
            ),
            logging.StreamHandler()
        ]
    )

    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    logging.getLogger('discord.gateway').setLevel(logging.INFO)

    return logging.getLogger('bot')


logger = setup_logging()
