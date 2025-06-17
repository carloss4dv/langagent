# 📊 Resumen Completo del Análisis de Chunks

**Fecha de análisis:** 2025-06-16 16:29:59

---

## 📈 Datos Generales del Corpus

| Métrica | Valor |
|---------|-------|
| 📁 Documentos analizados | 23 |
| 📝 Total de unidades textuales | 637 |
| 📏 Total de caracteres | 373,082 |
| 📖 Total de palabras | 71,785 |
| 🎯 Densidad textual promedio | 585.7 chars/unidad |
| 📊 Eficiencia léxica | 19.24% (palabras por carácter) |

---

## 📈 Métricas Estadísticas Utilizadas en el Análisis

### Métodos de Análisis Estadístico

- **🔹 Medidas de tendencia central:** Media aritmética, Mediana, Moda
- **🔸 Medidas de dispersión:** Desviación estándar, Varianza, Coeficiente de variación  
- **🔷 Medidas de posición:** Cuartiles (Q1, Q2, Q3), Percentiles (P5, P10, P90, P95)
- **🔺 Medidas de forma:** Asimetría (skewness), Curtosis (kurtosis)
- **🔻 Análisis de outliers:** Método del rango intercuartílico (IQR)
- **⚡ Análisis de distribuciones:** Histogramas, boxplots, distribuciones acumulativas

---

## 📊 Distribuciones Estadísticas por Tipo de Unidad

### 🔹 Oraciones (243 unidades)

| Métrica | Valor |
|---------|-------|
| Media | 218.9 ± 131.1 caracteres |
| Mediana | 172.0 caracteres |
| Asimetría | 1.839 (sesgada derecha) |
| Rango intercuartílico | 147.5 |
| Mínimo | 65 caracteres |
| Máximo | 893 caracteres |
| Q1 (Percentil 25) | 130.5 |
| Q3 (Percentil 75) | 278.0 |

### 🔸 Párrafos (348 unidades)

| Métrica | Valor |
|---------|-------|
| Media | 455.5 ± 887.5 caracteres |
| Mediana | 214.5 caracteres |
| Asimetría | 6.358 (sesgada derecha) |
| Rango intercuartílico | 219.2 |
| Mínimo | 64 caracteres |
| Máximo | 10115 caracteres |
| Q1 (Percentil 25) | 150.0 |
| Q3 (Percentil 75) | 369.2 |

### 🔷 Secciones (46 unidades)

| Métrica | Valor |
|---------|-------|
| Media | 3508.3 ± 2746.0 caracteres |
| Mediana | 2999.0 caracteres |
| Asimetría | 0.846 (sesgada derecha) |
| Rango intercuartílico | 3780.2 |
| Mínimo | 258 caracteres |
| Máximo | 11259 caracteres |
| Q1 (Percentil 25) | 1293.2 |
| Q3 (Percentil 75) | 5073.5 |

---

## 🎯 Configuraciones Recomendadas Basadas en Análisis Estadístico

### 📈 Basadas en Cuartiles de Párrafos

| Tipo de Chunk | Tamaño Recomendado |
|---------------|-------------------|
| Chunk pequeño (Q1) | ~150 caracteres |
| Chunk mediano (Q2) | ~214 caracteres |
| Chunk grande (Q3) | ~369 caracteres |

### 📊 Basadas en Oraciones Promedio

| Configuración | Tamaño Estimado |
|--------------|----------------|
| 3-5 oraciones | ~875 caracteres |
| 8-12 oraciones | ~2188 caracteres |

---

## ⚡ Métricas de Eficiencia y Calidad Textual

| Métrica | Valor |
|---------|-------|
| 🔹 Densidad léxica promedio | 19.24% |
| 🔸 Caracteres por palabra | 5.20 |
| 🔷 Palabras por unidad textual | 112.7 |
| 🎯 Coeficiente de eficiencia | 112.692 |

---

## 🏆 Top Configuraciones Óptimas de Chunk-Overlap

| Rank | Chunk Size | Overlap | % Overlap | Justificación | Rendimiento Esperado |
|------|------------|---------|-----------|---------------|---------------------|
| 🥇 1 | 150 | 37 | 24.7% | pequeño - 25% | Rápido pero menos contexto |
| 🥈 2 | 369 | 73 | 19.8% | pequeño - 20% | Rápido pero menos contexto |
| 🥉 3 | 646 | 96 | 14.9% | mediano - 15% | Equilibrio ideal velocidad-contexto |
| 🔸 4 | 1094 | 107 | 9.8% | grande - 1/2 párrafo mediano | Más contexto, procesamiento lento |
| 🔸 5 | 1499 | 107 | 7.1% | grande - 1/2 párrafo mediano | Más contexto, procesamiento lento |

