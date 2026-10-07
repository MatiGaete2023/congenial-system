# AUTOLOOP.md

Este proyecto debe trabajarse mediante ciclos controlados de implementación,
prueba y corrección.

## Ciclo obligatorio

Para cada tarea:

1. Definir objetivo.
2. Identificar archivos relevantes.
3. Hacer cambio mínimo.
4. Ejecutar prueba.
5. Leer resultado.
6. Corregir.
7. Repetir máximo 3 veces.
8. Registrar resultado.

## Prohibiciones

- No hacer loops infinitos.
- No reescribir todo el proyecto.
- No modificar archivos no relacionados.
- No optimizar antes de tener funcionamiento básico.
- No afirmar éxito sin prueba.
- No consumir API si existe modo dry-run suficiente.
- No enviar documentos completos al modelo salvo necesidad justificada.
- No borrar archivos sin respaldo.

## Ahorro de tokens

- Usar búsqueda antes que lectura completa.
- Leer solo funciones o archivos relevantes.
- Resumir hallazgos en vez de copiar archivos.
- Reutilizar resultados previos.
- Usar caché por hash para bloques procesados.
- Separar pruebas locales de pruebas con API.

## Criterios de éxito

Una tarea se considera lista solo si:

- el cambio fue implementado;
- existe prueba o verificación;
- la prueba fue ejecutada;
- el resultado quedó documentado;
- no se rompió una etapa anterior.
