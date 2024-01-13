"""
Extra functions.

"""


def reverse_ordering(ordering_tuple: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(("-" + item) if not item.startswith("-") else item[1:] for item in ordering_tuple)
