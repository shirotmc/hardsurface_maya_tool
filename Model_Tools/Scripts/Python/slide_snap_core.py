# -*- coding: utf-8 -*-
"""
Slide Snap - geometry core (pure Python, no Maya import, so it can be unit tested anywhere).

A vertex P slides along a LINE (an edge direction, a world axis or the face normal) until it meets the
target face. The face is described by its polygon (list of world space points):

  * plane of the face  = Newell normal + centroid (works for non planar quads too: average plane)
  * "face" mode        = the hit point must lie inside the polygon (boundary tolerance applies)
  * "plane" mode       = the hit point may lie anywhere on the infinite plane of the face
"""
INF = float('inf')
PARALLEL_EPS = 1e-7


#----------------------------------------------------------------------------- vector helpers

def sub(a, b):
	return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def add(a, b):
	return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def mul(a, s):
	return (a[0] * s, a[1] * s, a[2] * s)


def dot(a, b):
	return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def length(a):
	return dot(a, a) ** 0.5


def normalize(a):
	l = length(a)
	if l < 1e-12:
		return None
	return (a[0] / l, a[1] / l, a[2] / l)


#----------------------------------------------------------------------------- face

def polygon_plane(points):
	"""(centroid, unit normal) of a polygon. normal is None when the polygon is degenerate."""
	n = len(points)
	if n < 3:
		return None, None
	nx = ny = nz = 0.0
	for i in range(n):
		p = points[i]
		q = points[(i + 1) % n]
		nx += (p[1] - q[1]) * (p[2] + q[2])
		ny += (p[2] - q[2]) * (p[0] + q[0])
		nz += (p[0] - q[0]) * (p[1] + q[1])
	centroid = (sum(p[0] for p in points) / n, sum(p[1] for p in points) / n, sum(p[2] for p in points) / n)
	return centroid, normalize((nx, ny, nz))


def polygon_tolerance(points):
	"""Distance tolerance relative to the size of the polygon."""
	xs = [p[0] for p in points]
	ys = [p[1] for p in points]
	zs = [p[2] for p in points]
	diag = ((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2 + (max(zs) - min(zs)) ** 2) ** 0.5
	return max(1e-6, diag * 1e-4)


def point_segment_distance(p, a, b):
	ab = sub(b, a)
	t = dot(sub(p, a), ab) / max(dot(ab, ab), 1e-18)
	t = min(max(t, 0.0), 1.0)
	return length(sub(p, add(a, mul(ab, t))))


def point_in_polygon(point, poly, normal, tol):
	"""Point (already on the polygon plane) inside the polygon? Works for concave polygons."""
	n = len(poly)
	for i in range(n):
		if point_segment_distance(point, poly[i], poly[(i + 1) % n]) <= tol:
			return True          # on the border counts as inside
	axis = max(range(3), key=lambda k: abs(normal[k]))     # drop the dominant axis -> 2D test
	u, v = [k for k in range(3) if k != axis]
	x, y = point[u], point[v]
	inside = False
	j = n - 1
	for i in range(n):
		xi, yi = poly[i][u], poly[i][v]
		xj, yj = poly[j][u], poly[j][v]
		if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
			inside = not inside
		j = i
	return inside


#----------------------------------------------------------------------------- candidate lines
# A candidate is (unit direction, t_min, t_max): the vertex may move to  P + direction * t,  t in [t_min, t_max].

def edge_candidates(p, neighbors, both=True, keep_on_edge=False):
	"""One candidate per edge of the vertex. neighbors = positions of the vertices at the other end."""
	out = []
	for q in neighbors:
		v = sub(q, p)
		l = length(v)
		if l < 1e-9:
			continue
		d = mul(v, 1.0 / l)
		if keep_on_edge:
			out.append((d, 0.0, l))          # only the edge itself
		elif both:
			out.append((d, -INF, INF))       # the whole line through the edge
		else:
			out.append((d, 0.0, INF))        # from the vertex towards (and beyond) the other end
	return out


def line_candidate(direction):
	"""World axis / face normal: the vertex may go either way, the nearest hit wins."""
	return [(direction, -INF, INF)]


#----------------------------------------------------------------------------- solve

REASON_PARALLEL = 'parallel to the face'
REASON_RANGE = 'face is not reachable along the edge'
REASON_OUTSIDE = 'hit point is outside the face'
REASON_DISTANCE = 'farther than Max Distance'
REASON_NO_LINE = 'no direction to slide along'


def solve_vertex(p, candidates, centroid, normal, poly, use_face=True, max_dist=0.0, tol=1e-6):
	"""Best hit of the vertex P against the face.

	Returns (hit_point, t, None) on success, or (None, None, reason) when the vertex cannot be snapped.
	The candidate with the smallest |t| wins (the closest way to the face)."""
	if not candidates:
		return None, None, REASON_NO_LINE
	best = None
	seen = {'nonparallel': False, 'in_range': False, 'far': False, 'outside': False}
	to_plane = dot(normal, sub(centroid, p))
	for d, t_min, t_max in candidates:
		denom = dot(normal, d)
		if abs(denom) < PARALLEL_EPS:
			continue
		seen['nonparallel'] = True
		t = to_plane / denom
		if t < t_min - tol or t > t_max + tol:
			continue
		seen['in_range'] = True
		if max_dist > 0 and abs(t) > max_dist:
			seen['far'] = True
			continue
		hit = add(p, mul(d, t))
		if use_face and not point_in_polygon(hit, poly, normal, tol):
			seen['outside'] = True
			continue
		if best is None or abs(t) < abs(best[1]):
			best = (hit, t)
	if best:
		return best[0], best[1], None
	if not seen['nonparallel']:
		return None, None, REASON_PARALLEL
	if not seen['in_range']:
		return None, None, REASON_RANGE
	if seen['outside']:
		return None, None, REASON_OUTSIDE
	return None, None, REASON_DISTANCE
