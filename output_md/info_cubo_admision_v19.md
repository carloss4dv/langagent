# Información del Cubo: Admisión

*Fecha de generación: 14/06/2025*

*Archivo fuente: info_cubo_admision_v19.csv*

---

# Medidas

Las medidas son los valores numéricos que se pueden calcular y analizar en este cubo.

## Solicitudes

Número de peticiones de acceso a un plan de estudios presentadas por los estudiantes que cumplen alguno de los requisitos de acceso a la Universidad que marca la legislación vigente. Notas: >Si se ejecuta una consulta sin incluir la convocatoria, se contará dos veces a las personas que presenten una solicitud de admisión en la convocatoria ordinaria y otra en la convocatoria extraordinaria. >Si se ejecuta una consulta sin incluir el plan de estudios, se contará el número de personas que presentan una solicitud de admisión. >Si se ejecuta una consulta incluyendo el plan de estudios, se contarán tantas solicitudes como opciones de preferencia incluyan los estudiantes en su solicitud de admisión.

---

## Nota Media

Nota media de admisión de los estudiantes que participan en el proceso de admisión. Notas: >Si en la consulta se introduce el plan de estudios, el indicador resultante será la nota media de admisión de los estudiantes que solicitan admisión en el plan. Si se quiere conocer la nota media de los admitidos, deberá seleccionarse el valor S en la dimensión "Admitido" y si se desea conocer la nota media de los matriculados de nuevo ingreso, deberá seleccionarse el valor S en la dimensión "Matric. Nuevo Ingreso". >Es recomendable introducir la dimensión "cupo adjudicación" para poder distinguir las notas medias de admisión del cupo general y de los cupos de reserva.

---

## Solicitantes

Número de personas que presentan una solicitud de admisión. Nota: >Si se ejecuta una consulta sin incluir la convocatoria, se contará a cada estudiante una sola vez, independientemente de si presenta una o dos solicitudes de admisión en un mismo curso académico.

---

# Dimensiones

Las dimensiones permiten desglosar y filtrar los datos según diferentes criterios.

## CURSO ACADÉMICO

Identifica los diferentes cursos académicos (por ejemplo 2021/22).

---

### Adjudicación - Convocatoria

Clasifica las solicitudes en función de si participan en la convocatoria ordinaria de admisión o en la extraordinaria.

---

### Adjudicación – Tipo de Acceso

Distingue entre solicitudes participantes en el proceso de preinscripción (adjudicación por distrito propio) y matrícula directa sin necesidad de realizar solicitud de admisión en aquellos planes de estudios con plazas vacantes que activen este procedimiento en la convocatoria extraordinaria (adjudicación extraordinaria).

---

### Adjudicación – Tipo de Procedimiento

Clasifica las solicitudes en función de si han sido o no objeto de reclamación tras el proceso de adjudicación. Valores posibles: >Normal: el solicitante no presenta reclamación a las listas de admisión y, por tanto, no hay cambios tras el resultado de adjudicación. >Recurso: el solicitante presenta reclamación a las listas de admisión, resolviéndose ésta a favor del solicitante y modificándose su posición en las listas de admisión.

---

### Adjudicación – Admitido (S/N)

Identifica si la solicitud han sido admitida (S) o no (N) en un estudio y curso académico determinados. Notas: >Un estudiante admitido es aquél al que se le adjudica una plaza de nuevo ingreso, independientemente de si después formaliza o no la matrícula. >Esta variable incluye los admitidos en el momento de la adjudicación y los admitidos posteriores, en virtud de los llamamientos o de un recurso resuelto a su favor.

---

### Adjudicación – Estado

Distingue si las solicitudes han sido admitidas (en el proceso de adjudicación), admitidas posteriores (en virtud de un llamamiento o de un recurso resuelto a favor del solicitante), se encuentran en lista de espera, no han sido consideradas por tratarse de una preferencia posterior a la de un plan de estudios en que ha sido admitido el solicitante, o han sido desactivadas por llamamiento (si ha sido llamado en cualquier estudio y en cualquier cupo, se desactiva el estudio que tenga por debajo de sus preferencias).

---

### Adjudicación – Matriculado de Nuevo Ingreso (S/N)

Indica si el solicitante ha formalizado su matrícula (S) o no (N) en el estudio y curso académico en que ha sido admitido. Notas: >Se identifica con la persona que se matricula en un plan de estudios, consumiendo alguna de las plazas ofertadas para ese año y plan. >No se consideran matriculados de nuevo ingreso los que acceden a un estudio por el procedimiento de cambio de estudios, traslado de expediente o de adaptación al grado.

