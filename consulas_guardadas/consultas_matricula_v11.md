# Consultas de Matrícula

*Fecha de generación: 09/04/2025*

*Archivo fuente: consultas_matricula_v11.csv*

---

## creditos tipoestudio plan numvecesmatriculada

### Medidas

* Créditos
Matriculados
(columnas)

### Dimensiones

* Curso Académico (columnas) (selección
del valor: curso más reciente)
* Número de Veces Matriculada
(columnas)
* Tipo Estudio (filas) (selección valores:
Grado, Máster)
* Estudio (filas)
* Localidad centro (filas)

### Descripción

Indica, para un curso académico, los créditos matriculados por los estudiantes, no anulados, hayan sido calificados o no, clasificados por estudio de grado o máster, según el número de veces que el estudiante ha matriculado una misma asignatura. >Nota: no se incluyen los créditos matriculados por los estudiantes de movilidad de entrada.

---

## matriculados adaptaciongrado centro estudio locali

### Medidas

* Alumnos
Matriculados
(columnas)

### Dimensiones

* Curso de adaptación al Grado
(columnas) (selección valor S)
* Curso Académico (columnas) (selección
valores de 2010/11 a 2018/19)
* Centro (filas)
* Estudio (filas)

### Descripción

Indica la evolución de los alumnos matriculados el curso de adaptación al grado, clasificados por centro y por Estudio.

---

## matriculados centro tipoestudio plan sexo

### Medidas

* Alumnos
Matriculados
(columnas)

### Dimensiones

* Curso Académico (columnas) (selección
del valor: curso más reciente)
* Sexo (columnas)
* Centro (filas)
* Tipo Estudio (filas)
* Estudio (filas)

### Descripción

Indica, para un curso académico, los alumnos matriculados, clasificados por sexo, centro, tipo estudio (grado, máster, doctorado, movilidad de entrada) y estudio.

---

## matriculados centro tipoestudio residenciafamiliar sexo

### Medidas

* Alumnos
Matriculados
(columnas)

### Dimensiones

* Curso Académico (columnas) (selección
del valor: curso más reciente)
* Sexo (columnas)
* Centro (filas)
* Tipo Estudio (filas)
* Comunidad Autónoma de residencia
familiar (filas)

### Descripción

Indica, para un curso académico, los alumnos matriculados, clasificados por sexo, centro, tipo estudio (grado, máster, doctorado, movilidad de entrada) y Comunidad Autónoma de residencia familiar.

---

## matriculados plan cursomasalto

### Medidas

* Alumnos
Matriculados
(columnas)

### Dimensiones

* Curso Académico (columnas) (selección
del valor: curso más reciente)
* Curso más alto matriculado (columnas)
* Tipo Estudio (filas)
* Estudio (filas)
* Localidad centro (filas)

### Descripción

Indica, para un curso académico, los alumnos matriculados, clasificados por tipo de estudio y estudio, según el máximo curso en que el estudiante tiene asignaturas matriculadas. >Nota: para los estudiantes de movilidad de entrada y doctorado se muestra Curso 0.

---

## matriculados regulares movilidad evolucion

### Medidas

* Alumnos
Matriculados
(columnas)

### Dimensiones

* Curso Académico (filas)
* Programa de Movilidad de entrada
(S/N) (columnas)

### Descripción

Indica la evolución de los alumnos matriculados ( todos los posibles tipos de estudio), distinguiend los estudiantes regulares (N) de los que procede de un programa de intercambio nacional o internacional de entrada (S). >Nota: no se incluyen en cursos anteriores al 201 13 los estudiantes matriculados en programas de doctorado regulados por los RD 185/1985 y 778/1998 (por no estar incluidos en SIGMA)

---

## matriculados regulares tipoEstudio nacionalidad

### Medidas

* Alumnos
Matriculados
(columnas)

### Dimensiones

* Programa de Movilidad de entrada
(S/N) (columnas) (selección valor N)
* Curso Académico (columnas) (selección
del valor: curso más reciente)
* Tipo Estudio (columnas)
* País Nacionalidad (filas)

### Descripción

Indica, para un curso académico, los alumnos matriculados regulares (es decir, los que no form parte de un programa de intercambio nacional o internacional de entrada), clasificados por tipo de estudio (Grado, Máster, Doctorado) y por país de nacionalidad.

---

## matriculados tipoestudio rama

### Medidas

* Alumnos
Matriculados
(columnas)

### Dimensiones

* Curso Académico (columnas) (selección
del valor: curso más reciente)
* Rama de conocimiento (columnas)
* Tipo de Estudio (filas)

### Descripción

Indica, para un curso académico, la distribución de estudiantes matriculados, según tipo de estudio rama de conocimiento a la que pertenece el estudio que cursan. >Nota: para los estudiantes de movilidad de entrada se muestra rama “No informada” (son asignados a un plan de estudios específico de movilidad).

---

## movilidadIN centro sexo

### Medidas

* Alumnos
Matriculados
(columnas)

### Dimensiones

* Programa de Movilidad de entrada
(S/N) (columnas) (selección valor S)
* Curso Académico (columnas) (selección
del valor: curso más reciente)
* Sexo (columnas)
* Centro (filas)

### Descripción

Indica, para un curso académico, los alumnos matriculados en un programa de intercambio nacional o internacional de entrada, clasificados por sexo y por centro administrativo de acogida.

---

## movilidadIN nacionalidad

### Medidas

* Alumnos
Matriculados
(columnas)

### Dimensiones

* Programa de Movilidad de entrada
(S/N) (columnas) (selección valor S)
* Curso Académico (columnas) (selección
del valor: curso más reciente)
* País Nacionalidad

### Descripción

Indica, para un curso académico, los estudiantes matriculados en un programa de intercambio nacional o internacional de entrada, clasificados por país de nacionalidad.

---

## movilidadOUT centro tipoestudio plan sexo

### Medidas

* Alumnos en
programa de
movilidad de
salida (columnas)

### Dimensiones

* Curso Académico (columnas) (selección
del valor: curso más reciente)
* Sexo (columnas)
* Centro (filas)
* Tipo de Estudio (filas)
* Estudio (filas)
* Localidad Centro (filas)

### Descripción

Indica, para un curso académico, los estudiantes matriculados que, en virtud de un Programa de Intercambio nacional o internacional, realizan un estancia temporal en otra universidad que conlle algún tipo de reconocimiento académico, según sexo, centro UZ, tipo de estudio, estudio y localidad.

---

## Ratiocreditosalumnos matriculados tipoestudio estudio locali

### Medidas

* Ratio
Creditos/Alumnos
Matriculados
(columnas)

### Dimensiones

* Curso Académico (columnas) (selección
del valor: curso más reciente)
* Tipo de Estudio (filas) (selección del
valor: Grado, Máster)
* Estudio (filas)
* Localidad Centro (filas)

### Descripción

Indica, para un curso determinado, el cociente entre las medidas "créditos matriculados" y "alumnos matriculados" (media de créditos matriculados por los estudiantes), por estudio de grado o máster y localidad.

---



*Documento generado automáticamente mediante script de conversión CSV a Markdown.*
