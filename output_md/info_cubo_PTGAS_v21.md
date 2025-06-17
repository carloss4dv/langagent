# Información del Cubo: Personal Técnico, de Gestión y Administración y Servicios (PTGAS)

*Fecha de generación: 17/06/2025*

*Archivo fuente: info_cubo_PTGAS_v21.csv*

---

# Medidas

Las medidas son los valores numéricos que se pueden calcular y analizar en este cubo.

## Número de PTGAS

Número de efectivos de Personal Técnico, de Gestión, de Administración y Servicios (PTGAS) que constan en bases de datos de personal con contrato activo a la fecha de consulta. Observaciones: 

> **⚠️ IMPORTANTE:** se debe utilizar la dimensión TIEMPO (año o mes) para filtrar el número de efectivos en un periodo o fecha concreta. Se incluye la totalidad de efectivos, estén ocupando o no su puesto.

---

# Dimensiones

Las dimensiones permiten desglosar y filtrar los datos según diferentes criterios.

## TIEMPO

Permite ubicar en el tiempo la relación del personal con la UZ. Se pueden desglosar los datos según el año o mes: • MES: se incluyen los efectivos existentes a fecha último día del mes seleccionado (si se trata de un m en curso, se incluyen los efectivos existentes a la fecha de la última carga). • AÑO: se acumulan los efectivos existentes a fecha último día de todos los meses del año seleccionad (si el año seleccionado es un año en curso, se acumulan los efectivos existentes a fecha último día de los meses anteriores y para el mes en curso los efectivos existentes a la fecha de la última carga).

---

### Contrato – Categoría Cuerpo Escala

Permite clasificar los datos en función de la categoría/cuerpo/escala a la que pertenecen los empleados.

---

### Contrato – Dedicación

Identifica el tipo de dedicación que tienen los empleados. 

**Valores posibles:** tiempo completo, tiempo parcial.

---

### Contrato – Grado complemento

Permite agrupar los datos en función del grado de complemento personal consolidado por los empleados. >Nota: en caso de que el empleado no haya consolidado grado de complemento se indica "No informado".

---

### Contrato – Grupo

Permite agrupar los datos en función del grupo de pertenencia laboral de los empleados. 

**Valores posibles:** A1, A2, C1, C2, LA, LB, LC, LD.

---

### Contrato – Régimen Jurídico

Permite agrupar a los empleados en función del régimen jurídico en el que se adscribe su nombramiento o contrato. 

**Valores posibles:** funcionario, laboral.

---

### Contrato – Situación Administrativa

Permite agrupar los empleados en función de la situación administrativa en la que se encuentren. 

**Ejemplos:** servicio activo, excedencia, suspensión de contrato, servicios especiales.

---

### Contrato – Tipo personal

Permite agrupar los empleados en función de la modalidad de régimen jurídico. 

**Valores posibles:** de carrera, interino, indefinido fijo, temporal, en prácticas.

---

### Persona - Edad

Permite agrupar los empleados en función de su edad a fecha 31 de diciembre del año seleccionado. 

**Valores posibles:** 21-25, 26-30, 31-35, 36-40, 41-45, 46-50, 51-55, 56-60, 61-65,>65.

---

### Persona – Nivel Titulación

Permite clasificar los datos en función del nivel de titulación de los empleados. 

**Valores posibles:** Doctor, Máster, Grado, Licenciados o equivalentes, Diplomados o equivalentes, Bachiller Superior o equivalente, Bachiller elemental o equivalente, Enseñanza primaria o equivalente.

---

### Persona – País Nacionalidad

Permite clasificar los datos en función del país de nacionalidad legal del personal.

---

### Persona - Residencia

Identifica el país, la comunidad autónoma, la provincia o la población de residencia familiar informada por lo empleados.

---

### Persona – Sexo

Permite clasificar los empleados en función de su sexo.

---

### Puesto - Categoría

Permite clasificar los datos en función de la categoría del puesto que ocupan los empleados.

---

### Puesto – Centro

Permite clasificar los datos en función del centro al que están adscritos los empleados.

---

### Puesto – Centro Localidad

Permite clasificar los datos en función de la localidad donde se sitúa el centro al que están adscritos los empleados.

---

## Puesto-Especialidad RPT

Permite clasificar a los empleados en función de la especialidad a la que está asignado en la Relación de Puestos de Trabajo el puesto que ocupan. 

**Valores posibles:** Área de Administración y Servicios Generales, Área Técnica, de Mantenimiento y Oficios, Apoyo a la Docencia e Investigación y Laboratorios, Fuera RPT.

---

### Puesto – PTGAS de Investigación (S/N)

Permite distinguir si los efectivos de PTGAS se remuneran con cargo a proyectos de investigación (S) o no (N) >Observación: se considerarán PTGAS de Investigación si ocupan puestos asignados a los programas 148I, 171I, 417-I, 423-I ó 425-I.

---

### Puesto – Unidad

Permite clasificar los datos en función de la unidad a la que están adscritos los empleados.

---

### Tramos – Gestión Trienios

Permite clasificar los datos en función del número de trienios o tramos de gestión que tienen reconocidos los empleados. >Nota: contabiliza los trienios acumulados por el empleado en la fecha (año o mes) seleccionada en la dimensión “tiempo”.

---

### Compatibilidad – Concedida (S/N)

Permite clasificar los datos en función de si los empleados tienen concedida (S) o no (N), por esta institución, compatibilidad con otras actividades públicas o privadas.

---

## Sindicato

Permite clasificar a los empleados en función de si tienen concedida o no algún tipo de reducción horaria par el desempeño de tareas sindicales. >Nota: si los empleados tienen concedida reducción se detalla la denominación del sindicato y si no tienen concedida reducción figura el valor “No Informado”.

---

### Sindicato – Reducción

Identifica el porcentaje de reducción horaria o número de horas lectivas que se reducen por el desempeño d tareas sindicales, figuran con el valor “No informado”. >Nota: si el empleado no tiene concedida reducción horaria, figura con el valor “Sin reducción”.

---

## Fecha de actualización

Indica la fecha de la última recarga de datos. Habitualmente es el domingo anterior a la consulta de datos.

---

## Resumen

- **Total de medidas:** 1
- **Total de dimensiones:** 24
- **Total de elementos:** 25


---

*Documento generado automáticamente mediante script de conversión de cubos CSV a Markdown.*
