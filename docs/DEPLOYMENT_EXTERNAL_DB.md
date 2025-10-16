# Deployment con PostgreSQL Externo

Esta guía es para cuando YA tienes PostgreSQL corriendo en tu servidor y quieres conectar el backend a esa base de datos existente.

---

## 🔍 Paso 1: Identificar tu PostgreSQL

### Verificar si está en Docker:

```bash
docker ps | grep postgres
```

Si ves algo como:
```
abc123def456   postgres:17   ...   5432/tcp   my_postgres_container
```

Entonces PostgreSQL está en Docker. **Anota el nombre del contenedor** (ej: `my_postgres_container`).

### Verificar si está instalado directo:

```bash
systemctl status postgresql
# o
ps aux | grep postgres
```

Si ves que está corriendo como servicio del sistema, está instalado directamente.

---

## 🔧 Paso 2: Preparar la base de datos

### Conectar a PostgreSQL:

**Si está en Docker:**
```bash
docker exec -it NOMBRE_CONTENEDOR psql -U postgres
```

**Si está instalado directo:**
```bash
sudo -u postgres psql
```

### Crear base de datos y usuario (si no existen):

```sql
-- Crear base de datos
CREATE DATABASE ecommerce_bo;

-- Verificar que se creó
\l

-- Conectar a la base de datos
\c ecommerce_bo

-- Salir
\q
```

**Nota:** NO necesitas crear las tablas manualmente. SQLAlchemy las creará automáticamente cuando el backend se conecte.

---

## 📝 Paso 3: Configurar DATABASE_URL

Edita tu `.env.production` según tu caso:

### **CASO A: PostgreSQL en contenedor Docker**

```env
# Si el contenedor PostgreSQL está en network_public:
DATABASE_URL=postgresql://postgres:TU_PASSWORD@nombre_contenedor_postgres:5432/ecommerce_bo

# Ejemplo real:
# DATABASE_URL=postgresql://postgres:MiPassword123@my_postgres_container:5432/ecommerce_bo
```

### **CASO B: PostgreSQL instalado directo en el servidor**

```env
# Opción 1: Usando host.docker.internal (Docker Desktop)
DATABASE_URL=postgresql://postgres:TU_PASSWORD@host.docker.internal:5432/ecommerce_bo

# Opción 2: Usando IP del gateway Docker (Linux)
DATABASE_URL=postgresql://postgres:TU_PASSWORD@172.17.0.1:5432/ecommerce_bo

# Opción 3: Usando localhost (si PostgreSQL escucha en todas las interfaces)
DATABASE_URL=postgresql://postgres:TU_PASSWORD@localhost:5432/ecommerce_bo
```

### **CASO C: PostgreSQL en otro servidor**

```env
DATABASE_URL=postgresql://postgres:TU_PASSWORD@192.168.1.100:5432/ecommerce_bo
```

---

## 🔒 Paso 4: Configurar acceso de PostgreSQL

Si PostgreSQL está instalado directo, necesitas permitir conexiones desde Docker:

### Editar `postgresql.conf`:

```bash
sudo nano /etc/postgresql/17/main/postgresql.conf
```

Busca y modifica:

```conf
listen_addresses = '*'  # O 'localhost,172.17.0.1'
```

### Editar `pg_hba.conf`:

```bash
sudo nano /etc/postgresql/17/main/pg_hba.conf
```

Agrega al final:

```conf
# Permitir conexiones desde Docker
host    ecommerce_bo    postgres    172.17.0.0/16    md5
```

### Reiniciar PostgreSQL:

```bash
sudo systemctl restart postgresql
```

---

## 🔧 Paso 5: Ajustar docker-compose según tu caso

### **CASO A: PostgreSQL en contenedor**

Tu `docker-compose.swarm-external-db.yml` debe tener:

```yaml
services:
  backend:
    networks:
      - network_public  # ← Misma red que PostgreSQL
    environment:
      DATABASE_URL: postgresql://postgres:${POSTGRES_PASSWORD}@nombre_contenedor:5432/ecommerce_bo
```

### **CASO B: PostgreSQL instalado directo**

```yaml
services:
  backend:
    extra_hosts:
      - "host.docker.internal:host-gateway"  # ← Importante para Linux
    environment:
      DATABASE_URL: postgresql://postgres:${POSTGRES_PASSWORD}@host.docker.internal:5432/ecommerce_bo
```

---

## 🚀 Paso 6: Deploy

```bash
# Ir al directorio
cd /opt/ecommerce-backend

# Cargar variables
export $(cat .env.production | xargs)

# Build imagen
docker build -t crismed0101/ecommerce-backend:latest .

# Deploy con el archivo correcto
docker stack deploy -c docker-compose.swarm-external-db.yml ecommerce
```

---

## ✅ Paso 7: Verificar conexión a la base de datos

```bash
# Ver logs del backend
docker service logs -f ecommerce_backend

# Deberías ver:
# INFO:     Application startup complete.
# INFO:     Connected to database successfully
```

### Verificar que las tablas se crearon:

```bash
# Conectar a PostgreSQL
docker exec -it NOMBRE_CONTENEDOR psql -U postgres -d ecommerce_bo

# O si está instalado directo:
sudo -u postgres psql -d ecommerce_bo
```

```sql
-- Listar schemas
\dn

-- Deberías ver:
-- operations
-- product
-- finance
-- marketing

-- Listar tablas del schema operations
\dt operations.*

-- Deberías ver ~10 tablas:
-- customers, orders, order_items, etc.

-- Salir
\q
```

---

## 🔍 Troubleshooting

### Error: "could not connect to server"

```bash
# Verificar que PostgreSQL está corriendo
docker ps | grep postgres
# o
sudo systemctl status postgresql

# Verificar conectividad desde el contenedor backend
docker exec -it NOMBRE_CONTENEDOR_BACKEND ping postgres_container
```

### Error: "password authentication failed"

Verifica que el password en `DATABASE_URL` es correcto:

```bash
# Probar conexión manual
psql "postgresql://postgres:PASSWORD@localhost:5432/ecommerce_bo"
```

### Error: "database does not exist"

Crea la base de datos manualmente:

```bash
docker exec -it postgres_container createdb -U postgres ecommerce_bo
# o
sudo -u postgres createdb ecommerce_bo
```

### Backend no puede resolver el hostname

Si usas nombre de contenedor, ambos deben estar en la misma red:

```bash
# Ver redes del contenedor postgres
docker inspect postgres_container | grep NetworkMode

# Asegurarse que backend está en la misma red
docker service inspect ecommerce_backend --format='{{json .Spec.TaskTemplate.Networks}}'
```

---

## 📊 Ventajas de usar PostgreSQL externo

✅ No duplicas recursos
✅ Más fácil hacer backups
✅ Puedes usar pgAdmin existente
✅ Otras apps pueden acceder a la misma BD
✅ Menos contenedores que manejar

---

## 🎯 Resumen

1. ✅ Identificar si PostgreSQL está en Docker o instalado directo
2. ✅ Crear base de datos `ecommerce_bo`
3. ✅ Configurar `DATABASE_URL` correctamente
4. ✅ Ajustar permisos de PostgreSQL (si está instalado directo)
5. ✅ Deploy con `docker-compose.swarm-external-db.yml`
6. ✅ Verificar que tablas se crearon automáticamente

---

## 📞 URLs después del deployment

- **Health:** `https://ecom-app.bytebase.my/health`
- **Docs:** `https://ecom-app.bytebase.my/docs`
- **Create Order:** `POST https://ecom-app.bytebase.my/api/v1/orders`
