"""
Stage B -- runs INSIDE Blender's bundled Python, headless, on Amarel.

Invoked as:
    blender --background --python render_banc.py -- \\
        --mesh-dir /scratch/$USER/banc/meshes_obj \\
        --out-dir /scratch/$USER/banc/renders \\
        --engine CYCLES --device GPU

Everything after the bare `--` is this script's own argv; Blender consumes
everything before it. This is a real gotcha the first time you hit it --
`blender --background --python foo.py --mesh-dir X` will NOT work, because
Blender itself tries to parse `--mesh-dir` and fails silently/weirdly.

This script does NOT use navis.interfaces.blender (b3d.Handler) at all --
that module is built for interactive/live sessions (h.select(), h.colorize()
assume you're clicking around in an open Blender window). For a one-shot
headless render, going through bpy directly is actually less code and more
predictable, since b3d's convenience layer buys you nothing when there's no
human in the loop to interact with the result.
"""

import bpy
import sys
import csv
import math
import argparse
from pathlib import Path
from mathutils import Vector


def parse_args():
    # Strip everything up to and including Blender's own '--' separator.
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--mesh-dir", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--engine", default="CYCLES", choices=["CYCLES", "BLENDER_EEVEE_NEXT"])
    p.add_argument("--device", default="GPU", choices=["GPU", "CPU"])
    p.add_argument(
        "--compute-type",
        default=None,
        choices=["CUDA", "OPTIX", "HIP", "ONEAPI", "METAL", "NONE"],
        help="Cycles compute backend. Auto-detected from platform if not given: "
             "METAL on macOS, CUDA on Amarel's NVIDIA gpu partition. Override "
             "explicitly if auto-detection guesses wrong.",
    )
    p.add_argument("--resolution", type=int, default=2400, help="longest edge, px")
    p.add_argument("--samples", type=int, default=128)
    return p.parse_args(argv)


GROUP_COLORS = {
    "ORN": (0.85, 0.15, 0.15, 1.0),
    "OviDN": (0.15, 0.75, 0.15, 1.0),
    "CA": (0.15, 0.25, 0.85, 1.0),
    "DA": (0.4793, 0.1912, 0.1413, 1.0),      # Dopamine (#B87969)
    "SER": (0.2623, 0.1221, 0.3005, 1.0),     # Serotonin (#8C6295)
    "ACH": (0.3005, 0.3663, 0.6172, 1.0),     # Acetylcholine (#95A3CE)
    "GABA": (0.6654, 0.3916, 0.0648, 1.0),    # GABA (#D5A848)
    "GLUT": (0.2384, 0.3916, 0.0999, 1.0),    # Glutamate (#86A859)
    "HIST": (0.5711, 0.2016, 0.2542, 1.0),    # Histamine (#C77C8A)
    "TYR": (0.159, 0.3864, 0.3663, 1.0),      # Tyrosine (#6FA7A3)
    "OCT": (0.1683, 0.107, 0.314, 1.0),       # Octopamine (#725C98)
    "Unknown": (0.5906, 0.5906, 0.5906, 1.0) # Unknown (#CACACA)
}

# Camera views expressed as ANATOMICAL labels, not raw world-axis vectors.
# The earlier version hardcoded world (0,0,1) = dorsal, which assumed the
# CNS's dorsal-ventral axis lines up with Blender's world Z -- it doesn't
# (confirmed empirically: bounding box extents were X=88.7, Y=31.6,
# Z=109.6, and a CNS's longest axis is anterior-posterior, shortest is
# dorsal-ventral -- so world Z is actually A-P here, world Y is D-V, world
# X is left-right). Rather than hardcode that one-off mapping (fragile if
# a different circuit's outline mesh or a coordinate-convention change
# shifts things), axis roles are inferred from bounding-box shape at
# render time: longest extent = anterior-posterior, shortest = dorsal-
# ventral, middle = medial-lateral. This holds for any CNS-shaped volume
# regardless of which world axis it happens to occupy.
#
# Each entry: (name, axis_role, sign, up_role). sign=+1/-1 picks which end
# of that axis the camera sits on; up_role names which anatomical axis
# should map to the camera's "up" so the roll comes out right (this is
# the fix for the earlier upside-down dorsal render, which used a fixed
# world-Y up-hint that fought the real anatomy).
CAMERA_VIEWS = [
    ("dorsal", "dorsal_ventral", -1, "anterior_posterior", "medial_lateral", "anterior_posterior"),
    ("anterior", "anterior_posterior", -1, "dorsal_ventral", "medial_lateral", "dorsal_ventral"),
    ("lateral_L", "medial_lateral", +1, "dorsal_ventral", "anterior_posterior", "dorsal_ventral"),
    ("lateral_R", "medial_lateral", -1, "dorsal_ventral", "anterior_posterior", "dorsal_ventral"),
    ("oblique", None, None, "dorsal_ventral", None, None),  # handled specially, see render_all_angles
]

