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
}

# Camera angles as (name, direction_vector, up_hint_degrees) -- direction
# is normalized and scaled by the scene's actual bounding-sphere radius at
# render time, NOT a hardcoded distance. This is the fix for the "camera
# pointed at empty space" bug: BANC's mesh content is NOT centered at
# world (0,0,0) after import (CAVE/graphene coordinates are absolute, not
# relative to any particular neuron), so cameras built around a fixed
# (0,0,0) target and fixed absolute distances only work by coincidence.
# Direction vectors don't need to be unit length -- get_camera_angles()
# normalizes them.
CAMERA_DIRECTIONS = [
    ("dorsal", (0, 0, 1)),
    ("lateral_L", (1, 0, 0.15)),
    ("lateral_R", (-1, 0, 0.15)),
    ("anterior", (0, -1, 0.15)),
    ("oblique", (0.7, -0.7, 0.5)),
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
    """Returns mesh_id_ (str, no extension) -> group.

    Mesh mesh_ids are NOT root IDs (navis.write_mesh names them by some
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
                "mesh_id (path.stem) alongside root_id and group."
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
    """World-space bounding box center + radius across all given mesh
    objects. This is the actual fix for the framing bug: CAVE/graphene
    root IDs carry absolute connectome coordinates, so imported geometry
    is NOT centered at (0,0,0) -- it sits wherever that ID's absolute
    position was, offset by nothing. Cameras need to target and frame
    around this computed center, not the world origin.
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
    radius = (max_co - min_co).length / 2
    print(f"Scene bounds: center={tuple(round(c, 3) for c in center)}, "
          f"radius={radius:.3f}")
    return center, radius


def frame_camera_on_target(cam_obj, target, location):
    direction = target - location
    cam_obj.location = location
    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def render_all_angles(out_dir, resolution):
    out_dir.mkdir(parents=True, exist_ok=True)

    mesh_objects = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not mesh_objects:
        raise RuntimeError("No mesh objects in scene -- did import_meshes run first?")
    center, radius = compute_scene_bounds(mesh_objects)
    if radius == 0:
        raise RuntimeError("Computed scene radius is 0 -- bounding box degenerate, "
                            "check that meshes actually imported with real geometry.")

    # Distance scaled to bounding radius rather than a fixed number, with
    # a margin so the full extent fits in frame (empirical factor -- 2.2x
    # radius comfortably fits a roughly spherical/ellipsoid cluster with a
    # ~50mm lens; tighten/loosen after seeing a real render).
    distance = radius * 2.2

    bpy.ops.object.camera_add(location=(0, 0, 0))
    cam_obj = bpy.context.object
    cam_obj.name = "render_cam"
    cam_obj.data.lens = 50
    cam_obj.data.clip_end = distance * 10  # avoid far-plane clipping at these scales
    bpy.context.scene.camera = cam_obj

    for name, direction in CAMERA_DIRECTIONS:
        dir_vec = Vector(direction).normalized()
        location = center + dir_vec * distance
        frame_camera_on_target(cam_obj, center, location)

        out_path = out_dir / f"banc_{name}.png"
        bpy.context.scene.render.filepath = str(out_path)
        print(f"Rendering '{name}' from {tuple(round(c, 2) for c in location)} at {cam_obj.rotation_euler} "
              f"-> {out_path}")
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