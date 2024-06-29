import logging
import os

from dotenv import dotenv_values

is_dev = False
if os.path.exists('.env'):
    config = dotenv_values('.env')
    is_dev = config['DEV_MODE'] == 'true'

logger = logging.getLogger('GFD_Bot')
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG if is_dev else logging.INFO)
