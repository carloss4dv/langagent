# Consultas de Admisión

*Fecha de generación: 09/04/2025*

*Archivo fuente: consultas_admision_v11.csv*

---

## indice ocupacion plazas grado

**Cubo:** Oferta de plazas

### Medidas

* Plazas ofertadas
(columnas)
* Plazas matriculadas
(columnas)
* Índice de ocupación
(columnas)

### Dimensiones

* Curso Académico (columnas)
(selección del valor: curso más
reciente)
* Tipo Estudio (filas) (selección
valor: Grado)
* Estudio (filas)
* Localidad (filas)

### Descripción

Indica las plazas matriculadas, plazas ofertadas el cociente entre ambas (índice de ocupación) para cada uno de los estudios de grado de la UZ para un curso académico, por localidad.

---

## indice ocupacion plazas master

**Cubo:** Oferta de plazas

### Medidas

* Plazas ofertadas
(columnas)
* Plazas matriculadas
(columnas)
* Índice de ocupación
(columnas)

### Dimensiones

* Curso Académico (columnas)
(selección del valor: curso más
reciente)
* Tipo Estudio (filas) (selección
valor: Máster)
* Estudio (filas)

### Descripción

Indica las plazas matriculadas, plazas ofertadas el cociente entre ambas (índice de ocupación) para cada uno de los estudios de máster de la U para un curso académico.

---

## notas corte adjudicacion julio

**Cubo:** Oferta de plazas

### Medidas

* Nota corte
adjudicación 1 (columnas)

### Dimensiones

* Cupo Adjudicación (columnas)
* Curso Académico (filas)
(selección del valor: curso más
reciente)
* Tipo Estudio (filas)
* Estudio (filas)
* Localidad (filas)

### Descripción

Indica la nota más baja de admisión de entre la totalidad de admitidos en un estudio de grado, calculada en el momento de la adjudicación de plazas de la convocatoria de julio, para todos los cupos de adjudicación y para un curso académi segmentada por Estudio y localidad.

---

## notas corte adjudicación julio evolución cupogeneral

**Cubo:** Oferta de plazas

### Medidas

* Nota corte
adjudicación 1 (columnas)

### Dimensiones

* Cupo Adjudicación (columnas)
(selección del valor: General)
* Curso Académico (columnas)
* Estudio (filas)
* Localidad (filas)
* Tipo Estudio (filtro) (selección del
valor: Grado)

### Descripción

Indica la evolución desde el curso 2010/11 de la nota más baja de admisión de entre la totalidad de admitidos en un estudio de grado, calculada el momento de la adjudicación de plazas de la convocatoria de julio, para el Cupo General (PAU/EVAU+FP), segmentada por Estudio y localidad.

---

## notas corte adjudicacion septiembre

**Cubo:** Oferta de plazas

### Medidas

* Nota corte
adjudicación 2 (columnas)

### Dimensiones

* Cupo Adjudicación (columnas)
* Curso Académico (filas)
(selección del valor: curso más
reciente)
* Tipo Estudio (filas)
* Estudio (filas)
* Localidad (filas)
* Prelación convo Nota de Corte

### Descripción

Indica la nota más baja de admisión de entre la totalidad de admitidos en un estudio de grado, calculada en el momento de la adjudicación de plazas de la convocatoria de septiembre, para todos los cupos de adjudicación y para un curso académico, segmentada por Estudio y localidad >Nota: desde 2017/18 no existe prelación en la nota de corte, pero se incluye esta dimensión po si se quiere hacer una consulta sobre años anteriores.

---

## notas corte definitivas cupo general

**Cubo:** Oferta de plazas

### Medidas

* Nota corte definitiva 1
(columnas)
* Nota corte definitiva 2
(columnas)

### Dimensiones

* Cupo Adjudicación (columnas)
(selección del valor: General
(EvAU-PAU/ CFGS/ Cred. UNED/
Bach. sin EvAU))
* Curso Académico (filas)
(selección del valor: curso más
reciente)
* Tipo Estudio (filas)
* Estudio (filas)
* Localidad (filas)
* Prelación convo Nota de Corte

### Descripción

Indica las notas más bajas de admisión de entre totalidad de admitidos en un estudio en las convocatorias de julio (1) y septiembre (2) calculadas a fecha 31 de diciembre del curso académico que se seleccione, para el cupo general, para cada estudio y localidad. Incluye en efecto que sobre las listas de admisión tienen lo llamamientos y la resolución de recursos. >Nota: desde 2017/18 no existe prelación en la nota de corte, pero se incluye esta dimensión po si se quiere hacer una consulta sobre años anteriores.

---

