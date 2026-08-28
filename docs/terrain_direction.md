# Direccion del terreno de Umbral

## Objetivo de la primera etapa

Obtener un terreno reconocible, explorable y con buena composicion antes de desarrollar cualquier sistema de juego. La referencia es la claridad visual y verticalidad de los mundos abiertos estilizados, sin copiar mapas ni recursos de otros juegos.

## Escala activa

La base activa mide 10 km x 10 km. El heightmap es de 2048 x 2048 muestras, equivalente a 4.8828125 metros por vertice. Esta densidad se eligio para conservar la escala amplia sin crear una malla de cien millones de vertices.

## Composicion activa

1. Acantilados conectados al noroeste con una corona montanosa reconocible.
2. Cadena de picos al norte con pasos que evitan una pared continua.
3. Escarpes y mesetas de dos niveles al este.
4. Valle central amplio, dividido por mesetas interiores y rutas naturales.
5. Corredor fluvial sinuoso que desciende del norte hacia una cuenca sur irregular.
6. Mesetas secundarias al suroeste y sureste para futuros hitos.
7. Pradera de aparicion al sureste para medir escala y transitabilidad.

## Referencia visual aprobada

La meta visual de esta base esta guardada en `docs/references/terrain_world_10km_visual_target.png`. La imagen parte de la captura real del relieve de 10 km y simula las capas futuras: roca estratificada, praderas, corredor de agua turquesa, cascadas, senderos, arboledas dispersas, ruinas y puntos de interes lejanos.

Esta imagen es una guia de arte y composicion, no una captura del estado implementado. El relieve reproducible y el R16 siguen siendo la fuente de verdad. Deben conservarse grandes espacios abiertos y rutas legibles; la vegetacion y los hitos no deben llenar todo el mapa.

Orden previsto para aproximarse a la referencia:

1. Aprobar relieve, escala, pendientes y rutas.
2. Definir niveles de rio, lago y cascadas.
3. Crear materiales finales de hierba, roca y suelo.
4. Trazar senderos y reservar puntos de interes.
5. Distribuir vegetacion por zonas y densidad.
6. Agregar ruinas, asentamientos, iluminacion y atmosfera.

## Regla de construccion

- La forma grande del mundo es intencional y reproducible.
- El ruido solo agrega irregularidad natural de baja intensidad.
- El jugador debe distinguir destinos desde lejos.
- Las pendientes importantes deben crear rutas, no bloquear toda la exploracion.
- Las formas grandes se construyen con mesetas irregulares, gaussianas orientadas y depresiones intencionales.
- Los bordes de acantilado deben ser legibles sin convertirse en figuras geometricas perfectas.
- La escala horizontal y la resolucion se mantienen separadas: ampliar el mundo no significa generar una imagen de 10 000 x 10 000.

## Criterios para aprobar el terreno

- Los sistemas de acantilados oeste y este se distinguen desde el punto inicial.
- El valle ofrece al menos dos rutas visualmente diferentes.
- El cauce mantiene una direccion legible de extremo a extremo.
- Existen zonas planas suficientes para futuros puntos de interes.
- La escena mantiene una navegacion fluida en la laptop de William.
- La vista 3D no muestra escalones de cuantizacion ni paredes circulares repetitivas.

## Fuera de alcance por ahora

- Combate y enemigos.
- Vegetacion definitiva.
- Materiales definitivos y agua renderizada.
- Edificios terminados.
- Misiones, inventario y progresion.
- Mundo procedural infinito.
