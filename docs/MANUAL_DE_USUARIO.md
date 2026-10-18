# Manual de usuario

Sistema de Administración del Asilo de Ancianos Cabeza de Algodón.

## 1. Ingreso al sistema

1. Verifique que MySQL esté encendido, inicie el sistema (ver *Instalación* en el `README.md`) y abra **http://127.0.0.1:8002**.
2. Escriba su **usuario** y **contraseña** y presione **Iniciar sesión**.
3. El menú principal muestra solo los módulos que su rol puede usar.
4. Para salir, presione **Cerrar sesión** (arriba a la derecha). La sesión se cierra sola después de 8 horas.

## 2. Qué puede hacer cada rol

| Rol | Puede |
|---|---|
| Administrador | Todo, incluida la administración de usuarios |
| Personal del asilo | Registrar y editar pacientes; registrar enfermeros |
| Médico general | Consultar y actualizar la ficha, crear y cancelar solicitudes, asignar enfermero, registrar visitas con exámenes y medicamentos, ver correos a familiares |
| Médico especialista | Consultar y actualizar la ficha, registrar visitas, solicitar exámenes e indicar medicamentos |
| Enfermero(a) | Consultar pacientes, solicitudes, ficha e historial |
| Fundación | Asignar médico y horario, administrar médicos, especialidades, exámenes, medicamentos y el descuento |
| Laboratorio | Ver exámenes solicitados y registrar resultados |
| Farmacia | Ver medicamentos indicados y registrar entregas |
| Encargado financiero | Finanzas y reportes financieros |

## 3. Pacientes

1. Entre a **Pacientes**. Use **Buscar** para encontrar un paciente por nombre o habitación.
2. **Registrar paciente**: complete nombre, edad (60 a 120 años) y habitación (obligatorios), y los
   datos del familiar. El correo del familiar se usa para los avisos de solicitudes médicas.
3. **Ver** muestra los datos del paciente y sus solicitudes. **Editar** permite cambiar sus datos.

## 4. Atención médica

1. **Crear la solicitud** (médico general): *Solicitudes médicas* → **Nueva solicitud**. Elija el
   paciente, la especialidad, el motivo y, si ya se conoce, el enfermero(a) acompañante.
   El sistema envía un correo al familiar.
2. **Asignar enfermero(a)** (médico general): en el detalle de la solicitud.
3. **Asignar médico y horario** (fundación): en el detalle de la solicitud elija el médico de la
   especialidad y la fecha y hora. La solicitud pasa a *Asignada* y se avisa al familiar.
4. **Atender al paciente** (médico): *Atención médica* → **Atender**. Se muestra la solicitud y el motivo;
   el botón *Consultar ficha e historial* abre la ficha del paciente. Registre el diagnóstico y las
   observaciones. La solicitud pasa a *Atendida* y se convierte en visita médica.
5. En la visita, el médico puede **solicitar exámenes** de laboratorio e **indicar medicamentos**
   (cantidad, cómo tomarlo y tiempo de aplicación).
6. **Ficha médica**: desde el paciente → *Ficha e historial médico*. Registre tipo de sangre, alergias,
   psicopatología, enfermedades crónicas y medicamentos de base. Debajo aparece el historial de visitas
   con exámenes, resultados y medicamentos.

## 5. Laboratorio y farmacia

- **Laboratorio**: filtre por paciente para identificar al interno, realice los exámenes y escriba el
  resultado. El médico lo ve en la visita y en el historial.
- **Farmacia**: en *Pendientes de entrega* presione **Registrar entrega**. Se descuenta la existencia y
  el costo se asigna a la visita médica.

## 6. Finanzas

- **Resumen**: entradas, salidas, balance y cuenta con la fundación, para todo el periodo o un rango de fechas.
- **Cuentas de pacientes**: cargos de consultas, exámenes y medicamentos con el descuento de la fundación.
  En el estado de cuenta de cada paciente se ve qué citas están pendientes de pago y se registra el cobro.
- **Donaciones**, **Cuotas mensuales**, **Gastos** y **Pagos a la fundación**: formulario para registrar
  y lista con filtro por fechas.

## 7. Reportes

*Reportes* muestra los reportes que su rol puede generar. Elija paciente y fechas si aplica, presione
**Generar** y use **Imprimir / PDF** para guardarlo.

1. Costos de cada cita por paciente (consulta, exámenes y medicamentos).
2. Análisis médico por paciente (ficha, motivo de ingreso, visitas y medicamentos).
3. Cobros por paciente y rango de fechas, con el detalle de los gastos médicos.
4. Pagos a la fundación.
5. Entradas: donaciones, cuotas y cobros.
6. Exámenes médicos realizados por paciente.
7. Medicamentos aplicados por paciente.

## 8. Usuarios (administrador)

*Usuarios* → **Nuevo usuario**: nombre de usuario sin espacios, nombre completo, rol y contraseña de
al menos 8 caracteres. En **Editar** se cambia el nombre, el rol, la contraseña o se desactiva el usuario.

## 9. Mensajes de error y qué hacer

| Mensaje | Causa | Qué hacer |
|---|---|---|
| Usuario o contraseña incorrectos | Datos de acceso equivocados | Revise mayúsculas y vuelva a intentar |
| Su usuario está desactivado | El administrador desactivó la cuenta | Comuníquese con el administrador |
| Acceso denegado | Su rol no puede usar ese módulo | Use un usuario con el rol adecuado |
| Campos marcados en rojo | Falta un dato obligatorio o tiene un formato inválido | Corrija el campo indicado; lo demás que escribió se conserva |
| Ya existe un paciente / registro con ese nombre | Registro duplicado | Busque el registro existente |
| El servicio de … no está disponible | Ese servicio está apagado o sin conexión | Use los demás módulos y vuelva a intentar; si continúa, avise al administrador |
| No hay existencia suficiente | La farmacia no tiene la cantidad indicada | Actualice la existencia en *Médicos y catálogos* → Medicamentos |
| El monto excede el saldo pendiente | El cobro es mayor que lo que se debe | Revise el saldo de la cita |

| Base de datos no disponible | MySQL está apagado o sin conexión | Encienda el servicio MySQL de Windows y vuelva a intentar |
| No se puede eliminar: otros registros dependen de este | El registro tiene historial (solicitudes, visitas, pagos) | No se elimina, para conservar el historial |
