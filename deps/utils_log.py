import inspect
import logging
import os
import time
import traceback
from datetime import timezone, datetime

from z_deps_scan.settings import LOG_LEVEL, LOG_FORMAT

log = logging.getLogger('consoleAndGeneralFile')


def setupProcessLogger(specificLogFilePath):
    logger = logging.getLogger("thread-{threading.get_ident()}")

    # Empty the log file if it exists
    if os.path.isfile(specificLogFilePath):
        with open(specificLogFilePath, 'w'):
            pass  # This will truncate the file

    # Remove any existing handlers from the logger
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create a file handler with a unique file name based on the process_id
    file_handler = logging.FileHandler(specificLogFilePath)
    file_handler.setLevel(LOG_LEVEL)

    # Create a formatter and set it for the handler
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(file_handler)

    # Add handlers from the general logger
    # for handler in log.handlers:
    #     logger.addHandler(handler)

    # Prevent propagation to avoid duplicate logging
    logger.propagate = False
    return logger


def writeToGeneralLog(pathLogFile):
    with open(pathLogFile, 'r') as processLogLines:
        lines = processLogLines.readlines()
        for line in lines:
            log.info(line)


def funName(depth=1):
    currentframe = inspect.currentframe()
    for i in range(0, depth):
        currentframe = currentframe.f_back
    return currentframe.f_code.co_name


def startMessage(entity=None) -> str:
    return message('START', 3, entity)


def endMessage(entity=None) -> str:
    return message('END', 3, entity)


def message(suffix: str, depth=2, entity=None) -> str:
    if entity is None:
        return f'{suffix} {funName(depth)}'
    elif hasattr(entity, 'id'):
        return f'{entity.__class__.__name__} {entity.id} - {suffix} {funName(depth)}'
    else:
        return f'{entity.__class__.__name__} - {suffix} {funName(depth)}'


def logExecTime(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        log.info(f"{func.__name__} done in {execution_time:.4f} sec")
        return result

    return wrapper


def logResponse(response):
    return f'code: {str(response.status_code)}, message: {response.text}'


def get_current_datetime():
    # Get the current date and time
    current_datetime = datetime.now(timezone.utc)
    # Format the date and time
    formatted_datetime = current_datetime.strftime("%d/%m/%Y %H:%M:%S")
    return formatted_datetime


def exceptionMessage(e: Exception):
    # TODO use log.error(e, exc_info=True)
    return funName(2) + ' -  ' + str(e) + '\n' + traceback.format_exc()
