import numpy as np

# smooth value noise, works on numbers or whole numpy arrays

_p = np.random.default_rng(7).permutation(256)
_P = np.concatenate([_p, _p])


def _hash(x, y, z):
    return _P[(_P[(_P[x & 255] + y) & 255] + z) & 255] / 255.0


def noise3(x, y, z):
    """noise in -1..1"""
    x, y, z = (np.asarray(v, np.float64) for v in (x, y, z))
    xi, yi, zi = (np.floor(v).astype(np.int64) for v in (x, y, z))
    u, v, w = ((t - np.floor(t)) for t in (x, y, z))
    u, v, w = (t * t * (3 - 2 * t) for t in (u, v, w))  # smooth the steps

    def lerp(a, b, t):
        return a + (b - a) * t

    a = lerp(lerp(_hash(xi, yi, zi), _hash(xi + 1, yi, zi), u),
             lerp(_hash(xi, yi + 1, zi), _hash(xi + 1, yi + 1, zi), u), v)
    b = lerp(lerp(_hash(xi, yi, zi + 1), _hash(xi + 1, yi, zi + 1), u),
             lerp(_hash(xi, yi + 1, zi + 1), _hash(xi + 1, yi + 1, zi + 1), u), v)
    return lerp(a, b, w) * 2 - 1


def fbm(x, y, z, octaves=3):
    """a few layers of noise, each smaller and quieter"""
    total, amp = 0.0, 0.5
    for i in range(octaves):
        total = total + amp * noise3(x * 2 ** i, y * 2 ** i, z * 2 ** i)
        amp *= 0.5
    return total


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)
