# Información del Cubo: Matrícula

*Fecha de generación: 14/06/2025*

*Archivo fuente: info_cubo_matricula_v24.csv*

---

# Medidas

Las medidas son los valores numéricos que se pueden calcular y analizar en este cubo.

## Alumnos Matriculados

Número de estudiantes que tienen al menos una asignatura matriculada de un plan de estudios oficial en curso académico, sin tener en cuenta si las asignaturas han sido o no calificadas. Según la dimensión que seleccione, cabe distinguir entre estudiantes matriculados por plan y estudiantes matriculados por asignatura • Matriculados en un plan de estudios: estudiantes cuyo expediente está asociado a un plan de estudios. >Se incluyen los estudiantes del plan que en virtud de programas de intercambio van a estudiar a ot universidades españolas o extranjeras. >No se incluyen los estudiantes que sólo formalizan matrícula con convalidaciones o adaptaciones reconocimiento de créditos. • Matriculados en una asignatura: estudiantes que, en el curso académico que se seleccione, vayan a obten una calificación en las actas de esa asignatura. >Se incluyen los estudiantes del plan de la asignatura, estudiantes de otros planes, estudiantes que en virt de programas de intercambio vienen a la UZ, estudiantes en programas de movilidad de salida y estudian visitantes. Notas: 1. Se contabilizan estudiantes matriculados por plan de estudios. Por tanto, en el total de matriculados cuentan dos veces a los estudiantes matriculados en dos estudios que no formen parte de una programaci conjunta de estudios oficiales de grado o de máster. 2. Los estudiantes que en virtud de programas de intercambio vienen a la UZ a cursar asignaturas de un pl concreto se incluyen en los planes 107 (Movilidad para 1º y 2º ciclo y grado) ó 266 (Movilidad para máste Si no se desea incluir a este tipo de estudiantes, se debe incluir en la consulta la dimensión “Programa Movilidad de Entrada”, filtrándose por el valor ‘N’ (no). 3. No se contabilizan los estudiantes que anulan la matrícula. 4. Si se quiere obtener el número de estudiantes matriculados del plan en asignaturas de ese plan, deb seleccionarse en la consulta las dimensiones "Plan de Estudio" y "Asignatura", seleccionando en "Plan estudios" el que corresponda.

---

## Créditos Matriculados

Créditos matriculados por los estudiantes, no anulados, hayan sido calificados o no. >Nota: no se incluyen créditos de asignaturas que se reconocen, adaptan o convalidan.

---

## Alumnos en programa de movilidad de Salida

Estudiantes matriculados que, en virtud de un Programa de Intercambio nacional o internacional, realizan u estancia temporal en otra universidad que conlleva algún tipo de reconocimiento académico.

---

## Alumnos de Nuevo Ingreso

Número de estudiantes matriculados en un plan de estudios que consumen alguna de las plazas ofertadas p un año y plan (preinscripción). Se incluyen expedientes SIGMA que han sido abiertos en el curso académico q se seleccione y tienen algún registro en cualquiera de los procedimientos de preinscripción. >Nota: no se consideran matriculados de nuevo ingreso los que acceden a un estudio por el procedimien distinto al ordinario de preinscripción: cambio de estudios, traslado de expediente, adaptación al grado, o que anulan la matrícula.

---

## Ratio Créditos/Alumnos Matriculados

Cociente entre las medidas "créditos matriculados" y "alumnos matriculados". Así se obtiene la media de crédit matriculados por los estudiantes.

---

# Dimensiones

Las dimensiones permiten desglosar y filtrar los datos según diferentes criterios.

## CURSO ACADÉMICO

Identifica los diferentes cursos académicos (por ejemplo 2023/24).

---

### Acceso – Estudio previo

Identifica la clase de estudio cursado anteriormente por los estudiantes, que les da acceso a la Universidad, acuerdo con los requisitos establecidos por la legislación vigente. 

**Valores posibles:** Pruebas de Acceso, COU sin PAU, FP, Titulados Universitarios, Mayores de 25, Mayores de Mayores de 45. >Los estudiantes procedentes de Bachillerato se incluyen en “Pruebas de Acceso”. Los estudiantes proceden de Ciclos Formativos de Grado Superior se incluyen en “Formación Profesional”, aunque se hayan presenta a la fase específica de la EvAU. >Nota: el valor “No informado” se aplica a estudiantes procedentes de adaptaciones por extinción de planes estudios o que no han accedido a la titulación por procedimientos de preinscripción.

---

### Acceso – Nuevo Ingreso (S/N)

Indica si los estudiantes son de nuevo ingreso (S) o no (N) en el curso académico que se seleccione. Ver definici de la medida "Alumnos de Nuevo Ingreso".

---

### Alumno – País Nacionalidad

Permite clasificar los datos en función del país de nacionalidad legal de los estudiantes.

---

### Alumno – Rango de Edad

Permite agrupar los rangos de edad de los estudiantes en función de su edad a fecha 31 de diciembre del cur académico en que están matriculados. 

**Valores posibles:** 18 años o menos, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30 a 34, 35 a 39, 40 a 44, 45 a 50 a 54, 55 a 59, 60 a 64, 65 años o más.

---

### Alumno – Residencia Familiar

Identifica el país, la comunidad autónoma, la provincia o la población de residencia familiar indicada por alumno en el curso académico en que se matricula.

---

### Alumno - Sexo

Permite agrupar los estudiantes en función de su sexo.

---

## Asignatura

Permite clasificar los datos en función de la asignatura (código y denominación) en que se matriculan estudiantes.

---

### Asignatura - Clase

Permite clasificar los datos en función de la clase de asignatura (formación básica, obligatoria, optativa, lib elección, troncal, trabajo fin de grado, trabajo fin de máster, prácticas externas, complementos de formaci actividades académicas complementarias, investigación –en el caso de los doctorados regulados por el 99/2011), tal como viene identificada en el plan de estudios.

---

### Asignatura - Grupo

Permite diferenciar los diferentes grupos de matrícula existentes en cada asignatura. >Nota: se recomienda utilizar esta dimensión junto con la de Asignatura.

---

## Centro

Permite clasificar los datos en función del centro (código y denominación) de matrícula de los estudiantes.

---

### Centro – Campus

Permite clasificar los datos en función del campus en el que se ubica el centro de matrícula de los estudiantes

---

### Centro – Localidad

Permite clasificar los datos en función de la localidad a la que pertenece el centro de matrícula de los estudiant

---

### Centro - Tipo

Permite clasificar los datos en función del tipo de centro (facultad, escuela universitaria, centro adscrito, etc.) que se matriculan los estudiantes.

---

### Matrícula – Curso más alto matriculado

Identifica el máximo curso en el que el alumno tiene asignaturas matriculadas en el curso académico que seleccione. >Nota: el valor 0 se corresponde con asignaturas de Programas de Doctorado, Proyectos Fin de Carre asignaturas no asociadas a curso, sino a ciclo, y asignaturas matriculadas por estudiantes de Programas Intercambio que vienen a la UZ.

---

### Matrícula – Modalidad

Permite diferenciar los datos en función de la dedicación que el estudiante tenga en la titulación en la que matricula. Esta condición se regula en el Reglamento de permanencia en títulos oficiales adaptados al EEES. 

**Valores posibles:** tiempo completo, tiempo parcial, otra dedicación (finalizando estudios, con menos del 1 de los créditos del plan por superar). >En titulaciones anteriores al EEES todos los estudiantes se matriculan a tiempo completo. >Existe un número mínimo de créditos en que deberán matricularse los estudiantes, en función de ca modalidad.

---

### Matrícula – Número de veces

Determina el número de veces que el alumno ha matriculado una misma asignatura en el curso académico q se seleccione (1 vez, 2 veces, 3 veces, 4 ó más veces). >Nota: es una dimensión orientada a la asignatura, por lo que se recomienda no combinar esta variable con plan de estudios si queremos obtener el número de estudiantes matriculados, dado que éstos pueden matricu asignaturas con distinto número de veces en un mismo plan.

---

### Matrícula – Programa de Movilidad de Entrada (S/N)

Permite filtrar a los estudiantes que proceden de un programa de intercambio nacional o internacional entrada (S) o no (N) en el curso académico que se seleccione.

---

### Matrícula – Traslado por Continuación de Estudio

Indica si los estudiantes accedieron al centro en el que están matriculados a través de un traslado (S) o no ( para continuar los mismos estudios iniciados en el centro de origen.

---

### Titulación – Grado Experimentalidad

Permite clasificar los datos en función del grado de experimentalidad en que se encuentren las enseñan conducentes a la obtención de títulos oficiales de grado y máster. >Nota: se ofrecen datos de experimentalidad desde el curso 2015/16. Desde el curso 2017/18 los estudios grado tienen 4 posibles grados de experimentalidad.

---

### Titulación – Interuniversitario (S/N)

Permite clasificar los estudios o planes de estudio en función de si se imparten de manera conjunta entre var universidades (S) o no (N).

---

### Titulación – Interuniversitario coordina Unizar (S/N)

Permite clasificar los estudios o planes de estudio en función de si la Universidad de Zaragoza es la universid coordinadora del estudio universitario (S) o no (N).

---

### Titulación – Máster habilitante (S/N)

Permite clasificar los estudios o planes de estudio de Máster en función de si son habilitantes (S) o no (N), acuerdo con lo establecido en el Decreto del Gobierno de Aragón, por el que se fijan los precios públicos por prestación de servicios académicos universitarios, para el curso que corresponda. >Nota: para tipos de estudio distintos de Máster se muestra “-“.

---

### Titulación – Múltiple titulación (S/N)

Permite clasificar los datos en función de si el estudio o plan de estudios se articula a través de un Progra Oficial de Estudios Oficiales de Grado o Máster (S) o no (N).

---

### Titulación – Plan de Estudios

Permite clasificar los datos en función del plan de estudios (código y denominación) en que se matriculan estudiantes.

---

### Titulación – Rama de Conocimiento

Permite clasificar los datos en función de la Rama de Conocimiento (Artes y Humanidades, Ciencias, Cienc Sociales y Jurídicas, Ciencias de la Salud, Ingeniería y Arquitectura) a la que pertenece el estudio en que matriculan los estudiantes.

---

### Titulación – Tipo de Estudio

Permite identificar el tipo de estudio del plan en que se matriculan los estudiantes: grado, máster, doctora movilidad de entrada. Con anterioridad al curso 2016/17 se muestran también licenciatura o equivalen diplomatura o equivalente.

---

### Titulación - Estudio

Permite clasificar los datos en función del estudio (código y denominación) en que se matriculan los estudiant Observaciones: >No es lo mismo “estudio” que “plan de estudios”. >Bajo un mismo estudio pueden existir varios planes, bien porque se imparten en distintas localidades (ejempl ADE, Enfermería, Magisterio, Medicina, etc.) o bien porque se ha modificado el plan de estudios, pero el estu sigue siendo el mismo (ejemplos: másteres regulados por el RD 56/2005 que se renuevan en virtud del 1393/2007).

---

## Fecha de actualización

Indica la fecha de la última recarga de datos. Habitualmente es el domingo anterior a la fecha de consulta datos.

---

## Resumen

- **Total de medidas:** 5
- **Total de dimensiones:** 29
- **Total de elementos:** 34


---

*Documento generado automáticamente mediante script de conversión de cubos CSV a Markdown.*
