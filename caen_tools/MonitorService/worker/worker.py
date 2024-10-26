import logging
from .loader import LoaderControl
from .utils import Address


def worker(device_backend: Address, monitor: Address, period: float):
    """Main function of monitor worker

    Parameters
    ----------
    device_backend: Address
        connection address to devback
    monitor: Address
        connection address to monitor API
    period: float
        loader period (in seconds)
    """

    logging.info("Start Monitor worker")
    loader = LoaderControl(device_backend, monitor, period)

    loop = loader.run()

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logging.info("Keyboard Interrupt. Finish the program")
    finally:
        logging.info("Final program close")
        loader.close()

    return
