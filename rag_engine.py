"""
rag_engine.py
============
Motor de Generación Aumentada por Recuperación (RAG) para EduBot.
Configura LangChain con Google Generative AI Embeddings, ChromaDB como base de datos
vectorial persistente y Gemini 1.5 Flash como modelo de lenguaje generativo.
"""

import os
import glob
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# Cargar variables de entorno desde archivo .env
load_dotenv(override=True)

# Constantes del Sistema RAG
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "chroma_db")
DOCS_DIR = os.getenv("DOCS_DIR", "docs")
DOCS_HELP = os.getenv("DOCS_HELP", "help")
EMBEDDINGS_MODEL = "models/gemini-embedding-001"
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")

# System Prompt Robusto para EduBot Coach #MejoroTuFuturo
SYSTEM_PROMPT = """Eres EduBot Coach #MejoroTuFuturo. Actúas como un mentor experto y un asesor integral enfocado en el desarrollo profesional, financiero y personal del usuario.

Tu sistema está calibrado para ejecutar los 14 módulos de análisis definidos, enfocándote en las siguientes áreas clave:

1. **Optimización de Empleabilidad**: Analizas el perfil frente a ofertas laborales, generas currículums optimizados (ATS-friendly) y calculas el porcentaje de ajuste, trazando un camino de desarrollo a corto, mediano y largo plazo.
2. **Decisiones Estratégicas**: Evalúas de manera exhaustiva y comparativa la viabilidad de mantener un empleo tradicional frente a iniciar un proyecto de emprendimiento, analizando ingresos proyectados, riesgos y costos de oportunidad.
3. **Salud y Calidad de Vida**: Estructuras menús mensuales costeados, rutinas de ejercicio adaptadas a la jornada, estrategias para prevenir el agotamiento mental y dinámicas para asegurar tiempo de calidad con la familia.
4. **Proyección Financiera**: Diseñas escenarios de ahorro, simulaciones de inversión para saldos positivos y estrategias de generación de ingresos extra para saldos negativos, orientados a metas concretas como la adquisición de bienes.

Tienes acceso a dos fuentes de conocimiento principales:
- **Documentación de Análisis e Inteligencia (`docs/`)**: Contiene informes, estudios técnicos, PDFs y guías sobre los cuales realizas análisis exhaustivos, resúmenes y respuestas especializadas.
- **Documentación de Soporte y Plataforma (`help/`)**: Contiene la base de conocimiento oficial de EduBot, preguntas frecuentes (FAQ), planes y precios, términos de uso y políticas de privacidad.

Directrices de respuesta:
1. **Precisión y Veracidad**: Responde utilizando como fuente primordial el CONTEXTO RECUPERADO a continuación.
2. **Manejo de Incertidumbre**: Si el contexto recuperado no contiene la información necesaria para responder con precisión, declara amablemente: "No encontré suficiente información en la documentación para responder a esta pregunta." NO inventes ni alucines datos.
3. **Formato Profesional**: Estructura tus respuestas utilizando Markdown limpio, resaltando conceptos clave en negrita, usando listas estructuradas y tablas/bloques de código cuando sea apropiado.
4. **Citación de Fuentes**: Cuando utilices información del contexto, menciona brevemente la fuente (nombre del archivo PDF o Markdown).
5. **Estilo de Comunicación**: Profesional, directo y fundamentado en la realidad, ofreciendo claridad estratégica y recomendaciones accionables que protejan tanto la economía como el bienestar integral del usuario.

---
CONTEXTO RECUPERADO:
{context}
---
"""


