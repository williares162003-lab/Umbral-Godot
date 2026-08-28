"""Genera un grafo Graphify determinista para el proyecto Godot de Umbral.

Graphify 0.9.51 todavia no clasifica GDScript como codigo. Este adaptador
extrae relaciones comprobables de .gd, .tscn, project.godot y del generador
Python sin inventar dependencias semanticas.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "graphify-out"

TYPE_TOKENS = {
    "Camera3D",
    "DirAccess",
    "Image",
    "ImageTexture",
    "Input",
    "Node3D",
    "OS",
    "ProjectSettings",
    "RenderingServer",
    "ResourceLoader",
    "Terrain3D",
    "Terrain3DAssets",
    "Terrain3DMaterial",
    "Terrain3DRegion",
    "Terrain3DTextureAsset",
    "Terrain3DUtil",
}


def slug(value: str) -> str:
    normalized = value.replace("\\", "/").lower()
    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")


@dataclass
class Graph:
    nodes: dict[str, dict] = field(default_factory=dict)
    links: list[dict] = field(default_factory=list)
    edge_keys: set[tuple[str, str, str]] = field(default_factory=set)

    def node(
        self,
        node_id: str,
        label: str,
        source_file: str,
        source_location: str = "L1",
        *,
        kind: str = "symbol",
        callable_symbol: bool = False,
    ) -> str:
        self.nodes.setdefault(
            node_id,
            {
                "id": node_id,
                "label": label,
                "kind": kind,
                "file_type": "code",
                "source_file": source_file,
                "source_location": source_location,
                "_origin": "ast",
                "_callable": callable_symbol,
                "norm_label": slug(label),
            },
        )
        return node_id

    def edge(
        self,
        source: str,
        target: str,
        relation: str,
        source_file: str,
        source_location: str = "L1",
        *,
        context: str = "structure",
    ) -> None:
        key = (source, target, relation)
        if source == target or key in self.edge_keys:
            return
        self.edge_keys.add(key)
        self.links.append(
            {
                "source": source,
                "target": target,
                "relation": relation,
                "_origin": "ast",
                "confidence": "EXTRACTED",
                "confidence_score": 1.0,
                "context": context,
                "source_file": source_file,
                "source_location": source_location,
                "weight": 1.0,
            }
        )


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def file_node(graph: Graph, path: Path, *, kind: str = "file") -> str:
    rel = relative(path)
    return graph.node(f"file_{slug(rel)}", path.name, rel, kind=kind)


def add_external_type(graph: Graph, token: str, source_file: str, line: int) -> str:
    return graph.node(
        f"godot_type_{slug(token)}",
        token,
        source_file,
        f"L{line}",
        kind="engine-type",
    )


def parse_gdscript(graph: Graph, path: Path) -> None:
    rel = relative(path)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    script_id = file_node(graph, path, kind="gdscript")

    extends_match = re.search(r"^extends\s+([A-Za-z_]\w*)", text, flags=re.MULTILINE)
    if extends_match:
        line = text[: extends_match.start()].count("\n") + 1
        type_id = add_external_type(graph, extends_match.group(1), rel, line)
        graph.edge(script_id, type_id, "extends", rel, f"L{line}", context="inheritance")

    functions: dict[str, tuple[str, int, int]] = {}
    starts: list[tuple[str, int, str]] = []
    for index, line in enumerate(lines, start=1):
        match = re.match(r"^func\s+([A-Za-z_]\w*)\s*\(", line)
        if not match:
            continue
        name = match.group(1)
        node_id = graph.node(
            f"{slug(rel)}_{slug(name)}",
            name,
            rel,
            f"L{index}",
            kind="function",
            callable_symbol=True,
        )
        graph.edge(script_id, node_id, "contains", rel, f"L{index}")
        starts.append((name, index, node_id))

    for position, (name, start, node_id) in enumerate(starts):
        end = starts[position + 1][1] - 1 if position + 1 < len(starts) else len(lines)
        functions[name] = (node_id, start, end)

    for name, (node_id, start, end) in functions.items():
        body = "\n".join(lines[start - 1 : end])
        for called in re.findall(r"\b([A-Za-z_]\w*)\s*\(", body):
            target = functions.get(called)
            if target and called != name:
                graph.edge(node_id, target[0], "calls", rel, f"L{start}", context="call")

    for line_number, line in enumerate(lines, start=1):
        for token in TYPE_TOKENS:
            if re.search(rf"\b{re.escape(token)}\b", line):
                type_id = add_external_type(graph, token, rel, line_number)
                graph.edge(
                    script_id,
                    type_id,
                    "references",
                    rel,
                    f"L{line_number}",
                    context="engine-api",
                )
        for resource_path in re.findall(r'"(res://[^"\n]+)"', line):
            target_path = ROOT / resource_path.removeprefix("res://")
            if target_path.exists() and target_path.is_file():
                target_id = file_node(graph, target_path)
                graph.edge(
                    script_id,
                    target_id,
                    "loads",
                    rel,
                    f"L{line_number}",
                    context="resource",
                )


def parse_scene(graph: Graph, path: Path) -> None:
    rel = relative(path)
    text = path.read_text(encoding="utf-8")
    scene_id = file_node(graph, path, kind="scene")

    for match in re.finditer(r'^\[ext_resource[^\]]*path="([^"]+)"[^\]]*\]', text, re.MULTILINE):
        resource_path = match.group(1)
        line = text[: match.start()].count("\n") + 1
        target_path = ROOT / resource_path.removeprefix("res://")
        if target_path.exists() and target_path.is_file():
            target_id = file_node(graph, target_path)
            graph.edge(scene_id, target_id, "uses_script", rel, f"L{line}", context="scene-resource")

    for match in re.finditer(r'^\[node\s+name="([^"]+)"\s+type="([^"]+)"', text, re.MULTILINE):
        name, node_type = match.groups()
        line = text[: match.start()].count("\n") + 1
        child_id = graph.node(
            f"{slug(rel)}_node_{slug(name)}",
            name,
            rel,
            f"L{line}",
            kind=f"scene-node:{node_type}",
        )
        graph.edge(scene_id, child_id, "contains", rel, f"L{line}", context="scene-tree")
        type_id = add_external_type(graph, node_type, rel, line)
        graph.edge(child_id, type_id, "instance_of", rel, f"L{line}", context="scene-tree")


def parse_project(graph: Graph, path: Path) -> None:
    rel = relative(path)
    project_id = file_node(graph, path, kind="godot-project")
    text = path.read_text(encoding="utf-8")
    main_match = re.search(r'^run/main_scene="([^"]+)"', text, flags=re.MULTILINE)
    main_scene = main_match.group(1) if main_match else ""
    if main_scene.startswith("res://"):
        scene_path = ROOT / main_scene.removeprefix("res://")
        if scene_path.exists():
            graph.edge(project_id, file_node(graph, scene_path, kind="scene"), "starts", rel, "L8")

    plugin_match = re.search(r'^enabled=PackedStringArray\((.+)\)$', text, flags=re.MULTILINE)
    plugin_text = plugin_match.group(1) if plugin_match else ""
    for plugin in re.findall(r'"(res://[^"\n]+)"', plugin_text):
        plugin_path = ROOT / plugin.removeprefix("res://")
        if plugin_path.exists():
            graph.edge(project_id, file_node(graph, plugin_path, kind="plugin"), "enables", rel, "L21")


def parse_python(graph: Graph, path: Path) -> None:
    rel = relative(path)
    module_id = file_node(graph, path, kind="python-module")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
    functions: dict[str, tuple[str, ast.FunctionDef]] = {}

    for item in tree.body:
        if not isinstance(item, ast.FunctionDef):
            continue
        node_id = graph.node(
            f"{slug(rel)}_{slug(item.name)}",
            item.name,
            rel,
            f"L{item.lineno}",
            kind="function",
            callable_symbol=True,
        )
        functions[item.name] = (node_id, item)
        graph.edge(module_id, node_id, "contains", rel, f"L{item.lineno}")

    for name, (node_id, function) in functions.items():
        for call in (node for node in ast.walk(function) if isinstance(node, ast.Call)):
            if isinstance(call.func, ast.Name) and call.func.id in functions and call.func.id != name:
                graph.edge(
                    node_id,
                    functions[call.func.id][0],
                    "calls",
                    rel,
                    f"L{call.lineno}",
                    context="call",
                )

    generated = [
        ROOT / "assets/terrain/heightmaps/umbral_world_heightmap.r16",
        ROOT / "assets/terrain/heightmaps/umbral_world_heightmap.png",
        ROOT / "assets/terrain/heightmaps/umbral_world_preview.png",
        ROOT / "assets/terrain/heightmaps/umbral_world_layout.json",
    ]
    main = functions.get("main")
    if main:
        for target in generated:
            if target.exists():
                graph.edge(main[0], file_node(graph, target, kind="terrain-asset"), "generates", rel, f"L{main[1].lineno}")


def parse_docs(graph: Graph) -> None:
    documented_files = [
        ROOT / "README.md",
        ROOT / "docs/terrain_direction.md",
    ]
    candidates = [
        ROOT / "project.godot",
        ROOT / "scenes/terrain/TerrainPrototype.tscn",
        ROOT / "scripts/terrain/terrain_prototype.gd",
        ROOT / "scripts/terrain/terrain_fly_camera.gd",
        ROOT / "tools/generate_heightmap.py",
    ]
    for doc in documented_files:
        if not doc.exists():
            continue
        rel = relative(doc)
        text = doc.read_text(encoding="utf-8")
        doc_id = file_node(graph, doc, kind="documentation")
        for target in candidates:
            target_rel = relative(target)
            if target_rel in text:
                graph.edge(doc_id, file_node(graph, target), "documents", rel, "L1", context="documentation")


def build() -> Graph:
    graph = Graph()
    parse_project(graph, ROOT / "project.godot")
    for path in sorted((ROOT / "scripts").rglob("*.gd")):
        parse_gdscript(graph, path)
    for path in sorted((ROOT / "scenes").rglob("*.tscn")):
        parse_scene(graph, path)
    parse_python(graph, ROOT / "tools/generate_heightmap.py")
    parse_docs(graph)
    return graph


def main() -> None:
    graph = build()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data = {
        "directed": True,
        "multigraph": False,
        "graph": {
            "name": "Umbral-Godot",
            "adapter": "tools/generar_graphify_umbral.py",
            "scope": "active-project-files",
        },
        "nodes": sorted(graph.nodes.values(), key=lambda item: item["id"]),
        "links": sorted(
            graph.links,
            key=lambda item: (item["source"], item["target"], item["relation"]),
        ),
        "hyperedges": [],
    }
    (OUTPUT / "graph.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (OUTPUT / ".graphify_root").write_text(str(ROOT.resolve()), encoding="utf-8")
    print(f"Umbral Graphify: {len(data['nodes'])} nodos, {len(data['links'])} relaciones.")


if __name__ == "__main__":
    main()
