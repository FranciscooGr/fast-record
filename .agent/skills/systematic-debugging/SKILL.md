---
name: systematic-debugging
description: Use when debugging FastAPI errors, failed webhook deliveries, LLM orchestration issues, database query problems, or any unexpected backend behavior.
---

# Systematic Debugging — Backend Master

## Use this skill when
- Un endpoint devuelve un error inesperado
- El webhook de WhatsApp no está llegando o falla silenciosamente
- La orquestación LLM (Gemini/Groq) no hace fallback correctamente
- Una query SQL devuelve resultados incorrectos
- Un test falla y no está claro por qué

## Proceso de debugging (seguir en orden)

### 1. Reproducir el error de forma mínima
```python
# Aislar el problema — reducir al mínimo que lo reproduce
# Si es un endpoint: usar curl o httpx directamente
import httpx
response = httpx.post("http://localhost:8000/api/v1/webhook", json={...})
print(response.status_code, response.json())
```

### 2. Leer el traceback completo
- Ir al error MÁS INTERNO del stack trace
- No asumir que el error está donde dice la primera línea
- Buscar el `caused by` si existe

### 3. Agregar logging temporal
```python
import structlog
log = structlog.get_logger()

# Agregar antes y después del punto sospechoso
log.debug("antes_de_llamada", payload=payload, service="whatsapp")
result = await servicio_sospechoso()
log.debug("despues_de_llamada", result=result)
```

### 4. Verificar el estado de la DB
```sql
-- Ver las últimas transacciones insertadas
SELECT * FROM transacciones ORDER BY created_at DESC LIMIT 10;

-- Verificar que el saldo calculado es correcto
SELECT cuenta_id,
       SUM(CASE WHEN tipo = 'ingreso' THEN monto ELSE -monto END) AS saldo
FROM transacciones GROUP BY cuenta_id;
```

### 5. Debugging de webhooks WhatsApp
```python
# Verificar que la firma HMAC es válida
import hmac, hashlib

def debug_webhook_signature(raw_body: bytes, header_sig: str, secret: str):
    computed = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    print(f"Expected: sha256={computed}")
    print(f"Received: {header_sig}")
    print(f"Match: {hmac.compare_digest(f'sha256={computed}', header_sig)}")
```

### 6. Debugging del fallback LLM
```python
# Verificar cada paso del fallback manualmente
async def debug_llm_fallback(prompt: str):
    try:
        result = await gemini_call(prompt)
        print("Gemini OK:", result)
    except Exception as e:
        print("Gemini FAIL:", e)
        try:
            result = await groq_call(prompt)
            print("Groq OK:", result)
        except Exception as e2:
            print("Groq FAIL:", e2)
            print("→ Fallback a categoría 'Otros'")
```

## Errores comunes y soluciones

| Error | Causa probable | Solución |
|---|---|---|
| `422 Unprocessable Entity` | Schema Pydantic no coincide | Revisar tipos en el DTO |
| `asyncpg.exceptions` | Query async mal formada | Verificar `await` y sesión DB |
| `401 Unauthorized` | JWT expirado o mal formado | Verificar `exp` y `SECRET_KEY` |
| `WebhookVerificationError` | HMAC no coincide | Verificar que el body no fue modificado |
| `LLM timeout` | Proveedor lento | Ajustar timeout y activar fallback |

## Do not
- No agregar prints en producción — usar structlog
- No asumir el error sin reproducirlo primero
- No modificar código de producción para debuggear — usar tests
