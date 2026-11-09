"""Export the campus lap for Unity scenario placement (Unity xz coordinates)."""

import numpy as np

from .campus_route import RouteTracker, campus_lap, xyz


def unity(point):
    """ROS map (x=north, y=west) to Unity xz."""
    return {"x": round(float(-point[1]), 2), "y": round(float(point[0]), 2)}


def nearest_road(data, points):
    """Closest centerline point and half width of any road segment for each point."""
    starts, ends, halves = [], [], []
    for road in data["roads"]:
        line = np.array([xyz(p)[:2] for p in road["points"]])
        starts.extend(line[:-1])
        ends.extend(line[1:])
        halves.extend([road["width"] / 2] * (len(line) - 1))
    a, b, halves = np.array(starts), np.array(ends), np.array(halves)
    d = b - a
    lengths = np.maximum((d ** 2).sum(axis=1), 1e-9)
    centers, widths = [], []
    for p in points:
        t = np.clip(((p - a) * d).sum(axis=1) / lengths, 0, 1)
        closest = a + d * t[:, None]
        i = int(np.argmin(np.linalg.norm(closest - p, axis=1)))
        centers.append(closest[i])
        widths.append(float(halves[i]))
    return centers, widths


def straight_spans(points, s, turn=0.03, minimum=60.0):
    heading = np.arctan2(*np.diff(points, axis=0).T[::-1])
    change = np.abs(np.angle(np.exp(1j * np.diff(heading))))
    spans, start = [], 0
    for i, value in enumerate(change):
        if value > turn:
            if s[i] - s[start] > minimum:
                spans.append({"start": round(float(s[start]), 2), "end": round(float(s[i]), 2)})
            start = i + 1
    if s[-1] - s[start] > minimum:
        spans.append({"start": round(float(s[start]), 2), "end": round(float(s[-1]), 2)})
    return spans


def export_route(data, step=1.0):
    tracker = RouteTracker(campus_lap(data))
    samples = np.arange(0, tracker.s[-1], step)
    points = np.column_stack([np.interp(samples, tracker.s, tracker.points[:, k]) for k in range(2)])
    centers, halves = nearest_road(data, points)
    signals = []
    for stop in tracker.signal_stops(data):
        crossing = xyz(stop["crossing"])[:2]
        after = tracker.s >= stop["route_s"]
        index = np.flatnonzero(after)[np.argmin(np.linalg.norm(tracker.points[after] - crossing, axis=1))]
        signals.append({"id": stop["id"], "stopS": round(stop["route_s"], 2),
                        "crossS": round(float(tracker.s[index]), 2)})
    return {
        "length": round(float(tracker.s[-1]), 2),
        "points": [unity(p) for p in points],
        "roadCenters": [unity(c) for c in centers],
        "roadHalfWidths": [round(w, 2) for w in halves],
        "signals": signals,
        "straights": straight_spans(tracker.points, tracker.s),
    }