---

## 🚀 Recomendaciones Finales para Implementación

### ✅ Estrategias Prioritarias

1. **Utilizar configuraciones basadas en percentiles de párrafos** para mejor coherencia semántica
2. **Considerar overlap de 15-25% del tamaño del chunk** para mantener contexto
3. **Priorizar chunks de ~214 caracteres** (mediana de párrafos)
4. **Implementar análisis A/B testing** con las configuraciones sugeridas vs actuales

### 🎯 Configuración Recomendada Principal

**Configuración óptima identificada:**

- **Chunk Size:** 150 caracteres
- **Overlap:** 37 caracteres (24.7% del chunk)
- **Justificación:** pequeño - 25%
- **Ventajas:** Equilibrio óptimo entre coherencia semántica y eficiencia de procesamiento

### 📊 Comparación con Configuraciones Actuales

| Configuración | Actual | Recomendada | Mejora |
|--------------|--------|-------------|--------|
| Pequeña | 256 chars, 50 overlap | 150 chars, 37 overlap | -106 chars, -13 overlap |
| Mediana | 512 chars, 50 overlap | 369 chars, 73 overlap | -143 chars, +23 overlap |
| Grande | 1024 chars, 50 overlap | 4377 chars, 107 overlap | +3353 chars, +57 overlap |


---

## 📋 Análisis Detallado por Documento

### 📄 info_cubo_acuerdos_bilaterales_v11.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 21 |
| Caracteres | 9,555 (2.6% del total) |
| Palabras | 1,784 |
| Densidad | 455.0 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 19
- Sections: 2

### 📄 info_cubo_admision_v19.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 32 |
| Caracteres | 23,089 (6.2% del total) |
| Palabras | 4,481 |
| Densidad | 721.5 chars/unidad |

**Distribución por tipo:**
- Sentences: 24
- Paragraphs: 6
- Sections: 2

### 📄 info_cubo_cargo_v14.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 17 |
| Caracteres | 6,835 (1.8% del total) |
| Palabras | 1,377 |
| Densidad | 402.1 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 12
- Sentences: 3
- Sections: 2

### 📄 info_cubo_docenciaAsignatura_v10.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 25 |
| Caracteres | 13,488 (3.6% del total) |
| Palabras | 2,633 |
| Densidad | 539.5 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 13
- Sentences: 10
- Sections: 2

### 📄 info_cubo_docenciaPDI_v11.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 37 |
| Caracteres | 34,566 (9.3% del total) |
| Palabras | 6,629 |
| Densidad | 934.2 chars/unidad |

**Distribución por tipo:**
- Sentences: 25
- Paragraphs: 10
- Sections: 2

### 📄 info_cubo_egresados_v23.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 42 |
| Caracteres | 30,993 (8.3% del total) |
| Palabras | 6,097 |
| Densidad | 737.9 chars/unidad |

**Distribución por tipo:**
- Sentences: 25
- Paragraphs: 15
- Sections: 2

### 📄 info_cubo_estudiantesIN_v12.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 23 |
| Caracteres | 15,325 (4.1% del total) |
| Palabras | 2,906 |
| Densidad | 666.3 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 19
- Sections: 2
- Sentences: 2

### 📄 info_cubo_estudiantesOUT_v11.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 26 |
| Caracteres | 13,540 (3.6% del total) |
| Palabras | 2,584 |
| Densidad | 520.8 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 24
- Sections: 2

### 📄 info_cubo_grupos_v13.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 27 |
| Caracteres | 14,025 (3.8% del total) |
| Palabras | 2,718 |
| Densidad | 519.4 chars/unidad |

**Distribución por tipo:**
- Sentences: 19
- Paragraphs: 6
- Sections: 2

### 📄 info_cubo_indicesBibliometricos_v11.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 17 |
| Caracteres | 5,789 (1.6% del total) |
| Palabras | 1,077 |
| Densidad | 340.5 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 14
- Sections: 2
- Sentences: 1

