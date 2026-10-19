-- Migracion: Eliminar login de clientes, hacer Cliente standalone
-- Ejecutar en MariaDB/MySQL

-- 1. Eliminar foreign keys que dependen de personas
ALTER TABLE `solicitudes` DROP FOREIGN KEY `solicitudes_ibfk_1`;
ALTER TABLE `solicitudes_empleo` DROP FOREIGN KEY `solicitudes_empleo_ibfk_1`;
ALTER TABLE `vehiculos` DROP FOREIGN KEY `vehiculos_ibfk_1`;
ALTER TABLE `ordenes` DROP FOREIGN KEY `ordenes_ibfk_2`;
ALTER TABLE `clientes` DROP FOREIGN KEY `clientes_persona_ptr_id_fk_personas_id`;

-- 2. Eliminar tabla clientes antigua (hereda de personas)
DROP TABLE IF EXISTS `clientes`;

-- 3. Crear nueva tabla clientes (independiente, con id propio)
CREATE TABLE `clientes` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(255) NOT NULL,
  `apellido` varchar(255) DEFAULT '',
  `dni` varchar(50) NOT NULL,
  `direccion` varchar(255) DEFAULT '',
  `contacto` varchar(255) DEFAULT '',
  PRIMARY KEY (`id`),
  UNIQUE KEY `dni` (`dni`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 4. Migrar datos de clientes desde personas
INSERT INTO `clientes` (`nombre`, `apellido`, `dni`, `direccion`, `contacto`)
SELECT `nombre`, `apellido`, `dni`, `direccion`, `contacto`
FROM `personas`
WHERE `rol` = 'cliente';

-- 5. Eliminar todas las cuentas de cliente de personas
DELETE FROM `personas` WHERE `rol` = 'cliente';

-- 6. Actualizar solicitudes para apuntar al nuevo cliente por DNI
ALTER TABLE `solicitudes` ADD COLUMN `cliente_id` int(11) DEFAULT NULL;
UPDATE `solicitudes` s
INNER JOIN `clientes` c ON s.`dni` = c.`dni`
SET s.`cliente_id` = c.`id`;
ALTER TABLE `solicitudes` MODIFY `cliente_id` int(11) NOT NULL;
ALTER TABLE `solicitudes` ADD CONSTRAINT `solicitudes_cliente_fk` FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`);

-- 7. Eliminar columna username de solicitudes
ALTER TABLE `solicitudes` DROP COLUMN `username`;

-- 8. Actualizar solicitudes_empleo: eliminar FK, guardar datos personales
ALTER TABLE `solicitudes_empleo` ADD COLUMN `nombre` varchar(255) DEFAULT '';
ALTER TABLE `solicitudes_empleo` ADD COLUMN `apellido` varchar(255) DEFAULT '';
ALTER TABLE `solicitudes_empleo` ADD COLUMN `dni` varchar(50) DEFAULT '';
ALTER TABLE `solicitudes_empleo` ADD COLUMN `contacto` varchar(255) DEFAULT '';
UPDATE `solicitudes_empleo` se
INNER JOIN `personas` p ON se.`username` = p.`username`
SET se.`nombre` = p.`nombre`, se.`apellido` = p.`apellido`, se.`dni` = p.`dni`, se.`contacto` = p.`contacto`;

-- 9. Recrear empleados con FK a personas (OneToOne)
ALTER TABLE `empleados` DROP FOREIGN KEY `empleados_persona_ptr_id_fk_personas_id`;
ALTER TABLE `empleados` DROP PRIMARY KEY;
ALTER TABLE `empleados` CHANGE `persona_ptr_id` `persona_id` int(11) NOT NULL;
ALTER TABLE `empleados` ADD PRIMARY KEY (`persona_id`);
ALTER TABLE `empleados` ADD CONSTRAINT `empleados_persona_fk` FOREIGN KEY (`persona_id`) REFERENCES `personas` (`id`);

-- 10. Recrear FK de vehiculos a clientes
ALTER TABLE `vehiculos` ADD CONSTRAINT `vehiculos_cliente_fk` FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`);

-- 11. Recrear FK de ordenes a clientes y empleados
ALTER TABLE `ordenes` ADD CONSTRAINT `ordenes_cliente_fk` FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`);
ALTER TABLE `ordenes` ADD CONSTRAINT `ordenes_empleado_fk` FOREIGN KEY (`empleado_id`) REFERENCES `empleados` (`persona_id`);

-- 12. Limpiar solicitudes_empleo: eliminar username FK (ya no necesario)
-- Mantener username como campo de texto plano
