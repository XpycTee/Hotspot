from logging import getLogger
import threading
from core.config.listener import ConfigListener
from core.config.logging import configure_logger


logger = getLogger('GunicornHook')
configure_logger(logger)

def post_fork(server, worker):
    logger.info(f"Worker {worker.pid} forked, starting config_listener thread")
    t = threading.Thread(
        target=ConfigListener().run,
        name='redis-config-listener',
        daemon=True  # чтобы не блокировал завершение процесса
    )
    t.start()
    logger.info(f"Listener thread started in worker {worker.pid}")
