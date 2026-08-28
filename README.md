# Umbral - Godot

Nueva base de Umbral enfocada primero en el terreno. El proyecto original de Unity se conserva por separado como referencia tecnica y visual.

## Prioridad actual

Construir y validar una base geografica de 10 km x 10 km con composicion manual:

- sistemas de acantilados conectados al noroeste y este;
- valle central amplio con pasos naturales;
- corredor fluvial sinuoso de norte a sur;
- cuenca lacustre irregular al sur;
- mesetas escalonadas y cimas anchas para futuros puntos de interes;
- pradera inicial al sureste para comprobar escala.

No se agregaran materiales definitivos, agua, vegetacion, edificios, combate, enemigos, inventario ni misiones hasta aprobar la forma del terreno.

## Abrir

Ejecutar `Abrir Umbral Godot.cmd` o abrir esta carpeta desde Godot 4.6.3. La etapa de terreno usa GDScript porque Terrain3D se integra directamente con el editor; el lenguaje del gameplay se decidira cuando el mapa base este aprobado.

## Archivos principales

- `assets/terrain/heightmaps/umbral_world_heightmap.r16`: relieve activo de 2048 x 2048 con precision de 16 bits.
- `assets/terrain/heightmaps/umbral_world_heightmap.png`: copia visual de 16 bits.
- `assets/terrain/heightmaps/umbral_world_preview.png`: vista superior coloreada de composicion.
- `assets/terrain/heightmaps/umbral_world_layout.json`: escala y coordenadas de los hitos principales.
- `scenes/terrain/TerrainPrototype.tscn`: escena principal.
- `scripts/terrain/terrain_prototype.gd`: carga el terreno en Terrain3D.
- `scripts/terrain/terrain_fly_camera.gd`: camara libre de inspeccion.
- `docs/terrain_direction.md`: direccion del mapa y criterios de aprobacion.

## Regenerar el relieve

```powershell
C:\Users\WILLIAM\Documents\Codex\Herramientas\Graphify\venv\Scripts\python.exe tools\generate_heightmap.py
```

La semilla `162003` es fija, por lo que el resultado es reproducible. El generador solo necesita NumPy: escribe los PNG con la biblioteca estandar y no depende de Pillow. El relieve general se disena de forma intencional; el ruido solo aporta variacion secundaria.

Terrain3D representa los 10 000 metros con 2048 muestras y `4.8828125 m` entre vertices. La escena carga el archivo R16 para evitar escalones visibles en las pendientes. El PNG queda como referencia, pero no se usa para construir la malla.