---

### Solicitante – País de Nacionalidad

Permite clasificar los datos en función del país de nacionalidad legal de los solicitantes.

---

### Solicitante – Población de nacimiento

Identifica el país, la comunidad autónoma, la provincia o la población de nacimiento informada por el solicitante.

---

### Solicitante – Rango de Edad

Permite agrupar los rangos de edad de los solicitantes en función de su edad a 31 de diciembre del curso académico en que solicitan admisión. 

**Valores posibles:** 18 años o menos, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30 a 34, 35 a 39, 40 a 44, 45 a 49, 50 a 54, 55 a 59, 60 a 64, 65 años o más.

---

### Solicitante – Residencia Familiar

Identifica el país, la comunidad autónoma, la provincia o la población de residencia familiar informada por el solicitante.

---

### Solicitante – Sexo

Permite agrupar los solicitantes en función de su sexo.

---

### Solicitante – Universidad de Origen

Clasifica a los solicitantes en función de la universidad de la que proceden (en la que han cursado estudios previos o en la que han superado las Pruebas de Acceso correspondientes).

---

### Solicitud – Centro

Permite clasificar las solicitudes en función del centro en que se imparte la titulación solicitada.

---

### Solicitud – Centro Campus

Permite clasificar las solicitudes en función del campus en que se ubica el centro en que se imparte la titulación solicitada.

---

### Solicitud – Centro Localidad

Permite clasificar las solicitudes en función de la localidad en que se ubica el centro en que se imparte la titulación solicitada.

---

### Solicitud – Centro Tipo

Permite clasificar las solicitudes en función del tipo de centro (facultad, escuela universitaria, centro adscrito, etc.) en que se imparte la titulación solicitada.

---

### Solicitud – Cupo de Adjudicación

Clasifica las solicitudes en función de si participan del cupo general (EVAU-PAU, CFGS, Credencial UNED) o de los de reserva (titulados universitarios o equivalentes, mayores de 25 años, mayores de 45 años, mayores de 40 años con experiencia profesional, discapacitados, deportistas de alto nivel o de alto rendimiento).

---

### Solicitud – Estudio Previo

Identifica la clase de estudio cursado anteriormente por los estudiantes, que les da acceso a la Universidad, de acuerdo con los requisitos establecidos por la legislación vigente. 

**Valores posibles:** Pruebas de Acceso, COU sin PAU, FP, Titulados Universitarios, Mayores de 25, Mayores de 40, Mayores de 45. >Los estudiantes procedentes de Bachillerato se incluyen en “Pruebas de Acceso”. Los estudiantes procedentes de Ciclos Formativos de Grado Superior se incluyen en “FP”, aunque se hayan presentado a la fase específica de la EvAU. >Nota: el valor “No informado” se aplica a estudiantes procedentes de adaptaciones por extinción de planes de estudios o que no han accedido a la titulación por procedimientos de preinscripción.

---

### Solicitud – Orden de Preferencia

Clasifica las solicitudes en función del orden de preferencia consignada en la solicitud de admisión para cada una de las titulaciones solicitadas. 

**Valores posibles:** 1, 2, 3, 4, 5, 6, 7, 8, 9, 10.

---

### Solicitud – Rango de calificación

Clasifica las solicitudes en función del rango de la nota de admisión válida para cada una de las titulaciones solicitadas. 

**Valores posibles:** entre 5 y 6, entre 6 y 7, entre 7 y 8, entre 8 y 9, entre 9 y 10, entre 10 y 11, entre 11 y 12, entre 12 y 13, entre 13 y 14.

---

### Solicitud – Titulación Plan

Permite identificar el plan de estudios solicitado en el proceso de admisión.

---

### Solicitud – Titulación Rama

Permite identificar la rama de conocimiento asignada a la titulación solicitada en el proceso de admisión.

---

### Solicitud – Titulación Tipo

Permite identificar el tipo de titulación solicitada: grado, licenciatura o equivalente, diplomatura o equivalente.

---

### Solicitud – Titulación Estudio

Permite identificar el estudio solicitado en el proceso de admisión.

---

## Fecha de actualización

Indica la fecha de la última recarga de datos. Habitualmente es el domingo anterior a la consulta de datos.

---

## Resumen

- **Total de medidas:** 3
- **Total de dimensiones:** 26
- **Total de elementos:** 29


---

*Documento generado automáticamente mediante script de conversión de cubos CSV a Markdown.*
