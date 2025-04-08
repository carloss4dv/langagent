=== MEDIDAS ===

** Alumnos Matriculados **
Número total de estudiantes matriculados en Estudios Propios.

>Se debe introducir en la consulta la dimensión “CURSO ACADÉMICO”. De esta forma se evita acumular el to
de estudiantes de todos los cursos.

=== DIMENSIONES ===

## DIMENSION: Alumno ##

Atributos:
• País Nacionalidad:
Permite clasificar los datos en función del país de nacionalidad legal de los estudiantes.

• País Procedencia:
Identifica el país de residencia familiar indicado por el estudiante en SIGMA.

• Rango de Edad:
Permite agrupar los rangos de edad de los estudiantes en función de su edad a fecha 31 de diciembre del cur académico en que están matriculados.

>Valores posibles: 18 años o menos, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30 a 34, 35 a 39, 40 a 44, 45 a 4
50 a 54, 55 a 59, 60 a 64, 65 años o más.

• Sexo:
Permite agrupar los estudiantes en función de su sexo.

## DIMENSION: CURSO ACADÉMICO ##

Notas generales:
- Identifica los diferentes cursos académicos (por ejemplo 2013/14) de matrícula de los estudiantes.

## DIMENSION: Estudio Propio ##

Atributos:
• Duración (cursos):
Permite clasificar los datos en función del número de cursos de que consta el estudio.

• Edición:
Permite clasificar los datos en función del número de edición de los cursos desde su implantación.

• Modalidad:
Permite clasificar los datos en función de la presencialidad del estudio.

>Valores posibles: Presencial, Semipresencial, Semipresencial/On-line, Presencial/Semipresencial/On-line,
Presencial/Semipresencial, Presencial / On line, On line.

• Nombre:
Permite clasificar los datos en función del estudio (código y denominación) en que se matriculan los estudiantes.

• Rama:
Permite clasificar los datos en función de la Rama de Conocimiento (Artes y Humanidades, Ciencias, Ciencias Sociales y Jurídicas, Ciencias de la Salud, Ingeniería y Arquitectura) a la que pertenece el estudio en que se matriculan los estudiantes.

• Tipo:
Permite clasificar los datos en función de la tipología recogida en el marco del Reglamento de Formación Permanente.

>Valores posibles: Máster Propio, Experto Universitario, Diploma de Especialización, Certificación de Extensi
Universitaria, Diploma de Extensión Universitaria.

• Órgano Gestión:
Permite clasificar los datos en función del centro encargado de la gestión administrativa de las enseñanzas.

• Órgano Proponente:
Permite clasificar los datos en función del centro responsable de la impartición de las enseñanzas.

## DIMENSION: Fecha de actualización ##

Notas generales:
- Indica la fecha de la última recarga de datos. Habitualmente es el domingo anterior a la consulta de datos.

