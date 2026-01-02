
import logging
import os

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
            logging.FileHandler('bot.log'),
            logging.StreamHandler()
        ]
    )

    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    logging.getLogger('discord.gateway').setLevel(logging.INFO)

    return logging.getLogger('bot')

logger = setup_logging()
