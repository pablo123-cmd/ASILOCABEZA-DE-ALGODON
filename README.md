# Sistema de Administración — Asilo de Ancianos Cabeza de Algodón

Sistema para gestionar a los internos del asilo, su atención médica con la fundación
(solicitudes, visitas, laboratorio y farmacia) y las finanzas (cuentas, cobros, cuotas,
donaciones, gastos y pagos a la fundación).

Proyecto final de Análisis de datos — Universidad Mariano Gálvez, sede Mazatenango.

## Arquitectura

El sistema está formado por cinco servicios en **Python con FastAPI**. El usuario solo usa el
**menú principal (gateway)**; este muestra las pantallas y consulta a los demás servicios.

```mermaid
flowchart LR
    U[Navegador] -->|HTML| G["Menú principal / gateway<br/>:8002<br/>inicio de sesión, usuarios,<br/>pantallas y reportes"]
    G -->|JSON + token| P["Pacientes<br/>:8000"]
    G -->|JSON + token| S["Solicitudes médicas<br/>:8001<br/>asignaciones y correo"]
    G -->|JSON + token| M["Atención médica<br/>:8003<br/>catálogos, ficha, visitas,<br/>laboratorio, farmacia"]
    G -->|JSON + token| F["Finanzas<br/>:8004"]
    S --> P
    S --> M
    M --> P
    M --> S
    F --> P
    F --> M
```

| Carpeta | Contenido |
|---|---|
| `gateway/` | Menú principal: rutas (controladores), plantillas HTML (vistas) y estilos |
| `pacientes/` | Microservicio de pacientes |
| `solicitudes/` | Microservicio de solicitudes, asignación de médico, horario y enfermero, y correo al familiar |
| `medico/` | Microservicio de médicos, especialidades, enfermeros, ficha e historial, visitas, laboratorio y farmacia |
| `finanzas/` | Microservicio de entradas, salidas y caja |
| `comun/` | Código compartido: seguridad y roles, validación, mensajes de error, repositorio de datos, correo |
| `tests/` | Pruebas automáticas basadas en el plan de pruebas SQA |
| `docs/` | Informe de correcciones para SQA y manual de usuario |

Cada servicio separa sus capas: **modelos** (Pydantic, validan los datos), **rutas**
(controladores) y **repositorio** (`comun/repositorio.py`, patrón Repository). Las pantallas
usan plantillas Jinja2, que escapan automáticamente el texto del usuario.

### Datos

Los datos se guardan en **MySQL 8** (base de datos `asilo_cabeza_algodon`, 19 tablas con llaves
foráneas). El script `docs/bd/asilo.sql` crea la base de datos, el usuario `asilo` que usa el
sistema y los datos iniciales. Todo el acceso a datos pasa por los repositorios de
`comun/repositorio.py` (patrón Repository).

### Seguridad

- Inicio de sesión en el menú principal; las contraseñas se guardan cifradas (PBKDF2).
- La sesión es un token firmado (cookie `HttpOnly`) que vence en 8 horas.
- **Todos** los servicios exigen el token: sin sesión responden `401` y con un rol sin
  permiso responden `403`. Los permisos por rol están en `comun/seguridad.py`.

## Instalación

Requisitos: Python 3.12 o superior y MySQL 8.

### 1. Descargar el proyecto e instalar las dependencias

```powershell
git clone https://github.com/pablo123-cmd/ASILOCABEZA-DE-ALGODON.git
cd ASILOCABEZA-DE-ALGODON
python -m pip install -r requirements.txt
```

### 2. Instalar MySQL

1. Descargue **MySQL Installer for Windows** desde https://dev.mysql.com/downloads/installer/.
2. Elija el tipo de instalación **Server only**.
3. Deje el puerto **3306** y escriba una contraseña para el usuario `root` (anótela).
4. Deje marcado que MySQL se inicie como servicio de Windows.

### 3. Crear la base de datos

Desde la carpeta del proyecto, en **cmd** (Símbolo del sistema):

```bat
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root -p --default-character-set=utf8mb4 < docs\bd\asilo.sql
```

Escriba la contraseña de `root`. El script borra la base de datos si ya existe y la crea de
nuevo con los datos iniciales, así que úselo también para reiniciar los datos de prueba.

## Ejecución

