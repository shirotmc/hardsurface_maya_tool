"""
HS ReBevel Tool for Maya
========================
Port of the Blender hardsurface_blender_tool  TMC_OP_Unbevel (tmc.re_bevel) operator.

WHAT IT DOES
------------
Detects an existing bevel ring (the mesh strip created by a previous bevel operation),
reconstructs the original sharp-corner point ("bevel target"), and lets you:
  • Resize the bevel (drag mouse left/right, or use the Size slider)
  • Reshape the bevel profile (Tension slider: 0 = flat chamfer, 0.5 = circle, 1 = sharp)
  • Resize mode: Uniform (all rings scale evenly) or Proportional (relative to ring width)

USAGE
-----
  1. Select a mesh object in Maya.
  2. Enter Edge Component mode  (F10 / right-click > Edge).
  3. Select ALL edges that span the bevel face strip
     (the cross-edges between the two bevel edge-loops, NOT the loops themselves).
  4. Run from the Script Editor:
         import hs_rebevel_maya; hs_rebevel_maya.run()
  5. Use the floating HS ReBevel window:
       • Drag mouse in viewport to resize (Size changes live).
       • Adjust the Size / Tension sliders.
       • Click Apply to commit, Cancel to revert.

REQUIREMENTS
------------
  Maya 2020+ (uses OpenMaya API 2 / maya.api.OpenMaya).

UNDO
----
  The tool wraps its final result in a single undo chunk; pressing Ctrl+Z once
  reverts the full rebevel.  Cancel reverts immediately without touching the undo queue.
"""

import math
from copy import deepcopy

import maya.cmds as cmds
import maya.api.OpenMaya as om

# ─────────────────────────────────────────────────────────────────────────────
# Math helpers  (all operate on om.MVector unless stated otherwise)
# ─────────────────────────────────────────────────────────────────────────────

def _lerp(a, b, t):
    """Scalar lerp."""
    return a + (b - a) * t


def _lerp_v(a, b, t):
    """Vector lerp: returns om.MVector."""
    return om.MVector(
        a.x + (b.x - a.x) * t,
        a.y + (b.y - a.y) * t,
        a.z + (b.z - a.z) * t,
    )


def _reflect_point_across_line(v1, v2, pt):
    """Reflect pt across the infinite line defined by v1 → v2."""
    d = (v2 - v1)
    length = d.length()
    if length < 1e-10:
        return om.MVector(pt)
    d.normalize()
    v1_pt = pt - v1
    parallel = d * (d * v1_pt)
    perp = v1_pt - parallel
    return v1 + parallel - perp


# ── Plane / line intersections ──────────────────────────────────────────────

def _intersect_plane_plane(pt1, n1, pt2, n2):
    """
    Intersection of two planes.
    Returns (point_on_line, unit_direction) or (None, None) if parallel.
    """
    line_dir = n1 ^ n2         # cross product  (om.MVector ^ om.MVector)
    if line_dir.length() < 1e-8:
        return None, None
    line_dir.normalize()
    d1 = n1 * pt1              # dot
    d2 = n2 * pt2
    # Compute a point on both planes
    n12 = n1 ^ n2
    denom = n12 * n12
    if abs(denom) < 1e-8:
        return None, None
    pt = ((n2 ^ line_dir) * d1 + (line_dir ^ n1) * d2) / denom
    return pt, line_dir


def _intersect_line_plane(ray_pt, ray_dir, plane_pt, plane_n):
    """Ray-plane intersection.  Returns om.MVector or None if parallel."""
    denom = plane_n * ray_dir
    if abs(denom) < 1e-8:
        return None
    t = ((plane_pt - ray_pt) * plane_n) / denom
    return ray_pt + ray_dir * t


def _closest_point_on_line(point, line_pt, line_dir):
    """Project `point` onto an infinite line.  Returns om.MVector."""
    if line_dir.length() < 1e-10:
        return om.MVector(line_pt)
    t = ((point - line_pt) * line_dir) / (line_dir * line_dir)
    return line_pt + line_dir * t


# ── Bevel profile (super-ellipse) ────────────────────────────────────────────

