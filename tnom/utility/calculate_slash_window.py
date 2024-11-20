"""Create epoch is a function that creates an fictive epoch.

Usage:
    Used to create an fictive epoch.
"""
import numpy as np


def create_epoch(current_block_height: int, slash_window: int) -> int:
    """Create epoch is a function that creates an fictive epoch.

    The function takes the current block height and the slash window as input
    and returns the epoch number.

    Args:
        current_block_height (int): The current block height.
        slash_window (int): The slash window.

    Return:
        int: The epoch number.

    """
    #Until there is a better solution this will have to suffice
    #It works by dividing the current block height by the slash window
    #And it return the floor of that division
    return np.floor_divide(current_block_height, slash_window)