MESH_SCALE = 1 / 10000  # matches the scaling convention in 3d_skeleton.py / b3d.Handler(scaling=...)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block_type in (bpy.data.meshes, bpy.data.materials):
        for block in list(block_type):
            if block.users == 0:
                block_type.remove(block)


def load_manifest(mesh_dir):
    """Returns mesh_id (str, no extension) -> group.

    Mesh IDs are NOT root IDs (navis.write_mesh names them by some
    internal/UUID-like scheme, not the root_id you passed in), so the
    manifest must carry both the mesh_id and the root_id, and this
    lookup has to key on mesh_id since that's the only thing
    import_meshes can see when it globs the directory.
    """
    mapping = {}
    manifest_path = mesh_dir / "manifest.csv"
    with open(manifest_path) as f:
        reader = csv.DictReader(f)
        if "mesh_id" not in reader.fieldnames:
            raise ValueError(
                f"manifest.csv has columns {reader.fieldnames}, expected a "
                "'mesh_id' column -- update Stage A to write the mesh "
                "ID (path.stem) alongside root_id and group."
            )
        for row in reader:
            mapping[row["mesh_id"]] = row["group"]
    return mapping


def make_material(name, rgba, emission_strength=0.15):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.4
    # A little emission keeps thin ORN processes visible against dark
    # background without needing aggressive scene lighting everywhere.
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = rgba
    emit.inputs["Strength"].default_value = emission_strength
    mix = nodes.new("ShaderNodeAddShader")

    links.new(bsdf.outputs["BSDF"], mix.inputs[0])
    links.new(emit.outputs["Emission"], mix.inputs[1])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat


def import_meshes(mesh_dir, id_to_group, materials):
    obj_files = sorted(p for p in mesh_dir.glob("*.obj") if p.stem != "cns_outline")
    print(f"Importing {len(obj_files)} meshes...")

    imported = []
    for i, path in enumerate(obj_files):
        stem = path.stem  # matches manifest's "mesh_id" column, NOT root_id
        # Blender 5.x/4.x use wm.obj_import; older versions used
        # import_scene.obj -- if this throws AttributeError on your
        # cluster's Blender version, swap to the legacy operator.
        bpy.ops.wm.obj_import(filepath=str(path))
        obj = bpy.context.selected_objects[-1]
        obj.name = stem
        obj.scale = (MESH_SCALE, MESH_SCALE, MESH_SCALE)

        group = id_to_group.get(stem, "Other")
        mat = materials.get(group, materials.get("Other"))
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

        imported.append(obj)
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(obj_files)}")
            # Only meaningful in an interactive GUI session (headless
            # --background has no window to redraw and view_layer.update()
            # is a no-op cost there) -- keeps Blender's UI responsive/
            # visibly-alive during a long import run in the console instead
            # of appearing frozen for the full ~35s+ duration. Harmless to
            # leave in for headless runs, just does nothing useful there.
            if bpy.context.window_manager.windows:
                bpy.context.view_layer.update()
                for window in bpy.context.window_manager.windows:
                    for area in window.screen.areas:
                        area.tag_redraw()

    # Optionally import the CNS outline as translucent context.
    outline_path = mesh_dir / "cns_outline.obj"
    if outline_path.exists():
        bpy.ops.wm.obj_import(filepath=str(outline_path))
        outline_obj = bpy.context.selected_objects[-1]
        outline_obj.name = "cns_outline"
        outline_obj.scale = (MESH_SCALE, MESH_SCALE, MESH_SCALE)
        outline_mat = bpy.data.materials.new("outline_mat")
        outline_mat.use_nodes = True
        outline_mat.blend_method = "BLEND"
        bsdf = outline_mat.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (0.7, 0.7, 0.7, 1.0)
        bsdf.inputs["Alpha"].default_value = 0.06
        outline_obj.data.materials.append(outline_mat)
        imported.append(outline_obj)
        print("Imported cns_outline.obj")

    return imported


