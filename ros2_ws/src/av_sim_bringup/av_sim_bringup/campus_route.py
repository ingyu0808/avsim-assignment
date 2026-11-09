"""Directed road-graph routing and right-hand lane paths in ROS map coordinates."""

import json
import math

import cv2
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra


def xyz(point):
    return np.array([point[k] for k in ("x", "y", "z")], dtype=float)


def load_map(path):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


class RoadSurface:
    """Signed clearance to the generated asphalt boundaries, including islands."""
    def __init__(self, data):
        self.polygons = [np.array([xyz(v)[:2] for v in surface["points"]], np.float32)
                         for surface in data["surfaces"]]
        self.signs = [1 if cv2.contourArea(p, oriented=True) > 0 else -1 for p in self.polygons]

    def clearance(self, position):
        distances = [cv2.pointPolygonTest(p, tuple(map(float, position[:2])), True) for p in self.polygons]
        inside = sum(sign for sign, distance in zip(self.signs, distances) if distance >= 0) > 0
        return min(map(abs, distances)) * (1 if inside else -1)


def campus_lap(data, corner_trim=6.0):
    nodes, lookup, edges, widths = [], {}, {}, {}
    for road in data["roads"]:
        ids = []
        for point in road["points"]:
            p = xyz(point)[:2]
            key = tuple(np.round(p, 2))
            if key not in lookup:
                lookup[key] = len(nodes)
                nodes.append(p)
            ids.append(lookup[key])
        for a, b in zip(ids, ids[1:]):
            if a == b:
                continue
            distance = float(np.linalg.norm(nodes[b] - nodes[a]))
            for u, v in ([(a, b)] if road["oneWay"] else [(a, b), (b, a)]):
                edges[u, v] = distance
                widths[u, v] = 0.0 if road["oneWay"] else road["width"] / 4
    points = np.array(nodes)
    rows, cols = zip(*edges)
    graph = csr_matrix((list(edges.values()), (rows, cols)), shape=(len(nodes), len(nodes)))
    # Gate, divided entrance avenue, administration/lake, south road, east road, gate.
    anchors_xz = [(194.29, 393.34), (131.11, 359.8), (-89.1, 247.11),
                  (-242.71, 164.11), (-8.97, -288.35), (362.37, -91.81),
                  (131.11, 359.8), (194.29, 393.34)]
    anchors = [int(np.argmin(np.linalg.norm(points - [z, -x], axis=1))) for x, z in anchors_xz]
    chain = [anchors[0]]
    for start, goal in zip(anchors, anchors[1:]):
        distances, predecessors = dijkstra(graph, directed=True, indices=start, return_predecessors=True)
        if not math.isfinite(distances[goal]):
            raise ValueError(f"Campus route disconnected at {start} -> {goal}")
        segment = [goal]
        while segment[-1] != start:
            segment.append(int(predecessors[segment[-1]]))
        chain.extend(reversed(segment[:-1]))
    centers = points[chain]
    tangents = np.diff(centers, axis=0)
    tangents /= np.linalg.norm(tangents, axis=1)[:, None]
    offsets = np.array([widths[a, b] for a, b in zip(chain, chain[1:])])
    right = np.column_stack((tangents[:, 1], -tangents[:, 0]))
    lane = [centers[0] + right[0] * offsets[0]]
    for i in range(1, len(centers) - 1):
        normals = right[i - 1] + right[i]
        normal = normals / max(np.linalg.norm(normals), 1e-6)
        offset = (offsets[i - 1] + offsets[i]) / 2
        lane.append(centers[i] + normal * offset / max(0.5, np.dot(normal, right[i])))
    lane.append(centers[-1] + right[-1] * offsets[-1])
    # OSM includes short, collinear survey segments next to junctions. Retaining
    # them artificially restricts the turn radius to a fraction of those lengths.
    lane = cv2.approxPolyDP(np.array(lane, dtype=np.float32), 0.2, False).reshape(-1, 2).astype(float)
    # Round turns with tangent-continuous quadratic segments, then sample by distance.
    rounded = [lane[0]]
    for i in range(1, len(lane) - 1):
        before, after = lane[i] - lane[i - 1], lane[i + 1] - lane[i]
        lb, la = np.linalg.norm(before), np.linalg.norm(after)
        trim = min(corner_trim, lb * 0.35, la * 0.35)
        a, b = lane[i] - before / lb * trim, lane[i] + after / la * trim
        for t in np.linspace(0, 1, max(3, int(trim * 4))):
            rounded.append((1 - t) ** 2 * a + 2 * t * (1 - t) * lane[i] + t ** 2 * b)
    rounded.append(lane[-1])
    rounded = np.array(rounded)
    distance = np.r_[0, np.cumsum(np.linalg.norm(np.diff(rounded, axis=0), axis=1))]
    samples = np.arange(0, distance[-1], 0.5)
    path = np.column_stack([np.interp(samples, distance, rounded[:, k]) for k in range(2)])
    spawn = xyz(data["spawn"])[:2]
    first = np.argmin(np.linalg.norm(path[:100] - spawn, axis=1))
    last = len(path) - 100 + np.argmin(np.linalg.norm(path[-100:] - spawn, axis=1))
    path = path[first:last + 1]
    return path


class RouteTracker:
    def __init__(self, points):
        self.points = np.asarray(points, dtype=float)
        self.s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(self.points, axis=0), axis=1))]
        self.index = 0

    def update(self, position):
        lo, hi = max(0, self.index - 4), min(len(self.points), self.index + 60)
        index = lo + int(np.argmin(np.linalg.norm(self.points[lo:hi] - position[:2], axis=1)))
        self.index = max(self.index, index)
        return float(np.linalg.norm(self.points[self.index] - position[:2]))

    def pursuit(self, position, yaw, speed, lookahead=None):
        if lookahead is None:
            lookahead = float(np.clip(2.5 + abs(speed) * 0.35, 3.0, 4.5))
        target_index = min(len(self.points) - 1, np.searchsorted(self.s, self.s[self.index] + lookahead))
        rear_axle = position[:2] - 1.25 * np.array([math.cos(yaw), math.sin(yaw)])
        delta = self.points[target_index] - rear_axle
        lateral = -math.sin(yaw) * delta[0] + math.cos(yaw) * delta[1]
        curvature = 2 * lateral / max(float(np.dot(delta, delta)), 1.0)
        return math.atan(2.5 * curvature), self.points[target_index], curvature

    @property
    def remaining(self):
        return float(self.s[-1] - self.s[self.index])

    def signal_stops(self, data):
        stops = []
        for signal in data["signals"]:
            stop = xyz(signal["stop"])[:2]
            distances = np.linalg.norm(self.points - stop, axis=1)
            for i in range(1, len(self.points) - 1):
                if distances[i] > 2.2 or distances[i] > min(distances[i - 1], distances[i + 1]):
                    continue
                tangent = self.points[i + 1] - self.points[i - 1]
                tangent /= np.linalg.norm(tangent)
                if np.dot(tangent, xyz(signal["facing"])[:2]) < -0.7:
                    stops.append(dict(signal, route_s=float(self.s[i])))
        return sorted(stops, key=lambda stop: stop["route_s"])