def _interp1d(t, xp, fp):
    """Simple piecewise-linear 1-D interpolation (replaces numpy.interp)."""
    if t <= xp[0]:
        return fp[0]
    if t >= xp[-1]:
        return fp[-1]
    for i in range(len(xp) - 1):
        if xp[i] <= t <= xp[i + 1]:
            r = (t - xp[i]) / (xp[i + 1] - xp[i])
            return fp[i] + (fp[i + 1] - fp[i]) * r
    return fp[-1]


def _super_elipse2(tension, segments):
    """
    Generate `segments` normalized profile points in the unit corner space
    ( a10=(1,0,0), a01=(0,1,0), a11=(1,1,0) ).

    Mirrors Blender's  super_elipse2()  in rebevel.py:
      tension  0  → flat chamfer
      tension  0.5 → circular arc  (default)
      tension  1  → sharp V corner
      tension <0  → concave arc
    """
    if segments < 2:
        return [om.MVector(1, 0, 0), om.MVector(0, 1, 0)]

    t_abs = abs(tension)

    # ── sharp corner ─────────────────────────────────────────────────────────
    if t_abs >= 1.0:
        pts = []
        for i in range(segments):
            t = i / (segments - 1)
            if t < 0.5:
                x = 1.0
                y = _lerp(0.0, 1.0, t * 2)
            else:
                x = _lerp(1.0, 0.0, (t - 0.5) * 2)
                y = 1.0
            pts.append(om.MVector(x, y, 0))
        return pts

    # ── flat chamfer ↔ circular arc  (tension in [0, 0.5]) ──────────────────
    if t_abs < 0.5:
        flat   = [om.MVector(_lerp(1, 0, i / (segments - 1)),
                             _lerp(0, 1, i / (segments - 1)), 0)
                  for i in range(segments)]
        circle = [om.MVector(math.cos(math.pi / 2 * i / (segments - 1)),
                             math.sin(math.pi / 2 * i / (segments - 1)), 0)
                  for i in range(segments)]
        blend  = t_abs * 2
        pts    = [om.MVector(_lerp(f.x, c.x, blend),
                             _lerp(f.y, c.y, blend), 0)
                  for f, c in zip(flat, circle)]
        if tension < 0:                        # concave: swap x ↔ y
            pts = [om.MVector(p.y, p.x, 0) for p in pts]
        return pts

    # ── super-ellipse  (tension in (0.5, 1.0)) ──────────────────────────────
    n_pow      = 2 * t_abs + 1 + (2 ** ((t_abs - 0.5) * 10)) - 1
    half_seg   = max(segments // 2 + 1, 2)
    max_range  = math.pi / 4

    first_pass = []
    for i in range(half_seg):
        t       = i / (half_seg - 1)
        t_remap = max_range * (t ** (n_pow / 2))
        first_pass.append(om.MVector(
            math.cos(t_remap) ** (2 / n_pow),
            math.sin(t_remap) ** (2 / n_pow),
            0,
        ))

    # Mirror (0°→45°) to (45°→90°)
    full_pass = list(first_pass)
    for i in range(len(first_pass) - 2, -1, -1):
        p = first_pass[i]
        full_pass.append(om.MVector(p.y, p.x, 0))

    # Resample to exactly `segments` points
    xp_src  = [i / (len(full_pass) - 1) for i in range(len(full_pass))]
    xp_dst  = [i / (segments - 1)       for i in range(segments)]
    xs_src  = [p.x for p in full_pass]
    ys_src  = [p.y for p in full_pass]

    pts = [om.MVector(_interp1d(t, xp_src, xs_src),
                      _interp1d(t, xp_src, ys_src), 0)
           for t in xp_dst]

    if tension < 0:                            # concave
        pts = [om.MVector(p.y, p.x, 0) for p in pts]
    return pts


def _barycentric_transform(elips_pt, v1, bevel_t, v2):
    """
    Map a normalized profile point (from super_elipse2 – lives in the
    reference triangle  a10=(1,0), a11=(1,1), a01=(0,1) ) into world space.

    Mirrors Blender's  mathutils.geometry.barycentric_transform()  call in
    rebevel.py with fixed src triangle (a10, a11, a01).

    Ref tri  (1,0)*w1 + (1,1)*w2 + (0,1)*w3 = (ex, ey) :
        w2 = ex + ey - 1
        w1 = ex - w2
        w3 = ey - w2
    """
    ex, ey = elips_pt.x, elips_pt.y
    w2 = ex + ey - 1.0
    w1 = ex - w2
    w3 = ey - w2
    return v1 * w1 + bevel_t * w2 + v2 * w3


def _get_bevel_pts(bevel_target, v1, v2, tension, n_verts):
    """
    Return `n_verts` world-space positions that form the bevel profile
    from v1 to v2, curving toward bevel_target with the given tension.
    (Includes boundary verts v1 and v2 at index 0 and -1.)
    """
    normalized = _super_elipse2(tension, n_verts)
    if tension < 0:
        bt = _reflect_point_across_line(v1, v2, bevel_target)
    else:
        bt = bevel_target
    return [_barycentric_transform(p, v1, bt, v2) for p in normalized]


# ─────────────────────────────────────────────────────────────────────────────
# Maya mesh utilities  (OpenMaya API 2)
# ─────────────────────────────────────────────────────────────────────────────

def _dag_and_fn(mesh_name):
    """Return (MDagPath, MFnMesh) for a mesh shape node name."""
    sel = om.MSelectionList()
    sel.add(mesh_name)
    dag = sel.getDagPath(0)
    return dag, om.MFnMesh(dag)


def _vert_world_pos(fn, vid):
    pt = fn.getPoint(vid, om.MSpace.kWorld)
    return om.MVector(pt.x, pt.y, pt.z)


def _set_vert_world_pos(fn, vid, v):
    fn.setPoint(vid, om.MPoint(v.x, v.y, v.z), om.MSpace.kWorld)


def _edge_verts(fn, eid):
    vts = fn.getEdgeVertices(eid)
    return int(vts[0]), int(vts[1])


def _face_normal_world(fn, fid):
    it = om.MItMeshPolygon(fn.dagPath())
    it.setIndex(fid)
    n = it.getNormal(om.MSpace.kWorld)
    return om.MVector(n.x, n.y, n.z)


def _vert_face_ids(fn, vid):
    it = om.MItMeshVertex(fn.dagPath())
    it.setIndex(vid)
    return list(it.getConnectedFaces())


# ─────────────────────────────────────────────────────────────────────────────
# Edge strip sorting
# Ports  TMC_OP_Unbevel.my_get_sorted_loops()  from rebevel.py
# ─────────────────────────────────────────────────────────────────────────────

def _sort_edge_strips(fn, selected_edge_ids):
    """
    Arrange selected edges into ordered, continuous strips.

    Each strip is one "column" across the bevel face:
        vert_strip[0]  →  vert_strip[-1]   (boundary ↔ boundary)

    Returns (list_of_vert_strips, list_of_edge_strips).
    """
    # Build vertex → [adjacent selected edges] mapping
    vert_to_edges = {}
    for eid in selected_edge_ids:
        v0, v1 = _edge_verts(fn, eid)
        for v in (v0, v1):
            vert_to_edges.setdefault(v, []).append(eid)

    remaining = set(selected_edge_ids)
    vert_strips = []
    edge_strips = []

    while remaining:
        seed = next(iter(remaining))
        remaining.discard(seed)

        cur_v_strip = []
        cur_e_strip = [seed]
        sv0, sv1 = _edge_verts(fn, seed)

        def _follow(toward_v, from_v, append_right):
            """Walk the chain in one direction, extending the strip."""
            curr_v = toward_v
            while True:
                if append_right:
                    cur_v_strip.append(curr_v)
                else:
                    cur_v_strip.insert(0, curr_v)

                # Next selected edge from curr_v that we have not yet visited
                ref_edge = cur_e_strip[-1] if append_right else cur_e_strip[0]
                nxt = [e for e in vert_to_edges.get(curr_v, [])
                       if e != ref_edge and e in remaining]
                if not nxt:
                    break

                next_edge = nxt[0]
                remaining.discard(next_edge)
                if append_right:
                    cur_e_strip.append(next_edge)
                else:
                    cur_e_strip.insert(0, next_edge)

                nv0, nv1 = _edge_verts(fn, next_edge)
                curr_v = nv1 if nv0 == curr_v else nv0

        _follow(sv0, sv1, False)   # extend left
        _follow(sv1, sv0, True)    # extend right

        vert_strips.append(cur_v_strip)
        edge_strips.append(cur_e_strip)

    return vert_strips, edge_strips


def _orient_strips(fn, vert_strips, edge_strips):
    """
    Make parallel bevel-ring strips point in the same direction.
    Ports  TMC_OP_Unbevel.sort_loops_by_first_vert().

    Uses the quad-face topology: the ring-adjacent vertex of strip[0]
    in the next strip should be that strip's strip[0].
    """
    if len(vert_strips) <= 1:
        return vert_strips, edge_strips

    all_strip_verts = {v for s in vert_strips for v in s}

    def _ring_adj(v, edge_in_strip):
        """
        Find the vertex directly across the bevel quad from v
        (across a non-selected edge, through a quad face).
        """
        adj = []
        it_e = om.MItMeshEdge(fn.dagPath())
        it_e.setIndex(edge_in_strip)
        for fid in it_e.getConnectedFaces():
            it_p = om.MItMeshPolygon(fn.dagPath())
            it_p.setIndex(fid)
            fverts = list(it_p.getVertices())
            if len(fverts) != 4 or v not in fverts:
                continue
            opp = fverts[(fverts.index(v) + 2) % 4]
            if opp in all_strip_verts:
                adj.append(opp)
        return adj

    sorted_v = [vert_strips[0]]
    sorted_e = [edge_strips[0]]
    rem_v    = list(vert_strips[1:])
    rem_e    = list(edge_strips[1:])

    # Two passes: extend right, then left
    for go_right in (True, False):
        anchor_strip = sorted_v[-1] if go_right else sorted_v[0]
        anchor_edge  = sorted_e[-1] if go_right else sorted_e[0]
        adj_v = _ring_adj(anchor_strip[0], anchor_edge[0])
        curr  = adj_v[0] if adj_v else None

        while curr is not None and rem_v:
            found = None
            for idx, rstrip in enumerate(rem_v):
                rev = False
                if curr == rstrip[0]:
                    found = idx
                elif curr == rstrip[-1]:
                    found = idx
                    rev   = True
                if found is not None:
                    vs = rem_v.pop(found)
                    es = rem_e.pop(found)
                    if rev:
                        vs, es = vs[::-1], es[::-1]
                    if go_right:
                        sorted_v.append(vs)
                        sorted_e.append(es)
                    else:
                        sorted_v.insert(0, vs)
                        sorted_e.insert(0, es)
                    nxt_adj = _ring_adj(curr, es[0])
                    curr    = nxt_adj[0] if nxt_adj else None
                    break
            else:
                break

    sorted_v.extend(rem_v)
    sorted_e.extend(rem_e)
    return sorted_v, sorted_e


# ─────────────────────────────────────────────────────────────────────────────
# Bevel target calculation
# Ports the bevel_target_pts section of  TMC_OP_Unbevel.rebevel()
# ─────────────────────────────────────────────────────────────────────────────

def _calc_bevel_target(fn, v1_id, v2_id, vert_strip):
    """
    Reconstruct the original sharp corner ("bevel target") for one bevel ring.

    Strategy (identical to Blender):
      1. Gather faces adjacent to v1 and v2 that are NOT shared with the
         inner-neighbour verts (i.e. the non-bevel faces).
      2. Collect up to 3 non-coplanar planes from those faces.
      3. Intersect planes:
           3 planes → exact point  (best case)
           2 planes → project mid-point onto plane×plane line
           1 plane  → project mid-point onto that plane
           0 planes → midpoint of v1,v2  (fallback)
    """
    v1_co = _vert_world_pos(fn, v1_id)
    v2_co = _vert_world_pos(fn, v2_id)

    # Inner neighbours to avoid picking the bevel face itself
    v1_neib = vert_strip[1]  if len(vert_strip) > 2 else v2_id
    v2_neib = vert_strip[-2] if len(vert_strip) > 2 else v1_id

    v1_faces  = set(_vert_face_ids(fn, v1_id))
    v2_faces  = set(_vert_face_ids(fn, v2_id))
    v1n_faces = set(_vert_face_ids(fn, v1_neib))
    v2n_faces = set(_vert_face_ids(fn, v2_neib))

    candidates = (
        [{'vid': v1_id, 'co': v1_co, 'fid': f} for f in v1_faces if f not in v1n_faces] +
        [{'vid': v2_id, 'co': v2_co, 'fid': f} for f in v2_faces if f not in v2n_faces]
    )

    cross_planes = []
    for cand in candidates:
        n = _face_normal_world(fn, cand['fid'])
        if not any(abs(p['n'] * n) > 0.98 for p in cross_planes):   # skip coplanar
            cross_planes.append({'n': n, 'co': cand['co']})
        if len(cross_planes) >= 3:
            break

    avg = (v1_co + v2_co) * 0.5

    if not cross_planes:
        return avg

    if len(cross_planes) == 1:
        n    = cross_planes[0]['n']
        dist = (avg - cross_planes[0]['co']) * n
        return avg - n * dist

    line_pt, line_dir = _intersect_plane_plane(
        cross_planes[0]['co'], cross_planes[0]['n'],
        cross_planes[1]['co'], cross_planes[1]['n'],
    )

    if line_pt is None:
        return avg

    if len(cross_planes) >= 3:
        # 3 planes → exact point
        result = _intersect_line_plane(
            line_pt, line_dir,
            cross_planes[2]['co'], cross_planes[2]['n'],
        )
        return result if result is not None else _closest_point_on_line(avg, line_pt, line_dir)
    else:
        # 2 planes → closest point on line from midpoint
        return _closest_point_on_line(avg, line_pt, line_dir)


# ─────────────────────────────────────────────────────────────────────────────
# ReBevelState  –  all state for one interactive rebevel session
# ─────────────────────────────────────────────────────────────────────────────

class ReBevelState:
    """Encapsulates one interactive ReBevel session."""

    def __init__(self):
        self.mesh_shape    = None          # str  mesh shape node
        self.fn            = None          # MFnMesh
        self.vert_strips   = []            # [[vid, …], …]
        self.edge_strips   = []            # [[eid, …], …]
        self.bevel_targets = []            # [MVector, …]
        self.scale_factors = []            # [float, …]   (UNIFORM mode)
        self.orig_pos      = {}            # {vid: MVector}

        self.start_segments = 0
        self.rebevel_size   = 1.0
        self.segments       = 0
        self.tension        = 0.5
        self.resize_mode    = 'UNIFORM'    # 'UNIFORM' | 'PROP'

    # ── initialise ───────────────────────────────────────────────────────────

    def load(self, mesh_shape, selected_edge_ids):
        """
        Initialise from a mesh shape name and a list of integer edge IDs.
        Returns True on success.
        """
        self.mesh_shape = mesh_shape
        _, self.fn = _dag_and_fn(mesh_shape)

        vs, es = _sort_edge_strips(self.fn, selected_edge_ids)
        if not vs:
            return False

        vs, es = _orient_strips(self.fn, vs, es)

        self.vert_strips = vs
        self.edge_strips = es

        # Cache original vert positions
        for strip in vs:
            for vid in strip:
                if vid not in self.orig_pos:
                    self.orig_pos[vid] = _vert_world_pos(self.fn, vid)

        # Detect the current bevel segment count from the first strip
        self.start_segments = max(len(s) - 2 for s in vs) if vs else 0
        self.segments       = self.start_segments

        # Per-strip bevel targets
        self.bevel_targets = []
        for strip in vs:
            self.bevel_targets.append(
                _calc_bevel_target(self.fn, strip[0], strip[-1], strip)
            )

        # Scale factors for UNIFORM mode
        # (mirrors Blender: smaller bevel rings scale more slowly)
        sfs = []
        for strip, tgt in zip(vs, self.bevel_targets):
            v1c = self.orig_pos[strip[0]]
            v2c = self.orig_pos[strip[-1]]
            sf  = ((v1c - tgt).length + (v2c - tgt).length) * 0.5
            sfs.append(sf if sf > 1e-8 else 1.0)
        min_sf = min(sfs) if sfs else 1.0
        self.scale_factors = [s / (min_sf if min_sf > 1e-8 else 1.0) for s in sfs]

        return True

    # ── restore / apply ──────────────────────────────────────────────────────

    def restore(self):
        """Restore all cached vertices to their pre-tool positions."""
        for vid, pos in self.orig_pos.items():
            _set_vert_world_pos(self.fn, vid, pos)
        self.fn.updateSurface()

    def apply(self, rebevel_size=None, segments=None, tension=None, resize_mode=None):
        """
        Move bevel-ring vertices to the new size / shape.

        Mirrors the core of  TMC_OP_Unbevel.rebevel()  from rebevel.py.

        Parameters
        ----------
        rebevel_size : float
            1.0 = no change, 0.0 = collapse to corner, >1 = expand.
        segments     : int
            Number of inner vertices per strip  (topology NOT modified –
            inner verts are repositioned within the existing strip).
        tension      : float
            −1 → concave, 0 → flat, 0.5 → circular, 1 → sharp corner.
        resize_mode  : 'UNIFORM' | 'PROP'
        """
        if rebevel_size is None: rebevel_size = self.rebevel_size
        if segments    is None: segments     = self.segments
        if tension     is None: tension      = self.tension
        if resize_mode is None: resize_mode  = self.resize_mode

        for strip, tgt, sf in zip(self.vert_strips, self.bevel_targets, self.scale_factors):
            v1_id  = strip[0]
            v2_id  = strip[-1]
            v1_orig = self.orig_pos[v1_id]
            v2_orig = self.orig_pos[v2_id]

            if rebevel_size == 0.0:
                # Collapse the entire strip to the corner point
                for vid in strip:
                    _set_vert_world_pos(self.fn, vid, tgt)
                continue

            # ── Reposition boundary verts ────────────────────────────────
            # Blender (UNIFORM):
            #   targt = v.co.lerp(bevel_target, 1/sc_fac)
            #   v.co  = targt.lerp(v.co, reb_size)
            if resize_mode == 'UNIFORM':
                t_v1  = _lerp_v(v1_orig, tgt, 1.0 / sf)
                new_v1 = _lerp_v(t_v1,  v1_orig, rebevel_size)
                t_v2  = _lerp_v(v2_orig, tgt, 1.0 / sf)
                new_v2 = _lerp_v(t_v2,  v2_orig, rebevel_size)
            else:   # PROP
                new_v1 = _lerp_v(tgt, v1_orig, rebevel_size)
                new_v2 = _lerp_v(tgt, v2_orig, rebevel_size)

            # ── Reposition all verts (including inner) on the profile ────
            n_verts    = len(strip)    # includes the two boundary verts
            bevel_pts  = _get_bevel_pts(tgt, new_v1, new_v2, tension, n_verts)

            for vid, pos in zip(strip, bevel_pts):
                _set_vert_world_pos(self.fn, vid, pos)

        self.fn.updateSurface()
        cmds.refresh()


# ─────────────────────────────────────────────────────────────────────────────
# Selection helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_selected_edges():
    """
    Returns (mesh_shape_name, [edge_ids]) from the current Maya selection.
    Works whether the selection is a component list or an object+component mix.
    """
    sel_flat = cmds.ls(selection=True, flatten=True) or []
    edge_comps = [s for s in sel_flat if '.e[' in s]

    if not edge_comps:
        cmds.warning("HSReBevel: No edges selected. "
                     "Select the edges spanning the bevel strip first.")
        return None, []

    # Derive mesh shape from first component
    xform = edge_comps[0].split('.')[0]
    shapes = cmds.listRelatives(xform, shapes=True, fullPath=False,
                                type='mesh') or []
    if not shapes:
        # Maybe the user selected the shape directly
        if cmds.nodeType(xform) == 'mesh':
            mesh_shape = xform
        else:
            cmds.warning("HSReBevel: Cannot find a mesh shape node.")
            return None, []
    else:
        mesh_shape = shapes[0]

    # Parse edge indices  (handles  .e[0]  and  .e[0:5]  forms)
    edge_ids = []
    for comp in edge_comps:
        part = comp.split('.e[')[1].rstrip(']')
        if ':' in part:
            start, end = part.split(':')
            edge_ids.extend(range(int(start), int(end) + 1))
        else:
            edge_ids.append(int(part))

    return mesh_shape, edge_ids


# ─────────────────────────────────────────────────────────────────────────────
# Dragger-context callbacks  (must be module-level for Maya's string eval)
# ─────────────────────────────────────────────────────────────────────────────

_DRAG_CTX   = 'hsReBevelDraggerCtx'
_drag_start_x   = 0.0
_drag_base_size = 1.0


def _drag_press():
    global _drag_start_x, _drag_base_size
    anchor = cmds.draggerContext(_DRAG_CTX, query=True, anchorPoint=True)
    _drag_start_x   = float(anchor[0])
    _drag_base_size = (cmds.floatSliderGrp('hsRB_size', q=True, value=True)
                       if cmds.floatSliderGrp('hsRB_size', exists=True) else 1.0)


def _drag_drag():
    global _STATE
    if _STATE is None:
        return
    pos  = cmds.draggerContext(_DRAG_CTX, query=True, dragPoint=True)
    diff = (float(pos[0]) - _drag_start_x) / 200.0
    new_size = max(0.0, _drag_base_size + diff)

    if cmds.floatSliderGrp('hsRB_size', exists=True):
        cmds.floatSliderGrp('hsRB_size', edit=True, value=new_size)

    _STATE.restore()
    segs = (cmds.intSliderGrp('hsRB_segs', q=True, value=True)
            if cmds.intSliderGrp('hsRB_segs', exists=True) else _STATE.segments)
    tens = (cmds.floatSliderGrp('hsRB_tension', q=True, value=True)
            if cmds.floatSliderGrp('hsRB_tension', exists=True) else _STATE.tension)
    mode_idx = (cmds.radioButtonGrp('hsRB_mode', q=True, select=True)
                if cmds.radioButtonGrp('hsRB_mode', exists=True) else 1)
    mode = 'UNIFORM' if mode_idx == 1 else 'PROP'

    _STATE.apply(rebevel_size=new_size, segments=segs, tension=tens, resize_mode=mode)


def _drag_release():
    pass   # no extra action needed; positions are already set


def _setup_dragger():
    if cmds.draggerContext(_DRAG_CTX, exists=True):
        cmds.deleteUI(_DRAG_CTX)

    # Command strings reference module-level functions via Python eval
    press_cmd   = ('import hs_rebevel_maya as _hs; _hs._drag_press()')
    drag_cmd    = ('import hs_rebevel_maya as _hs; _hs._drag_drag()')
    release_cmd = ('import hs_rebevel_maya as _hs; _hs._drag_release()')

    cmds.draggerContext(
        _DRAG_CTX,
        pressCommand   = press_cmd,
        dragCommand    = drag_cmd,
        releaseCommand = release_cmd,
        cursor         = 'crossHair',
        space          = 'screen',
        name           = _DRAG_CTX,
    )
    cmds.setToolTo(_DRAG_CTX)


# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

_WIN_NAME = 'hsReBevelWin'
_STATE    = None    # module-level ReBevelState instance


def _ui_update(*_):
    """Read all sliders and re-apply the rebevel."""
    if _STATE is None:
        return
    size     = cmds.floatSliderGrp('hsRB_size',    q=True, value=True)
    segs     = cmds.intSliderGrp  ('hsRB_segs',    q=True, value=True)
    tens     = cmds.floatSliderGrp('hsRB_tension', q=True, value=True)
    mode_idx = cmds.radioButtonGrp('hsRB_mode',    q=True, select=True)
    mode     = 'UNIFORM' if mode_idx == 1 else 'PROP'

    _STATE.restore()
    _STATE.apply(rebevel_size=size, segments=segs, tension=tens, resize_mode=mode)


def _on_apply(*_):
    global _STATE
    if _STATE:
        # Wrap the final positions in one undo chunk
        cmds.undoInfo(openChunk=True, chunkName='HSReBevel')
        try:
            _ui_update()
        finally:
            cmds.undoInfo(closeChunk=True)
        cmds.setToolTo('selectSuperContext')
        _STATE = None
    if cmds.window(_WIN_NAME, exists=True):
        cmds.deleteUI(_WIN_NAME, window=True)
    if cmds.draggerContext(_DRAG_CTX, exists=True):
        cmds.deleteUI(_DRAG_CTX)


def _on_cancel(*_):
    global _STATE
    if _STATE:
        _STATE.restore()
        cmds.setToolTo('selectSuperContext')
        _STATE = None
    if cmds.window(_WIN_NAME, exists=True):
        cmds.deleteUI(_WIN_NAME, window=True)
    if cmds.draggerContext(_DRAG_CTX, exists=True):
        cmds.deleteUI(_DRAG_CTX)


def _build_ui(start_segments):
    if cmds.window(_WIN_NAME, exists=True):
        cmds.deleteUI(_WIN_NAME, window=True)

    win  = cmds.window(_WIN_NAME, title='HS ReBevel',
                       widthHeight=(330, 260),
                       sizeable=False, resizeToFitChildren=True)
    col  = cmds.columnLayout(adjustableColumn=True, rowSpacing=4,
                              columnOffset=('both', 8), parent=win)

    cmds.separator(height=8, style='none', parent=col)

    # ── Size ──────────────────────────────────────────────────────────────
    cmds.floatSliderGrp(
        'hsRB_size', label='Size', field=True,
        minValue=0.0, maxValue=3.0, fieldMinValue=0.0, fieldMaxValue=20.0,
        value=1.0, precision=3,
        columnWidth3=(65, 60, 170),
        changeCommand=_ui_update,
        dragCommand=_ui_update,
        parent=col,
    )

    # ── Segments ──────────────────────────────────────────────────────────
    cmds.intSliderGrp(
        'hsRB_segs', label='Segments', field=True,
        minValue=0, maxValue=20,
        value=start_segments,
        columnWidth3=(65, 60, 170),
        changeCommand=_ui_update,
        parent=col,
    )

    # ── Tension ───────────────────────────────────────────────────────────
    cmds.floatSliderGrp(
        'hsRB_tension', label='Tension', field=True,
        minValue=-1.0, maxValue=1.0,
        value=0.5, precision=3,
        columnWidth3=(65, 60, 170),
        changeCommand=_ui_update,
        dragCommand=_ui_update,
        parent=col,
    )

    # ── Resize mode ───────────────────────────────────────────────────────
    cmds.radioButtonGrp(
        'hsRB_mode', label='Resize',
        labelArray2=['Uniform', 'Proportional'],
        numberOfRadioButtons=2, select=1,
        columnWidth3=(65, 90, 100),
        changeCommand=_ui_update,
        parent=col,
    )

    cmds.separator(height=8, parent=col)

    # ── Hint text ─────────────────────────────────────────────────────────
    cmds.text(label='Drag in viewport to resize  |  Adjust sliders for live preview',
              align='center', font='smallPlainLabelFont', parent=col)

    cmds.separator(height=8, parent=col)

    # ── Buttons ───────────────────────────────────────────────────────────
    row = cmds.rowLayout(numberOfColumns=2,
                          columnWidth2=(155, 155),
                          columnAlign2=('center', 'center'),
                          parent=col)
    cmds.button(label='Apply',  width=145, command=_on_apply,  parent=row)
    cmds.button(label='Cancel', width=145, command=_on_cancel, parent=row)

    cmds.showWindow(win)


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def run():
    """
    Launch the HS ReBevel tool.

    Call from Maya's Script Editor (Python tab):

        import hs_rebevel_maya
        hs_rebevel_maya.run()

    Or add to a shelf button.
    """
    global _STATE

    # Close any previous session
    _on_cancel()

    mesh_shape, edge_ids = _get_selected_edges()
    if mesh_shape is None:
        return

    _STATE = ReBevelState()
    if not _STATE.load(mesh_shape, edge_ids):
        cmds.warning("HSReBevel: Could not parse the edge selection as a "
                     "valid bevel ring.  Make sure you select the edges "
                     "that cross the bevel face strip (not the edge loops).")
        _STATE = None
        return

    _build_ui(_STATE.start_segments)
    _setup_dragger()

    # Live-apply at default size=1 so the user sees the detected ring instantly
    _STATE.apply()

    cmds.inViewMessage(
        assistMessage=(
            '<hl>HS ReBevel</hl>  –  '
            'Drag in viewport to resize  |  '
            'Adjust sliders  |  '
            'Apply / Cancel'
        ),
        pos='midCenter', fade=True, fadeStayTime=3500,
    )


if __name__ == '__main__':
    run()
