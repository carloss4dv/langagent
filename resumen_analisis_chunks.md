# 📊 Resumen Completo del Análisis de Chunks

**Fecha de análisis:** 2025-06-13 08:48:03

---

## 📈 Datos Generales del Corpus

| Métrica | Valor |
|---------|-------|
| 📁 Documentos analizados | 24 |
| 📝 Total de unidades textuales | 2,330 |
| 📏 Total de caracteres | 456,967 |
| 📖 Total de palabras | 87,122 |
| 🎯 Densidad textual promedio | 196.1 chars/unidad |
| 📊 Eficiencia léxica | 19.07% (palabras por carácter) |

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

### 🔹 Oraciones (1,005 unidades)

| Métrica | Valor |
|---------|-------|
| Media | 151.2 ± 77.5 caracteres |
| Mediana | 138.0 caracteres |
| Asimetría | 1.839 (sesgada derecha) |
| Rango intercuartílico | 77.0 |
| Mínimo | 2 caracteres |
| Máximo | 838 caracteres |
| Q1 (Percentil 25) | 101.0 |
| Q3 (Percentil 75) | 178.0 |

### 🔸 Párrafos (1,092 unidades)

| Métrica | Valor |
|---------|-------|
| Media | 138.8 ± 114.4 caracteres |
| Mediana | 124.5 caracteres |
| Asimetría | 2.843 (sesgada derecha) |
| Rango intercuartílico | 110.0 |
| Mínimo | 11 caracteres |
| Máximo | 1164 caracteres |
| Q1 (Percentil 25) | 63.0 |
| Q3 (Percentil 75) | 173.0 |

### 🔷 Secciones (233 unidades)

| Métrica | Valor |
|---------|-------|
| Media | 658.8 ± 819.4 caracteres |
| Mediana | 307.0 caracteres |
| Asimetría | 2.751 (sesgada derecha) |
| Rango intercuartílico | 695.0 |
| Mínimo | 20 caracteres |
| Máximo | 6019 caracteres |
| Q1 (Percentil 25) | 167.0 |
| Q3 (Percentil 75) | 862.0 |

---

## 🎯 Configuraciones Recomendadas Basadas en Análisis Estadístico

### 📈 Basadas en Cuartiles de Párrafos

| Tipo de Chunk | Tamaño Recomendado |
|---------------|-------------------|
| Chunk pequeño (Q1) | ~63 caracteres |
| Chunk mediano (Q2) | ~124 caracteres |
| Chunk grande (Q3) | ~173 caracteres |

### 📊 Basadas en Oraciones Promedio

| Configuración | Tamaño Estimado |
|--------------|----------------|
| 3-5 oraciones | ~604 caracteres |
| 8-12 oraciones | ~1511 caracteres |

---

## ⚡ Métricas de Eficiencia y Calidad Textual

| Métrica | Valor |
|---------|-------|
| 🔹 Densidad léxica promedio | 19.07% |
| 🔸 Caracteres por palabra | 5.25 |
| 🔷 Palabras por unidad textual | 37.4 |
| 🎯 Coeficiente de eficiencia | 37.391 |

---

## 🏆 Top Configuraciones Óptimas de Chunk-Overlap

| Rank | Chunk Size | Overlap | % Overlap | Justificación | Rendimiento Esperado |
|------|------------|---------|-----------|---------------|---------------------|
| 🥇 1 | 63 | 6 | 9.5% | pequeño - 10% | Rápido pero menos contexto |
| 🥈 2 | 124 | 37 | 29.8% | pequeño - 30% | Rápido pero menos contexto |
| 🥉 3 | 167 | 41 | 24.6% | pequeño - 25% | Rápido pero menos contexto |
| 🔸 4 | 249 | 49 | 19.7% | pequeño - 20% | Rápido pero menos contexto |
| 🔸 5 | 307 | 61 | 19.9% | pequeño - 20% | Rápido pero menos contexto |

---

## 🚀 Recomendaciones Finales para Implementación

### ✅ Estrategias Prioritarias

1. **Utilizar configuraciones basadas en percentiles de párrafos** para mejor coherencia semántica
2. **Considerar overlap de 15-25% del tamaño del chunk** para mantener contexto
3. **Priorizar chunks de ~124 caracteres** (mediana de párrafos)
4. **Implementar análisis A/B testing** con las configuraciones sugeridas vs actuales

### 🎯 Configuración Recomendada Principal

**Configuración óptima identificada:**

- **Chunk Size:** 63 caracteres
- **Overlap:** 6 caracteres (9.5% del chunk)
- **Justificación:** pequeño - 10%
- **Ventajas:** Equilibrio óptimo entre coherencia semántica y eficiencia de procesamiento

### 📊 Comparación con Configuraciones Actuales

| Configuración | Actual | Recomendada | Mejora |
|--------------|--------|-------------|--------|
| Pequeña | 256 chars, 50 overlap | 63 chars, 6 overlap | -193 chars, -44 overlap |
| Mediana | 512 chars, 50 overlap | 124 chars, 37 overlap | -388 chars, -13 overlap |
| Grande | 1024 chars, 50 overlap | 3023 chars, 151 overlap | +1999 chars, +101 overlap |


---

## 📋 Análisis Detallado por Documento

### 📄 info_cubo_acuerdos_bilaterales_v11.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 85 |
| Caracteres | 13,851 (3.0% del total) |
| Palabras | 2,598 |
| Densidad | 163.0 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 42
- Sentences: 29
- Sections: 14

### 📄 info_cubo_admision_v19.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 113 |
| Caracteres | 24,414 (5.3% del total) |
| Palabras | 4,740 |
| Densidad | 216.1 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 54
- Sentences: 52
- Sections: 7

