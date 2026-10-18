-- ==================================================
-- INSTANCIA DE LA BASE DE DATOS
-- Sistema de Administración del Asilo Cabeza de Algodón
-- Gestor: MySQL 8
--
-- Ejecutar como root:
--   mysql -u root -p < docs/bd/asilo.sql
--
-- ATENCIÓN: borra la base de datos si ya existe y la crea de
-- nuevo con los datos iniciales.
-- ==================================================

DROP DATABASE IF EXISTS asilo_cabeza_algodon;

CREATE DATABASE asilo_cabeza_algodon
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_spanish_ci;

-- Usuario con el que se conecta el sistema (ver comun/config.py).
CREATE USER IF NOT EXISTS 'asilo'@'localhost' IDENTIFIED BY 'Asilo2026!';
CREATE USER IF NOT EXISTS 'asilo'@'127.0.0.1' IDENTIFIED BY 'Asilo2026!';
GRANT SELECT, INSERT, UPDATE, DELETE ON asilo_cabeza_algodon.* TO 'asilo'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON asilo_cabeza_algodon.* TO 'asilo'@'127.0.0.1';

USE asilo_cabeza_algodon;

-- --------------------------------------------------
-- USUARIOS Y SEGURIDAD
-- --------------------------------------------------

CREATE TABLE usuarios (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    usuario     VARCHAR(50)  NOT NULL UNIQUE,
    nombre      VARCHAR(150) NOT NULL,
    rol         VARCHAR(50)  NOT NULL,
    activo      TINYINT(1)   NOT NULL DEFAULT 1,
    contrasena  VARCHAR(200) NOT NULL COMMENT 'PBKDF2-SHA256: sal$resumen'
);

-- --------------------------------------------------
-- PACIENTES
-- --------------------------------------------------

CREATE TABLE pacientes (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    nombre             VARCHAR(150) NOT NULL,
    edad               INT          NOT NULL CHECK (edad BETWEEN 60 AND 120),
    habitacion         VARCHAR(150) NOT NULL,
    fecha_ingreso      DATE         NOT NULL,
    motivo_ingreso     TEXT,
    familiar_nombre    VARCHAR(150),
    familiar_telefono  VARCHAR(50),
    familiar_correo    VARCHAR(150)
);

-- --------------------------------------------------
-- CATÁLOGOS DE LA FUNDACIÓN
-- --------------------------------------------------

CREATE TABLE configuracion (
    id             INT PRIMARY KEY,
    descuento_pct  DECIMAL(5,2) NOT NULL CHECK (descuento_pct BETWEEN 0 AND 100)
);

CREATE TABLE especialidades (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    nombre           VARCHAR(150)  NOT NULL UNIQUE,
    precio_consulta  DECIMAL(10,2) NOT NULL
);

CREATE TABLE medicos (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    nombre           VARCHAR(150) NOT NULL,
    especialidad_id  INT          NOT NULL,
    colegiado        VARCHAR(150) NOT NULL,
    telefono         VARCHAR(50),
    FOREIGN KEY (especialidad_id) REFERENCES especialidades (id)
);

CREATE TABLE enfermeros (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    nombre    VARCHAR(150) NOT NULL,
    turno     ENUM('Mañana', 'Tarde', 'Noche') NOT NULL,
    telefono  VARCHAR(50)
);

CREATE TABLE tipos_examen (
    id      INT AUTO_INCREMENT PRIMARY KEY,
    nombre  VARCHAR(150)  NOT NULL UNIQUE,
    precio  DECIMAL(10,2) NOT NULL
);

CREATE TABLE medicamentos (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    nombre           VARCHAR(150)  NOT NULL UNIQUE,
    presentacion     VARCHAR(150)  NOT NULL,
    precio_unitario  DECIMAL(10,2) NOT NULL,
    existencia       INT           NOT NULL DEFAULT 0 CHECK (existencia >= 0)
);

-- --------------------------------------------------
-- FICHA MÉDICA
-- --------------------------------------------------

CREATE TABLE fichas (
    id                     INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id            INT NOT NULL UNIQUE,
    tipo_sangre            VARCHAR(20),
    alergias               TEXT,
    psicopatologia         TEXT,
    enfermedades_cronicas  TEXT,
    medicamentos_base      TEXT,
    observaciones          TEXT,
    FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
);

-- --------------------------------------------------
-- SOLICITUDES MÉDICAS
-- Los campos paciente, especialidad, enfermero y médico guardan
-- el nombre en el momento de la solicitud (historial).
-- --------------------------------------------------

