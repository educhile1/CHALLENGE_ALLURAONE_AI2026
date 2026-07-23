"""
app.py
======
Interfaz Web interactiva en Streamlit para EduBot (Agente RAG Profesional).
Gestiona la autenticación con GEMINI_API_KEY, permite indexar la base de conocimientos `docs/`,
mantiene la sesión de chat y despliega el contexto recuperado de ChromaDB.
"""

import os
import streamlit as st
from dotenv import load_dotenv

# Cargar variables del archivo .env local
load_dotenv(override=True)

import rag_engine

# -----------------------------------------------------------------------------
# Configuración Principal de la Página de Streamlit
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="EduBot - Asistente RAG Profesional",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS Personalizados para una apariencia profesional y moderna
st.markdown("""
<style>
    /* Estilos globales */
    .main {
        background-color: #0e1117;
    }
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    /* Estilo del Encabezado */
    .header-container {
        padding: 1.5rem 0rem;
        border-bottom: 1px solid #1e293b;
        margin-bottom: 2rem;
    }
    .header-title {
        color: #f8fafc;
        font-weight: 700;
        font-size: 2.2rem;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    .header-subtitle {
        color: #94a3b8;
        font-size: 1rem;
        margin-top: 0.4rem;
    }
    /* Tarjetas de fuentes recuperadas */
    .source-box {
        background-color: #1e293b;
        border-left: 4px solid #3b82f6;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        border-radius: 4px;
        font-size: 0.88rem;
        color: #cbd5e1;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Control de Autenticación y Roles por Plan (Starter, Pro, Premium 360)
# -----------------------------------------------------------------------------
USER_ACCOUNTS = {
    os.getenv("ADMIN_USER", "admin"): {
        "pass": os.getenv("ADMIN_PASS", "edubot2026"),
        "role": "Premium 360 ($19.99/mes)",
        "badge": "⭐ Plan Premium 360 (100% Ilimitado - 14 Módulos)"
    },
    os.getenv("PRO_USER", "pro_user"): {
        "pass": os.getenv("PRO_PASS", "pro2026"),
        "role": "Pro ($9.99/mes)",
        "badge": "🚀 Plan Pro (Módulos 1-9, M14 + Reportes PDF)"
    },
    os.getenv("STARTER_USER", "starter"): {
        "pass": os.getenv("STARTER_PASS", "free2026"),
        "role": "Starter (Gratis)",
        "badge": "🌱 Plan Starter (Gratis - Módulos 1 y 2)"
    }
}

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("""
    <div style="max-width: 500px; margin: 2rem auto 1.5rem auto; padding: 2rem; background-color: #1e293b; border-radius: 12px; border: 1px solid #334155; text-align: center;">
        <h2 style="color: #f8fafc; margin: 0;">🤖 EduBot Coach</h2>
        <p style="color: #94a3b8; font-size: 0.95rem; margin-top: 0.5rem;">#MejoroTuFuturo | Acceso Seguro según Plan de Suscripción</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        with st.form("login_form"):
            st.markdown("### 🔐 Acceso al Sistema")
            input_user = st.text_input("👤 Usuario:", placeholder="ej. admin, pro_user, starter")
            input_pass = st.text_input("🔑 Contraseña:", type="password", placeholder="••••••••")
            submit_login = st.form_submit_button("🔓 Iniciar Sesión", use_container_width=True, type="primary")
            
            if submit_login:
                u_clean = input_user.strip()
                p_clean = input_pass.strip()
                
                if u_clean in USER_ACCOUNTS and USER_ACCOUNTS[u_clean]["pass"] == p_clean:
                    st.session_state.authenticated = True
                    st.session_state.logged_user = u_clean
                    st.session_state.user_plan = USER_ACCOUNTS[u_clean]["role"]
                    st.session_state.user_badge = USER_ACCOUNTS[u_clean]["badge"]
                    st.success(f" Acceso concedido como {USER_ACCOUNTS[u_clean]['role']}. Redirigiendo...")
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos.")
    
    st.markdown("""
    <div style="max-width: 550px; margin: 1rem auto; padding: 1rem; background-color: #0f172a; border-radius: 8px; border: 1px solid #1e293b; font-size: 0.85rem; color: #94a3b8;">
        <b>🔑 Usuarios y Roles Disponibles para Pruebas:</b><br>
        • <b>Premium 360 ($19.99/mes):</b> usuario: <code>admin</code> | clave: <code>edubot2026</code><br>
        • <b>Plan Pro ($9.99/mes):</b> usuario: <code>pro_user</code> | clave: <code>pro2026</code><br>
        • <b>Plan Starter (Gratis):</b> usuario: <code>starter</code> | clave: <code>free2026</code>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# -----------------------------------------------------------------------------
# Gestión del Estado de Sesión (Session State)
# -----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "¡Hola! Soy tu **EduBot Coach #MejoroTuFuturo**. Actúo como tu mentor experto y asesor integral en optimización de empleabilidad, decisiones estratégicas, salud y proyección financiera. ¿En qué te puedo ayudar hoy?"
        }
    ]

if "vectorstore_ready" not in st.session_state:
    # Comprobar si ya existe la carpeta de persistencia chroma_db con contenido
    st.session_state.vectorstore_ready = os.path.exists(rag_engine.CHROMA_PERSIST_DIR) and len(os.listdir(rag_engine.CHROMA_PERSIST_DIR)) > 0


# -----------------------------------------------------------------------------
# Barra Lateral (Sidebar) - Configuración y Control
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("🤖 EduBot Panel")
    st.caption(f"Sesión Activa: 👤 **{st.session_state.get('logged_user', 'Usuario')}**")
    st.info(f"{st.session_state.get('user_badge', '⭐ Plan Activo')}", icon="🛡️")
    
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

    st.divider()

    # 1. Validación de Clave de API GEMINI_API_KEY
    raw_key = os.getenv("GEMINI_API_KEY", "").strip()
    is_placeholder = not raw_key or "tu_google_gemini_api_key" in raw_key.lower() or "tu_clave" in raw_key.lower() or "your_gemini_api_key" in raw_key.lower()
    
    if not is_placeholder:
        api_key = raw_key
        st.success("✅ GEMINI_API_KEY válida detectada en .env", icon="🔑")
    else:
        st.warning("⚠️ Proporcione una GEMINI_API_KEY válida de Google AI Studio.", icon="🚨")
        api_key = st.text_input("Ingrese su Google Gemini API Key:", type="password", help="Obténgala gratuitamente en Google AI Studio (aistudio.google.com).")
    
    st.divider()

    # 2. Gestión de la Base de Datos Vectorial
    st.subheader("📚 Base de Conocimiento")
    st.info(f"🧠 Inteligencia: `{rag_engine.DOCS_DIR}/`\n\nℹ️ Ayuda & Planes: `{rag_engine.DOCS_HELP}/`", icon="📁")
    
    if st.session_state.vectorstore_ready:
        st.success(" Base de datos ChromaDB activa.", icon="⚡")
    else:
        st.error(" Base de datos ChromaDB no indexada.", icon="❌")

    # Botón para Vectorizar / Re-indexar Documentos
    if st.button("🔄 Vectorizar / Re-indexar Docs", use_container_width=True, type="primary"):
        if not api_key:
            st.error("Por favor, proporcione una GEMINI_API_KEY válida para generar los embeddings.")
        else:
            with st.spinner("Procesando documentos y vectorizando en ChromaDB..."):
                try:
                    vectorstore = rag_engine.vectorize_documents(api_key=api_key)
                    st.session_state.vectorstore_ready = True
                    st.success("¡Vectorización completada exitosamente!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error durante la vectorización: {str(e)}")

    st.divider()
    
    # Botón para Limpiar Historial de Chat
    if st.button("🗑️ Limpiar Conversación", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Historial reiniciado. ¿En qué puedo ayudarte?"
            }
        ]
        st.rerun()

    st.caption("EduBot Architecture v1.0 | Gemini 1.5 Flash + ChromaDB")


# -----------------------------------------------------------------------------
# Cuerpo Principal de la Aplicación
# -----------------------------------------------------------------------------
# Encabezado del Chat
st.markdown("""
<div class="header-container">
    <div class="header-title">
        <span>🤖</span> <span>EduBot Coach</span>
    </div>
    <div class="header-subtitle">
        Mentor e Inteligencia Corporativa #MejoroTuFuturo
    </div>
</div>
""", unsafe_allow_html=True)

# Sección de Adjuntos en el Chat Principal (PDF de CV)
cv_container = st.container()
with cv_container:
    col_upload, col_status = st.columns([1, 2])
    with col_upload:
        with st.popover("📎 Adjuntar CV (PDF)", use_container_width=True):
            uploaded_cv = st.file_uploader(
                "Sube tu archivo CV en PDF:",
                type=["pdf"],
                key="main_chat_cv_uploader",
                help="EduBot analizará tu CV para optimización de empleabilidad y compatibilidad ATS."
            )
    
    user_cv_text = None
    if uploaded_cv is not None:
        try:
            from pypdf import PdfReader
            pdf_reader = PdfReader(uploaded_cv)
            extracted_pages = [page.extract_text() for page in pdf_reader.pages if page.extract_text()]
            if extracted_pages:
                user_cv_text = "\n".join(extracted_pages)
                with col_status:
                    st.success(f" CV listo: `{uploaded_cv.name}` ({len(pdf_reader.pages)} pág.)", icon="📑")
            else:
                with col_status:
                    st.warning("⚠️ No se pudo extraer texto del PDF.")
        except Exception as e:
            with col_status:
                st.error(f"Error al leer el PDF: {e}")

st.divider()

# Desplegar Historial de Mensajes
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Mostrar fuentes de contexto si existen en la respuesta del asistente
        if "sources" in message and message["sources"]:
            with st.expander("📚 Fuentes y Contexto Recuperado (RAG)", expanded=False):
                for idx, doc in enumerate(message["sources"], start=1):
                    source_name = doc.metadata.get("source", "Documento")
                    page = f" (Pág. {doc.metadata.get('page') + 1})" if "page" in doc.metadata else ""
                    st.markdown(f"**Fuente #{idx}:** `{source_name}{page}`")
                    st.markdown(f"> {doc.page_content[:300]}...")


# Captura de Preguntas del Usuario
if prompt := st.chat_input("Escribe tu pregunta o consulta técnica sobre los documentos..."):
    
    # 1. Validar Clave de API
    if not api_key:
        st.error(" No se puede procesar la solicitud sin una `GEMINI_API_KEY`. Ingrésala en la barra lateral.")
        st.stop()

    # 2. Validar que la Base Vectorial esté Lista
    if not st.session_state.vectorstore_ready:
        st.warning("⚠️ La base de datos vectorial aún no se ha generado. Haz clic en **'🔄 Vectorizar / Re-indexar Docs'** en la barra lateral antes de consultar.")
        # Agregar mensaje del usuario al chat de todas formas
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Por favor, ejecuta la vectorización de la carpeta `docs/` en la barra lateral para inicializar mi base de conocimientos."
        })
        st.rerun()

    # 3. Mostrar la pregunta del usuario en la interfaz
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 4. Generar Respuesta con el Motor RAG
    with st.chat_message("assistant"):
        with st.spinner("Buscando en la base de conocimientos y generando respuesta con Gemini 1.5 Flash..."):
            try:
                answer, sources = rag_engine.generate_response(
                    query=prompt,
                    chat_history=st.session_state.messages[:-1],
                    user_cv_text=user_cv_text,
                    user_plan=st.session_state.get("user_plan", "Premium 360"),
                    api_key=api_key
                )
                
                # Desplegar respuesta
                st.markdown(answer)
                
                # Mostrar fuentes en un expander si existen
                if sources:
                    with st.expander("📚 Fuentes y Contexto Recuperado (RAG)", expanded=False):
                        for idx, doc in enumerate(sources, start=1):
                            source_name = doc.metadata.get("source", "Documento")
                            page = f" (Pág. {doc.metadata.get('page') + 1})" if "page" in doc.metadata else ""
                            st.markdown(f"**Fuente #{idx}:** `{source_name}{page}`")
                            st.markdown(f"> {doc.page_content[:300]}...")

                # Guardar respuesta y fuentes en la sesión
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources
                })

            except Exception as e:
                error_msg = f" Ocurrió un error al procesar tu solicitud: `{str(e)}`"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
