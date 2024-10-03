import os

envList = os.environ.copy()


def toEnvFormat(envKey: str):
    return '${' + envKey + '}'


def filterEnvVariables(keys_to_keep):
    """
    Filters the environment variables, keeping only the keys specified in keys_to_keep.

    Parameters:
    keys_to_keep (list): The list of keys to keep in the filtered environment variables.

    Returns:
    dict: A dictionary containing only the specified environment variables.
    """
    return {key: value for key, value in envList.items() if key in keys_to_keep}
