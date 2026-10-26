"""Pure password comparison functions; inputs are exact Unicode strings."""


def levenshtein_distance(first, second):
    """Unit-cost insertions, deletions and substitutions, O(min(n, m)) memory."""
    if len(first) < len(second):
        first, second = second, first
    previous = list(range(len(second) + 1))
    for row, left in enumerate(first, start=1):
        current = [row]
        for column, right in enumerate(second, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (left != right),
                )
            )
        previous = current
    return previous[-1]
