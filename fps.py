#!/usr/bin/python

"""
__author__    = "Leon Fedden"
__copyright__ = "Copyright (C) 2016 Leon Fedden

"""

import time

class Fps(object):

    """Simple fps timing and management for inside the context of a loop.

    Really simple class to pause thread of execution to meet desired fps.
    Call within a loop and call start and sleep at the beginning and the
    end of the loop respectively to properly to get the desired fps.

    """

    def __init__(self, fps=8):
        """__init__ method

        Args:
            fps (int): The desired frames per second. Defaulted to 8.

        """
        self.fps = fps
        self.start_frame = 0
        self.ms_per_frame = 1000 / fps

    def start(self):
        """start method begins the timer.

        This begins the timer to calculate the loops execution time so
        the rest of the time can be slept off.
        """
        self.start_frame = int(round(time.time() * 1000))

    def sleep(self):
        """sleep method pauses the current thread of execution.

        The time left for the desired fps after the loop's operations
        is slept off using time.sleep()
        """
        self.end_frame = int(round(time.time() * 1000))
        self.sleep_amount = float(self.start_frame + self.ms_per_frame - self.end_frame) / 1000.0
        self.sleep_amount = max(0.0, self.sleep_amount)

        time.sleep(self.sleep_amount)

