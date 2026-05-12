# 🆘 Troubleshooting Guide - Heavy Freight Platform

Guía rápida para diagnosticar y resolver problemas en AWS Lambda deployment.

---

## 🔴 Production Down / 500 Errors

### Checklist Inmediato

```bash
# 1. Ver últimos errores
aws logs tail /aws/lambda/heavy-freight-api-production --follow -n 50

# 2. Revisar health endpoints
curl https://$ENDPOINT/health/live
curl https://$ENDPOINT/health/ready
curl https://$ENDPOINT/health/deep | jq .

# 3. Verificar Secrets Manager acceso
aws secretsmanager get-secret-value --secret-id /heavy-freight/production/JWT_SECRET_KEY

# 4. Revisar Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=heavy-freight-api-production \
  --start-time $(date -u -d '5 min ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum
```

### Diagnóstico Step-by-Step

#### Problema: `503 Service Unavailable`

```bash
# Causa 1: MongoDB circuit breaker OPEN
grep "CircuitBreaker" /aws/lambda/heavy-freight-api-production | tail -20

# Solución:
# - MongoDB se recuperó? Verificar: mongo shell o AWS console
# - Si recovered: esperar 60 segundos (RECOVERY_TIMEOUT)
# - Si no: escalate a DevOps, MongoDB es crítico
```

#### Problema: `502 Bad Gateway`

```bash
# Causa 1: Lambda timeout
aws logs tail /aws/lambda/heavy-freight-api-production | grep "Task timed out"

# Solución:
# Ver qué endpoint está lento:
grep "duration_ms" /aws/lambda/heavy-freight-api-production | awk -F'"duration_ms": ' '{print $2}' | sort -rn | head

# Si /health/deep está lento: aumentar timeout en serverless.yml timeout: 60
# Si /api/trips está lento: optimizar MongoDB query
```

#### Problema: `422 Validation Error`

```bash
# Esto es EXPECTED - cliente envió datos inválidos
# No es un error de backend

# Ver qué field está causando problemas:
jq '.errors[0].field' < /tmp/response.json

# Informar al client qué cambiar
```

---

## 📊 Performance Issues (Requests > 5 segundos)

### Identificar Endpoint Lento

```bash
# CloudWatch Insights
fields @timestamp, path, duration_ms, status_code
| filter duration_ms > 5000
| stats avg(duration_ms) as avg_ms, max(duration_ms) as max_ms, count() as requests by path
| sort max_ms desc
```

### Diagnóstico por Endpoint

#### GET /api/trips muy lento

```bash
# 1. ¿Es query sin filtros?
fields @timestamp, query_string, duration_ms
| filter path = "/api/trips"
| stats avg(duration_ms) as avg_ms by query_string
| sort avg_ms desc

# 2. ¿MongoDB tiene índices?
# Conectar a MongoDB y verificar:
db.trips.getIndexes()
# Debe haber índice en { status: 1 }

# 3. ¿Circuit breaker está retrying?
fields @timestamp, message, attempt
| filter message like /list_trips/
| stats max(attempt) as max_attempts by @message

# Solución:
# - Agregar índice: db.trips.createIndex({ status: 1, created_at: -1 })
# - Limitar query: add pagination filters
# - Aumentar Lambda memory: serverless.yml memorySize: 1024
```

#### POST /api/trips muy lento

```bash
# 1. ¿Request es muy grande?
fields @timestamp, content_length, duration_ms
| filter path = "/api/trips" and method = "POST"
| stats avg(duration_ms) by content_length
| sort content_length desc

# 2. MongoDB insert lento?
# Verificar write concern en connection string

# Solución:
# - Comprimir payloads en client
# - Usar bulk inserts
# - Verificar MongoDB write performance
```

---

## 💾 Secrets Manager Issues

### Error: `Permission Denied Getting Secret`

```bash
# 1. Verificar IAM role tiene permisos
aws iam get-role-policy \
  --role-name heavy-freight-lambda-role \
  --policy-name heavy-freight-permissions

# 2. Verificar resource ARN es correcto
# Debe tener: arn:aws:secretsmanager:us-east-1:*:secret:/heavy-freight/production/*

# 3. Re-crear role si falta permiso
aws iam put-role-policy \
  --role-name heavy-freight-lambda-role \
  --policy-name heavy-freight-permissions \
  --policy-document file://./iam-permissions.json

# 4. Update Lambda role en serverless.yml
serverless deploy --stage production
```

### Error: `Secret Not Found`