Desde la carpeta del proyecto:

```powershell
python iniciar.py
```

Esto revisa la conexión con MySQL e inicia los cinco servicios. Abra
**http://127.0.0.1:8002** en el navegador. Para detenerlos presione `Ctrl+C`.

Sin MySQL se puede hacer una demostración con `python iniciar.py --memoria`; en ese modo los
datos se pierden al detener el sistema.

También se puede iniciar cada servicio por separado (siempre desde la carpeta raíz):

```powershell
python -m uvicorn pacientes.main:app --port 8000
python -m uvicorn solicitudes.main:app --port 8001
python -m uvicorn gateway.main:app --port 8002
python -m uvicorn medico.main:app --port 8003
python -m uvicorn finanzas.main:app --port 8004
```

La documentación de cada API está en `/docs` de su puerto, por ejemplo
http://127.0.0.1:8000/docs. Para probarla desde ahí, inicie sesión primero en el menú principal
en el mismo navegador.

### Usuarios de prueba

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `Admin2026!` | Administrador (acceso a todo) |
| `personal` | `Asilo2026!` | Personal del asilo |
| `medico` | `Asilo2026!` | Médico general |
| `especialista` | `Asilo2026!` | Médico especialista |
| `enfermero` | `Asilo2026!` | Enfermero(a) |
| `fundacion` | `Asilo2026!` | Fundación |
| `laboratorio` | `Asilo2026!` | Laboratorio |
| `farmacia` | `Asilo2026!` | Farmacia |
| `finanzas` | `Asilo2026!` | Encargado financiero |

### Configuración opcional (variables de entorno)

| Variable | Uso |
|---|---|
| `MYSQL_HOST`, `MYSQL_PUERTO`, `MYSQL_USUARIO`, `MYSQL_CONTRASENA`, `MYSQL_BD` | Conexión a MySQL. Por defecto `127.0.0.1`, `3306`, `asilo`, `Asilo2026!`, `asilo_cabeza_algodon` (los que crea el script). |
| `MYSQL_SSL` | `1` para cifrar la conexión (necesario en Aiven y otras bases en la nube). |
| `PORT` | Puerto público del menú principal; lo pone Render. Sin él, todo escucha en `127.0.0.1`. |
| `ASILO_BD` | `mysql` (por defecto) o `memoria`. |
| `ASILO_CLAVE_SECRETA` | Clave con la que se firman las sesiones. **Cámbiela en producción**; debe ser la misma en los cinco servicios. |
| `SMTP_HOST`, `SMTP_PUERTO`, `SMTP_USUARIO`, `SMTP_CONTRASENA`, `SMTP_REMITENTE` | Servidor de correo para avisar a los familiares. Sin `SMTP_HOST` los correos se registran como «Simulado» en *Correos a familiares*. |
| `URL_PACIENTES`, `URL_SOLICITUDES`, `URL_MEDICO`, `URL_FINANZAS` | Direcciones de los servicios si no se ejecutan en `127.0.0.1`. |

## Publicación en la nube

El sistema se publica gratis con **Aiven** (base de datos MySQL) y **Render** (servidor).

1. En [aiven.io](https://aiven.io) cree un servicio **MySQL** del plan gratuito y anote
   *Host*, *Port*, *User* (`avnadmin`) y *Password*.
2. Cargue la base de datos desde su computadora:

   ```powershell
   & "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -h <host> -P <port> -u avnadmin -p --ssl-mode=REQUIRED --default-character-set=utf8mb4 < docs/bd/asilo.sql
   ```

3. En [render.com](https://render.com) elija **New → Blueprint** y conecte este repositorio.
   Render lee `render.yaml` y pide `MYSQL_HOST`, `MYSQL_PUERTO`, `MYSQL_USUARIO` y
   `MYSQL_CONTRASENA`: escriba los datos de Aiven.
4. Al terminar, Render muestra la dirección pública (`https://….onrender.com`).

En el plan gratuito Render apaga el servidor tras 15 minutos sin visitas; la primera visita
después tarda cerca de un minuto en abrir.

## Pruebas automáticas

```powershell
python -m pytest
```

Las pruebas siguen los casos del plan de pruebas SQA (CP-01 a CP-49). Usan los repositorios
en memoria, así que no necesitan MySQL ni que los servicios estén encendidos.
