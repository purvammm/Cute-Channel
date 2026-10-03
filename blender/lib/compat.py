"""Version-tolerant helpers for Blender's Python API (import only inside Blender).

Blender's API shifts between releases:
- the EEVEE engine id was BLENDER_EEVEE_NEXT in 4.2-4.5 and is BLENDER_EEVEE again in 5.x;
- Principled BSDF sockets were renamed in 4.0 ("Subsurface" became "Subsurface Weight");
- 5.x creates node trees by default and deprecates `use_nodes` (removed in 6.0).
Scripts call these helpers instead of the raw API, so a Blender upgrade means fixing one file.
Tested on 5.2.2 LTS. Written to also run on 4.5 LTS (Intel Macs), but not yet tested there.
"""

from __future__ import annotations

import bpy

ENGINE_ALIASES = {
    "EEVEE": ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"),  # 4.2-4.5 name first, then 5.x
    "CYCLES": ("CYCLES",),
    "WORKBENCH": ("BLENDER_WORKBENCH",),
}


def version() -> tuple[int, int, int]:
    return tuple(bpy.app.version)


def resolve_engine(name: str, scene=None) -> str:
    """Map a generic engine name to this Blender's identifier, and set it on the scene.

    The engine list is built at runtime. In background mode its RNA enum lists only one
    entry, so instead of reading the list we try each identifier and keep the first one
    Blender accepts.
    """
    scene = scene or bpy.context.scene
    tried = ENGINE_ALIASES.get(name.upper(), (name,))
    for identifier in tried:
        try:
            scene.render.engine = identifier
        except TypeError:
            continue
        return identifier
    raise ValueError(f"render engine {name!r} is not available (tried {', '.join(tried)})")


def configure_engine(scene, engine_id: str, samples: int, denoise: bool = False) -> None:
    scene.render.engine = engine_id
    if engine_id == "CYCLES":
        scene.cycles.device = "CPU"  # GPU Cycles needs per-machine setup; Phase 5 may add it
        scene.cycles.samples = samples
        scene.cycles.use_denoising = denoise
    elif engine_id.startswith("BLENDER_EEVEE"):
        scene.eevee.taa_render_samples = samples


def new_material(name: str):
    material = bpy.data.materials.new(name)
    if getattr(material, "node_tree", None) is None:
        material.use_nodes = True  # < 5.0 starts without nodes; 5.x has them already
    return material


def principled_node(material):
    """The material's Principled BSDF node, created and wired up if it is missing."""
    tree = material.node_tree
    for node in tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            return node
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    output = next((n for n in tree.nodes if n.type == "OUTPUT_MATERIAL"), None)
    output = output or tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return bsdf


def set_input(node, names, value):
    """Set the first of `names` that exists on the node (sockets get renamed between versions).

    Returns the socket name that was set, or None if none exist.
    """
    for name in names:
        socket = node.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return name
    return None


def shade_smooth(mesh) -> None:
    if hasattr(mesh, "shade_smooth"):  # Blender 4.1+
        mesh.shade_smooth()
    else:
        for polygon in mesh.polygons:
            polygon.use_smooth = True


def set_world_color(scene, rgb_linear, strength: float = 1.0) -> None:
    """A plain pastel world: the soft all-round light from guide §12.3."""
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    if getattr(world, "node_tree", None) is None:
        world.use_nodes = True
    tree = world.node_tree
    background = next((n for n in tree.nodes if n.type == "BACKGROUND"), None)
    if background is None:
        background = tree.nodes.new("ShaderNodeBackground")
        output = next((n for n in tree.nodes if n.type == "OUTPUT_WORLD"), None)
        output = output or tree.nodes.new("ShaderNodeOutputWorld")
        tree.links.new(background.outputs["Background"], output.inputs["Surface"])
    background.inputs["Color"].default_value = (*rgb_linear, 1.0)
    background.inputs["Strength"].default_value = strength


def gpu_info() -> dict | None:
    """Which GPU and driver rendered the frame. None when no GPU context exists (Cycles CPU)."""
    try:
        import gpu

        return {
            "backend": gpu.platform.backend_type_get(),
            "vendor": gpu.platform.vendor_get(),
            "renderer": gpu.platform.renderer_get(),
            "version": gpu.platform.version_get(),
        }
    except Exception:  # the gpu module raises if nothing initialised it; that's expected
        return None
