# Examen de Robótica Industrial – PacMan y Procedural

Este repositorio contiene tres ejercicios de Pac-Man con diferentes objetivos, cada uno con la función `solve()` implementada, documentación y personalizaciones de la interfaz y el ejercicio de Procedural con el elemento extra.

---

## Ejercicio 2 — `PacMan.py`

**Objetivo:** Implementar un agente que recorra el mapa y recoja todos los pellets respetando paredes y límites.

**Personalización de interfaz añadida:**  
- Soporte para múltiples mapas seleccionables con `--map (1, 2 o 3)`.  
- En la interfaz gráfica se muestra cuántos pellets quedan por recoger.  

**Ejemplo de uso:**  
```bash
python PacMan.py --map 1
python PacMan.py --map 2
python PacMan.py --map 3
```
**Salida en consola al terminar:**
- Ruta encontrada (lista de movimientos).
- Número de pasos.
- Tiempo de ejecución.

---

## Ejercicio 3 — `PacMan2.py`

**Objetivo:** Extender Pac-Man para incluir enemigos móviles que quitan vidas al tocar al agente.

**Reglas:**
- Enemigos se mueven de forma aleatoria “inteligente”.
- Colisiones restan vidas y - generan respawn con 2 segundos de invulnerabilidad.
- WIN si recolecta todos los pellets con ≥1 vida.
- GAME OVER si las vidas llegan a 0.

**Personalización de interfaz añadida:**
- Soporte para múltiples mapas seleccionables con --map.
- En la interfaz gráfica se muestra cuántos pellets quedan por recoger.

**Ejemplo de uso:**
```bash
python PacMan2.py --map 1
python PacMan2.py --map 2
python PacMan2.py --map 3
```
**Salida en consola al terminar:**
- Eventos de colisión con enemigos y vidas restantes.
- Estado final: WIN o GAME OVER.
- Ruta encontrada con pasos, tiempo y movimientos.

---

## Ejercicio 4 — `PacMan3.py`

**Objetivo:** Extender Pac-Man con evasión de enemigos y estrategia de replanteo de rutas.

**Estrategia implementada:**
- Los enemigos y sus celdas vecinas son tratados como obstáculos dinámicos.
- El agente replantea su ruta en cada celda.
- Si un pellet queda bloqueado por enemigos → se marca como inaccesible.

**Personalización de interfaz añadida:**
- Soporte para múltiples mapas seleccionables con --map.
- En la interfaz gráfica se muestra cuántos pellets quedan por recoger.
- Ejemplos de ejecución con mini mapas en consola:
    - MINI_MAP_SUCCESS: Pac-Man recoge todos los pellets.
    - MINI_MAP_FAIL: Un fantasma bloquea un pellet, se reporta como inaccesible.

**Ejemplo de uso:**
```bash
python PacMan3.py --map 1
python PacMan3.py --map 2
python PacMan2.py --map 3
```
**Salida en consola al terminar:**
- Eventos de evasión y pellets inaccesibles.
- Estado final (WIN, LOSE o parcial).
- Ruta encontrada con pasos, tiempo y movimientos.

---

## Dependencias

El proyecto usa la librería arcade. Instalar con:

```bash
pip install arcade 
```

---

## Notas

- Cada script (`PacMan.py`, `PacMan2.py`, `PacMan3.py`) es ejecutable de forma independiente.
- Todos incluyen documentación de interfaz en el docstring inicial.
- Las personalizaciones de interfaz están claramente descritas y visibles en ejecución.

---

## Ejercicio 6 — `Procedural.py` con llaves

**Para ejecutar el caso de prueba:**

```bash
python Procedural.py
```
La consola mostrará primero un caso de prueba sencillo de BFS con la salida esperada y la obtenida.
Después se abrirá el juego automáticamente.

**Ejemplo de salida en consola:**

```bash
=== Caso de prueba BFS ===
Salida esperada: [(0,0), (1,0), (1,1), (1,2)]
Salida obtenida: [(0,0), (1,0), (1,1), (1,2)]
==========================
```