CREATE TABLE solicitudes (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id      INT          NOT NULL,
    paciente         VARCHAR(150) NOT NULL,
    especialidad_id  INT          NOT NULL,
    especialidad     VARCHAR(150) NOT NULL,
    motivo           TEXT         NOT NULL,
    estado           ENUM('Pendiente', 'Asignada', 'Atendida', 'Cancelada') NOT NULL DEFAULT 'Pendiente',
    enfermero_id     INT,
    enfermero        VARCHAR(150),
    medico_id        INT,
    medico           VARCHAR(150),
    horario          DATETIME,
    visita_id        INT,
    fecha_creacion   DATETIME     NOT NULL,
    creada_por       VARCHAR(150) NOT NULL,
    FOREIGN KEY (paciente_id)     REFERENCES pacientes (id),
    FOREIGN KEY (especialidad_id) REFERENCES especialidades (id),
    FOREIGN KEY (enfermero_id)    REFERENCES enfermeros (id),
    FOREIGN KEY (medico_id)       REFERENCES medicos (id)
);

CREATE TABLE notificaciones (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    solicitud_id  INT          NOT NULL,
    paciente      VARCHAR(150) NOT NULL,
    destinatario  VARCHAR(150),
    asunto        VARCHAR(200) NOT NULL,
    cuerpo        TEXT         NOT NULL,
    estado        VARCHAR(300) NOT NULL,
    fecha         DATETIME     NOT NULL,
    FOREIGN KEY (solicitud_id) REFERENCES solicitudes (id)
);

-- --------------------------------------------------
-- VISITAS, LABORATORIO Y FARMACIA
-- Cada servicio guarda su precio regular, el descuento y el
-- costo final del momento en que se realizó.
-- --------------------------------------------------

CREATE TABLE visitas (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    solicitud_id    INT           NOT NULL UNIQUE,
    paciente_id     INT           NOT NULL,
    fecha           DATETIME      NOT NULL,
    motivo          TEXT          NOT NULL,
    medico_id       INT           NOT NULL,
    medico          VARCHAR(150)  NOT NULL,
    especialidad    VARCHAR(150)  NOT NULL,
    enfermero       VARCHAR(150),
    diagnostico     TEXT          NOT NULL,
    observaciones   TEXT,
    registrada_por  VARCHAR(150)  NOT NULL,
    precio_regular  DECIMAL(10,2) NOT NULL,
    descuento_pct   DECIMAL(5,2)  NOT NULL,
    costo           DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (solicitud_id) REFERENCES solicitudes (id),
    FOREIGN KEY (paciente_id)  REFERENCES pacientes (id),
    FOREIGN KEY (medico_id)    REFERENCES medicos (id)
);

CREATE TABLE examenes (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    visita_id        INT          NOT NULL,
    paciente_id      INT          NOT NULL,
    tipo_examen_id   INT          NOT NULL,
    examen           VARCHAR(150) NOT NULL,
    indicaciones     TEXT,
    estado           ENUM('Solicitado', 'Completado') NOT NULL DEFAULT 'Solicitado',
    fecha_solicitud  DATETIME     NOT NULL,
    resultado        TEXT,
    fecha_resultado  DATETIME,
    registrado_por   VARCHAR(150),
    precio_regular   DECIMAL(10,2),
    descuento_pct    DECIMAL(5,2),
    costo            DECIMAL(10,2),
    FOREIGN KEY (visita_id)      REFERENCES visitas (id),
    FOREIGN KEY (paciente_id)    REFERENCES pacientes (id),
    FOREIGN KEY (tipo_examen_id) REFERENCES tipos_examen (id)
);

CREATE TABLE recetas (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    visita_id         INT          NOT NULL,
    paciente_id       INT          NOT NULL,
    medicamento_id    INT          NOT NULL,
    medicamento       VARCHAR(150) NOT NULL,
    cantidad          INT          NOT NULL CHECK (cantidad > 0),
    indicaciones      VARCHAR(150) NOT NULL,
    duracion          VARCHAR(150) NOT NULL,
    estado            ENUM('Pendiente de entrega', 'Entregado') NOT NULL DEFAULT 'Pendiente de entrega',
    fecha_indicacion  DATETIME     NOT NULL,
    fecha_entrega     DATETIME,
    entregado_por     VARCHAR(150),
    precio_regular    DECIMAL(10,2),
    descuento_pct     DECIMAL(5,2),
    costo             DECIMAL(10,2),
    FOREIGN KEY (visita_id)      REFERENCES visitas (id),
    FOREIGN KEY (paciente_id)    REFERENCES pacientes (id),
    FOREIGN KEY (medicamento_id) REFERENCES medicamentos (id)
);

