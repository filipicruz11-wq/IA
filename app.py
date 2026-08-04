import time
import os
import streamlit as st
from google import genai
from google.genai import errors, types

# Configuração da página
st.set_page_config(
    page_title="IA DO CEJUSC", 
    page_icon="⚖️", 
    layout="wide"
)

# Estilização CSS Profissional
st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC; }
    
    .header-container {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .header-title {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        color: #FFFFFF !important;
    }
    .header-subtitle {
        font-size: 0.95rem;
        color: #93C5FD;
        margin-top: 4px;
    }

    .stSelectbox label, .stTextArea label, .stAudioInput label, .stRadio label {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        color: #1E293B !important;
    }

    .stTextArea textarea {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
        font-size: 0.95rem !important;
        color: #0F172A !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.5rem !important;
        width: 100% !important;
    }

    /* Caixa única estilizada do Documento Gerado */
    div[data-testid="stTextArea"] textarea[aria-label="Documento Gerado:"] {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-left: 6px solid #2563EB !important;
        border-radius: 8px !important;
        font-family: 'Georgia', 'Times New Roman', serif !important;
        font-size: 1.05rem !important;
        line-height: 1.7 !important;
        color: #0F172A !important;
    }

    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Chave API
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    try:
        API_KEY = st.secrets["GEMINI_API_KEY"]
    except Exception:
        API_KEY = None

if not API_KEY:
    st.error("⚠️ A chave GEMINI_API_KEY não foi encontrada.")
    st.stop()

client = genai.Client(api_key=API_KEY)

ARQUIVO_BANCO_MODELOS = "BANCO DE DADOS OBJETOS.txt"
ARQUIVO_BANCO_TERMOS = "BANCO DE DADOS TERMOS.txt"

def carregar_arquivo_texto(nome_arquivo):
    diretorios = [os.getcwd(), os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()]
    for pasta in diretorios:
        caminho_direto = os.path.join(pasta, nome_arquivo)
        if os.path.exists(caminho_direto):
            try:
                with open(caminho_direto, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception as e:
                return f"[Erro ao ler {nome_arquivo}: {e}]"
    return f"[Aviso: O arquivo '{nome_arquivo}' não foi encontrado.]"

PROMPTS = {
    "1": """Você é um assistente especialista na redação de RELATOS DE CASOS para o CEJUSC. Retorne APENAS o texto final do relato sem símbolos markdown (como asteriscos). Mantenha sempre a nomenclatura Reclamante(s) e Reclamado(a)(s).""",
    "2": """Você é um assistente especializado na redação de CERTIDÕES PROCESSUAIS para o CEJUSC. Finalize rigorosamente com 'CERTIFICO e dou fé.'""",
    "3": """Você é um assistente especializado em MINUTAS DE SENTENÇA E HOMOLOGAÇÕES para o CEJUSC.""",
    "4": """Você é um assistente especializado na redação de DESPACHOS E DECISÕES INTERLOCUTÓRIAS para o CEJUSC.""",
    "5": """Você é um assistente especializado em REDAÇÃO DE E-MAILS INSTITUCIONAIS para o CEJUSC.""",
    "6": """Você é um assistente especializado em NOTIFICAÇÕES VIA WHATSAPP para o CEJUSC.""",
    "7": """Você é um assistente especialista de consulta e esclarecimento de DÚVIDAS GERAIS.""",
    "8": """Você é um assistente especializado na redação e estruturação de TERMOS DE AUDIÊNCIA para o CEJUSC.""",
    "9": """Você é um revisor de textos. Corrija a gramática e clareza preservando o estilo original.""",
    "10": """Você é um assistente objetivo para consulta rápida de documentos no atendimento do CEJUSC."""
}

def processar_com_gemini(conteudo_entrada, opcao_menu, eh_audio=False):
    prompt_sistema = PROMPTS.get(opcao_menu, PROMPTS["1"])
    
    if eh_audio:
        # Formatação correta para envio de áudio no SDK google-genai
        audio_part = types.Part.from_bytes(
            data=conteudo_entrada["data"],
            mime_type=conteudo_entrada["mime_type"]
        )
        prompt_completo = [
            f"{prompt_sistema}\n\nINSTRUÇÃO: Escute o áudio gravado e extraia/estruture as informações para gerar o documento solicitado.",
            audio_part
        ]
    else:
        if opcao_menu == "1":
            conteudo_banco = carregar_arquivo_texto(ARQUIVO_BANCO_MODELOS)
            prompt_completo = f"{prompt_sistema}\n\nBANCO DE DADOS DE MODELOS:\n{conteudo_banco}\n\nPEDIDO/RELATO:\n{conteudo_entrada}"
        elif opcao_menu == "8":
            conteudo_termos = carregar_arquivo_texto(ARQUIVO_BANCO_TERMOS)
            prompt_completo = f"{prompt_sistema}\n\nBANCO DE DADOS DE TERMOS:\n{conteudo_termos}\n\nDADOS DA AUDIÊNCIA:\n{conteudo_entrada}"
        else:
            prompt_completo = f"{prompt_sistema}\n\nTEXTO FORNECIDO:\n{conteudo_entrada}"

    modelos = ["gemini-flash-latest", "gemini-2.0-flash-lite", "gemini-flash-lite-latest"]
    for modelo in modelos:
        try:
            response = client.models.generate_content(model=modelo, contents=prompt_completo)
            return response.text
        except errors.APIError:
            time.sleep(2)
    raise Exception("Servidores indisponíveis no momento. Tente novamente.")

# Topo
st.markdown("""
    <div class="header-container">
        <div class="header-title">⚖️ IA DO CEJUSC</div>
        <div class="header-subtitle">Plataforma Inteligente de Redação e Padronização Jurídica Pré-Processual</div>
    </div>
""", unsafe_allow_html=True)

col_esquerda, col_direita = st.columns([1, 1], gap="large")

with col_esquerda:
    st.subheader("📝 Dados de Entrada")
    
    opcao_escolhida = st.selectbox(
        "Selecione o tipo de documento a ser gerado:",
        (
            "1 - Relato de Caso", "2 - Certidão Processual", "3 - Sentença / Homologação de Acordo",
            "4 - Despacho / Decisão", "5 - E-mail Institucional", "6 - Mensagem para WhatsApp",
            "7 - Dúvidas Gerais", "8 - Termo de Audiência", "9 - Correção de Redação", "10 - Orientações de Documentos"
        )
    )
    opcao = opcao_escolhida.split(" - ")[0]

    # Alternância entre Texto e Áudio
    tipo_entrada = st.radio("Como prefere informar o caso?", ["✍️ Digitar Texto", "🎙️ Gravar Áudio"], horizontal=True)

    texto_usuario = ""
    audio_usuario = None

    if tipo_entrada == "✍️ Digitar Texto":
        texto_usuario = st.text_area(
            "Insira as informações do atendimento ou rascunho abaixo:",
            height=260,
            placeholder="Exemplo: Reclamante relata que a parte Reclamada atrasou o aluguel..."
        )
    else:
        audio_usuario = st.audio_input("Clique no microfone abaixo para gravar o relato:")

    btn_processar = st.button("✨ Gerar Documento Jurídico", type="primary")

with col_direita:
    st.subheader("📄 Documento Gerado")
    
    if "resultado_texto" not in st.session_state:
        st.session_state.resultado_texto = ""

    if btn_processar:
        if tipo_entrada == "✍️ Digitar Texto" and not texto_usuario.strip():
            st.warning("⚠️ Digite o relato antes de gerar.")
        elif tipo_entrada == "🎙️ Gravar Áudio" and audio_usuario is None:
            st.warning("⚠️ Grave um áudio antes de clicar em gerar.")
        else:
            with st.spinner("Escutando/Processando informações e redigindo o documento..."):
                try:
                    if tipo_entrada == "🎙️ Gravar Áudio":
                        audio_bytes = audio_usuario.read()
                        st.session_state.resultado_texto = processar_com_gemini(
                            {"mime_type": audio_usuario.type, "data": audio_bytes}, 
                            opcao, 
                            eh_audio=True
                        )
                    else:
                        st.session_state.resultado_texto = processar_com_gemini(texto_usuario, opcao, eh_audio=False)
                except Exception as e:
                    st.error(f"Erro ao processar: {e}")

    st.text_area(
        "Documento Gerado:",
        value=st.session_state.resultado_texto,
        height=400,
        placeholder="O documento pronto para cópia aparecerá aqui..."
    )
