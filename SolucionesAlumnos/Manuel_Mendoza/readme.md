# Examen 1

## Ejercicio 1 — 1_Laberinto.ipynb

Objetivo  
Mostrar la generación del laberinto y la solución paso a paso, con visualizaciones que permitan entender el proceso.

Requisitos mínimos

- Generar y mostrar la representación inicial del laberinto (texto y/o gráfico).
- Visualizar la evolución de la resolución: secuencia de estados o animación que permita ver las celdas visitadas, la celda actual y el progreso hacia la meta.
- Indicar claramente la celda de inicio y la celda objetivo en las visualizaciones.
- Mostrar el camino final y su longitud (número de pasos).
- Incluir instrucciones claras para ejecutar el notebook: cómo ejecutar todas las celdas y qué parámetros opcionales existen (por ejemplo, semilla aleatoria, tamaño del laberinto, modos de visualización).

Entrega

- Archivo 1_Laberinto.ipynb con visualizaciones funcionales y una breve sección “Cómo reproducir” que explique los pasos para ejecutar y repetir los resultados.

Criterios de evaluación (breves)

- Claridad de las visualizaciones y de la explicación.
- Correcta demostración de la evolución del algoritmo.
- Reproducibilidad usando los parámetros indicados.

## Ejercicio 2 — PacMan.py

Objetivo  
Implementar un agente que recorra el mapa y recoja todos los puntos (pellets) respetando paredes y límites.

Requisitos mínimos

- Implementar una función principal pública (por ejemplo: solve(maze, start) o main ejecutable) que devuelva la secuencia de movimientos o la lista de posiciones visitadas hasta recoger todos los pellets.
- El agente debe respetar paredes y límites y finalizar únicamente cuando no queden pellets por recoger.
- Informar en la salida: la ruta encontrada, el número total de pasos y un tiempo de ejecución aproximado.
- Añadir un docstring en PacMan.py que describa la interfaz: formato del laberinto (p. ej. matriz/lista de strings), representación de paredes, pellets y posición de inicio, y el formato de salida.
- Incluir una breve explicación (README o comentario) del algoritmo elegido (ej.: búsqueda greedy, A\*, aproximación a TSP) y la motivación de la elección.
- Proveer al menos un ejemplo de uso y un caso de prueba sencillo (entrada y salida esperada).

Entrega

- Archivo PacMan.py funcional con docstring y un ejemplo de ejecución (o script de prueba).

Criterios de evaluación (breves)

- Correctitud (recoge todos los pellets sin traspasar muros).
- Claridad de la interfaz y documentación.
- Eficiencia razonable para mapas de tamaño moderado.

## Ejercicio 3 — PacMan con enemigos

Objetivo  
Extender PacMan para incluir enemigos que quiten vidas al tocar al agente.

Requisitos mínimos

- Añadir enemigos móviles en el mapa cuya colisión con el agente reduzca su contador de vidas.
- Definir reglas claras de movimiento de los enemigos (p. ej. patrulla fija, movimiento aleatorio, o búsqueda del jugador).
- Especificar las condiciones de fin: vidas agotadas -> fallo; pellets recogidos -> éxito (siempre que el agente aún tenga vidas).
- Mostrar en la salida eventos relevantes: colisiones, vidas restantes, ruta seguida y estado final.

Entrega

- Versión de PacMan2.py que soporte enemigos y documente las reglas de movimiento y las condiciones de colisión.

Criterios de evaluación (breves)

- Implementación coherente de colisiones y vidas.
- Registro claro de eventos y estado final.

## Ejercicio 4 — Evitar enemigos y completar la recolección

Objetivo  
Modificar el algoritmo para que Evite a los enemigos y, a la vez, capture todos los pellets.

Requisitos mínimos

- Implementar estrategias para evitar colisiones (ej.: planificación con obstáculos dinámicos, margen de seguridad, replanteo en tiempo real).
- El agente debe intentar recoger todos los pellets si es posible; si la recolección completa es impossible por la dinámica de los enemigos, debe informar qué pellets no pudo alcanzar y por qué.
- Mantener las restricciones del entorno: no atravesar muros ni salir del mapa.
- Documentar la estrategia usada (replanning frecuente, predicción simple de rutas enemigas, heurística de seguridad) y sus limitaciones.
- Incluir ejemplos de ejecución donde se muestre comportamiento exitoso (evita enemigos y recoge todo) y uno donde no sea posible completar la tarea.

Entrega

- Versión modificada de PacMan3.py con la lógica de evasión, documentación de la estrategia y ejemplos de prueba.

Criterios de evaluación (breves)

- Capacidad del agente para evitar enemigos y aún así recoger pellets.
- Calidad de la estrategia de replanteo/predicción.
- Claridad en la documentación sobre cuándo la solución es o no factible.

Notas generales para todos los ejercicios

- Preferible código limpio, modular y con tests mínimos o ejemplos reproducibles.
- Indicar claramente comandos para ejecutar los ejemplos (p. ej. python PacMan.py --map sample.txt --start 1,1 --seed 42).
- Comentar supuestos sobre el formato de entrada y cómo se representan muros, pellets y enemigos.
- Si se usan librerías externas, incluir instrucciones de instalación (requirements.txt o pip install).
- Puntuarán especialmente las soluciones reproducibles y bien documentadas.