def get_embeddings(api_key: str = None) -> GoogleGenerativeAIEmbeddings:
    """
    Inicializa el cliente de Embeddings de Google Generative AI.
    
    Args:
        api_key (str, optional): Clave de API de Google Gemini.
    Returns:
        GoogleGenerativeAIEmbeddings: Instancia configurada para vectorización.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY no encontrada. Proporcione la clave en el archivo .env o en el sidebar.")
    return GoogleGenerativeAIEmbeddings(model=EMBEDDINGS_MODEL, google_api_key=key)


def load_documents_from_folder(folder_path: str, category: str = "general") -> List[Any]:
    """
    Lee recursivamente archivos (.pdf, .txt, .md) desde el directorio especificado.
    
    Args:
        folder_path (str): Ruta al directorio conteniendo los documentos.
        category (str): Categoria del documento (ej. 'inteligencia' o 'ayuda_planes').
    Returns:
        List[Document]: Lista de objetos Document de LangChain con metadata asignada.
    """
    documents = []
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
        return documents

    # Procesar archivos PDF
    pdf_files = glob.glob(os.path.join(folder_path, "**/*.pdf"), recursive=True)
    for pdf_path in pdf_files:
        try:
            loader = PyPDFLoader(pdf_path)
            loaded_docs = loader.load()
            for doc in loaded_docs:
                doc.metadata["category"] = category
            documents.extend(loaded_docs)
        except Exception as e:
            print(f"Error al cargar el archivo PDF {pdf_path}: {e}")

    # Procesar archivos de texto (.txt, .md)
    text_patterns = ["**/*.txt", "**/*.md"]
    for pattern in text_patterns:
        text_files = glob.glob(os.path.join(folder_path, pattern), recursive=True)
        for text_path in text_files:
            try:
                loader = TextLoader(text_path, encoding="utf-8")
                loaded_docs = loader.load()
                for doc in loaded_docs:
                    doc.metadata["category"] = category
                documents.extend(loaded_docs)
            except Exception as e:
                print(f"Error al cargar archivo de texto {text_path}: {e}")

    return documents


def vectorize_documents(
    docs_dir: str = DOCS_DIR,
    docs_help: str = DOCS_HELP,
    persist_dir: str = CHROMA_PERSIST_DIR,
    api_key: str = None
) -> Chroma:
    """
    Lee los documentos de DOCS_DIR (inteligencia) y DOCS_HELP (ayuda y planes),
    realiza la división en fragmentos (chunking) y almacena en ChromaDB.

    Args:
        docs_dir (str): Carpeta principal de conocimiento de EduBot.
        docs_help (str): Carpeta de ayuda, términos y planes.
        persist_dir (str): Carpeta de destino para ChromaDB.
        api_key (str): Clave de API para Gemini.
    Returns:
        Chroma: Instancia de la base vectorial Chroma inicializada.
    """
    # Cargar de carpeta de inteligencia principal
    documents_intel = load_documents_from_folder(docs_dir, category="inteligencia")
    # Cargar de carpeta de ayuda y planes
    documents_help = load_documents_from_folder(docs_help, category="ayuda_terminos_planes")
    
    all_documents = documents_intel + documents_help

    if not all_documents:
        raise ValueError(f"No se encontraron documentos en las carpetas '{docs_dir}' ni '{docs_help}'. Añada archivos para vectorizar.")

    # Dividir texto en fragmentos manejables (Chunks)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=150,
        length_function=len
    )
    chunks = text_splitter.split_documents(all_documents)

    embeddings = get_embeddings(api_key=api_key)

    # Crear la colección en ChromaDB insertando en lotes pequeños con pausas (evita 429 Rate Limit)
    import time
    batch_size = 25
    vectorstore = None

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        if vectorstore is None:
            vectorstore = Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                persist_directory=persist_dir
            )
        else:
            vectorstore.add_documents(batch)
        
        # Pausa ligera entre lotes para no exceder cuotas de la API de Gemini (Rate Limit 429)
        if i + batch_size < len(chunks):
            time.sleep(1.5)

    return vectorstore


def get_vectorstore(persist_dir: str = CHROMA_PERSIST_DIR, api_key: str = None) -> Chroma:
    """
    Carga la base de datos vectorial Chroma persistida en disco.

    Args:
        persist_dir (str): Directorio donde reside ChromaDB.
        api_key (str): Clave de API de Gemini.
    Returns:
        Chroma: Instancia cargada de la base vectorial.
    """
    embeddings = get_embeddings(api_key=api_key)
    return Chroma(persist_directory=persist_dir, embedding_function=embeddings)


def generate_response(
    query: str,
    chat_history: List[Dict[str, str]] = None,
    user_cv_text: str = None,
    user_emails_text: str = None,
    user_plan: str = "Premium 360",
    persist_dir: str = CHROMA_PERSIST_DIR,
    api_key: str = None,
    k: int = 4
) -> Tuple[str, List[Any]]:
    """
    Invoca el modelo Gemini utilizando el contexto recuperado de ChromaDB,
    el CV del usuario (si fue adjuntado), el plan activo y el System Prompt.

    Args:
        query (str): Pregunta planteada por el usuario.
        chat_history (List[Dict[str, str]], optional): Historial de conversación.
        user_cv_text (str, optional): Texto extraído del PDF del CV del usuario.
        user_emails_text (str, optional): Texto de correos extraídos.
        user_plan (str): Plan de suscripción activo ('Starter (Gratis)', 'Pro', 'Premium 360').
        persist_dir (str): Ruta de persistencia de Chroma.
        api_key (str): Clave de API de Gemini.
        k (int): Número de fragmentos relevantes a recuperar.
    Returns:
        Tuple[str, List[Document]]: Respuesta generada por el LLM y la lista de documentos de contexto recuperados.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY no encontrada.")

    # 1. Cargar Vectorstore y recuperar contexto
    vectorstore = get_vectorstore(persist_dir=persist_dir, api_key=key)
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    retrieved_docs = retriever.invoke(query)

    # 2. Formatear contexto recuperado de la base de conocimiento
    context_text = f"PLAN DE SUSCRIPCIÓN ACTIVO DEL USUARIO: {user_plan}\n\n"
    context_text += "\n\n".join([
        f"[Fuente: {doc.metadata.get('source', 'Documento Desconocido')}]\n{doc.page_content}"
        for doc in retrieved_docs
    ])

    # 3. Adjuntar información de restricciones según el Plan del usuario
    if "Starter" in user_plan:
        context_text += (
            "\n\n=========================================\n"
            "NIVEL DE ACCESO SEGÚN PLAN (STARTER - GRATIS $0/mes):\n"
            "- Módulos Desbloqueados: Módulo 1 (Optimización CV & Match Score, límite 3/mes) y Módulo 2 (Visión Estratégica y Proyección Salarial).\n"
            "- Módulos Bloqueados: Módulos 3 al 14 (Networking, Finanzas, Salud, Ejercicios, Autoemprendimiento y Simulador).\n"
            "- Nota: Si el usuario solicita un módulo bloqueado, responde amablemente indicando las limitaciones de su plan gratuito y sugiriendo actualizar a Pro ($9.99/mes) o Premium 360 ($19.99/mes).\n"
            "========================================="
        )
    elif "Pro" in user_plan and "Premium" not in user_plan:
        context_text += (
            "\n\n=========================================\n"
            "NIVEL DE ACCESO SEGÚN PLAN (PRO - $9.99/mes):\n"
            "- Módulos Desbloqueados: Módulos 1 al 9 (Networking, Benchmark Internacional, Radar Laboral, Finanzas & Futuro, Gamificación) + Módulo 14 (Simulador Emprendimiento vs Empleo Limitado) + Reportes PDF.\n"
            "- Módulos Bloqueados: Módulos 10 y 11 (Rutinas de Alimentación, Ejercicio y Cohesión Familiar) y Módulos 12 y 13 (Inversión Avanzada Saldo Positivo y Autoemprendimiento).\n"
            "- Nota: Si el usuario solicita un módulo de salud/alimentación (10-11) o inversión avanzada (12-13), sugiere amablemente desbloquear el Plan Premium 360 ($19.99/mes).\n"
            "========================================="
        )
    else:  # Premium 360
        context_text += (
            "\n\n=========================================\n"
            "NIVEL DE ACCESO SEGÚN PLAN (PREMIUM 360 - $19.99/mes):\n"
            "- Acceso Total Ilimitado a los 14 Módulos de EduBot Coach (Empleabilidad, Finanzas, Salud, Nutrición, Ejercicios, Cohesión Familiar, Inversiones Avanzadas, Autoemprendimiento y Simulador 360).\n"
            "========================================="
        )

    # 4. Adjuntar el CV del usuario al contexto si está disponible
    if user_cv_text:
        context_text += (
            "\n\n=========================================\n"
            "📄 CURRÍCULUM VITAE DEL USUARIO (ADJUNTADO POR EL USUARIO EN PDF):\n"
            f"{user_cv_text}\n"
            "========================================="
        )

    # 5. Adjuntar los correos del usuario si están disponibles
    if user_emails_text:
        context_text += (
            "\n\n=========================================\n"
            "📬 CORREOS ELECTRÓNICOS DEL USUARIO (RECUPERADOS DESDE SU BANDEJA DE ENTRADA):\n"
            f"{user_emails_text}\n"
            "========================================="
        )

    # 3. Construir lista de mensajes para el modelo conversacional
    system_message_content = SYSTEM_PROMPT.format(context=context_text)
    messages = [SystemMessage(content=system_message_content)]

    # 4. Incluir el historial de chat si existe (últimos N intercambios para no desbordar)
    if chat_history:
        for msg in chat_history[-6:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

    # 5. Agregar la pregunta actual del usuario
    messages.append(HumanMessage(content=query))

    # 6. Inicializar modelo LLM gemini-1.5-flash
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        google_api_key=key,
        temperature=0.3
    )

    # 7. Invocar al LLM
    response = llm.invoke(messages)

    return response.content, retrieved_docs
