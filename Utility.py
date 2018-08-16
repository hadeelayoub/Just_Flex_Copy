import math

class Utility:
    """Class of useful utility functions"""

    def __init__(self):
        return

    @staticmethod
    def euc(a, b):
        """Calculate Euclidean distance between two vectors

        Parameters `a` and `b` should be of identical dimension.

        :param a: First input vector
        :type a: [float]
        :param b: First input vector
        :type b: [float]
        :return: Euclidean distance between input vectors
        :rtype: float
        """
        assert len(a) == len(b)
        distance = 0

        for dimension in zip(a, b):
            distance += pow(dimension[0] - dimension[1], 2)

        return math.sqrt(distance)