### 📄 info_cubo_matricula_v24.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 37 |
| Caracteres | 29,129 (7.8% del total) |
| Palabras | 5,659 |
| Densidad | 787.3 chars/unidad |

**Distribución por tipo:**
- Sentences: 25
- Paragraphs: 10
- Sections: 2

### 📄 info_cubo_matriEEPP_v11.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 18 |
| Caracteres | 7,562 (2.0% del total) |
| Palabras | 1,507 |
| Densidad | 420.1 chars/unidad |

**Distribución por tipo:**
- Sentences: 10
- Paragraphs: 6
- Sections: 2

### 📄 info_cubo_movilidad_idi_v11.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 18 |
| Caracteres | 5,142 (1.4% del total) |
| Palabras | 1,030 |
| Densidad | 285.7 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 16
- Sections: 2

### 📄 info_cubo_ofertaplazas_v18.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 25 |
| Caracteres | 17,187 (4.6% del total) |
| Palabras | 3,276 |
| Densidad | 687.5 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 16
- Sentences: 7
- Sections: 2

### 📄 info_cubo_PDI_v21.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 32 |
| Caracteres | 21,510 (5.8% del total) |
| Palabras | 4,209 |
| Densidad | 672.2 chars/unidad |

**Distribución por tipo:**
- Sentences: 24
- Paragraphs: 6
- Sections: 2

### 📄 info_cubo_produccionCientifica_v13.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 27 |
| Caracteres | 13,956 (3.7% del total) |
| Palabras | 2,754 |
| Densidad | 516.9 chars/unidad |

**Distribución por tipo:**
- Sentences: 17
- Paragraphs: 8
- Sections: 2

### 📄 info_cubo_proyectos_v11.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 30 |
| Caracteres | 10,186 (2.7% del total) |
| Palabras | 1,806 |
| Densidad | 339.5 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 28
- Sections: 2

### 📄 info_cubo_PTGAS_v21.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 28 |
| Caracteres | 15,151 (4.1% del total) |
| Palabras | 3,036 |
| Densidad | 541.1 chars/unidad |

**Distribución por tipo:**
- Sentences: 20
- Paragraphs: 6
- Sections: 2

### 📄 info_cubo_puesto_v14.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 21 |
| Caracteres | 9,437 (2.5% del total) |
| Palabras | 1,904 |
| Densidad | 449.4 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 19
- Sections: 2

### 📄 info_cubo_rendimiento_v21.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 42 |
| Caracteres | 32,055 (8.6% del total) |
| Palabras | 6,020 |
| Densidad | 763.2 chars/unidad |

**Distribución por tipo:**
- Sentences: 22
- Paragraphs: 18
- Sections: 2

### 📄 info_cubo_RRHHidi_v13.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 32 |
| Caracteres | 19,014 (5.1% del total) |
| Palabras | 3,569 |
| Densidad | 594.2 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 26
- Sentences: 4
- Sections: 2

### 📄 info_cubo_solicitudConvocatoria_v11.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 31 |
| Caracteres | 12,842 (3.4% del total) |
| Palabras | 2,368 |
| Densidad | 414.3 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 26
- Sentences: 3
- Sections: 2

### 📄 info_cubo_solicitudes_movilidad_OUT_v11.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 29 |
| Caracteres | 12,706 (3.4% del total) |
| Palabras | 2,361 |
| Densidad | 438.1 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 25
- Sections: 2
- Sentences: 2


---

## 🔗 Archivos Generados

Este análisis ha generado los siguientes archivos:

- `resumen_analisis_chunks.md` - Este resumen completo
- `chunk_analysis_results.csv` - Datos detallados del análisis
- `optimal_chunk_overlap_configs.csv` - Configuraciones óptimas
- `chunk_analysis_1_boxplot_distribucion.png` - Distribución por tipos
- `chunk_analysis_2_histograma_paragrafos.png` - Histograma con métricas
- `chunk_analysis_3_scatter_chars_palabras.png` - Relación chars-palabras
- `chunk_analysis_4_longitud_palabras.png` - Distribución longitud palabras
- `chunk_analysis_5_comparacion_configs.png` - Configuraciones actuales vs sugeridas
- `chunk_analysis_6_configuraciones_optimas.png` - Top configuraciones chunk-overlap

---

**Análisis generado por:** chunk_analyzer.py  
**Versión:** 1.0  
**Fecha:** 2025-06-16 16:29:59
