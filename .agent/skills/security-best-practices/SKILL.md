---
name: security-best-practices
description: Use when implementing JWT authentication, WhatsApp webhook HMAC verification, input validation, secret management, CORS or any security concern in ./backend. Do not use for frontend security.
---

# Security Best Practices — Backend Master

## Use this skill when
- Implementando autenticación JWT
- Verificando firmas HMAC de webhooks de WhatsApp
- Configurando CORS para el frontend Angular
- Manejando secretos y variables de entorno
- Validando inputs externos con Pydantic

## JWT — Autenticación
```python
# core/security.py
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.core.config import settings

def create_access_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {**data, "exp": expire},
        settings.SECRET_KEY,
        algorithm="HS256"
    )

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
```

## WhatsApp Webhook — Verificación HMAC
```python
# services/whatsapp.py
import hmac, hashlib
from fastapi import Request, HTTPException
from app.core.config import settings

async def verify_whatsapp_signature(request: Request) -> bytes:
    signature = request.headers.get("X-Hub-Signature-256", "")
    raw_body = await request.body()

    expected = "sha256=" + hmac.new(
        settings.WHATSAPP_APP_SECRET.encode(),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Firma de webhook inválida")

    return raw_body
```

## Pydantic — Validación estricta de inputs
```python
# schemas/webhook.py
from pydantic import BaseModel, field_validator
from typing import Literal

class WhatsAppMessage(BaseModel):
    object: Literal["whatsapp_business_account"]  # solo acepta este valor
    entry: list

    @field_validator("entry")
    def entry_no_vacio(cls, v):
        if not v:
            raise ValueError("entry no puede estar vacío")
        return v
```

## CORS — Configuración para Angular
```python
# main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # solo el frontend Angular
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

## Secrets — Variables de entorno
```bash
# .env (nunca commitear este archivo)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/fast_record
SECRET_KEY=genera-con-openssl-rand-hex-32
WHATSAPP_APP_SECRET=secret-de-meta-developers
WHATSAPP_VERIFY_TOKEN=token-de-verificacion
GEMINI_API_KEY=tu-api-key
GROQ_API_KEY=tu-api-key
```

```python
# .env.example (sí commitear — sin valores reales)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname
SECRET_KEY=change-me
WHATSAPP_APP_SECRET=change-me
WHATSAPP_VERIFY_TOKEN=change-me
GEMINI_API_KEY=change-me
GROQ_API_KEY=change-me
```

## Checklist de seguridad antes de cada PR
- [ ] ¿Hay secretos hardcodeados? → Mover a `.env`
- [ ] ¿El webhook verifica la firma HMAC?
- [ ] ¿Los JWT tienen `exp`?
- [ ] ¿Los inputs externos pasan por Pydantic?
- [ ] ¿El `.env` está en `.gitignore`?

## Do not
- No loggear tokens, passwords ni payloads crudos de WhatsApp
- No saltear la verificación HMAC en desarrollo
- No usar `allow_origins=["*"]` en producción
- No guardar el SECRET_KEY en el código fuente
- No usar algoritmos débiles (MD5, SHA1) para hashing de passwords
