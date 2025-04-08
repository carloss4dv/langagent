=== MEDIDAS ===

** Número de PDI **
Número de efectivos de PDI que constan en las bases de datos de personal con contrato activo a la fecha de consulta. Observaciones:

>IMPORTANTE: se debe utilizar la dimensión TIEMPO (año o mes) para filtrar el número de efectivos en un
periodo o fecha concreta. Se incluye la totalidad de efectivos, estén ocupando o no su puesto.

=== DIMENSIONES ===

## DIMENSION: Compatibilidad ##

Atributos:
• Concedida (S/N):
Permite clasificar los datos en función de si el personal tiene concedida (S) o no (N), por esta institución, compatibilidad con otras actividades públicas o privadas.

## DIMENSION: Contrato ##

Atributos:
• Asociado Sanitario (S/N):
Permite distinguir a los profesores asociados de ciencias de la salud (S) del resto del personal (N).

• Carga Docente Semanal:
Permite clasificar al personal en función del número horas semanales que conlleva su carga docente.

• Categoría Cuerpo Escala:
Permite clasificar los datos en función de la categoría/cuerpo/escala a la que pertenece el personal.

>Valores posibles: Catedráticos de Universidad, Titulares de Universidad, Catedráticos de Escuelas
Universitarias, Titulares de Escuelas Universitarias, Asociados, Contratados Doctores, Personal Investigador Formación, Personal Docente Investigador o Técnico, Ayudantes Doctores, Colaboradores, Colaboradores Extraordinarios, Eméritos, etc.

• Dedicación:
Identifica el tipo de dedicación que tiene el personal.

>Valores posibles: tiempo completo, tiempo parcial, tiempo parcial 6 horas, tiempo parcial 4 horas, tiempo
parcial 3 horas, conjunta completa (es la dedicación de algunos profesores vinculados a instituciones sanitar distintos de los asociados de ciencias de la salud), conjunta parcial (es la dedicación de los asociados de cien de la salud), colaborador extraordinario.

• Permanente (S/N):
Permite agrupar los datos en función de si el personal tiene vinculación permanente con la Universidad Zaragoza (S) o no (N). Según la disposición adicional décima de los Estatutos de la UZ, “son profesores con vinculación permanente Universidad los funcionarios de los cuerpos docentes universitarios y los profesores contratados con cará indefinido". Por tanto se consideran permanentes: • Funcionarios de los cuerpos docentes universitarios: catedráticos de universidad, profesores titulare universidad, catedráticos de escuelas universitarias y profesores titulares de escuelas universitarias. • Profesores contratados con carácter indefinido: los que tienen régimen jurídico "laboral" y contrato con modalidades "indefinido fijo" o "indefinido no fijo".

• Régimen Jurídico:
Permite agrupar al personal en función del régimen jurídico en el que se adscribe su nombramiento o contra

>Valores posibles: funcionario, laboral, atípico (es el caso de los colaboradores extraordinarios y el de los
eméritos), contratado administrativo.

• Situación Administrativa:
Permite agrupar el personal en función de la situación administrativa en la que se encuentre.

>Ejemplos: servicio activo, excedencia, suspensión de contrato, servicios especiales.

• Tipo personal:
Permite agrupar el personal en función de la modalidad de régimen jurídico.

>Valores posibles: de carrera, indefinido fijo, temporal, convencional (es el caso de los colaboradores
extraordinarios y el de los eméritos).

## DIMENSION: Fecha de actualización ##

Notas generales:
- Indica la fecha de la última recarga de datos. Habitualmente es el domingo anterior a la consulta de datos.

## DIMENSION: Persona ##

Atributos:
• Edad:
Permite agrupar el personal en función de su edad a fecha 31 de diciembre del año seleccionado.

>Valores posibles: 21-25, 26-30, 31-35, 36-40, 41-45, 46-50, 51-55, 56-60,61-65, >65.

• País Nacionalidad:
Permite clasificar los datos en función del país de nacionalidad legal del personal.

