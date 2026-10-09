import logging

from .bot import Bot
from .config import load

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
Bot(load()).run()
