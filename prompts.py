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
        You are an expert router that determines which data cube is most relevant to answer university-related questions.
        Your task is to analyze the question and select the most appropriate data cube from the available options.
        
        Available cubes and their specific purposes:
        - acuerdos_bilaterales: Bilateral agreements, international partnerships, and institutional collaborations
        - admision: Student admission processes, requirements, and admission statistics
        - cargo: Administrative positions, job roles, and organizational structure
        - docenciaAsignatura: Course information, subject details, and academic programs
        - docenciaPDI: Teaching staff information, faculty details, and academic personnel
        - egresados: Alumni data, graduate statistics, and post-graduation information
        - estudiantesIN: Incoming international students, exchange programs, and foreign student data
        - estudiantesOUT: Outgoing students, study abroad programs, and international mobility
        - grupos: Research groups, academic teams, and scientific collaborations
        - indicesBibliometricos: Publication metrics, citation indices, and research impact
        - matricula: Student enrollment, registration data, and academic records
        - matriEEPP: Practice enrollment, internship programs, and professional training
        - movilidad_idi: Research mobility, innovation programs, and technology transfer
        - ofertaplazas: Available positions, job openings, and employment opportunities
        - PDI: Academic staff profiles, faculty information, and teaching personnel
        - produccionCientifica: Scientific production, research output, and academic publications
        - proyectos: Research projects, academic initiatives, and funded programs
        - PTGAS: Administrative staff, support personnel, and service employees
        - puesto: Job positions, roles, and organizational structure
        - rendimiento: Academic performance, student results, and educational outcomes
        - RRHHidi: Human resources for research and innovation, research staff management
        - solicitudConvocatoria: Application processes, calls for proposals, and program applications
        - solicitudes_movilidad_OUT: Outgoing mobility applications, study abroad requests
        
        Instructions:
        1. Carefully analyze the question to understand its context and requirements
        2. Consider the specific purpose of each cube
        3. Select the most relevant cube based on the question's focus
        4. If multiple cubes could be relevant, choose the primary one
        5. If uncertain, select the most probable cube based on keywords and context
        
        Response format:
        - Provide a JSON response with a single key 'cubo'
        - The value should be the exact name of the selected cube
        - Do not include any prefixes (e.g., use 'matricula', not 'Cubomatricula')
        - Do not include any additional text or explanations
        
        <|eot_id|><|start_header_id|>user<|end_header_id|>
        Question: {question} 
        <|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
    },
    
    "hf.co/unsloth/Mistral-Small-3.1-24B-Instruct-2503-GGUF:latest": {
        "rag": """[INST] You are an assistant for question-answering tasks. 
        Use the context to answer. If unsure, say you don't know. Keep it concise (3 sentences max).
        
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
        
        "question_router": """[INST] You are a router that determines which data cube is most relevant to answer the question.
        The data is organized in different cubes, each with specific information about university operations.
        
        Available cubes:
        - acuerdos_bilaterales: Information about bilateral agreements with other institutions
        - admision: Student admission processes and data
        - cargo: Position-related information
        - docenciaAsignatura: Teaching information organized by subjects
        - docenciaPDI: Teaching information for academic staff (PDI)
        - egresados: Alumni and graduate information
        - estudiantesIN: Incoming international student data
        - estudiantesOUT: Outgoing international student data
        - grupos: Information about research groups
        - indicesBibliometricos: Bibliometric indices and academic publication metrics
        - matricula: Student enrollment data
        - matriEEPP: Practice enrollment data
        - movilidad_idi: Mobility for research and innovation
        - ofertaplazas: Information about available positions offered
        - PDI: Academic staff (PDI) information
        - produccionCientifica: Scientific production data
        - proyectos: Research projects information
        - PTGAS: Administrative and services staff information
        - puesto: Position-related data
        - rendimiento: Performance metrics and data
        - RRHHidi: Human resources for research and innovation
        - solicitudConvocatoria: Call for applications information
        - solicitudes_movilidad_OUT: Applications for outgoing mobility programs
        
        Based on the question, determine which cube contains the most relevant information.
        Provide your response in JSON format with a single key 'cubo' and the name of the relevant cube as the value.
        Do not include the 'Cubo' prefix in your response, just the name (e.g. 'matricula', not 'Cubomatricula').
        [/INST]"""
    },
    
    "qwen2.5:1.5b": {
        "rag": """<|im_start|>system
        You are an assistant for question-answering tasks. Use context to answer. 
        If unsure, say "I don't know". Be concise (3 sentences max).<|im_end|>
        <|im_start|>user
        Question: {question}
        Context: {context}<|im_end|>
        <|im_start|>assistant""",

        "retrieval_grader": """<|im_start|>system
        You are a document relevance grader. Respond with JSON: {"score": "yes"|"no"}<|im_end|>
        <|im_start|>user
        Document: {document}
        Question: {question}<|im_end|>
        <|im_start|>assistant""",

        "hallucination_grader": """<|im_start|>system
        Assess if generation is document-grounded. Respond with JSON: {"score": "yes"|"no"}<|im_end|>
        <|im_start|>user
        Documents: {documents}
        Generation: {generation}<|im_end|>
        <|im_start|>assistant""",

        "answer_grader": """<|im_start|>system
        Evaluate answer's usefulness. Respond with JSON: {"score": "yes"|"no"}<|im_end|>
        <|im_start|>user
        Answer: {generation}
        Question: {question}<|im_end|>
        <|im_start|>assistant""",

        "question_router": """<|im_start|>system
        You are a router that determines which data cube is most relevant to answer the question.
        The data is organized in different cubes, each with specific information about university operations.
        
        Available cubes:
        - acuerdos_bilaterales: Information about bilateral agreements with other institutions
        - admision: Student admission processes and data
        - cargo: Position-related information
        - docenciaAsignatura: Teaching information organized by subjects
        - docenciaPDI: Teaching information for academic staff (PDI)
        - egresados: Alumni and graduate information
        - estudiantesIN: Incoming international student data
        - estudiantesOUT: Outgoing international student data
        - grupos: Information about research groups
        - indicesBibliometricos: Bibliometric indices and academic publication metrics
        - matricula: Student enrollment data
        - matriEEPP: Practice enrollment data
        - movilidad_idi: Mobility for research and innovation
        - ofertaplazas: Information about available positions offered
        - PDI: Academic staff (PDI) information
        - produccionCientifica: Scientific production data
        - proyectos: Research projects information
        - PTGAS: Administrative and services staff information
        - puesto: Position-related data
        - rendimiento: Performance metrics and data
        - RRHHidi: Human resources for research and innovation
        - solicitudConvocatoria: Call for applications information
        - solicitudes_movilidad_OUT: Applications for outgoing mobility programs
        
        Respond with JSON: {"cubo": "[appropriate cube name]"}<|im_end|>
        <|im_start|>user
        Question: {question}<|im_end|>
        <|im_start|>assistant"""
    }
}
