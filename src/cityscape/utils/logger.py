from prefect.logging import get_logger as prefect_get_logger

def get_logger(name: str | None = None)::
    """Get a Prefect logger.

    Args:
        name: The name of the logger. If `None`, the root logger is returned.

    Returns:
        A Prefect logger.
    """
    return prefect_get_logger(name)