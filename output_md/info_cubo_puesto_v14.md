# Información del Cubo: Cargos y Puestos

*Fecha de generación: 17/06/2025*

*Archivo fuente: info_cubo_puesto_v14.csv*

---

# Medidas

Las medidas son los valores numéricos que se pueden calcular y analizar en este cubo.

## Número de puestos

Número de puestos de trabajo existentes en la UZ. Se incluyen todos los puestos de RPT y los puestos fuera d RPT que estén ocupados.

---

# Dimensiones

Las dimensiones permiten desglosar y filtrar los datos según diferentes criterios.

## TIEMPO

Permite ubicar en el tiempo la existencia de los puestos de trabajo. Se pueden desglosar los datos según el a o el mes: • MES: se incluyen los puestos existentes a fecha último día del mes seleccionado (si se trata de un mes curso, se incluyen los puestos existentes a la fecha de la última carga). • AÑO: se acumulan los puestos existentes a fecha último día de todos los meses del año seleccionado ( el año seleccionado es un año en curso, se acumulan los puestos existentes a fecha último día de los meses anteriores y para el mes en curso los puestos existentes a la fecha de la última carga).

---

## Área

Permite clasificar los datos en función del área a la que están adscritos los puestos.

---

## Centro

Permite clasificar los datos en función del centro al que están adscritos los puestos.

---

## Dedicación del puesto

Identifica el tipo de dedicación de los puestos de trabajo. 

**Valores posibles:** tiempo completo, tiempo parcial, tiempo parcial 6 horas, tiempo parcial 4 horas, tiempo parcial 3 horas, conjunta completa, conjunta parcial (es la dedicación del personal de ciencias de la salud), colaborador extraordinario.

---

## Departamento

Permite clasificar los datos en función del departamento al que están adscritos los puestos.

---

## Grupos puesto

Permite agrupar los puestos de trabajo en función del grupo de pertenencia de los empleados que pueden desempeñarlos con carácter definitivo.

---

## Nivel complemento

Permite agrupar los puestos de trabajo en función del nivel de complemento que tienen asignado.

---

## Puesto

Permite agrupar los puestos de trabajo según su denominación.

---

## Puesto Categoría

Permite agrupar los datos en función de la categoría de los puestos de trabajo.

---

## Puesto Desempeño

Permite agrupar los puestos de trabajo en función de la persona que lo está desempeñando. 

**Valores posibles:** Titular, No Titular, Sin ocupante. >TITULAR: la persona que desempeña el puesto es su titular. >NO TITULAR: quien desempeña el puesto es una persona distinta de su titular. En caso de que el puesto sea fuera de RPT, figurará siempre en esta dimensión el valor “no titular”, porque los puestos fuera de RPT no tienen titular, pero sí una persona que lo desempeña. >SIN OCUPANTE: el puesto no lo desempeña ninguna persona.

---

## Puesto Situación

Permite agrupar los puestos de trabajo según su situación. 

**Valores posibles:** ocupado por el titular, vacante técnica, vacante efectiva, fuera de RPT >OCUPADO POR EL TITULAR: puesto de RPT asignado con carácter definitivo a un empleado. A su vez puede estar desempeñado por una persona distinta del titular del puesto (ver dimensión “puesto desempeño”). En estos casos habrá dos personas con vinculación a ese puesto: la titular y quien lo desempeñe –o más, según l casos, por ejemplo, si un sustituto es a su vez sustituido por una situación de ILT-. >VACANTE: puesto de RPT que no está asignado con carácter definitivo a nadie, no tiene titular. Se distingue dos casos: cuando el puesto está desempeñado temporalmente por un empleado (vacante TÉCNICA) y cuand nadie desempeña ese puesto (vacante EFECTIVA) >FUERA DE RPT: puestos fuera de plantilla.

---

## Puesto de Investigación (S/N)

Permite distinguir si los puestos se remuneran con cargo a proyectos de investigación (S) o no (N). >Observación: se considerarán Puesto de Investigación si están asignados a los programas 148I, 171I, 417-I, 423-I, 425-I ó 541-I.

---

## Régimen Jurídico

Permite agrupar los puestos de trabajo en función del régimen jurídico al que se adscribe su cobertura. 

**Valores posibles:** funcionario, laboral, atípico (es el caso de los colaboradores extraordinarios y el de los eméritos), contratado administrativo.

---

## Tipo puesto

Permite distinguir si los puestos de trabajo son de PDI o de PAS.

---

## Unidad

Permite clasificar los datos en función de la unidad a la que están adscritos los puestos.

---

## Vinculado Instituciones Sanitarias

Permite identificar si los puestos están vinculados a instituciones sanitarias (S) o no (N).

---

## Fecha de actualización

Indica la fecha de la última recarga de datos. Habitualmente es el domingo anterior a la consulta de datos.

---

## Resumen

- **Total de medidas:** 1
- **Total de dimensiones:** 17
- **Total de elementos:** 18


---

*Documento generado automáticamente mediante script de conversión de cubos CSV a Markdown.*
