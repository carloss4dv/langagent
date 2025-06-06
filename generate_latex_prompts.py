#!/usr/bin/env python3
"""
Script para generar código LaTeX con todos los prompts desde prompts.py
"""

import sys
import os

# Agregar el directorio actual al path para poder importar prompts
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from prompts import PROMPTS
    print("✅ Importación de prompts exitosa")
except ImportError as e:
    print(f"❌ Error al importar prompts: {e}")
    sys.exit(1)

def remove_accents(text):
    """Quitar tildes y caracteres especiales que causan problemas en LaTeX"""
    # Mapeo de caracteres con tilde/especiales a caracteres normales
    accent_map = {
        'á': 'a', 'à': 'a', 'ä': 'a', 'â': 'a', 'ā': 'a', 'ã': 'a',
        'Á': 'A', 'À': 'A', 'Ä': 'A', 'Â': 'A', 'Ā': 'A', 'Ã': 'A',
        'é': 'e', 'è': 'e', 'ë': 'e', 'ê': 'e', 'ē': 'e',
        'É': 'E', 'È': 'E', 'Ë': 'E', 'Ê': 'E', 'Ē': 'E',
        'í': 'i', 'ì': 'i', 'ï': 'i', 'î': 'i', 'ī': 'i',
        'Í': 'I', 'Ì': 'I', 'Ï': 'I', 'Î': 'I', 'Ī': 'I',
        'ó': 'o', 'ò': 'o', 'ö': 'o', 'ô': 'o', 'ō': 'o', 'õ': 'o',
        'Ó': 'O', 'Ò': 'O', 'Ö': 'O', 'Ô': 'O', 'Ō': 'O', 'Õ': 'O',
        'ú': 'u', 'ù': 'u', 'ü': 'u', 'û': 'u', 'ū': 'u',
        'Ú': 'U', 'Ù': 'U', 'Ü': 'U', 'Û': 'U', 'Ū': 'U',
        'ñ': 'n', 'Ñ': 'N',
        'ç': 'c', 'Ç': 'C',
        '€': 'EUR', '£': 'GBP', '¿': '', '¡': '',
        ''': "'", ''': "'", '"': '"', '"': '"',
        '–': '-', '—': '-', '…': '...'
    }
    
    for accent, replacement in accent_map.items():
        text = text.replace(accent, replacement)
    
    return text

def escape_latex(text):
    """Escapar caracteres especiales para LaTeX"""
    # Caracteres que necesitan escape en LaTeX
    latex_special_chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '^': r'\textasciicircum{}',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '\\': r'\textbackslash{}',
    }
    
    for char, escape in latex_special_chars.items():
        text = text.replace(char, escape)
    
    return text

def generate_latex():
    """Generar el código LaTeX completo"""
    
    print("🔄 Iniciando generación de LaTeX...")
    
    # Mapeo de nombres de modelos a títulos LaTeX
    model_titles = {
        "llama": "Modelo LLaMA",
        "mistral-small-3.1:24b": "Modelo Mistral-Small-3.1:24b", 
        "qwen": "Modelo Qwen"
    }
    
    # Mapeo de tipos de prompt a títulos LaTeX
    prompt_titles = {
        "rag": "RAG Prompt",
        "context_generator": "Context Generator",
        "retrieval_grader": "Retrieval Grader", 
        "hallucination_grader": "Hallucination Grader",
        "answer_grader": "Answer Grader",
        "query_rewriter": "Query Rewriter",
        "clarification_generator": "Clarification Generator",
        "sql_generator": "SQL Generator",
        "sql_interpretation": "SQL Interpretation"
    }
    
    latex_content = []
    models_processed = 0
    
    print(f"📊 Modelos disponibles: {list(PROMPTS.keys())}")
    
    for model_key, model_data in PROMPTS.items():
        print(f"🔍 Procesando modelo: {model_key}")
        
        if model_key in model_titles:
            models_processed += 1
            # Agregar subsección para el modelo
            latex_content.append(f"\\subsection{{{model_titles[model_key]}}}")
            latex_content.append("\\begin{itemize}")
            
            prompts_processed = 0
            for prompt_type, prompt_content in model_data.items():
                if prompt_type in prompt_titles:
                    prompts_processed += 1
                    print(f"  📝 Procesando prompt: {prompt_type}")
                    
                    # Agregar título del prompt
                    latex_content.append(f"    \\item \\textbf{{{prompt_titles[prompt_type]}}}:")
                    latex_content.append("    \\begin{lstlisting}[breaklines=true,basicstyle=\\small\\ttfamily]")
                    
                    # Procesar contenido del prompt - quitar tildes
                    clean_content = remove_accents(prompt_content.strip())
                    prompt_lines = clean_content.split('\n')
                    for line in prompt_lines:
                        latex_content.append(line)
                    
                    latex_content.append("    \\end{lstlisting}")
                    latex_content.append("")  # Línea vacía para separación
            
            latex_content.append("\\end{itemize}")
            latex_content.append("")  # Línea vacía entre modelos
            
            print(f"  ✅ {prompts_processed} prompts procesados para {model_key}")
        else:
            print(f"  ⚠️ Modelo {model_key} no está en la lista de títulos")
    
    print(f"📈 Total de modelos procesados: {models_processed}")
    return '\n'.join(latex_content)

def main():
    """Función principal"""
    try:
        print("🚀 Generando código LaTeX desde prompts.py...")
        
        # Generar el código LaTeX
        latex_code = generate_latex()
        
        if not latex_code.strip():
            print("⚠️ No se generó contenido LaTeX")
            return 1
        
        # Guardar en archivo
        output_file = "prompts_latex.tex"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("% Requiere el paquete listings en el preambulo:\n")
            f.write("% \\usepackage{listings}\n")
            f.write("% \\usepackage{xcolor}\n")
            f.write("% NOTA: Se han eliminado tildes y caracteres especiales para evitar problemas UTF-8\n\n")
            f.write(latex_code)
        
        print(f"✅ Código LaTeX generado exitosamente en: {output_file}")
        
        # Verificar el tamaño del archivo
        file_size = os.path.getsize(output_file)
        print(f"📄 Tamaño del archivo: {file_size} bytes")
        
        # Mostrar un resumen
        print("\n📋 Resumen de contenido generado:")
        for model_key in PROMPTS.keys():
            if model_key in ["llama", "mistral-small-3.1:24b", "qwen"]:
                prompt_count = len(PROMPTS[model_key])
                print(f"   • {model_key}: {prompt_count} prompts")
        
        # Mostrar las primeras líneas del archivo generado
        print(f"\n🔍 Primeras líneas del archivo generado:")
        with open(output_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:10]
            for i, line in enumerate(lines, 1):
                print(f"   {i:2d}: {line.rstrip()}")
        
        print("\n📝 NOTA: Asegúrate de incluir en el preámbulo de tu documento LaTeX:")
        print("   \\usepackage{listings}")
        print("   \\usepackage{xcolor}")
        print("   🔸 Se han eliminado tildes y caracteres especiales para evitar errores UTF-8")
        
    except Exception as e:
        print(f"❌ Error al generar LaTeX: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 