=== MEDIDAS ===

** Nº proyectos vigentes **
Número de proyectos de I+D+i activos en un año determinado (con algún movimiento contable en el año solicitado).

** Nº proyectos nuevos **
Número de proyectos nuevos de I+D+i en un año determinado.

** Importe concedido **
Es el importe que consta en la concesión del proyecto/contrato, siempre relacionado con la dimensión Año.

** Ingresos Totales **
Corresponde a los ingresos en proyectos/contratos, realizados en un ejercicio contable.

** Ingresos IVA **
Ingresos por IVA en un ejercicio contable.

** Ingresos Overhead **
Ingresos por costes indirectos en un ejercicio contable.

** Ingresos Proyecto **
Ingresos netos que se contabilizan en los proyectos/contratos.

** Costes totales del gasto **
Gastos externos y transferencias internas cargados en proyectos/contratos correspondientes a un ejercicio contable. La cifra total incluye el importe base de las facturas y el IVA.

** Costes de IVA **
Gastos de IVA en proyectos/contratos correspondientes a un ejercicio contable.

** Costes al proyecto **
Importe de los gastos totales que se imputa a los proyectos/contratos.

=== DIMENSIONES ===

## DIMENSION: AÑO ##

Notas generales:
- Permite clasificar los proyectos/contratos en función del año natural.

## DIMENSION: Costes ##

Atributos:
• Concepto:
Permite identificar el concepto contable de los gastos realizados en un proyecto de I+D+i.

>Ejemplos de valores posibles: Bienes y servicios, Gastos generales, Gastos de funcionamiento, Dietas y viajes,
Material Bibliográfico, Fungible, Inventariable, Equipo de Laboratorio, Estancias.

## DIMENSION: Fecha de actualización ##

Notas generales:
- Fecha de la última recarga de datos.

## DIMENSION: Investigador ##

Atributos:
• Centro:
Permite clasificar los datos en función del centro al que pertenece el investigador principal de cada proyecto. Esta dimensión se desagrega en dos atributos: Localidad Centro y Centro.

• Departamento:
Permite clasificar los datos en función del departamento al que está adscrito el investigador principal de cada proyecto.

• Grupo de Investigación:
Permite clasificar los datos en función del grupo de investigación al que pertenece el investigador principal de cada proyecto.

• Instituto de Investigación:
Permite clasificar los datos en función del instituto universitario de investigación al que pertenece el investigador principal de cada proyecto.

• Macroárea:
Permite clasificar los datos en función de la macroárea a la que pertenece el investigador principal de cada proyecto.

>Valores posibles: Artes y Humanidades, Ciencias, Ciencias Sociales y Jurídicas, Ciencias de la Salud, Ingeniería y
Arquitectura.

• Otros centros de investigación:
Permite clasificar los datos en función de si investigadores pertenecen o no a estructuras de investigación distintas de los institutos universitarios de investigación.

>Ejemplo: IIS ‐ Instituto de Investigación Sanitaria de Aragón.

• Área:
Permite clasificar los datos en función del área de conocimiento a la que está adscrito el investigador principal de cada proyecto.

## DIMENSION: Proyecto ##

Atributos:
• Agrupación:
Clasifica los proyectos/contratos según los valores siguientes:

>Valores posibles: Proy. de Investigación Básica (no Europeos), Proy. de Investigación Básica Europeos, Proy.
colaborativos con Empresa, Contratos y Convenios.

• Categoría baremo:
Clasifica los proyectos/contratos según los valores: Proyectos I+D en convocatorias no competitivas, Asesorías I+D en convocatorias no competitivas, Servicios en convocatorias no competitivas, Proyectos no baremables, Proyectos en convocatorias competitivas.

• Oficina gestora:
Permite obtener los datos clasificados por las oficinas gestoras. Esta dimensión se desagrega en dos atributos: Oficina Gestora (Siglas)

>Valores posibles: OPE, OTRI; SGI,EXT,TODAS
Oficina Gestora

>Valores posibles: Oficina de Proyectos Europeos, Oficina de Transferencia de Resultados de Investigación,
Servicio de Gestión de la Investigación, Proyectos externos.

• Sector industrial:
Pendiente añadir listado de valores

• Tipo de oportunidad:
Clasificación de los proyectos/contratos según los siguientes valores:

>Valores posibles: Contrato, Convenio, Convocatoria, Subcontratación convocatoria.

• Tipo de proyecto:
Clasifica los proyectos/contratos según los siguientes valores: Grupos, Proyectos I+D+I, Proyectos colaborativos, Movilidades, Asesorías, Cursos y seminarios, Servicios técnicos, Recursos Humanos, Infraestructuras, Royalties/Licencias, Mecenazgo/Donaciones, CIT, Proyectos Colaborativos, Otros.

• Ámbito territorial:
Permite identificar el ámbito de un proyecto.

