import atexit
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from logging import Logger

from deps.utils_env import envList
from deps.utils_log import startMessage, endMessage
from z_deps_scan.settings import MAX_WORKERS

THREAD_POOL_EXECUTOR = ThreadPoolExecutor(max_workers=MAX_WORKERS)


def processChunks(elemList, chunk_size=100):
    # Calculate the number of chunks needed
    for i in range(0, len(elemList), chunk_size):
        # Yield the current chunk
        yield elemList[i:i + chunk_size]
        

def shutdown_executor():
    THREAD_POOL_EXECUTOR.shutdown(wait=True)


atexit.register(shutdown_executor)


def parallelExec(taskFunction, entityList):
    return [THREAD_POOL_EXECUTOR.submit(taskFunction, entity) for entity in entityList]


def runCommand(processlogger: Logger, cwd, command, pathLogFile=None):
    processlogger.info(startMessage() + f' in {cwd} with cmd {command}')
    if pathLogFile is None:
        pathLogFile = processlogger.handlers[0].baseFilename
    with open(pathLogFile, 'a', buffering=1) as logFile:
        try:
            subprocess.run(command, cwd=cwd, check=True, text=True, stdout=logFile, stderr=subprocess.STDOUT,
                           env=envList)
            # Ensure all data is written to the log file
            logFile.flush()
            # Optionally, ensure the file is fully written to disk
            os.fsync(logFile.fileno())

        except subprocess.CalledProcessError as e:
            # Log the error output if the command fails
            message = endMessage() + ':\n' + (
                f"Command '{e.cmd}' returned non-zero exit status {e.returncode}.:\n") + (
                              "e.output :" + (e.output if e.output else "") + '\n') + (
                              "e.stderr :" + (e.stderr if e.stderr else "") + '\n')

            processlogger.error(message)
            # writeToGeneralLog(pathLogFile)
            raise e
        finally:
            processlogger.info(endMessage() + f' in {cwd} with cmd {command}')
