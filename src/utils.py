import json


# Define utility functions for unit conversions and JSON validation
def megabits_to_bits(megabits):
    """
    Converts megabits to bits.

    Args:
        megabits (float): The value in megabits to be converted.

    Returns:
        str: The converted value in bits per second.

    """
    bits_per_sec = float(megabits) * (10**6)
    return str(bits_per_sec)


def is_json(myjson):
    """
    Check if a string is a valid JSON.

    Args:
        myjson (str): The string to be checked.

    Returns:
        bool: True if the string is a valid JSON, False otherwise.
    """
    try:
        json.loads(myjson)
    except ValueError:
        return False
    return True