• Sexo:
Permite clasificar el personal en función de su sexo.

## DIMENSION: Puesto ##

Atributos:
• Centro:
Permite clasificar los datos en función del centro al que pertenece el personal.

• Centro Localidad:
Permite clasificar los datos en función de la localidad donde se sitúa el centro al que está adscrito el persona

• Departamento:
Permite clasificar los datos en función del departamento al que está adscrito el personal.

• Macroárea:
Permite clasificar los datos en función de la macroárea a la que se asigna el área de conocimiento de adscripción del personal, según lo dispuesto en el Anexo I del Real Decreto 415/2015, de 29 de mayo, por el que se modifica el Real Decreto 1312/2007, de 5 de octubre, por el que se establece la acreditación nacional para el acceso a los cuerpos docentes universitarios.

• Área:
Permite clasificar los datos en función del área de conocimiento a la que pertenece el personal.

## DIMENSION: Sindicato ##

Notas generales:
- Permite clasificar el personal en función de si tiene concedida o no algún tipo de reducción horaria para el desempeño de tareas sindicales.

>Nota: si los efectivos tienen concedida reducción se detalla la denominación del sindicato y si no tienen
concedida reducción figura el valor “No Informado”.

Atributos:
• Reducción:
Identifica el porcentaje de reducción horaria o número de horas lectivas que se reducen por el desempeño d tareas sindicales.

>Nota: si el empleado no tiene concedida reducción horaria, figura con el valor “Sin reducción”.

## DIMENSION: TIEMPO ##

Notas generales:
- Permite ubicar en el tiempo la relación del personal con la UZ. Se pueden desglosar los datos según el año o mes: • MES: se incluyen los efectivos existentes a fecha último día del mes seleccionado (si se trata de un m en curso, se incluyen los efectivos existentes a la fecha de la última carga). • AÑO: se acumulan los efectivos existentes a fecha último día de todos los meses del año seleccionad (si el año seleccionado es un año en curso, se acumulan los efectivos existentes a fecha último día d los meses anteriores y para el mes en curso los efectivos existentes a la fecha de la última carga).

## DIMENSION: Titulación ##

Notas generales:
- Permite clasificar los datos en función del nivel de titulación del personal.

>Valores posibles: SUP (licenciatura o equivalente), MED (diplomatura o equivalente), DOC (doctor), MAS
(máster), GRA (grado), ELE (elemental), BAC (bachillerato).

Atributos:
• Doctor (S/N):
Permite clasificar el personal en función de si figura como Doctor en las bases de datos de personal (S) o no

• Doctor País:
Permite clasificar el personal en función, en su caso, del país en que ha obtenido el título de Doctor.

>Nota: en caso de que no conste que el efectivo haya obtenido el título de Doctor se consignará "No aplica".

• Doctor Universidad:
Permite clasificar el personal en función, en su caso, de la universidad en que ha obtenido el título de Doctor

>Nota: en caso de que no conste que el efectivo haya obtenido el título de Doctor se consignará "No aplica".

## DIMENSION: Tramos ##

Atributos:
• Docencia Quinquenios:
Permite clasificar los datos en función del número de quinquenios o tramos de docencia que tiene reconocid el personal a efectos económicos.

>Nota: contabiliza los quinquenios acumulados por el efectivo en la fecha (año o mes) seleccionada en la
dimensión “tiempo”.

• Gestión Trienios:
Permite clasificar los datos en función del número de trienios o tramos de gestión que tiene reconocido el personal.

>Nota: contabiliza los trienios acumulados por el efectivo en la fecha (año o mes) seleccionada en la dimensi
“tiempo”.

• Investigación Estatal:
Permite clasificar los datos en función del número de sexenios o tramos de investigación reconocidos por la CNEAI, tanto para los cuerpos de funcionarios docentes universitarios como para el personal contratado.

>Nota: contabiliza los sexenios reconocidos a efectos económicos acumulados en la fecha (año o mes)
seleccionada en la dimensión “tiempo”.

