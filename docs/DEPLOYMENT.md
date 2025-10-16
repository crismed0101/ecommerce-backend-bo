# Guía de Deployment - Hetzner + Portainer + Docker

## Prerequisitos en tu servidor Hetzner

- Debian Linux
- Docker instalado
- Portainer instalado y corriendo
- PostgreSQL 17 (puede estar en contenedor o directo)

## Opción 1: Deployment via Portainer (Recomendado)

### Paso 1: Preparar archivos en el servidor

SSH a tu servidor Hetzner:

```bash
ssh tu-usuario@tu-ip-hetzner
```

Crear directorio para la aplicación:

```bash
mkdir -p /opt/ecommerce-backend
cd /opt/ecommerce-backend
```

### Paso 2: Clonar repositorio

```bash
git clone https://github.com/TU-USUARIO/ecommerce-backend-bo.git .
```

### Paso 3: Configurar variables de entorno

```bash
cp .env.example .env
nano .env
```

Configurar valores de producción:

```env
# Application
APP_NAME="E-commerce Backend"
APP_VERSION="1.0.0"
DEBUG=False

# Database (usa tu PostgreSQL existente)
DATABASE_URL=postgresql://postgres:TU_PASSWORD@TU_IP_POSTGRES:5432/ecommerce_bo

# Security (GENERAR NUEVOS!)
SECRET_KEY=aqui-un-secret-key-largo-y-aleatorio-minimo-32-caracteres
SHOPIFY_WEBHOOK_SECRET=tu-shopify-webhook-secret

# CORS
ALLOWED_ORIGINS=https://tu-dominio.com

# Server
HOST=0.0.0.0
PORT=8000
```

### Paso 4: Deployment via Portainer Web UI

1. Abrir Portainer: `https://tu-ip:9443`
2. **Stacks** → **Add stack**
3. **Name:** `ecommerce-backend`
4. **Build method:** Upload
5. Upload tu archivo `docker-compose.yml`
6. **Environment variables:** Agregar desde `.env`
7. **Deploy the stack**

### Paso 5: Verificar deployment

```bash
# Ver containers corriendo
docker ps

# Ver logs
docker logs ecommerce_backend -f

# Test health
curl http://localhost:8000/health
```

## Opción 2: Deployment via SSH + Docker Compose

### Deployment completo

```bash
# Clonar repo
git clone https://github.com/TU-USUARIO/ecommerce-backend-bo.git
cd ecommerce-backend-bo

# Configurar .env
cp .env.example .env
nano .env

# Build y deploy
chmod +x deploy.sh
./deploy.sh production
```

### Comandos útiles

```bash
# Ver logs
docker-compose logs -f backend

# Restart
docker-compose restart backend

# Stop
docker-compose down

# Update y redeploy
git pull origin main
docker-compose up -d --build
```

## Configurar Nginx Reverse Proxy con SSL

### Paso 1: Instalar Certbot

```bash
apt update
apt install certbot python3-certbot-nginx -y
```

### Paso 2: Obtener certificado SSL

```bash
certbot certonly --standalone -d tu-dominio.com -d api.tu-dominio.com
```

### Paso 3: Configurar Nginx

Editar `nginx.conf` y descomentar sección HTTPS:

```nginx
server {
    listen 443 ssl http2;
    server_name api.tu-dominio.com;

    ssl_certificate /etc/letsencrypt/live/tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tu-dominio.com/privkey.pem;

    location / {
        proxy_pass http://backend:8000;
        # ... resto de configuración
    }
}
```

### Paso 4: Restart con nginx

```bash
docker-compose --profile production up -d
```

## Configurar GitHub Actions (CI/CD Automatizado)

### Paso 1: Configurar secrets en GitHub

Ve a tu repo → **Settings** → **Secrets and variables** → **Actions**

Agregar estos secrets:

- `SERVER_HOST`: IP de tu servidor Hetzner
- `SERVER_USER`: Usuario SSH
- `SSH_PRIVATE_KEY`: Tu private key SSH
- `SERVER_PORT`: Puerto SSH (default: 22)

### Paso 2: Generar SSH key en el servidor

```bash
ssh-keygen -t ed25519 -C "github-actions"
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
cat ~/.ssh/id_ed25519  # Copiar esto como SSH_PRIVATE_KEY en GitHub
```

### Paso 3: Actualizar workflow

Editar `.github/workflows/deploy.yml`:

```yaml
script: |
  cd /opt/ecommerce-backend
  git pull origin main
  docker-compose down
  docker-compose up -d --build
  docker-compose ps
```

### Paso 4: Push y auto-deploy

```bash
git add .
git commit -m "Configure CI/CD"
git push origin main
```

Ahora cada push a `main` deployeará automáticamente!

## Monitoreo y Logs

### Ver logs en tiempo real

```bash
docker-compose logs -f backend
```

### Ver health status

```bash
curl http://localhost:8000/health
```

### Ver endpoints disponibles

```bash
curl http://localhost:8000/openapi.json | jq '.paths | keys'
```

## Troubleshooting

### Container no inicia

```bash
docker-compose logs backend
docker-compose ps
```

### Base de datos no conecta

```bash
# Verificar que PostgreSQL está corriendo
docker ps | grep postgres

# Test conexión desde container
docker exec -it ecommerce_backend python -c "from app.core.database import engine; engine.connect()"
```

### Reset completo

```bash
docker-compose down -v
docker-compose up -d --build
```

## Backup y Restore

### Backup PostgreSQL

```bash
docker exec ecommerce_postgres pg_dump -U postgres ecommerce_bo > backup_$(date +%Y%m%d).sql
```

### Restore

```bash
cat backup_20251015.sql | docker exec -i ecommerce_postgres psql -U postgres ecommerce_bo
```

## Actualización de la aplicación

### Método 1: Manual

```bash
cd /opt/ecommerce-backend
git pull origin main
docker-compose up -d --build
```

### Método 2: Via GitHub Actions (Automático)

Solo hacer push a main:

```bash
git push origin main
```

## Seguridad

- Cambiar todos los secrets en `.env`
- Usar HTTPS (certificado SSL)
- Configurar firewall (ufw)
- Mantener Docker actualizado
- Backup regular de BD

## Próximos pasos

1. Configurar dominio DNS apuntando a tu IP
2. Obtener SSL certificate
3. Configurar monitoring (Prometheus + Grafana)
4. Setup alertas (email/Telegram)
5. Implementar frontend