-- --------------------------------------------------
-- FINANZAS
-- --------------------------------------------------

CREATE TABLE donaciones (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    tipo_donante    ENUM('Empresa internacional', 'Empresa nacional', 'Gobierno', 'Persona particular') NOT NULL,
    donante         VARCHAR(150)  NOT NULL,
    monto           DECIMAL(12,2) NOT NULL CHECK (monto > 0),
    fecha           DATE          NOT NULL,
    descripcion     TEXT,
    registrado_por  VARCHAR(150)  NOT NULL
);

CREATE TABLE cuotas (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id     INT           NOT NULL,
    paciente        VARCHAR(150)  NOT NULL,
    mes             CHAR(7)       NOT NULL COMMENT 'AAAA-MM',
    monto           DECIMAL(12,2) NOT NULL CHECK (monto > 0),
    fecha           DATE          NOT NULL,
    observaciones   TEXT,
    registrado_por  VARCHAR(150)  NOT NULL,
    UNIQUE (paciente_id, mes),
    FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
);

CREATE TABLE cobros (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id     INT           NOT NULL,
    paciente        VARCHAR(150)  NOT NULL,
    visita_id       INT           NOT NULL,
    monto           DECIMAL(12,2) NOT NULL CHECK (monto > 0),
    fecha           DATE          NOT NULL,
    observaciones   TEXT,
    registrado_por  VARCHAR(150)  NOT NULL,
    FOREIGN KEY (paciente_id) REFERENCES pacientes (id),
    FOREIGN KEY (visita_id)   REFERENCES visitas (id)
);

CREATE TABLE gastos (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    categoria       ENUM('Luz', 'Agua', 'Alimentación', 'Mantenimiento', 'Salarios', 'Medicamentos', 'Limpieza', 'Otros') NOT NULL,
    descripcion     VARCHAR(150)  NOT NULL,
    monto           DECIMAL(12,2) NOT NULL CHECK (monto > 0),
    fecha           DATE          NOT NULL,
    registrado_por  VARCHAR(150)  NOT NULL
);

CREATE TABLE pagos_fundacion (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    monto           DECIMAL(12,2) NOT NULL CHECK (monto > 0),
    fecha           DATE          NOT NULL,
    referencia      VARCHAR(150),
    registrado_por  VARCHAR(150)  NOT NULL
);

-- ==================================================
-- DATOS INICIALES
-- Contraseñas: admin = Admin2026!, los demás = Asilo2026!
-- ==================================================

INSERT INTO usuarios (usuario, nombre, rol, activo, contrasena) VALUES
('admin',        'Administrador del sistema',    'Administrador',        1, '75809d082149f736f9a5e789db70e190$b2ff0a930ec43ddc05a2316d32a7e76f7e7ee5611835246ae27d982371b73112'),
('personal',     'Marta Gómez',                  'Personal del asilo',   1, 'ee82cadef11b0d149327a42478972a20$cffa7e00e8d5300daf29b9ed436577e3a4a2bc7978c28ce49d0393140fb48b69'),
('medico',       'Dr. Roberto Castillo',         'Médico general',       1, 'ffb7612c2509b49692bb0231ac6627bd$ab8e11e6135315b6ff5ccc14552d15faa7659fbeeb9390ae4235ae684344c682'),
('especialista', 'Dra. Ana Ruiz',                'Médico especialista',  1, '51235b1637f31603117a4c4e2fbb80ca$848119c4d553e4437927c8f5ed28766c6435e8249979900a62e8f3632501616a'),
('enfermero',    'Rosa Hernández',               'Enfermero(a)',         1, '8f4cb5b6ff27efa93f0abf5a7c6a566d$2f1680ac16dacb4488f504ced904744c86f12954e5129bc859f48671847e7713'),
('fundacion',    'Coordinación de la Fundación', 'Fundación',            1, 'c78adf4668b9f5427f47c46a2925847e$eb9d1b6d0750f3164cc897fcd0420c91388cd55c0a6ce624d9bba46310b8fdbd'),
('laboratorio',  'Laboratorio Clínico',          'Laboratorio',          1, 'f2cce73861a3fb8d1e673728cb8502be$be8a3512e8033a10da29ad1ca0548638ba35daa3c24c3376a3e77519adfdeee4'),
('farmacia',     'Farmacia de la Fundación',     'Farmacia',             1, '2f9d63be670286ca203d9fa604aeaa18$d69b27517d0ab4ba9f6ea08c8a144ded16b2b97ac3bb245fb11f34d8f2a56a42'),
('finanzas',     'Lucía Ramírez',                'Encargado financiero', 1, 'd02a99e94a6aebd6619eb54713b58392$c8cf63d9800c1cbd74a27c2ec9db3af196f34ddc7e407f4ac76a559d85af0f64');

