=== MEDIDAS ===

** Número de puestos **
Número de puestos de trabajo existentes en la UZ. Se incluyen todos los puestos de RPT y los puestos fuera d RPT que estén ocupados.

=== DIMENSIONES ===

## DIMENSION: Centro ##

Notas generales:
- Permite clasificar los datos en función del centro al que están adscritos los puestos.

## DIMENSION: Dedicación del puesto ##

Notas generales:
- Identifica el tipo de dedicación de los puestos de trabajo.

>Valores posibles: tiempo completo, tiempo parcial, tiempo parcial 6 horas, tiempo parcial 4 horas, tiempo
parcial 3 horas, conjunta completa, conjunta parcial (es la dedicación del personal de ciencias de la salud), colaborador extraordinario.

## DIMENSION: Departamento ##

Notas generales:
- Permite clasificar los datos en función del departamento al que están adscritos los puestos.

## DIMENSION: Fecha de actualización ##

Notas generales:
- Indica la fecha de la última recarga de datos. Habitualmente es el domingo anterior a la consulta de datos.

## DIMENSION: Grupos puesto ##

Notas generales:
- Permite agrupar los puestos de trabajo en función del grupo de pertenencia de los empleados que pueden desempeñarlos con carácter definitivo.

## DIMENSION: Nivel complemento ##

Notas generales:
- Permite agrupar los puestos de trabajo en función del nivel de complemento que tienen asignado.

## DIMENSION: Puesto ##

Notas generales:
- Permite agrupar los puestos de trabajo según su denominación.

## DIMENSION: Puesto Categoría ##

Notas generales:
- Permite agrupar los datos en función de la categoría de los puestos de trabajo.

## DIMENSION: Puesto Desempeño ##

Notas generales:
- Permite agrupar los puestos de trabajo en función de la persona que lo está desempeñando.

>Valores posibles: Titular, No Titular, Sin ocupante.
>TITULAR: la persona que desempeña el puesto es su titular.
>NO TITULAR: quien desempeña el puesto es una persona distinta de su titular. En caso de que el puesto sea
fuera de RPT, figurará siempre en esta dimensión el valor “no titular”, porque los puestos fuera de RPT no tienen titular, pero sí una persona que lo desempeña.

>SIN OCUPANTE: el puesto no lo desempeña ninguna persona.

## DIMENSION: Puesto Situación ##

Notas generales:
- Permite agrupar los puestos de trabajo según su situación.

>Valores posibles: ocupado por el titular, vacante técnica, vacante efectiva, fuera de RPT
>OCUPADO POR EL TITULAR: puesto de RPT asignado con carácter definitivo a un empleado. A su vez puede
estar desempeñado por una persona distinta del titular del puesto (ver dimensión “puesto desempeño”). En estos casos habrá dos personas con vinculación a ese puesto: la titular y quien lo desempeñe –o más, según l casos, por ejemplo, si un sustituto es a su vez sustituido por una situación de ILT-.

>VACANTE: puesto de RPT que no está asignado con carácter definitivo a nadie, no tiene titular. Se distingue
dos casos: cuando el puesto está desempeñado temporalmente por un empleado (vacante TÉCNICA) y cuand nadie desempeña ese puesto (vacante EFECTIVA)

>FUERA DE RPT: puestos fuera de plantilla.

## DIMENSION: Puesto de Investigación (S/N) ##

Notas generales:
- Permite distinguir si los puestos se remuneran con cargo a proyectos de investigación (S) o no (N).

>Observación: se considerarán Puesto de Investigación si están asignados a los programas 148I, 171I, 417-I,
423-I, 425-I ó 541-I.

## DIMENSION: Régimen Jurídico ##

Notas generales:
- Permite agrupar los puestos de trabajo en función del régimen jurídico al que se adscribe su cobertura.

>Valores posibles: funcionario, laboral, atípico (es el caso de los colaboradores extraordinarios y el de los
eméritos), contratado administrativo.

## DIMENSION: TIEMPO ##

Notas generales:
- Permite ubicar en el tiempo la existencia de los puestos de trabajo. Se pueden desglosar los datos según el a o el mes: • MES: se incluyen los puestos existentes a fecha último día del mes seleccionado (si se trata de un mes curso, se incluyen los puestos existentes a la fecha de la última carga). • AÑO: se acumulan los puestos existentes a fecha último día de todos los meses del año seleccionado ( el año seleccionado es un año en curso, se acumulan los puestos existentes a fecha último día de los meses anteriores y para el mes en curso los puestos existentes a la fecha de la última carga).

## DIMENSION: Tipo puesto ##

Notas generales:
- Permite distinguir si los puestos de trabajo son de PDI o de PAS.

## DIMENSION: Unidad ##

Notas generales:
- Permite clasificar los datos en función de la unidad a la que están adscritos los puestos.

## DIMENSION: Vinculado Instituciones Sanitarias ##

Notas generales:
- Permite identificar si los puestos están vinculados a instituciones sanitarias (S) o no (N).