def setup_lighting():
    # Three-point-ish setup: key, fill, rim. Sun lamps since the scene
    # scale after MESH_SCALE is small and point-light falloff would need
    # per-scene tuning; sun lamps give consistent directional light
    # regardless of scene scale.
    def add_sun(name, rotation_deg, energy):
        bpy.ops.object.light_add(type="SUN", location=(0, 0, 0))
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.rotation_euler = tuple(math.radians(d) for d in rotation_deg)
        return light

    add_sun("key_light", (45, 0, 45), energy=3.0)
    add_sun("fill_light", (60, 0, -120), energy=1.0)
    add_sun("rim_light", (-30, 0, 160), energy=1.5)

    world = bpy.data.worlds["World"] if "World" in bpy.data.worlds else bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.01, 0.01, 0.015, 1.0)  # near-black backdrop
        bg.inputs[1].default_value = 1.0


def detect_compute_type():
    """METAL on Apple Silicon/macOS, CUDA elsewhere (Amarel's gpu partition
    is NVIDIA). This is a reasonable default, not a guarantee -- an Intel
    Mac with an AMD GPU would also want METAL (per Blender's own default-
    device logic), and a non-NVIDIA cluster node would need something else
    entirely, so --compute-type exists to override this outright."""
    import platform
    system = platform.system()
    if system == "Darwin":
        return "METAL"
    return "CUDA"


def setup_render(engine, device, resolution, samples, compute_type=None):
    scene = bpy.context.scene
    scene.render.engine = engine
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False

    if engine == "CYCLES":
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True

        if device == "GPU":
            compute_type = compute_type or detect_compute_type()
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = compute_type
            prefs.get_devices()
            enabled_any = False
            for d in prefs.devices:
                d.use = (d.type == compute_type)
                enabled_any = enabled_any or d.use
            if not enabled_any:
                print(f"WARNING: no Cycles device of type {compute_type} found -- "
                      f"available devices: {[(d.name, d.type) for d in prefs.devices]}. "
                      "Falling back to CPU for this render.")
                device = "CPU"
        scene.cycles.device = device
        print(f"Cycles device: {device}" + (f" ({compute_type})" if device == "GPU" else ""))
    else:
        # Eevee Next -- much faster on CPU-only nodes, decent quality for
        # a connectomics figure where readability > photorealism.
        scene.eevee.taa_render_samples = samples


def compute_scene_bounds(objects):
    """World-space bounding box center + per-axis extents across the
    given mesh objects. Called with ONLY the CNS outline object (not the
    neuron meshes) -- the outline is a strict spatial superset of every
    neuron in any circuit subset, so it's a stable, circuit-independent
    reference frame. Framing off the neuron subset instead would make
    different circuit renders inconsistently scaled/centered against
    one another.
    """
    min_co = Vector((float("inf"),) * 3)
    max_co = Vector((float("-inf"),) * 3)

    for obj in objects:
        if obj.type != "MESH":
            continue
        # bound_box gives 8 corners in LOCAL space; matrix_world converts
        # to world space, which accounts for the per-object .scale we set
        # in import_meshes (MESH_SCALE) automatically.
        for corner in obj.bound_box:
            world_co = obj.matrix_world @ Vector(corner)
            min_co.x = min(min_co.x, world_co.x)
            min_co.y = min(min_co.y, world_co.y)
            min_co.z = min(min_co.z, world_co.z)
            max_co.x = max(max_co.x, world_co.x)
            max_co.y = max(max_co.y, world_co.y)
            max_co.z = max(max_co.z, world_co.z)

    center = (min_co + max_co) / 2
    extents = max_co - min_co  # full extent per axis, not half
    radius = extents.length / 2
    print(f"Scene bounds: center={tuple(round(c, 3) for c in center)}, "
          f"extents={tuple(round(e, 3) for e in extents)}, radius={radius:.3f}")
    return center, extents, radius


def infer_axis_roles(extents):
    """Map world axes (0=X, 1=Y, 2=Z) to anatomical roles by extent size:
    longest = anterior_posterior, shortest = dorsal_ventral, middle =
    medial_lateral. This holds for any CNS-shaped bounding volume
    regardless of which world axis it happens to land on for a given
    mesh export/coordinate convention -- confirmed against the actual
    printed extents (X=88.68, Y=31.55, Z=109.56): Z is longest (A-P),
    Y is shortest (D-V), X is middle (M-L), matching known fly CNS
    proportions (elongated A-P, thin D-V).
    Returns {role_name: (axis_index, extent_value)}.
    """
    axis_extents = sorted(enumerate(extents), key=lambda t: t[1], reverse=True)
    roles = {
        "anterior_posterior": axis_extents[0],
        "medial_lateral": axis_extents[1],
        "dorsal_ventral": axis_extents[2],
    }
    print("Inferred axis roles (role -> (axis_index, extent)):", roles)
    return roles


def unit_vector_for_axis(axis_index, sign):
    v = [0.0, 0.0, 0.0]
    v[axis_index] = float(sign)
    return Vector(v)


