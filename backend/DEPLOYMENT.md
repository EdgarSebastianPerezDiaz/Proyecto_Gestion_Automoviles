# 🚀 Guía de Deployment - Heavy Freight Platform

## Índice
1. [Antes de Deployar](#antes-de-deployar)
2. [AWS Setup (Primera vez)](#aws-setup-primera-vez)
3. [Deployment a Lambda](#deployment-a-lambda)
4. [Verificación Post-Deployment](#verificación-post-deployment)
5. [Troubleshooting](#troubleshooting)

---

## ✅ Antes de Deployar

### Checklist de Seguridad
```
□ JWT_SECRET_KEY está en AWS Secrets Manager (no en .env)
□ MONGO_URI está en AWS Secrets Manager con credenciales fuertes
□ Todas las env vars críticas están en Secrets Manager
□ No hay valores dummy en producción
□ .env.production es solo template (No contiene valores reales)
□ venv/ está en .gitignore
□ Tests pasan 100% (758/758)
```

### Verificar Código Limpio
```bash
# Eliminar archivos temporales
rm -f debug_*.py test_debug.py *.pyc .coverage

# Verificar no hay credenciales en código
grep -r "your-secret\|password\|token" src/ --include="*.py" | grep -v "^Binary"

# Verificar estructura limpia
ls -la backend/ | grep -E "\.py$|debug|test_"  # No debe haber basura
```

---

## AWS Setup (Primera vez)

### 1. Crear Secrets en AWS Secrets Manager

```bash
# Usando AWS CLI

# Crear secret para JWT
aws secretsmanager create-secret \
  --name heavy-freight/production/JWT_SECRET_KEY \
  --secret-string "$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  --region us-east-1

# Crear secret para MongoDB URI
aws secretsmanager create-secret \
  --name heavy-freight/production/MONGO_URI \
  --secret-string "mongodb+srv://user:password@cluster.mongodb.net/heavy_freight?retryWrites=true&w=majority" \
  --region us-east-1

# Crear secret para CORS
aws secretsmanager create-secret \
  --name heavy-freight/production/CORS_ORIGIN \
  --secret-string "https://yourdomain.com" \
  --region us-east-1
```

**IMPORTANTE**: 
- MongoDB URL debe tener credenciales fuertes (16+ caracteres, símbolos)
- Rotar credenciales cada 90 días
- Usar IP whitelist en MongoDB Atlas

### 2. Crear IAM Role para Lambda

```bash
# Crear role
aws iam create-role \
  --role-name heavy-freight-lambda-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"Service": "lambda.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }
    ]
  }' \
  --region us-east-1

# Agregar policies
aws iam attach-role-policy \
  --role-name heavy-freight-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Policy para acceder a Secrets Manager
aws iam put-role-policy \
  --role-name heavy-freight-lambda-role \
  --policy-name secrets-access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": "secretsmanager:GetSecretValue",
        "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:heavy-freight/production/*"
      }
    ]
  }'
```

### 3. Configurar serverless.yml

```yaml
# serverless.yml
service: heavy-freight-api

provider:
  name: aws
  runtime: python3.9
  region: us-east-1
  environment:
    FLASK_ENV: production
    MONGO_URI: ${ssm:/heavy-freight/production/MONGO_URI~true}
    JWT_SECRET_KEY: ${ssm:/heavy-freight/production/JWT_SECRET_KEY~true}
    CORS_ORIGIN: ${ssm:/heavy-freight/production/CORS_ORIGIN~true}
  iamRoleStatements:
    - Effect: Allow
      Action: secretsmanager:GetSecretValue
      Resource: "arn:aws:secretsmanager:${aws:region}:${aws:accountId}:secret:heavy-freight/production/*"

functions:
  api:
    handler: wsgi.handler
    timeout: 30
    memorySize: 512
    events:
      - http:
          path: /{proxy+}
          method: ANY
          cors: true
      - http:
          path: /
          method: ANY
          cors: true

plugins:
  - serverless-python-requirements
  - serverless-wsgi

custom:
  pythonRequirements:
    dockerizePip: true
```

---

## Deployment a Lambda

### Opción 1: Con Serverless Framework

```bash
# Instalar serverless
npm install -g serverless

# Instalar plugins
npm install serverless-python-requirements serverless-wsgi

# Deployar
serverless deploy --stage production --region us-east-1

# O con variables
serverless deploy \
  --stage production \
  --region us-east-1 \
  --param="environment=production"
```

### Opción 2: Manual con AWS CLI + SAM

```bash
# Build
sam build

# Deploy (primera vez)
sam deploy --guided

# Deploy (updates)
sam deploy
```

### Opción 3: GitHub Actions CI/CD (RECOMENDADO)

Crear `.github/workflows/deploy.yml`:

```yaml
name: Deploy to AWS Lambda

on:
  push:
    branches: [main, production]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Run tests
        run: |
          pip install -r requirements-dev.txt
          pytest tests/ --tb=short
      
      - name: Deploy to Lambda
        run: serverless deploy --stage production
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: us-east-1
```

---

## Verificación Post-Deployment

### 1. Verificar Lambda está activa

```bash
# Obtener URL del API Gateway
aws lambda get-function \
  --function-name heavy-freight-api-production-api \
  --region us-east-1

# O desde serverless info
serverless info --stage production
```

### 2. Probar endpoints

```bash
# Health check
curl https://your-api-url.execute-api.us-east-1.amazonaws.com/health

# Respuesta esperada:
# {"message": "ok"}

# Health deep check
curl https://your-api-url/health/deep

# Respuesta:
# {"mongo": true, "secrets": true, "rate_limiter": true}
```

### 3. Ver logs en CloudWatch

```bash
# Último 1 hora de logs
aws logs tail /aws/lambda/heavy-freight-api-production-api --follow

# O en AWS Console:
# CloudWatch → Log Groups → /aws/lambda/heavy-freight-api-production-api
```

### 4. Monitorear errores

```bash
# Ver errores
aws logs filter-log-events \
  --log-group-name /aws/lambda/heavy-freight-api-production-api \
  --filter-pattern "ERROR"

# Ver latencia (CloudWatch Metrics)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=heavy-freight-api-production-api \
  --start-time 2026-04-04T00:00:00Z \
  --end-time 2026-04-05T00:00:00Z \
  --period 300 \
  --statistics Average,Maximum
```

---

## Troubleshooting

### ❌ Error: "Unable to import module 'wsgi'"

**Solución:**
```bash
# Asegurar serverless-wsgi está en requirements.txt
pip freeze | grep serverless

# O reinstalar
pip install serverless-wsgi Flask
```

### ❌ Error: "Cannot connect to Secrets Manager"

**Solución:**
1. Verificar IAM role tiene permisos
2. Verificar región matches
3. Verificar secret name es correcto

```bash
# Testear acceso a secret
aws secretsmanager get-secret-value \
  --secret-id heavy-freight/production/JWT_SECRET_KEY \
  --region us-east-1
```

### ❌ Error: "MongoDB connection timeout"

**Solución:**
1. Verificar MongoDB Atlas IP whitelist (agregar 0.0.0.0/0)
2. Verificar credenciales en Secret Manager
3. Verificar Lambda subnet tiene NAT Gateway

```bash
# Test conexión local antes de deployar
python -c "from src.infrastructure.database import MongoDBConnection; db = MongoDBConnection.get_instance(); print('✅ Connected')"
```

### ❌ Error: "Rate limit exceeded" en producción

**Solución:**
Es normal si estás haciendo stress testing. Ajusta límites en:
```python
# src/infrastructure/rate_limiter.py
rate_limit(limit=100, window=60)  # Default
rate_limit(limit=30, window=60)   # Más restrictivo
```

### ❌ Cold start muy lento

**Solución:**
1. Aumentar memory de Lambda (512MB → 1024MB)
2. Usar Lambda Provisioned Concurrency
3. Usar CloudFront + API caching

```yaml
# serverless.yml
functions:
  api:
    memorySize: 1024
    ephemeralSize: 512
```

---

## Rollback de Deployment

### Si algo falla en producción:

```bash
# Ver versiones previas
aws lambda list-versions-by-function --function-name heavy-freight-api-production-api

# Volver a versión anterior
aws lambda update-alias \
  --function-name heavy-freight-api-production-api \
  --name production \
  --function-version 5  # Version anterior estable
```

O con serverless:
```bash
# Ver deployments
serverless deploy list

# Rollback
serverless rollback
```

---

## Monitoring & Alertas

### CloudWatch Alarms (recomendado)

```bash
# Alarma por errores
aws cloudwatch put-metric-alarm \
  --alarm-name heavy-freight-lambda-errors \
  --alarm-description "Alert if Lambda has errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 60 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1

# Alarma por throttling
aws cloudwatch put-metric-alarm \
  --alarm-name heavy-freight-lambda-throttles \
  --alarm-description "Alert if Lambda is throttled" \
  --metric-name Throttles \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 60 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold
```

### CloudWatch Dashboard

Ver en AWS Console:
- CloudWatch → Dashboards → Create dashboard
- Agregar métricas: Lambda Errors, Duration, Invocations, Throttles

---

## Checklist Final Antes de Producción

```
[ ] Tests pasan 100% (758/758)
[ ] Secrets están en AWS Secrets Manager
[ ] IAM role tiene permisos correctos
[ ] serverless.yml está configurado
[ ] Logs van a CloudWatch
[ ] Health checks responden correctamente
[ ] Rate limiter está activo
[ ] CORS configurado para tu dominio
[ ] MongoDB backups están habilitados
[ ] Load testing hecho (aguanta 100+ req/sec)
[ ] Rollback plan documentado
[ ] Team entrenado en operación
[ ] Alertas configuradas en CloudWatch
```

---

## Soporte y Documentación

- **AWS Lambda Docs**: https://docs.aws.amazon.com/lambda/
- **Serverless Framework**: https://www.serverless.com/
- **Flask on AWS Lambda**: https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html
- **Troubleshooting**: Ver sección de Troubleshooting arriba

**Última actualización**: Abril 2026
