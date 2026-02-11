# TODO — Fallback policy for Agent A

Pendiente de decisión (post-PRD-015):

## Pregunta clave
¿Qué hacer cuando Agent A falla técnicamente?
- Ejemplos: 404 de modelo, timeout, error de conexión, provider saturado.

## Opciones a evaluar
1. **Modo benchmark (estricto):** retornar error tipado y no fallback silencioso.
2. **Modo producción (resiliente):** fallback determinista automático con metadatos de causa.
3. **Modo híbrido:** benchmark en entornos de prueba, fallback en producción.

## Contrato sugerido para error tipado
- `agent_a_status`: `ok | unavailable | timeout | model_not_found | provider_error`
- `agent_a_error_code`
- `agent_a_error_detail` (sanitizado)
- `used_deterministic_fallback: bool`

## Próximo paso
Definir política única por entorno y agregar tests de 404/timeout/conexión en orquestación agentic.
