=== MEDIDAS ===

** Alumnos graduados **
Número de estudiantes que han completado todos los créditos del plan de estudios, sin tener en cuenta si han solicitado o no el título. Notas:

>Para ser considerado graduado, un estudiante debe completar no sólo el número total de créditos de un plan
de estudios, sino los créditos mínimos de cada tipo de asignatura (básicos, obligatorios, optativos, etc.)

>Aclaración referente al tipo de estudio Doctorado: no se incluyen los programas de doctorado regulados por
los RD 185/1985 y 778/1998.

>Si se quiere obtener el número de alumnos graduados correspondientes al tipo de estudio Doctorado por curso
académico, el curso que se indica es aquél en que el doctorando lee su tesis doctoral.

** Alumnos que interrumpen sus estudios **
Número de estudiantes de un estudio que, sin obtener el título ni trasladarse a otra universidad, no se matriculan durante dos años consecutivos.

>Nota: se identifica con los tipos de egreso “abandono voluntario” (el expediente queda abierto), “régimen de
permanencia” y “cambio de estudios sin simultaneidad”.

** Alumnos que interrumpen sus estudios el primer año **
Es un caso particular de la medida “alumnos que interrumpen sus estudios”, siendo los dos años consecutivos de no matrícula los dos siguientes al año de acceso del estudiante al estudio.

** Alumnos que se trasladan a otra universidad **
Número de estudiantes de un plan de estudios a los que se les cierra el expediente por traslado a otra universidad o centro.

** Duración media en años de los graduados **
Media de los años que tardan los alumnos graduados en superar sus estudios.

>Cálculo de la duración: año de la graduación – año de acceso + 1
>Criterios de cálculo:
a) Se excluyen los alumnos de cursos de adaptación a grados. b) Se excluyen los alumnos que tengan reconocidos (o adaptados o convalidados) más del 15% de los créditos del plan de estudios. c) Se excluyen los alumnos acogidos a la modalidad de tiempo parcial en alguno de los años cursados.

** Media de cursos matriculados **
Calcula el promedio de cursos en que se han matriculado los estudiantes egresados en un estudio, cualquiera que sea el tipo de egreso (graduado, abandono, traslado).

>Nota: si quiere obtenerse la media de cursos matriculados por los graduados deberá seleccionarse la dimensión
"tipo de egreso", filtrando ésta por el valor "Graduado".

** Media de créditos matriculados **
Es el promedio de la totalidad de créditos en que se han matriculado los estudiantes egresados en un estudio, cualquiera que sea el tipo de egreso (graduado, abandono, traslado).

>Nota: si quiere obtenerse la media de créditos matriculados por los graduados deberá seleccionarse la
dimensión "tipo de egreso", filtrando ésta por el valor "Graduado".

** Tasa de Eficiencia (*) **
Relación porcentual entre el número total de créditos que han superado el conjunto de graduados de un determinado año académico a lo largo del estudio en el que se han titulado y el número total de créditos en que se han matriculado. Observaciones:

>Se excluyen los estudiantes de cursos de adaptación a grados.
>Se excluyen los estudiantes que tengan reconocidos (o adaptados o convalidados) más del 15% de los créditos
del plan de estudios.

=== DIMENSIONES ===

## DIMENSION: Acceso ##

Atributos:
• Estudio previo:
Identifica la clase de estudio cursado anteriormente por los estudiantes, que les da acceso a la Universidad, de acuerdo con los requisitos establecidos por la legislación vigente.

>Valores posibles: Pruebas de Acceso, COU sin PAU, FP, Titulados Universitarios, Mayores de 25, Mayores de 40,
Mayores de 45.

>Los estudiantes procedentes de Bachillerato se incluyen en “Pruebas de Acceso”. Los estudiantes procedentes
de Ciclos Formativos de Grado Superior se incluyen en “FP”, aunque se hayan presentado a la fase específica de la EvAU.

>Nota: el valor “No informado” se aplica a estudiantes procedentes de adaptaciones por extinción de planes de
estudios o que no han accedido a la titulación por procedimientos de preinscripción.

## DIMENSION: Alumno ##

