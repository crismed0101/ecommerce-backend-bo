# Deployment to Docker Swarm with Traefik

Esta guía es específica para deployar en un servidor con Docker Swarm + Traefik + Cloudflare ya configurados.

## Prerequisitos

- ✅ Docker Swarm inicializado
- ✅ Traefik corriendo como servicio
- ✅ Red `network_public` creada
- ✅ Cloudflare DNS configurado
- ✅ Acceso SSH al servidor

---

## 📋 Paso 1: Conectar al servidor

```bash
ssh root@tu-servidor-ip
```

---

## 📋 Paso 2: Crear directorio y clonar repositorio

```bash
# Crear directorio para la aplicación
mkdir -p /opt/ecommerce-backend
cd /opt/ecommerce-backend

# Clonar desde GitHub
git clone https://github.com/crismed0101/ecommerce-backend-bo.git .
```

---

## 📋 Paso 3: Configurar variables de entorno

```bash
# Copiar plantilla
cp .env.production.example .env.production

# Editar con tus valores reales
nano .env.production
```

Configura estos valores:

```env
POSTGRES_PASSWORD=tu-password-seguro-aqui
SECRET_KEY=genera-un-secret-key-largo-minimo-32-caracteres
SHOPIFY_WEBHOOK_SECRET=tu-shopify-webhook-secret
```

Para generar un SECRET_KEY seguro:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 📋 Paso 4: Crear volumen de PostgreSQL

```bash
docker volume create ecommerce_postgres_data
```

---

## 📋 Paso 5: Build de la imagen Docker

```bash
docker build -t crismed0101/ecommerce-backend:latest .
```

---

## 📋 Paso 6: Configurar DNS en Cloudflare

1. Ve a tu panel de Cloudflare
2. Añade registro DNS:
   - **Type:** A
   - **Name:** ecom-app
   - **IPv4:** Tu IP del servidor Hetzner
   - **Proxy status:** Proxied (nube naranja)
   - **TTL:** Auto

---

## 📋 Paso 7: Deploy del stack en Swarm

```bash
# Cargar variables de entorno
export $(cat .env.production | xargs)

# Deploy con Docker Swarm
docker stack deploy -c docker-compose.swarm.yml ecommerce
```

---

## 📋 Paso 8: Verificar deployment

```bash
# Ver servicios
docker stack services ecommerce

# Ver logs del backend
docker service logs -f ecommerce_backend

# Ver logs de PostgreSQL
docker service logs -f ecommerce_postgres
```

Deberías ver:

```
ecommerce_backend      1/1       crismed0101/ecommerce-backend:latest
ecommerce_postgres     1/1       postgres:17-alpine
```

---

## 📋 Paso 9: Verificar en navegador

Abre tu navegador:

```
https://ecom-app.bytebase.my/health
```

Deberías ver:

```json
{
  "status": "healthy",
  "app": "E-commerce Backend",
  "version": "1.0.0"
}
```

---

## 📋 Paso 10: Ver documentación de API

```
https://ecom-app.bytebase.my/docs
```

---

## 🔄 Actualizar la aplicación

```bash
# Pull últimos cambios
git pull origin main

# Rebuild imagen
docker build -t crismed0101/ecommerce-backend:latest .

# Update stack
docker stack deploy -c docker-compose.swarm.yml ecommerce
```

Docker Swarm hará rolling update sin downtime.

---

## 🛠️ Comandos útiles

### Ver estado de servicios

```bash
docker stack ps ecommerce
```

### Ver logs en tiempo real

```bash
# Backend
docker service logs -f --tail=100 ecommerce_backend

# PostgreSQL
docker service logs -f --tail=100 ecommerce_postgres
```

### Escalar el backend (más replicas)

```bash
docker service scale ecommerce_backend=3
```

### Remover stack completo

```bash
docker stack rm ecommerce
```

### Conectar a PostgreSQL desde servidor

```bash
docker exec -it $(docker ps -q -f name=ecommerce_postgres) psql -U postgres -d ecommerce_bo
```

---

## 🔍 Troubleshooting

### Servicio no inicia

```bash
# Ver logs con detalles
docker service ps ecommerce_backend --no-trunc

# Ver eventos
docker events --filter 'service=ecommerce_backend'
```

### Base de datos no conecta

```bash
# Verificar que postgres esté corriendo
docker service ps ecommerce_postgres

# Verificar red interna
docker network inspect ecommerce_internal
```

### Traefik no rutea

```bash
# Verificar labels
docker service inspect ecommerce_backend --format='{{json .Spec.Labels}}' | jq

# Verificar que esté en network_public
docker service inspect ecommerce_backend --format='{{json .Spec.TaskTemplate.Networks}}'
```

### SSL no funciona

Verificar en Cloudflare:
- SSL/TLS mode debe estar en "Full" o "Full (strict)"
- DNS debe estar en modo "Proxied" (nube naranja)

---

## 📊 Monitoreo

### Health check del backend

```bash
curl https://ecom-app.bytebase.my/health
```

### Ver métricas de recursos

```bash
docker stats $(docker ps -q -f name=ecommerce)
```

---

## 🔐 Seguridad

- ✅ PostgreSQL solo accesible desde red interna
- ✅ Backend expuesto solo via Traefik
- ✅ SSL automático via Let's Encrypt
- ✅ Cloudflare DDoS protection
- ✅ Secrets en variables de entorno

---

## 🎯 Próximos pasos

1. Configurar N8N para enviar webhooks a: `https://ecom-app.bytebase.my/api/v1/orders`
2. Configurar Shopify webhooks
3. Monitorear logs para verificar recepción de órdenes
4. Implementar frontend

---

## 📞 Endpoints importantes

- **Health:** `https://ecom-app.bytebase.my/health`
- **Docs:** `https://ecom-app.bytebase.my/docs`
- **Create Order:** `POST https://ecom-app.bytebase.my/api/v1/orders`
- **Shopify Webhook:** `POST https://ecom-app.bytebase.my/shopify/webhook`
