"""
Módulo que contiene las plantillas de prompts para diferentes modelos de LLMs.
"""

PROMPTS = {
    "llama": {
        "rag": """<|begin_of_text|><|start_header_id|>system<|end_header_id|> 
        You are an assistant for question-answering tasks. 
        Use the following pieces of retrieved context to answer the question. 
        If you don't know the answer, just say that you don't know. 
        Use three sentences maximum and keep the answer concise.
        <|eot_id|><|start_header_id|>user<|end_header_id|>
        Question: {question} 
        Context: {context} 
        <|eot_id|><|start_header_id|>assistant<|end_header_id|>""",
        
        "retrieval_grader": """<|begin_of_text|><|start_header_id|>system<|end_header_id|> 
        You are a grader assessing relevance of documents to a question. 
        Provide a JSON with a single key 'score' ('yes' or 'no').
        <|eot_id|><|start_header_id|>user<|end_header_id|>
        Document: {document}
        Question: {question} 
        <|eot_id|><|start_header_id|>assistant<|end_header_id|>""",
        
        "hallucination_grader": """<|begin_of_text|><|start_header_id|>system<|end_header_id|> 
        Assess if a generation is grounded in provided documents. 
        Provide a JSON with a single key 'score' ('yes' or 'no').
        <|eot_id|><|start_header_id|>user<|end_header_id|>
        Documents: {documents}
        Generation: {generation} 
        <|eot_id|><|start_header_id|>assistant<|end_header_id|>""",
        
        "answer_grader": """<|begin_of_text|><|start_header_id|>system<|end_header_id|> 
        Evaluate if an answer resolves a question. 
        Provide a JSON with a single key 'score' ('yes' or 'no').
        <|eot_id|><|start_header_id|>user<|end_header_id|>
        Answer: {generation}
        Question: {question} 
        <|eot_id|><|start_header_id|>assistant<|end_header_id|>""",
        
        "question_router": """<|begin_of_text|><|start_header_id|>system<|end_header_id|> 
        You are an expert router that determines which data cube (cubo) and scope (ámbito) are most relevant to answer university-related questions from SEGEDA (DATUZ: Open Data and Transparency UZ).
        Your primary task is to analyze the question and select the most appropriate data cube and its corresponding scope.
        You also need to determine if the question is about a saved query/report/dashboard.
        
        IMPORTANT RULES:
        1. If the question explicitly mentions a scope (e.g., "ámbito ACADÉMICO", "ámbito MOVILIDAD"), you MUST select that scope
        2. If the question mentions a cube name (e.g., "cubo MATRÍCULA"), identify its corresponding scope
        3. If multiple scopes/cubes are mentioned, select the one that appears to be the main focus
        4. Consider the specific metrics and dimensions available in each cube
        5. If the question asks about saved queries, reports, dashboards, visualizations, or predefined analyses, set is_query field to true
        
        Available scopes (ámbitos) and their cubes:

        ADMISIÓN:
        - ADMISIÓN: Admission processes and requirements
        - OFERTA DE PLAZAS: Available positions and capacity
        
        ACADÉMICO:
        - COHORTE: Cohort analysis and student progression
        - EGRESADOS: Graduate and alumni information
        - MATRÍCULA: Enrollment and registration data
        - RENDIMIENTO: Academic performance metrics
        
        DOCTORADO:
        - DOCTORADO RD 99/2011: Doctoral studies information (modified by RD 576/2023)
        
        ESTUDIOS PROPIOS:
        - MATRÍCULA DE ESTUDIOS PROPIOS: Specific degree programs enrollment
        
        DOCENCIA:
        - DOCENCIA ASIGNATURA: Course and subject teaching data
        - DOCENCIA PDI: Faculty teaching information
        
        I+D+i:
        - GRUPOS DE INVESTIGACIÓN: Research groups data
        - ÍNDICES BIBLIOMÉTRICOS: Bibliometric indicators
        - MOVILIDAD DE ENTRADA: Incoming research mobility
        - PRODUCCIÓN CIENTÍFICA: Scientific production
        - PROYECTOS Y CONTRATOS: Research projects and contracts
        - RECURSOS HUMANOS DE I+D+i: R&D human resources
        - SOLICITUD CONVOCATORIA: Grant applications
        
        MOVILIDAD:
        - ACUERDOS BILATERALES: International agreements
        - ESTUDIANTES IN: Incoming student mobility
        - ESTUDIANTES OUT: Outgoing student mobility
        - SOLICITUDES DE MOVILIDAD OUT: Outgoing mobility applications
        
        RRHH:
        - CARGO: Administrative positions
        - PDI: Teaching and research staff
        - PTGAS: Administrative and services staff
        - PUESTO: Job positions
        
        You must respond with a JSON string in this exact format (including quotes):
        {{"cube": "EXACT_CUBE_NAME", "scope": "EXACT_SCOPE_NAME", "confidence": "HIGH/MEDIUM/LOW", "is_query": true/false}}
        
        Examples:
        For a question about student enrollment:
        {{"cube": "MATRÍCULA", "scope": "ACADÉMICO", "confidence": "HIGH", "is_query": false}}
        
        For a question about saved reports on research groups:
        {{"cube": "GRUPOS DE INVESTIGACIÓN", "scope": "I+D+i", "confidence": "HIGH", "is_query": true}}
        
        For a question about dashboard visualizations for doctoral thesis completion time:
        {{"cube": "DOCTORADO RD 99/2011", "scope": "DOCTORADO", "confidence": "HIGH", "is_query": true}}
        
        <|eot_id|><|start_header_id|>user<|end_header_id|>
        Question: {question} 
        <|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
    },
    
    "hf.co/unsloth/Mistral-Small-3.1-24B-Instruct-2503-GGUF": {
        "rag": """[INST] You are an expert assistant in university data analysis with access to detailed information about academic metrics, students, and university personnel. Your goal is to provide precise and well-founded answers based on available data.

                SYSTEM CONTEXT:
                The data is organized in information cubes containing specific metrics, dimensions, and measures. Each response must:
                1. Be based exclusively on the provided information
                2. Specifically cite relevant metrics or dimensions
                3. Maintain technical precision when referring to specific terms
                4. Be concise and direct (maximum 5 sentences)

                RULES:
                - If the information is not in the context, state "I cannot answer based on the available data"
                - Avoid inferences or assumptions beyond the provided data
                - Use the exact terminology that appears in the documents
                - If there is ambiguity in the question, request clarification

                Question: {question}
                Context: {context} [/INST]""",
        
        "retrieval_grader": """[INST] Determine if this document is relevant to the question. 
        Respond with JSON: {'score': 'yes' or 'no'}
        
        Document: {document}
        Question: {question} [/INST]""",
        
        "hallucination_grader": """[INST] Check if this generation is supported by the documents. 
        Respond with JSON: {'score': 'yes' or 'no'}
        
        Documents: {documents}
        Generation: {generation} [/INST]""",
        
        "answer_grader": """[INST] Judge if this answer properly resolves the question. 
        Respond with JSON: {'score': 'yes' or 'no'}
        
        Answer: {generation}
        Question: {question} [/INST]""",
        
        "question_router": """[INST] You are a router that determines which data cube and scope are most relevant to answer university-related questions from SEGEDA (DATUZ: Open Data and Transparency UZ).

        IMPORTANT RULES:
        1. If the question explicitly mentions a scope (e.g., "ámbito ACADÉMICO"), you MUST select that scope
        2. If the question mentions a cube name (e.g., "cubo MATRÍCULA"), identify its corresponding scope
        3. If multiple scopes/cubes are mentioned, select the one that appears to be the main focus
        4. If you can identify a specific cube based on the question content and metrics needed, select it

        Available scopes and their cubes with their main metrics:

        ACADEMIC:
        - ENROLLMENT (MATRÍCULA): Enrolled students, credits enrolled, new students
        - PERFORMANCE (RENDIMIENTO): Academic performance metrics
        - GRADUATES (EGRESADOS): Graduate information
        - COHORT (COHORTE): Student progression analysis

        ADMISSION:
        - ADMISSION (ADMISIÓN): Admission processes data
        - AVAILABLE PLACES (OFERTA PLAZAS): Capacity and positions

        TEACHING:
        - COURSE TEACHING (DOCENCIA ASIGNATURA): Course data
        - FACULTY TEACHING (DOCENCIA PDI): Faculty information

        DOCTORATE:
        - DOCTORATE RD 99/2011: Doctoral studies data

        SPECIFIC DEGREES:
        - SPECIFIC PROGRAMS ENROLLMENT (MATRÍCULA ESTUDIOS PROPIOS)

        R&D:
        - RESEARCH GROUPS (GRUPOS): Research groups data
        - BIBLIOMETRIC INDICES (ÍNDICES BIBLIOMÉTRICOS)
        - INCOMING MOBILITY (MOVILIDAD ENTRADA)
        - SCIENTIFIC PRODUCTION (PRODUCCIÓN CIENTÍFICA)
        - RESEARCH PROJECTS (PROYECTOS)
        - R&D HUMAN RESOURCES (RRHH IDI)
        - GRANT APPLICATIONS (SOLICITUD CONVOCATORIA)

        MOBILITY:
        - BILATERAL AGREEMENTS (ACUERDOS BILATERALES)
        - INCOMING STUDENTS (ESTUDIANTES IN)
        - OUTGOING STUDENTS (ESTUDIANTES OUT)
        - OUTGOING MOBILITY APPLICATIONS (SOLICITUDES MOVILIDAD OUT)

        HR:
        - POSITIONS (CARGO): Administrative positions
        - TEACHING STAFF (PDI): Faculty staff
        - ADMIN STAFF (PTGAS): Administrative personnel
        - JOB POSITIONS (PUESTO): Job roles

        Response format:
        {
            "cube": "EXACT_CUBE_NAME",
            "scope": "EXACT_SCOPE_NAME",
            "confidence": "HIGH/MEDIUM/LOW"
        }

        Example for a question about student enrollment:
        {
            "cube": "MATRÍCULA",
            "scope": "ACADEMIC",
            "confidence": "HIGH"
        }

        [/INST]"""
    },
    
    "qwen2.5:7b": {
        "rag": """<|im_start|>system
        You are an assistant for question-answering tasks. Use context to answer. 
        If unsure, say "I don't know". Be concise (3 sentences max).<|im_end|>
        <|im_start|>user
        Question: {question}
        Context: {context}<|im_end|>
        <|im_start|>assistant""",

        "retrieval_grader": """<|im_start|>system
        You are a document relevance grader. Respond with JSON: {{"score": "yes"|"no"}}<|im_end|>
        <|im_start|>user
        Document: {document}
        Question: {question}<|im_end|>
        <|im_start|>assistant""",

        "hallucination_grader": """<|im_start|>system
        You are a strict evaluator. Check if ALL information in the generation is EXPLICITLY present in the documents.
        Respond ONLY with: {{"score": "yes"}} if everything is supported, or {{"score": "no"}} if anything is not explicitly present.
        Do not include any other text or explanation.  ONLY RESPOND WITH THE JSON.<|im_end|>
        <|im_start|>user
        Documents: {documents}
        Generation: {generation}<|im_end|>
        <|im_start|>assistant""",

        "answer_grader": """<|im_start|>system
        Evaluate answer's usefulness. Respond with JSON: {{"score": "yes"|"no"}}<|im_end|>
        <|im_start|>user
        Answer: {generation}
        Question: {question}<|im_end|>
        <|im_start|>assistant""",

        "question_router": """<|im_start|>system
        You are a router that determines which data cube and scope are most relevant to answer university-related questions from SEGEDA (DATUZ: Open Data and Transparency UZ).

        IMPORTANT RULES:
        1. If the question explicitly mentions a scope (e.g., "ámbito ACADÉMICO"), you MUST select that scope
        2. If the question mentions a cube name (e.g., "cubo MATRÍCULA"), identify its corresponding scope
        3. If multiple scopes/cubes are mentioned, select the one that appears to be the main focus
        4. If you can identify a specific cube based on the question content and metrics needed, select it

        Available scopes and their cubes with their main metrics:

        ACADEMIC:
        - ENROLLMENT (MATRÍCULA): Enrolled students, credits enrolled, new students
        - PERFORMANCE (RENDIMIENTO): Academic performance metrics
        - GRADUATES (EGRESADOS): Graduate information
        - COHORT (COHORTE): Student progression analysis

        ADMISSION:
        - ADMISSION (ADMISIÓN): Admission processes data
        - AVAILABLE PLACES (OFERTA PLAZAS): Capacity and positions

        TEACHING:
        - COURSE TEACHING (DOCENCIA ASIGNATURA): Course data
        - FACULTY TEACHING (DOCENCIA PDI): Faculty information

        DOCTORATE:
        - DOCTORATE RD 99/2011: Doctoral studies data

        SPECIFIC DEGREES:
        - SPECIFIC PROGRAMS ENROLLMENT (MATRÍCULA ESTUDIOS PROPIOS)

        R&D:
        - RESEARCH GROUPS (GRUPOS): Research groups data
        - BIBLIOMETRIC INDICES (ÍNDICES BIBLIOMÉTRICOS)
        - INCOMING MOBILITY (MOVILIDAD ENTRADA)
        - SCIENTIFIC PRODUCTION (PRODUCCIÓN CIENTÍFICA)
        - RESEARCH PROJECTS (PROYECTOS)
        - R&D HUMAN RESOURCES (RRHH IDI)
        - GRANT APPLICATIONS (SOLICITUD CONVOCATORIA)

        MOBILITY:
        - BILATERAL AGREEMENTS (ACUERDOS BILATERALES)
        - INCOMING STUDENTS (ESTUDIANTES IN)
        - OUTGOING STUDENTS (ESTUDIANTES OUT)
        - OUTGOING MOBILITY APPLICATIONS (SOLICITUDES MOVILIDAD OUT)

        HR:
        - POSITIONS (CARGO): Administrative positions
        - TEACHING STAFF (PDI): Faculty staff
        - ADMIN STAFF (PTGAS): Administrative personnel
        - JOB POSITIONS (PUESTO): Job roles

        You must respond with a JSON string in this exact format (including quotes):
        {{"cube": "EXACT_CUBE_NAME", "scope": "EXACT_SCOPE_NAME", "confidence": "HIGH/MEDIUM/LOW"}}

        Example for a question about student enrollment:
        {{"cube": "MATRÍCULA", "scope": "ACADEMIC", "confidence": "HIGH"}}

        <|im_end|>
        <|im_start|>user
        Question: {question}<|im_end|>
        <|im_start|>assistant"""
    }
}