Atributos:
• País Nacionalidad:
Permite clasificar los datos en función del país de nacionalidad legal de los estudiantes.

• Rango de Edad:
Permite agrupar los rangos de edad de los estudiantes en función de su edad a 31 de diciembre del curso académico seleccionado.

>Valores posibles: 18 años o menos, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30 a 34, 35 a 39, 40 a 44, 45 a 49,
50 a 54, 55 a 59, 60 a 64, 65 años o más.

• Residencia Familiar:
Identifica el país, la comunidad autónoma, la provincia o la población de residencia familiar indicada por el estudiante en el curso académico en que se egresa.

• Sexo:
Permite agrupar los estudiantes en función de su sexo.

## DIMENSION: CURSO ACADÉMICO ##

Notas generales:
- Identifica los diferentes cursos académicos (por ejemplo 2023/24).

>Si se quiere consultar el número de egresados por curso académico, el curso es aquél en que el estudiante
supera los créditos necesarios para la obtención del título.

>En el caso de los egresados en estudios de doctorado, el curso académico de obtención del título es el de lectura
de la tesis doctoral.

## DIMENSION: Centro Egreso ##

Notas generales:
- Permite clasificar los datos en función del centro (código y denominación) en que egresan los estudiantes.

Atributos:
• Localidad:
Permite clasificar los datos en función de la localidad a la que pertenece el centro en que egresan los estudiantes.

• Tipo:
Permite clasificar los datos en función del tipo de centro (facultad, escuela universitaria, centro adscrito, etc.) en que egresan los estudiantes.

## DIMENSION: Centro Origen ##

Notas generales:
- Permite clasificar los datos en función del centro (código y denominación) en que el estudiante comenzó los estudios en los que egresa.

>Nota: el centro de egreso y el centro de origen coincidirá cuando el estudiante haya cursado un estudio en el
mismo centro desde el curso académico de acceso hasta el de egreso. Sin embargo no coincidirán cuando haya habido un traslado de expediente para continuar estudios o un cambio de denominación del centro.

Atributos:
• Localidad:
Permite clasificar los datos en función de la localidad a la que pertenece el centro en que el estudiante comenzó los estudios en los que egresa.

## DIMENSION: Egreso ##

Atributos:
• Abandono Inicial (S/N):
Permite distinguir los estudiantes que han interrumpido sus estudios el primer año (S: dos años consecutivos sin matrícula después del de acceso al estudio) del resto (N).

>Nota: se recomienda cruzar esta dimensión con la medida "alumnos que interrumpen sus estudios".

• Créditos Matriculados:
Permite clasificar los datos en función del rango de créditos matriculados por los estudiantes egresados (cualquiera que sea su tipo de egreso: graduado, abandono, traslado).

• Créditos Necesarios:
Permite clasificar los datos en función del rango de créditos necesarios que el estudiante debe superar para finalizar el estudio.

• Créditos Reconocidos:
Permite clasificar los datos en función del rango de créditos reconocidos por los estudiantes egresados (cualquiera que sea su tipo de egreso: graduado, abandono, traslado).

• Créditos Superados:
Permite clasificar los datos en función del rango de créditos superados por los estudiantes egresados (cualquiera que sea su tipo de egreso: graduado, abandono, traslado).

• Curso más alto matriculado:
Identifica el máximo curso en que el estudiante egresado (cualquiera que sea su tipo de egreso: graduado, abandono, traslado) ha llegado a tener asignaturas matriculadas.

>Nota: el valor 0 se corresponde con asignaturas de Programas de Doctorado, Proyectos Fin de Carrera,
asignaturas no asociadas a curso, sino a ciclo, y asignaturas matriculadas por estudiantes de Programas de Intercambio que vienen a la UZ.

• Número de años cursados:
Permite clasificar los datos en función del número de años matriculados por los estudiantes que se egresan en el curso académico seleccionado (cualquiera que sea su tipo de egreso: graduado, abandono, traslado).

>Nota: se contabiliza como año cursado si al menos el estudiante se matricula en una asignatura. Si en un año
académico reconoce créditos pero no matricula ninguno, no se contabiliza como año cursado.