def frame_camera_on_target(cam_obj, target, location, up_hint="Y"):
    direction = target - location
    cam_obj.location = location
    cam_obj.rotation_euler = direction.to_track_quat("-Z", up_hint).to_euler()

def distance_for_fov(cam_data, horizontal_extent, vertical_extent, margin=1.15):
    """Required camera distance so both extents fit in frame, with margin."""
    fov_h = cam_data.angle_x   # radians, live from lens+sensor_width
    fov_v = cam_data.angle_y   # radians, live from lens+sensor_height
    d_for_width = horizontal_extent / (2 * math.tan(fov_h / 2))
    d_for_height = vertical_extent / (2 * math.tan(fov_v / 2))
    return max(d_for_width, d_for_height) * margin


def render_all_angles(out_dir, resolution):
    out_dir.mkdir(parents=True, exist_ok=True)

    outline_obj = bpy.data.objects.get("cns_outline")
    if outline_obj is None:
        raise RuntimeError(
            "No 'cns_outline' object found -- framing needs the outline mesh "
            "as the stable reference volume (see compute_scene_bounds docstring). "
            "Check that cns_outline.obj exists in mesh-dir and import_meshes loaded it."
        )
    center, extents, radius = compute_scene_bounds([outline_obj])
    if radius == 0:
        raise RuntimeError("Computed scene radius is 0 -- bounding box degenerate, "
                            "check that the outline mesh actually has real geometry.")
    axis_roles = infer_axis_roles(extents)

    # # Distance scaled to bounding radius, with margin so the fullest
    # # extent (anterior-posterior, always the longest) still fits in frame.
    # # 1.3x the A-P half-extent is tighter than the earlier flat 2.2x*radius
    # # guess, and won't clip since it's derived from the real long axis
    # # rather than a generic sphere-fit distance.
    # ap_axis, ap_extent = axis_roles["anterior_posterior"]
    # distance = max(radius * 2.2, ap_extent * 0.75)

    bpy.ops.object.camera_add(location=(0, 0, 0))
    cam_obj = bpy.context.object
    cam_obj.name = "render_cam"
    cam_obj.data.lens = 50
    cam_obj.data.clip_end = radius * 5  # avoid far-plane clipping at these scales
    bpy.context.scene.camera = cam_obj

    for name, axis_role, sign, up_role, h_dim, v_dim in CAMERA_VIEWS:
        if name == "oblique": continue
        if axis_role is None:
            # oblique: average of anterior + one lateral direction, so it
            # doesn't depend on a single anatomical axis.
            ap_idx, _ = axis_roles["anterior_posterior"]
            ml_idx, _ = axis_roles["medial_lateral"]
            dv_idx, _ = axis_roles["dorsal_ventral"]
            dir_vec = (
                unit_vector_for_axis(ap_idx, -1) * 0.7
                + unit_vector_for_axis(ml_idx, +1) * 0.7
                + unit_vector_for_axis(dv_idx, +1) * 0.4
            ).normalized()
        else:
            axis_idx, _ = axis_roles[axis_role]
            dir_vec = unit_vector_for_axis(axis_idx, sign)

        up_axis_idx, _ = axis_roles[up_role]
        # Blender's to_track_quat up-hint wants a named axis ("X"/"Y"/"Z"),
        # not a vector -- map the anatomical up-role back to whichever
        # world axis it corresponds to.
        up_hint = "XYZ"[up_axis_idx]

        margin = 0.8 if name == "dorsal" else 1.5 if name == "anterior" else 1.2
        distance = distance_for_fov(cam_obj.data, axis_roles[h_dim][1], axis_roles[v_dim][1], margin=margin)
        location = center + dir_vec * distance
        frame_camera_on_target(cam_obj, center, location, up_hint=up_hint)

        out_path = out_dir / f"banc_{name}.png"
        bpy.context.scene.render.filepath = str(out_path)
        print(f"Rendering '{name}' from {tuple(round(c, 2) for c in location)} "
              f"(up hint: world {up_hint}) -> {out_path}")
        bpy.ops.render.render(write_still=True)


def main():
    args = parse_args()
    clear_scene()

    id_to_group = load_manifest(args.mesh_dir)
    materials = {g: make_material(f"mat_{g}", c) for g, c in GROUP_COLORS.items()}
    materials["Other"] = make_material("mat_Other", (0.6, 0.6, 0.6, 1.0))

    import_meshes(args.mesh_dir, id_to_group, materials)
    setup_lighting()
    setup_render(args.engine, args.device, args.resolution, args.samples, args.compute_type)
    render_all_angles(args.out_dir, args.resolution)

    print("Done. Frames written to", args.out_dir)


if __name__ == "__main__":
    main()