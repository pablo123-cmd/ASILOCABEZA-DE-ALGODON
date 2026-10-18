# Entrega a SQA — Segunda versión

**Sistema:** Administración del Asilo de Ancianos Cabeza de Algodón
**Analista:** Pablo David Yoc Mota
**Versión evaluada en la ronda 1:** commit `7c22f6f` (10/10/2026)

Este documento responde a los resultados de la ronda 1 del *Plan de Pruebas SQA*: cómo
se corrigió cada defecto, el estado de cada requerimiento y las diferencias con la
documentación del proyecto.

## 1. Corrección de defectos

| Defecto | Severidad | Caso | Estado | Corrección |
|---|---|---|---|---|
| DEF-01 | Crítica | CP-20 | **Pendiente** | La base de datos aún no está conectada. El acceso a datos ya pasa por un repositorio (`comun/repositorio.py`) para conectarla sin cambiar el resto del sistema. |
| DEF-02 | Crítica | CP-37 | Corregido | Inicio de sesión con roles. Los cinco servicios rechazan las peticiones sin sesión (401) o sin permiso (403). |
| DEF-03 | Alta | CP-30 | Corregido | El menú principal tiene su propio formulario de solicitudes, que envía los datos al microservicio. |
| DEF-04 | Alta | CP-13 | Corregido | Pantallas de listado, búsqueda por nombre o habitación, detalle y edición de pacientes. |
| DEF-05 | Alta | CP-23 | Corregido | Al crear una solicitud se verifica con el servicio de pacientes que el paciente exista (422 si no). |
| DEF-06 | Alta | CP-19 | Corregido | Los id salen de un contador que nunca retrocede; no se repiten aunque se eliminen registros. |
| DEF-07 | Alta | CP-12 | Corregido | Las páginas usan plantillas Jinja2 que escapan todo el texto del usuario. |
| DEF-08 | Alta | CP-17 | Corregido | Cada API valida tipos, campos obligatorios y rechaza campos desconocidos (422). |
| DEF-09 | Media | CP-10 | Corregido | Solo se aceptan edades entre 60 y 120 años, en el formulario y en la API. |
| DEF-10 | Media | CP-09 | Corregido | Los textos se recortan antes de validar; un campo con solo espacios se rechaza. |
| DEF-11 | Media | CP-29 | Corregido | El menú ya no incrusta la página del microservicio; muestra su propia página con los datos. |
| DEF-12 | Media | CP-27 | Corregido | Solo se aceptan los estados Pendiente, Asignada, Atendida y Cancelada, con transiciones válidas. |
| DEF-13 | Baja | CP-25 | Corregido | La especialidad se valida contra el catálogo del servicio médico. |
| DEF-14 | Baja | CP-11 | Corregido | Se rechaza un paciente con el mismo nombre (sin distinguir mayúsculas, espacios ni acentos), con código 409. |
| DEF-15 | Baja | CP-08 | Corregido | Los errores de validación se devuelven en español, indicando el campo y el problema. |
| DEF-16 | Baja | CP-16 | Corregido | Un registro inexistente responde 404 en todos los servicios. |

### Notas para la nueva ronda de pruebas

- **Cómo iniciar el sistema:** `python iniciar.py` y abrir http://127.0.0.1:8002 (ver `README.md`).
  Los usuarios de prueba de cada rol están en el README.
- **Pruebas de API directas:** las APIs requieren sesión. Inicie sesión en el menú principal y use
  `/docs` de cada servicio en el mismo navegador, o envíe el encabezado `Authorization: Bearer <token>`.
- **CP-26 (cambio a Asignada):** una solicitud pasa a *Asignada* solo cuando la fundación indica médico
  y horario: `PUT /solicitudes/{id}/asignacion` con `{"medico_id": 2, "horario": "2026-10-30T09:00"}`.
  Cambiar el estado a *Asignada* sin médico (`PUT /solicitudes/{id}/estado`) se rechaza a propósito.
- **CP-06:** los microservicios ya no tienen formulario HTML propio; la interfaz es solo el menú principal.
  El registro directo en el microservicio se hace con `POST /pacientes` (o desde `/docs`).
- **Puertos:** se agregaron dos servicios: atención médica (8003) y finanzas (8004).

## 2. Requerimientos funcionales