```bash
# 1. Verificar nombre exacto
aws secretsmanager list-secrets | grep heavy-freight

# 2. Verificar región correcta
aws secretsmanager get-secret-value \
  --secret-id /heavy-freight/production/JWT_SECRET_KEY \
  --region us-east-1

# 3. Si no existe, crear:
aws secretsmanager create-secret \
  --name /heavy-freight/production/JWT_SECRET_KEY \
  --secret-string "$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  --region us-east-1
```

### Error: `Invalid JWT Token`

```bash
# 1. Verificar JWT_SECRET_KEY es igual que usada para sign
# En local test:
python << 'EOF'
from src.schemas.auth import AuthService
from os import environ

# Crear token con local secret
local_secret = environ.get("JWT_SECRET_KEY")
token = AuthService.create_token(user_id="test", secret=local_secret)
print(f"Token: {token}")

# Verificar con Lambda secret
jwt_secret = "...copy from AWS Secrets Manager..."
try:
    decoded = AuthService.verify_token(token, secret=jwt_secret)
    print("✓ Token válido")
except:
    print("✗ Token inválido - secrets no coinciden")
EOF

# 2. Si no coinciden, update JWT_SECRET_KEY en Secrets Manager
# Pero TODOS los tokens anteriores se invalidarán!
```

---

## 🔌 MongoDB Connection Issues

### Error: `Connection Timeout` (30+ seconds)

```bash
# 1. Verificar MONGO_URI en Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id /heavy-freight/production/MONGO_URI

# Expected format:
# mongodb+srv://user:strong-password@cluster.mongodb.net/heavy_freight?retryWrites=true

# 2. Verificar credenciales MongoDB

# 3. Verificar IP whitelist en MongoDB Atlas
# En Atlas console: Network Access → IP Whitelist
# Lambda IP debe estar permitida (o usar 0.0.0.0/0 en staging)

# 4. Verificar VPC (si Lambda está en VPC)
# Lambda security group debe permitir traffic a MongoDB

# Solución:
# mongodb+srv://user:pass@cluster.mongodb.net/db?retryWrites=true&serverSelectionTimeoutMS=5000
```

### Error: `CircuitBreaker: OPEN` (Repeated 503)

```bash
# 1. Verificar MongoDB está realmente down
mongo --uri "mongodb+srv://user:pass@cluster.mongodb.net" --eval "db.adminCommand('ping')"

# 2. Ver por cuánto tiempo estuvo down
grep "CircuitBreaker.*OPEN" /aws/lambda/heavy-freight-api-production | tail -5

# 3. Si MongoDB está up, CB debe recuperarse en 60 segundos
# HALF_OPEN state: próximo request testea conexión
# Si éxito: vuelve a CLOSED

# 4. Si sigue OPEN después 120s:
# - MongoDB realmente no responde
# - O FAILURE_THRESHOLD muy bajo (5)
# - Aumentar en circuit_breaker.py: FAILURE_THRESHOLD = 10

# Escalate:
echo "ALERT: MongoDB down for $(date -d @$(stat -c%Y /tmp/mongodb.down) +%s) seconds" | mail -s "Heavy Freight: MongoDB Down" devops@company.com
```

---

## 🔐 Authentication Issues

### Error: `401 Unauthorized` on Valid Token

```bash
# 1. Verificar JWT_ALGORITHM en app
python -c "from src.schemas.auth import AuthService; print(AuthService.ALGORITHM)"
# Should be: HS256

# 2. Verificar token expiration
python << 'EOF'
from src.schemas.auth import AuthService
import jwt

token = "eyJ...your token..."
decoded = jwt.decode(token, options={"verify_signature": False})
print(f"Expires: {decoded.get('exp')}")

# Compare con timestamp actual
import time
print(f"Current: {time.time()}")
print(f"Expired: {decoded['exp'] < time.time()}")
EOF

# 3. Si expirado, client debe re-login

# 4. Si token válido pero sigue 401:
# Verificar Authorization header format:
# Must be: "Authorization: Bearer <token>"
# NOT: "Authorization: <token>"
```

### Error: `403 Forbidden` (Token válido pero sin permiso)

```bash
# Este es EXPECTED si:
# - Token es de otro usuario
# - Token no tiene scope necesario
# - Intentar crear trip con user_id diferente

# Ver en logs qué scope falta:
grep "403\|Forbidden" /aws/lambda/heavy-freight-api-production
```

---

## 🖥️ Lambda Concurrency Issues

### Error: `Lambda quota exceeded` or `TooManyRequestsException`

