import logging
import os

from dotenv import dotenv_values

is_dev = False
if os.path.exists('.env'):
    config = dotenv_values('.env')
    is_dev = 'DEV_MODE' in config and config['DEV_MODE'] == 'true'

logger = logging.getLogger('GFD_Bot')
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s'))
logger.addHandler(handler)
file_handler = logging.FileHandler('bot-errors.log')
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(logging.Formatter('%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s'))
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG if is_dev else logging.INFO)
