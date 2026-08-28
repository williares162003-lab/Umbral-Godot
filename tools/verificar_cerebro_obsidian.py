"""Verifica la cobertura minima del cerebro Obsidian de Umbral-Godot."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


DEFAULT_VAULT = Path(
    os.environ.get(
        "OBSIDIAN_VAULT",
        r"C:\Users\WILLIAM\Documents\BOVEDA DE CONOCIMIENTO\WILLIAM",
    )
)

REQUIRED_REPO_FILES = [
    "project.godot",
    "README.md",
    "docs/terrain_direction.md",
    "docs/references/terrain_world_10km_visual_target.png",
    "scenes/terrain/TerrainPrototype.tscn",
    "scripts/terrain/terrain_prototype.gd",
    "scripts/terrain/terrain_fly_camera.gd",
    "tools/generate_heightmap.py",
    "tools/generar_graphify_umbral.py",
    "assets/terrain/heightmaps/umbral_world_heightmap.r16",
    "assets/terrain/heightmaps/umbral_world_layout.json",
]

REQUIRED_NOTES = [
    "Projects/Umbral/Umbral - Mapa principal.md",
    "Projects/Umbral/Arquitectura y navegacion.md",
    "Projects/Umbral/Estado pruebas y pendientes.md",
    "Projects/Umbral/Direccion/Vision alcance y roadmap.md",
    "Projects/Umbral/Mundo abierto/Mundo visuales y rendimiento.md",
    "Projects/Umbral/Mundo abierto/Diseno del terreno y regiones.md",
    "Projects/Umbral/Mundo abierto/Pipeline de heightmap y assets.md",
    "Projects/Umbral/Calidad/Criterios de aprobacion y pruebas.md",
    "Projects/Umbral/Operacion/Ejecucion controles y diagnostico.md",
    "Projects/Umbral/Historico/Unity - Referencia tecnica.md",
    "Risks/Umbral - Riesgos.md",
    "Decisions/2026-08-27 - Umbral prioriza terreno en Godot.md",
    "Decisions/2026-08-28 - Umbral adopta base de 10 km.md",
    "Debug Logs/2026-08-28 - Umbral - Generador portable sin Pillow.md",
]


def note_targets(vault: Path, text: str) -> list[str]:
    broken: list[str] = []
    for raw in re.findall(r"\[\[([^\]|#]+)", text):
        key = raw.strip()
        if not key or key.startswith("http"):
            continue
        if not (vault / f"{key}.md").exists():
            broken.append(key)
    return broken


def verify(repo: Path, vault: Path) -> int:
    errors: list[str] = []
    for relative in REQUIRED_REPO_FILES:
        if not (repo / relative).is_file():
            errors.append(f"Falta archivo del proyecto: {relative}")

    for relative in REQUIRED_NOTES:
        note = vault / relative
        if not note.is_file():
            errors.append(f"Falta nota requerida: {relative}")

    project_notes = vault / "Projects/Umbral"
    for note in project_notes.rglob("*.md") if project_notes.exists() else []:
        for target in note_targets(vault, note.read_text(encoding="utf-8")):
            errors.append(f"Wikilink roto: {note.relative_to(vault).as_posix()} -> {target}")

    graph_path = repo / "graphify-out/graph.json"
    if not graph_path.is_file():
        errors.append("Falta graphify-out/graph.json del proyecto activo.")
    else:
        try:
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            if len(graph.get("nodes", [])) < 10 or len(graph.get("links", [])) < 10:
                errors.append("El grafo activo tiene cobertura insuficiente.")
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"No se pudo leer graphify-out/graph.json: {exc}")

    hub = vault / "Projects/Umbral/Umbral - Mapa principal.md"
    if hub.is_file():
        hub_text = hub.read_text(encoding="utf-8")
        expected = repo.as_posix()
        if expected not in hub_text:
            errors.append("El mapa principal no apunta al proyecto Godot activo.")
        if "10 km x 10 km" not in hub_text:
            errors.append("El mapa principal no registra la escala activa de 10 km.")
        if "terrain_world_10km_visual_target.png" not in hub_text:
            errors.append("El mapa principal no enlaza la referencia visual aprobada.")
        if "umbral_world_heightmap.r16" not in (
            vault / "Projects/Umbral/Mundo abierto/Pipeline de heightmap y assets.md"
        ).read_text(encoding="utf-8"):
            errors.append("La nota del pipeline no apunta al R16 activo de 10 km.")

    for error in sorted(set(errors)):
        print(f"ERROR {error}")
    if errors:
        print("RESULTADO cerebro de Umbral incompleto o desactualizado.")
        return 1
    print("RESULTADO cerebro de Umbral vigente, distribuido y enlazado.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--sync", action="store_true")
    args = parser.parse_args()
    if args.sync:
        print("SYNC Umbral: no hay inventarios Obsidian generados dentro del repo.")
    raise SystemExit(verify(args.repo.resolve(), args.vault.resolve()))


if __name__ == "__main__":
    main()
