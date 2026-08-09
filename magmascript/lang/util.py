from __future__ import annotations


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    a_len, b_len = len(a), len(b)
    matrix = [[0] * (b_len + 1) for _ in range(a_len + 1)]

    for i in range(a_len + 1):
        matrix[i][0] = i
    for j in range(b_len + 1):
        matrix[0][j] = j

    for i in range(1, a_len + 1):
        for j in range(1, b_len + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j - 1] + cost,
            )

    return matrix[a_len][b_len]


def suggest(name: str, candidates: list[str], max_distance: int = 2) -> str | None:
    best: str | None = None
    best_distance = max_distance + 1

    for candidate in candidates:
        d = levenshtein(name.lower(), candidate.lower())
        if d < best_distance:
            best_distance = d
            best = candidate

    if best_distance <= max_distance:
        return best
    return None