### 📄 info_cubo_cargo_v14.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 61 |
| Caracteres | 8,842 (1.9% del total) |
| Palabras | 1,791 |
| Densidad | 145.0 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 28
- Sentences: 21
- Sections: 12

### 📄 info_cubo_docenciaAsignatura_v10.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 78 |
| Caracteres | 15,330 (3.4% del total) |
| Palabras | 2,946 |
| Densidad | 196.5 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 38
- Sentences: 33
- Sections: 7

### 📄 info_cubo_docenciaPDI_v11.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 139 |
| Caracteres | 37,400 (8.2% del total) |
| Palabras | 7,068 |
| Densidad | 269.1 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 67
- Sentences: 61
- Sections: 11

### 📄 info_cubo_egresados_v23.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 166 |
| Caracteres | 36,285 (7.9% del total) |
| Palabras | 7,113 |
| Densidad | 218.6 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 77
- Sentences: 76
- Sections: 13

### 📄 info_cubo_estudiantesIN_v12.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 90 |
| Caracteres | 21,613 (4.7% del total) |
| Palabras | 4,149 |
| Densidad | 240.1 chars/unidad |

**Distribución por tipo:**
- Sentences: 43
- Paragraphs: 37
- Sections: 10

### 📄 info_cubo_estudiantesOUT_v11.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 93 |
| Caracteres | 19,114 (4.2% del total) |
| Palabras | 3,707 |
| Densidad | 205.5 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 42
- Sentences: 42
- Sections: 9

### 📄 info_cubo_grupos_v13.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 81 |
| Caracteres | 14,447 (3.2% del total) |
| Palabras | 2,749 |
| Densidad | 178.4 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 38
- Sentences: 37
- Sections: 6

### 📄 info_cubo_indicesBibliometricos_v11.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 52 |
| Caracteres | 7,118 (1.6% del total) |
| Palabras | 1,314 |
| Densidad | 136.9 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 26
- Sentences: 20
- Sections: 6

### 📄 info_cubo_matricula_v24.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 142 |
| Caracteres | 32,795 (7.2% del total) |
| Palabras | 6,297 |
| Densidad | 231.0 chars/unidad |

**Distribución por tipo:**
- Sentences: 71
- Paragraphs: 61
- Sections: 10

### 📄 info_cubo_matriEEPP_v11.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 52 |
| Caracteres | 7,888 (1.7% del total) |
| Palabras | 1,536 |
| Densidad | 151.7 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 25
- Sentences: 21
- Sections: 6

### 📄 info_cubo_movilidad_idi_v11.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 50 |
| Caracteres | 6,411 (1.4% del total) |
| Palabras | 1,266 |
| Densidad | 128.2 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 25
- Sentences: 19
- Sections: 6

### 📄 info_cubo_ofertaplazas_v18.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 100 |
| Caracteres | 23,219 (5.1% del total) |
| Palabras | 4,395 |
| Densidad | 232.2 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 47
- Sentences: 43
- Sections: 10

### 📄 info_cubo_PDI_v21.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 113 |
| Caracteres | 23,452 (5.1% del total) |
| Palabras | 4,497 |
| Densidad | 207.5 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 55
- Sentences: 47
- Sections: 11

### 📄 info_cubo_produccionCientifica_v13.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 102 |
| Caracteres | 15,328 (3.4% del total) |
| Palabras | 2,961 |
| Densidad | 150.3 chars/unidad |

**Distribución por tipo:**
- Sentences: 50
- Paragraphs: 45
- Sections: 7

### 📄 info_cubo_proyectos_v11.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 83 |
| Caracteres | 13,795 (3.0% del total) |
| Palabras | 2,403 |
| Densidad | 166.2 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 41
- Sentences: 35
- Sections: 7

### 📄 info_cubo_PTGAS_v21.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 101 |
| Caracteres | 16,716 (3.7% del total) |
| Palabras | 3,273 |
| Densidad | 165.5 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 49
- Sentences: 42
- Sections: 10

### 📄 info_cubo_puesto_v14.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 95 |
| Caracteres | 14,116 (3.1% del total) |
| Palabras | 2,847 |
| Densidad | 148.6 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 43
- Sentences: 34
- Sections: 18

### 📄 info_cubo_rendimiento_v21.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 172 |
| Caracteres | 38,973 (8.5% del total) |
| Palabras | 7,227 |
| Densidad | 226.6 chars/unidad |

**Distribución por tipo:**
- Sentences: 81
- Paragraphs: 80
- Sections: 11

### 📄 info_cubo_RRHHidi_v13.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 142 |
| Caracteres | 26,867 (5.9% del total) |
| Palabras | 5,067 |
| Densidad | 189.2 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 66
- Sentences: 51
- Sections: 25

### 📄 info_cubo_solicitudConvocatoria_v11.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 104 |
| Caracteres | 16,394 (3.6% del total) |
| Palabras | 3,006 |
| Densidad | 157.6 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 49
- Sentences: 48
- Sections: 7

### 📄 info_cubo_solicitudes_movilidad_OUT_v11.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 89 |
| Caracteres | 17,156 (3.8% del total) |
| Palabras | 3,245 |
| Densidad | 192.8 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 42
- Sentences: 38
- Sections: 9

### 📄 info_cubo_test_v1.md

| Métrica | Valor |
|---------|-------|
| Unidades totales | 27 |
| Caracteres | 5,443 (1.2% del total) |
| Palabras | 927 |
| Densidad | 201.6 chars/unidad |

**Distribución por tipo:**
- Paragraphs: 15
- Sentences: 11
- Sections: 1


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
**Fecha:** 2025-06-13 08:48:03