## Nota importante sobre los ejercicios 2, 3 y 4

- Para que los ejercicios 2, 3 y 4 sean evaluados debes personalizar el juego: modificar la interfaz es obligatorio.
- "Personalizar la interfaz" incluye, por ejemplo, añadir nuevos parámetros de ejecución, cambiar la representación del mapa, introducir nuevos comandos o elementos visibles en la interfaz, o proporcionar una versión del juego con opciones de configuración distintas a la original.
- Si no se realiza una modificación explícita de la interfaz del juego, las soluciones a los ejercicios 2, 3 y 4 no serán tenidas en cuenta.
- Indica en tu entrega qué cambios de interfaz hiciste y cómo probarlos (comandos exactos o ejemplos).
- Si usas dependencias externas, añade instrucciones de instalación (requirements.txt o pip install).
- Se valorará especialmente la reproducibilidad y la documentación clara.


## Ejercicio 5 — Genera un pull request

Objetivo  
Entregar el examen también mediante un Pull Request (PR) en el repositorio público Examen1Robotica, además de subir el .zip a Blackboard. Esto facilita revisión y control de versiones.

Requisitos mínimos

- Crear una rama nueva para tu entrega con un nombre claro (ej.: feature/Apellido_Nombre).
- Dentro del repositorio, crear una carpeta con tu nombre (ej.: Apellido_Nombre) en la que se ubique todo tu código, notebooks, README y ficheros necesarios.
- Incluir un README breve en esa carpeta que describa qué contiene, cómo ejecutar los ejemplos y los comandos principales.
- Hacer commits claros y atómicos; subir (push) la rama al repositorio remoto y abrir un Pull Request hacia la rama principal del repositorio Examen1Robotica.
- En el cuerpo del PR indicar: resumen de la entrega, archivos principales, cómo reproducir y cualquier limitación conocida.
- Además de crear el PR, comprimir tu entrega (.zip) y subirla a Blackboard según las instrucciones del curso.

Entrega

- Pull Request abierto en Examen1Robotica con la rama creada y la carpeta con tu nombre.
- Archivo .zip subido a Blackboard con la misma estructura entregada en el PR.
- Indicar en el PR el enlace al .zip (si procede) o la confirmación de subida a Blackboard.

Criterios de evaluación (breves)

- Correcta estructura del repositorio (rama, carpeta con nombre, README).
- PR descriptivo y reproducible (instrucciones claras para ejecutar).
- Consistencia entre lo subido al repositorio y el .zip en Blackboard.

Pasos sugeridos (comandos)

- git checkout -b feature/Apellido_Nombre
- mkdir Apellido_Nombre && cp -r path/to/tu_codigo Apellido_Nombre/
- git add Apellido_Nombre
- git commit -m "Entrega: Apellido Nombre — Examen 1"
- git push origin feature/Apellido_Nombre
- Abrir Pull Request en GitHub: título claro (p. ej. "Entrega Examen1 - Apellido Nombre") y descripción con instrucciones de reproducción.
- Crear .zip (ej.: zip -r Apellido_Nombre_Examen1.zip Apellido_Nombre) y subir a Blackboard.

Recomendaciones rápidas

- Verifica que el README incluya comandos exactos para ejecutar (ej.: python PacMan.py --map sample.txt --start 1,1).
- Si usas dependencias externas, añade requirements.txt.
- Comprueba que los notebooks corran en orden y que las rutas sean relativas para facilitar ejecución local.

## Ejercicio 6 — Modifica el archivo procedural.py

Objetivo  
Personalizar procedural.py para añadir un nuevo elemento coleccionable en el mapa y desarrollar un algoritmo que lo localice y recoja.

Requisitos mínimos

- Añadir en procedural.py al menos un nuevo tipo de elemento (por ejemplo: llave, power‑up, gema) y su representación en el mapa.
- Implementar una función pública (ej.: find_item(maze, start, item_type) o integrar la funcionalidad en la API existente) que devuelva la secuencia de movimientos o la lista de posiciones hasta alcanzar el elemento, o indique que no es accesible.
- El agente debe respetar paredes y límites; el algoritmo puede usar BFS/DFS/A\*/otra heurística, con breve justificación en comentarios.
- Incluir docstring que describa la interfaz: formato del mapa (matriz/lista de strings), cómo se representa el nuevo elemento, parámetros de entrada y formato de salida.
- Añadir al menos un ejemplo de ejecución y un caso de prueba sencillo (entrada y salida esperada).
- Registrar en la salida información relevante: ruta encontrada, longitud (n.º de pasos) y tiempo aproximado de ejecución.

Entrega

- Archivo procedural.py modificado con docstrings y ejemplos reproducibles.
- Breve nota (README o comentario) explicando los cambios y cómo ejecutar los ejemplos (comando exacto).

Criterios de evaluación (breves)

- Correctitud: el algoritmo encuentra el elemento sin atravesar muros.
- Claridad de la interfaz y documentación.
- Reproducibilidad del ejemplo provisto.
