from pathlib import Path
import pbt9500
import time
import logging

logger = logging.getLogger('demo')

if __name__  == "__main__":
    logger.info('Initializing')

    sc = pbt9500.Scanner()
    sc.open()

    # path = Path(__file__).parent
    # path = path / 'images'
    # sc.set_image_path(path) # defaults to current working directory

    while True:
        logger.info("Ready to scan")
        sc.scan()