INSERT INTO pacientes (nombre, edad, habitacion, fecha_ingreso, motivo_ingreso, familiar_nombre, familiar_telefono, familiar_correo) VALUES
('Juan Pérez',  75, 'A-01', '2025-03-15', 'Hipertensión y necesidad de cuidado permanente', 'Carlos Pérez', '5555-1010', 'carlos.perez@example.com'),
('María López', 80, 'A-02', '2024-11-02', 'Diabetes tipo 2 y movilidad reducida',           'Ana López',    '5555-2020', 'ana.lopez@example.com');

INSERT INTO configuracion (id, descuento_pct) VALUES (1, 25.00);

INSERT INTO especialidades (nombre, precio_consulta) VALUES
('Medicina General', 100.00),
('Cardiología',      250.00),
('Medicina Interna', 200.00),
('Neurología',       275.00),
('Psiquiatría',      250.00),
('Traumatología',    225.00);

INSERT INTO medicos (nombre, especialidad_id, colegiado, telefono) VALUES
('Dr. Carlos Méndez',  1, '12345', '5555-0001'),
('Dra. Ana Ruiz',      2, '23456', '5555-0002'),
('Dr. Luis García',    3, '34567', '5555-0003'),
('Dra. Sofía Morales', 4, '45678', '5555-0004');

INSERT INTO enfermeros (nombre, turno, telefono) VALUES
('Rosa Hernández', 'Mañana', '5555-0101'),
('Pedro Sic',      'Tarde',  '5555-0102');

INSERT INTO tipos_examen (nombre, precio) VALUES
('Hematología completa', 75.00),
('Glucosa en ayunas',    30.00),
('Perfil lipídico',      90.00),
('Examen de orina',      40.00),
('Electrocardiograma',  150.00);

INSERT INTO medicamentos (nombre, presentacion, precio_unitario, existencia) VALUES
('Losartán 50 mg',      'Tableta', 2.50, 300),
('Metformina 850 mg',   'Tableta', 1.75, 250),
('Acetaminofén 500 mg', 'Tableta', 0.50, 500),
('Omeprazol 20 mg',     'Cápsula', 1.25, 200);

INSERT INTO fichas (paciente_id, tipo_sangre, alergias, psicopatologia, enfermedades_cronicas, medicamentos_base, observaciones) VALUES
(1, 'O+', 'Penicilina', 'Ansiedad leve', 'Hipertensión arterial', 'Losartán 50 mg cada 24 horas', '');

INSERT INTO solicitudes (paciente_id, paciente, especialidad_id, especialidad, motivo, estado, enfermero_id, enfermero, medico_id, medico, horario, visita_id, fecha_creacion, creada_por) VALUES
(1, 'Juan Pérez',  2, 'Cardiología',      'Dolor en el pecho', 'Pendiente', 1, 'Rosa Hernández', NULL, '',                NULL,                  NULL, '2026-10-10 08:30:00', 'Médico general'),
(2, 'María López', 3, 'Medicina Interna', 'Control médico',    'Asignada',  2, 'Pedro Sic',      3,    'Dr. Luis García', '2026-10-22 09:00:00', NULL, '2026-10-09 10:15:00', 'Médico general');

INSERT INTO donaciones (tipo_donante, donante, monto, fecha, descripcion, registrado_por) VALUES
('Empresa nacional',   'Distribuidora La Esperanza', 5000.00, '2026-10-01', 'Donación mensual', 'Datos iniciales'),
('Persona particular', 'Anónimo',                     350.00, '2026-10-05', '',                 'Datos iniciales');

INSERT INTO cuotas (paciente_id, paciente, mes, monto, fecha, observaciones, registrado_por) VALUES
(1, 'Juan Pérez', '2026-10', 1200.00, '2026-10-03', '', 'Datos iniciales');

INSERT INTO gastos (categoria, descripcion, monto, fecha, registrado_por) VALUES
('Luz',  'Factura de energía eléctrica septiembre', 1450.00, '2026-10-02', 'Datos iniciales'),
('Agua', 'Servicio de agua septiembre',              320.00, '2026-10-02', 'Datos iniciales');
