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
    current_block_height_np = np.int64(current_block_height)
    slash_window_np = np.int64(slash_window)
    return int(np.floor_divide(current_block_height_np, slash_window_np))

if __name__ == "__main__":
    print(create_epoch(7199, 3600))