```bash
# 1. Ver concurrency actual vs limit
aws lambda get-function-concurrency \
  --function-name heavy-freight-api-production

# 2. Aumentar reserved concurrency
aws lambda put-function-concurrency \
  --function-name heavy-freight-api-production \
  --reserved-concurrent-executions 1000

# 3. Verificar account-level quota
aws service-quotas get-service-quota-value \
  --service-code lambda \
  --quota-code L-B3A8E2C5

# 4. Aumentar account limit
aws service-quotas request-service-quota-increase \
  --service-code lambda \
  --quota-code L-B3A8E2C5 \
  --desired-value 5000
```

---

## 📈 Memory/Storage Issues

### Error: `Runtime.OutOfMemory`

```bash
# 1. Aumentar Lambda memory
# En serverless.yml:
memorySize: 1024  # De 512 a 1024 MB

# 2. Redeploy
serverless deploy --stage production

# 3. Monitor si resuelve
aws logs tail /aws/lambda/heavy-freight-api-production --follow
```

### Error: `/tmp` Disk Full

```bash
# 1. Limpiar /tmp al inicio de handler
import shutil
shutil.rmtree('/tmp', ignore_errors=True)

# 2. Usar solo 512MB de /tmp (Lambda limit)

# 3. No guardar logs locales, usar CloudWatch

# Fix en wsgi.py:
# Quitar cualquier logging a archivos locales
```

---

## 🌐 CORS Issues

### Error: `No 'Access-Control-Allow-Origin' header`

```bash
# 1. Verificar CORS está habilitado en serverless.yml
# events:
#   - http:
#       cors: true

# 2. Redeploy
serverless deploy --stage production

# 3. Test CORS
curl -H "Origin: http://localhost:4200" \
  -H "Access-Control-Request-Method: GET" \
  https://$ENDPOINT/health/live -v

# Should include:
# Access-Control-Allow-Origin: '*'
```

### Error: `Credentials mode is 'include' but 'Access-Control-Allow-Credentials' header missing`

```bash
# Si client envía credenciales (cookies, auth headers):

# 1. En serverless.yml cambiar:
cors:
  origin: 'https://app.example.com'
  allowedHeaders: [Content-Type, Authorization]
  allowCredentials: true

# 2. Redeploy
serverless deploy --stage production
```

---

## 📋 Query Validation Issues

### Error: `422 Unprocessable Entity` on Valid Query

```bash
# 1. Revisar qué field es inválido
curl "https://$ENDPOINT/api/trips?page=1&limit=50&status=pending" -i

# Error response incluirá:
# "errors": [{"field": "status", "message": "Input should be 'pending' or 'in_transit'"}]

# 2. Verificar enum válido en schemas/pagination.py
# status field debe permitir: pending, in_transit, completed, cancelled

# 3. Si válido pero falla: reportar como bug con correlation_id
```

---

## 🔄 Circuit Breaker Stuck Open

### Diagnosis

```bash
# 1. Ver estado actual
python << 'EOF'
from src.infrastructure.circuit_breaker import MongoDBCircuitBreaker
b = MongoDBCircuitBreaker()
print(f"State: {b.state}")
print(f"Failure count: {b._failure_count}")
print(f"Last failure: {b._last_failure_time}")
EOF

# 2. Probar si MongoDB está down
mongo --uri "$MONGO_URI" --eval "db.adminCommand('ping')"

# 3. Si MongoDB está up pero CB open: esperar 60 segundos
# CB automáticamente intenta recuperarse
```

### Manual Recovery

```bash
# Si necesitas resetear inmediatamente (último recurso):

python << 'EOF'
from src.infrastructure.circuit_breaker import MongoDBCircuitBreaker
b = MongoDBCircuitBreaker()
b._state = "CLOSED"
b._failure_count = 0
print("Circuit breaker reset to CLOSED")
EOF

# O redeploy Lambda function (limpio state)
serverless deploy --stage production
```

---

## 📞 Escalation Path

**Nivel 1 (Servidor de Aplicación):**
- ✅ Verificar logs en CloudWatch
- ✅ Revisar health endpoints
- ✅ Reintentar después 60s

**Nivel 2 (Infrastructure):**
- 🔧 Aumentar Lambda memory/timeout
- 🔧 Update Secrets Manager
- 🔧 Adjust concurrency limits

**Nivel 3 (DevOps/Database):**
- 📞 Contactar si: MongoDB caído, Network issues, IAM permissions
- 📞 Ticket: "Heavy Freight API - [issue] - correlation_id: xyz"

---

**Con esta guía deberías resolver 95% de production issues ✅**
