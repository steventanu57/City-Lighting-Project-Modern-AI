import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import Delaunay, ConvexHull


def generate_cities(n, seed=42):
    """Generate n random cities on a 2D map."""
    if n < 1:
        raise ValueError("n must be at least 1")

    rng = np.random.default_rng(seed)
    return rng.random((n, 2))


def generate_roads(cities):
    """Generate non-crossing roads using Delaunay triangulation."""
    n = len(cities)

    if n == 1:
        return set()

    if n == 2:
        return {(0, 1)}

    triangulation = Delaunay(cities)
    roads = set()

    for triangle in triangulation.simplices:
        a, b, c = map(int, triangle)

        roads.add(tuple(sorted((a, b))))
        roads.add(tuple(sorted((b, c))))
        roads.add(tuple(sorted((a, c))))

    return roads


def build_adjacency(n, roads):
    """Build a list of neighbouring cities."""
    adjacency = [set() for _ in range(n)]

    for a, b in roads:
        adjacency[a].add(b)
        adjacency[b].add(a)

    return adjacency


def plot_map(cities, roads, title="Blank City Map"):
    """Plot cities and roads without colours assigned."""
    fig, ax = plt.subplots(figsize=(8, 7))

    for a, b in roads:
        ax.plot(
            [cities[a, 0], cities[b, 0]],
            [cities[a, 1], cities[b, 1]],
            color="gray",
            linewidth=1,
            zorder=1,
        )

    ax.scatter(
        cities[:, 0],
        cities[:, 1],
        color="black",
        s=35,
        zorder=2,
    )

    for i, (x, y) in enumerate(cities):
        ax.annotate(
            str(i),
            (x, y),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=8,
        )

    ax.set_title(title)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.set_aspect("equal")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    plt.tight_layout()
    plt.show()


def validate_map(cities, roads, adjacency):
    """Check basic graph and triangulation properties."""
    n = len(cities)

    # 1. Every city must be represented.
    assert n >= 1, "Map must contain at least one city."

    # 2. Adjacency must be symmetric.
    for a, b in roads:
        assert b in adjacency[a], f"Missing neighbour {b} for city {a}"
        assert a in adjacency[b], f"Missing neighbour {a} for city {b}"

    # 3. Every road must connect two distinct valid cities.
    for a, b in roads:
        assert 0 <= a < n and 0 <= b < n, "Invalid city index"
        assert a != b, "Road cannot connect a city to itself"

    # 4. Check expected edge count for a triangulation.
    if n >= 3:
        hull = ConvexHull(cities)
        h = len(hull.vertices)
        expected_edges = 3 * n - 3 - h

        assert len(roads) == expected_edges, (
            f"Expected {expected_edges} roads, got {len(roads)}"
        )

    print("Basic map validation passed!")


def main():
    n = int(input("Masukkan jumlah kota n: "))

    cities = generate_cities(n, seed=42)
    roads = generate_roads(cities)
    adjacency = build_adjacency(n, roads)
    validate_map(cities, roads, adjacency)

    print(f"Jumlah kota : {len(cities)}")
    print(f"Jumlah jalan: {len(roads)}")
    print(f"Total tetangga: {sum(map(len, adjacency))}")

    plot_map(cities, roads, f"Blank City Map (n={n})")


if __name__ == "__main__":
    main()