• Solicita título (S/N):
Identifica si el estudiante ha solicitado el título (S) o no (N).

• Tipo de Egreso:
Clasifica a los estudiantes en función de la causa de su egreso: graduado, abandono voluntario (dos años consecutivos sin matrícula), incumplimiento de la normativa del régimen de permanencia, cambio de estudios sin simultaneidad, traslado a otra universidad.

## DIMENSION: Fecha de actualización ##

Notas generales:
- Indica la fecha de la última recarga de datos. Habitualmente es el sábado anterior a la consulta de datos.

## DIMENSION: Movilidad ##

Atributos:
• Internacional:
Identifica si los estudiantes egresados (cualquiera que sea su tipo de egreso: graduado, abandono, traslado) han realizado en alguno de los años en que han estado matriculados una estancia en una universidad extranjera (S) o no (N), en el marco de los acuerdos bilaterales o programas de movilidad internacionales.

## DIMENSION: Movilidad: Programa ##

Notas generales:
- Identifica el tipo de Programa Internacional o la denominación del mismo, en caso de que los estudiantes egresados (cualquiera que sea su tipo de egreso: graduado, abandono, traslado) hayan realizado en alguno de los años en que ha estado matriculado una estancia en una universidad extranjera, en el marco de los acuerdos bilaterales o programas de movilidad internacionales, según el programa de intercambio cursado.

>Valores posibles Tipo Programa de Movilidad: Erasmus, Otras Dentro de la UE, Otras Fuera de la UE.
>Valores posibles Programa de Movilidad: Erasmus, Movilidad Iberoamérica, UZ/Norteamérica, Oceanía y Asia,
Movilidad UE-Suiza, etc.

>En el caso de no haberse realizado estancia de movilidad, se indica “No Informado”.

## DIMENSION: Titulación ##

Atributos:
• Duración oficial:
Permite clasificar los datos en función de la duración oficial (en años) del estudio en que egresan los estudiantes.

>Valores posibles: 1, 2, 3, 4, 5, 6.
>Los programas de doctorado no tienen una duración establecida y figuran con el valor 0.

• Estudio:
Permite identificar el estudio cursado por los estudiantes egresados. Observaciones:

>No es lo mismo “estudio” que “plan de estudios”.
>Bajo un mismo estudio pueden existir varios planes, bien porque se imparten en distintas localidades (ejemplos:
ADE, Enfermería, Magisterio, Medicina, etc.) o bien porque se ha modificado el plan de estudios, pero el estudio sigue siendo el mismo (ejemplos: másteres regulados por el RD 56/2005 que se renuevan en virtud del RD 1393/2007).

• Múltiple titulación (S/N):
Permite identificar a los estudiantes egresados en estudios que forman parte de una múltiple titulación (S).

>Ejemplo: egresados en las titulaciones de Derecho o ADE cuando éstas han sido cursadas como parte de la
Programación Conjunta Derecho-ADE.

• Plan de Estudios:
Permite identificar el plan de estudios (código y denominación) cursado por los estudiantes egresados.

• Rama de Conocimiento:
Permite clasificar los datos en función de la Rama de Conocimiento (Artes y Humanidades, Ciencias, Ciencias Sociales y Jurídicas, Ciencias de la Salud, Ingeniería y Arquitectura) a la que pertenece el estudio en que egresan los estudiantes.

• Tipo de estudio:
Permite identificar el tipo de estudio cursado por los estudiantes egresados: grado, máster, doctorado, licenciatura o equivalente, diplomatura o equivalente.

## DIMENSION: Traslado ##

Atributos:
• Centro:
Identifica la universidad y el centro al que se trasladan los estudiantes a los que se cierra el expediente por traslado a otra universidad o centro.

>Nota: se recomienda cruzar esta dimensión con la medida "alumnos que se trasladan a otra universidad".

• Estudio:
Identifica el estudio al que trasladan los estudiantes a los que se cierra el expediente por traslado a otra universidad o centro.

>Nota: se recomienda cruzar esta dimensión con la medida "alumnos que se trasladan a otra universidad".

