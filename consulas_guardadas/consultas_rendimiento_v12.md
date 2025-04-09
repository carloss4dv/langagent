# Consultas de Rendimiento

*Fecha de generación: 09/04/2025*

*Archivo fuente: consultas_rendimiento_v12.csv*

---

## rendimiento calificaciones estudio asignatura grados

**Cubo:** Rendimiento

### Medidas

* Créditos evaluados (columnas)

### Dimensiones

* Curso Académico (columnas) (selección del valor: curso finalizadoo más reciente)
* Calificación (columnas)
* Estudioo (filas)
* Localidad (filas)
* Asignatura (filas)
* Tipo de Estudioo (filtro) (selección valor Grado)

### Descripción

Indica, para un curso determinado, los créditos matriculados por los estudioant de grado que han sido calificados, clasificados por la calificación obtenida Estudio, localidad y asignatura.

---

## rendimiento calificaciones estudio asignatura masteres

**Cubo:** Rendimiento

### Medidas

* Créditos evaluados (columnas)

### Dimensiones

* Curso Académico (columnas) (selección del valor: curso finalizadoo más reciente)
* Calificación (columnas)
* Estudioo (filas)
* Localidad (filas)
* Asignatura (filas)
* Tipo de Estudioo (filtro) (selección valor Máster)

### Descripción

Indica, para un curso determinado, los créditos matriculados por los estudioant de máster que han sido calificados, clasificados por la calificación obtenida Estudio, localidad y asignatura.

---

## tasas rendimiento exito asignatura grupos elegirEstudio

**Cubo:** Rendimiento

### Medidas

* Tasasa de Éxito (columnas)
* Tasasa de Rendimiento (columnas)

### Dimensiones

* Estudioo(columnas) (selección del plan XXX)
* Curso Académico (columnas) (selección del valor: curso finalizadoo más reciente)
* Clase de Asignatura (filas)
* Asignatura (filas)
* Grupo Asignatura (filas)

### Descripción

Indica, para un curso determinado, la t de éxito y la tasa de rendimiento, de un Estudio en concreto, clasificado por cla de asignatura, asignatura y grupo de asignatura.

---

## tasas rendimiento exito estudio asignatura grados

**Cubo:** Rendimiento

### Medidas

* Tasasa de Éxito (columnas)
* Tasasa de Rendimiento (columnas)

### Dimensiones

* Curso Académico (columnas) (selección del valor: curso finalizadoo más reciente)
* Tipo de Estudioo (filas) (selección valor Grado)
* Estudioo (filas)
* Localidad (filas)
* Asignatura (filas)

### Descripción

Indica, para un curso determinado, la t de éxito y la tasa de rendimiento de los estudioos de grado, clasificado por estud localidad y asignatura.

---

## tasas rendimiento exito estudio asignatura masteres

**Cubo:** Rendimiento

### Medidas

* Tasasa de Éxito (columnas)
* Tasasa de Rendimiento (columnas)

### Dimensiones

* Curso Académico (columnas) (selección del valor: curso finalizadoo más reciente)
* Estudioo (filas)
* Localidad (filas)
* Asignatura (filas)
* Tipo de Estudioo (filtro) (selección valor Máster)

### Descripción

Indica, para un curso determinado, la t de éxito y la tasa de rendimiento de los estudioos de máster, clasificado por estu localidad y asignatura.

---

## tasas rendimiento exito tipoest estudio

**Cubo:** Rendimiento

### Medidas

* Tasasa de Éxito (columnas)
* Tasasa de Rendimiento (columnas)

### Dimensiones

* Curso Académico (columnas) (selección del valor: curso finalizadoo más reciente)
* Tipo de Estudioo (filas) (selección todos loss valores excepto Doctorado)
* Estudioo (filas)
* Localidad (filas)
* Rama de conocimiento (filtro) (selección de todos loss valores excepto No informado)

### Descripción

Indica, para un curso determinado, la t de éxito y la tasa de rendimiento, clasificado por tipo de estudioo, estudioo localidad.

---



*Documento generado automáticamente mediante script de conversión CSV a Markdown.*