## notas corte definitivas julio evolución cupogeneral

**Cubo:** Oferta de plazas

### Medidas

* Nota corte
definitiva 1 (columnas)

### Dimensiones

* Cupo Adjudicación (columnas)
(selección del valor: General)
* Curso Académico (columnas)
* Estudio (filas)
* Localidad (filas)
* Tipo Estudio (filtro) (selección del
valor: Grado)

### Descripción

Indica la evolución desde el curso 2010/11 de la nota más baja de admisión de entre la totalidad de admitidos en un estudio de grado, en la convocatoria de julio, calculada a 31 de diciembre, para el Cupo General (PAU/EVAU+FP para cada Estudio y localidad. Incluye el efecto que sobre las listas de admisión tienen los llamamientos y la resolución de recursos.

---

## nuevo ingreso cupo adjudicacion

**Cubo:** Admisión

### Medidas

* Solicitantes (columnas)

### Dimensiones

* Curso Académico (columnas)
(selección del valor: curso más
reciente)
* Matric. Nuevo Ingreso (S/N)
(columnas) (selección del valor: S)
* Cupo Adjudicación (columnas)
* Estudio (filas)
* Localidad (filas)

### Descripción

Indica el número de personas que presentan un solicitud de admisión a un estudio de grado, y q finalmente se matriculan en ese estudio, para cada cupo de adjudicación, cada Estudio y localidad.

---

## nuevo ingreso cupo adjudicacion nota admision

**Cubo:** Admisión

### Medidas

* Solicitantes (columnas)

### Dimensiones

* Curso Académico (columnas)
(selección del valor: curso más
reciente)
* Matric. Nuevo Ingreso (S/N)
(columnas) (selección del valor: S)
* Cupo Adjudicación (columnas)
* Estudio (filas)
* Localidad (filas)
* Rango de calificación

### Descripción

Indica el número de personas que presentan un solicitud de admisión a un estudio de grado, y q finalmente se matriculan en ese estudio, para cada cupo de adjudicación, cada estudio y localidad, en función del rango de la nota de admisión válida para cada una de las titulaciones solicitadas

---

## nuevo ingreso nota media admision

**Cubo:** Admisión

### Medidas

* Nota Media (columnas)

### Dimensiones

* Curso Académico (columnas)
(selección del valor: curso más
reciente)
* Matric. Nuevo Ingreso (S/N)
(columnas) (selección del valor: S)
* Cupo Adjudicación (columnas)
* Estudio (filas)
* Localidad (filas)

### Descripción

Indica la nota media de admisión de los estudiantes que participan en el proceso de admisión a estudios de grado y que finalmente matriculan en ese estudio para cada cupo de adjudicación, cada estudio y localidad.

---

## nuevo ingreso orden preferencia

**Cubo:** Admisión

### Medidas

* Solicitantes (columnas)

### Dimensiones

* Curso Académico (columnas)
(selección del valor: curso más
reciente)
* Matric. Nuevo Ingreso (S/N)
(columnas) (selección del valor: S)
* Orden Preferencia (columnas)
* Estudio (filas)
* Localidad (filas)

### Descripción

Indica el número de personas que presentan un solicitud de admisión a un estudio de grado, y q finalmente se matriculan en ese estudio, para cada estudio y localidad, en función del orden de preferencia consignada en la solicitud de admis para cada una de las titulaciones solicitadas.

---

## solicitudes admision orden preferencia

**Cubo:** Admisión

### Medidas

* Solicitudes (columnas)

### Dimensiones

* Curso Académico (columnas)
(selección del valor: curso más
reciente)
* Orden Preferencia (columnas)
* Estudio (filas)
* Localidad (filas)
* Tipo de Acceso (filtro: selección
de todos loss valores posibles
excepto adjudicación
extraordinaria)

### Descripción

Indica el número de peticiones de acceso a cad estudio de grado presentadas por los estudiant que cumplen alguno de los requisitos de acceso la Universidad que marca la legislación vigente, función del orden de preferencia consignada en solicitud de admisión para cada una de las titulaciones solicitadas.

---

## solicitudes admision resultado

**Cubo:** Admisión

### Medidas

* Solicitudes (columnas)

### Dimensiones

* Curso Académico (columnas)
(selección del valor: curso más
reciente)
* Estado adjudicación (columnas)
* Estudio (filas)
* Localidad (filas)

### Descripción

Indica el número de peticiones de acceso a cad estudio de grado presentadas por los estudiant que cumplen alguno de los requisitos de acceso la Universidad que marca la legislación vigente, función del estado de la adjudicación.

---



*Documento generado automáticamente mediante script de conversión CSV a Markdown.*