| Req. | Descripción | Estado | Dónde |
|---|---|---|---|
| RF01 | Inicio de sesión y control de acceso | Implementado | Menú principal `/login`; permisos en `comun/seguridad.py` |
| RF02 | Administración de usuarios y roles | Implementado | Módulo *Usuarios* (administrador) |
| RF03 | Registro y actualización de pacientes | Implementado | Módulo *Pacientes* |
| RF04 | Registro de ficha médica | Implementado | Paciente → *Ficha e historial médico* |
| RF05 | Consulta del historial médico | Implementado | Misma pantalla de la ficha |
| RF06 | Registro de médicos | Implementado | *Médicos y catálogos* → Médicos |
| RF07 | Registro de especialidades | Implementado | *Médicos y catálogos* → Especialidades |
| RF08 | Creación de solicitudes médicas | Implementado | *Solicitudes médicas* (médico general) |
| RF09 | Asignación de médico | Implementado | Detalle de la solicitud (fundación) |
| RF10 | Asignación de horario | Implementado | Detalle de la solicitud (fundación); no permite dos citas del mismo médico a la misma hora |
| RF11 | Asignación de enfermero acompañante | Implementado | Al crear la solicitud o en su detalle |
| RF12 | Registro de visita médica | Implementado | *Atención médica*: la solicitud asignada se convierte en visita |
| RF13 | Solicitud de exámenes de laboratorio | Implementado | Detalle de la visita |
| RF14 | Registro y consulta de resultados | Implementado | Módulo *Laboratorio*; el médico ve el resultado en la visita y el historial |
| RF15 | Registro de medicamentos indicados | Implementado | Detalle de la visita (medicamento, cantidad, cómo tomarlo y duración) |
| RF16 | Entrega de medicamentos por farmacia | Implementado | Módulo *Farmacia*; descuenta la existencia |
| RF17 | Registro de costos y cuentas pendientes | Implementado | *Finanzas* → Cuentas de pacientes; cada visita muestra si está pagada |
| RF18 | Registro de donaciones | Implementado | *Finanzas* → Donaciones |
| RF19 | Registro de cuotas familiares | Implementado | *Finanzas* → Cuotas |
| RF20 | Registro de gastos | Implementado | *Finanzas* → Gastos |
| RF21 | Registro de pagos a la fundación | Implementado | *Finanzas* → Pagos a la fundación |
| RF22 | Generación de reportes | Implementado | *Reportes*: los 7 reportes del documento del proyecto, con filtros e impresión |
| RF23 | Correo al familiar | Implementado | Al crear la solicitud y al asignar médico. Requiere configurar SMTP para enviarse; sin SMTP queda registrado como «Simulado». |

Los costos de consultas, exámenes y medicamentos se calculan con el **descuento de la fundación**
(25 % por defecto, configurable en *Médicos y catálogos*) y se cargan a la cuenta del familiar.

## 3. Problemas y cambios

Diferencias entre el documento del proyecto y el sistema construido, con su justificación.

| Aspecto | Documento del proyecto | Sistema | Justificación |
|---|---|---|---|
| Lenguaje y entorno | Visual Studio y C# | Python 3 con FastAPI | La especificación permite "las herramientas de software que desee". FastAPI genera la documentación de cada API (`/docs`) y facilita separar el sistema en servicios. |
| Base de datos | MySQL, SQL Server u Oracle | Datos en memoria (pendiente) | Se priorizaron los módulos y la corrección de defectos. El acceso a datos está aislado en repositorios para conectar el SGBD sin rehacer el sistema. |
| Arquitectura | Por capas, con MVC y Repository/DAO | Microservicios por capas | Cada servicio mantiene la separación por capas: modelos Pydantic (validación), rutas (controladores), repositorio (acceso a datos). En el menú principal, las plantillas Jinja2 son las vistas (MVC). |
| Módulos | 12 módulos | 12 módulos, en 5 servicios | Usuarios y seguridad, y Configuración, en el menú principal; Pacientes; Solicitudes y citas; Médicos, especialidades, enfermería, ficha e historial, laboratorio y farmacia en el servicio médico; Entradas, salidas, caja, donaciones y cuotas en finanzas; Reportes en el menú principal. |
| Interfaces C# | `IPacienteService`, `IMedicoService`, ... | APIs REST por servicio | Cada interfaz de servicio del diseño corresponde a la API de un microservicio (ver `/docs`). |

Problemas encontrados en la primera versión y su causa:

1. **No se validaban los datos en el servidor** (DEF-08 a DEF-10, DEF-12 a DEF-14): solo el formulario
   HTML validaba. Ahora la validación está en cada servicio, que es la regla que se cumple siempre.
2. **El menú incrustaba páginas de otros servicios** (DEF-03, DEF-11): los formularios apuntaban a
   rutas que no existían en el menú. Ahora el menú tiene sus propias pantallas y solo pide datos JSON.
3. **El HTML se construía concatenando texto** (DEF-07): se reemplazó por plantillas que escapan el contenido.
4. **El análisis no definió los estados de una solicitud ni quién cambia cada uno**: se definieron
   Pendiente → Asignada → Atendida, o Cancelada, con el rol que puede hacer cada cambio.

## 4. Posibles errores conocidos

- Los datos se pierden al reiniciar los servicios (hasta conectar la base de datos).
- Si un servicio está apagado, sus módulos muestran "Servicio no disponible"; los demás siguen funcionando.
- Si se desactiva un usuario, pierde el acceso al menú de inmediato, pero un token suyo ya emitido sigue
  siendo aceptado por las APIs directas hasta que vence (8 horas).
- Sin servidor SMTP configurado, los correos a familiares no se envían; quedan registrados como «Simulado».

## 5. Pruebas automáticas

`python -m pytest` ejecuta 103 pruebas basadas en los casos del plan (cada prueba lleva el número
de caso en su nombre, por ejemplo `test_cp23_paciente_inexistente`), incluido un
flujo completo: solicitud → asignación → visita → examen → resultado → entrega de medicamento →
cobro, y la caída de servicios (CP-32, CP-33).

## 6. Pendientes

- Conexión a la base de datos (DEF-01, CP-20), modelo ER e instancia de la base de datos.
- Publicar el sistema en un servidor o en la nube para el acceso público.
- Actualizar el documento del proyecto con la sección "Problemas y cambios" de este informe.
