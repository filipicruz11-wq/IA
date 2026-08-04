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

    /* Estilo dos Botões */
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

    /* Caixa do Documento Gerado */
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
    "1": """Você é um assistente especialista na redação de RELATOS DE CASOS para o CEJUSC.
    REGRAS DE SAÍDA E FORMATAÇÃO:
    - Retorne APENAS o texto final do relato. NÃO inclua saudações, explicações, metadados ou tópicos informando as correções feitas.
    - NÃO use símbolos de markdown como asteriscos (** ou *) para negrito. Devolva texto limpo pronto para colar em editores oficiais.
    - OBRIGATÓRIO: Mantenha ou utilize sempre as nomenclaturas Reclamante(s) e Reclamado(a)(s). NUNCA substitua por Requerente(s) ou Requerido(a)(s).
    - INSTRUÇÃO DE MODELO: Analise o Banco de Dados de Modelos Oficiais fornecido abaixo. Se o caso trazido pelo usuário se encaixar em algum deles, utilize a estrutura daquele modelo preenchendo-o com os dados concretos fornecidos. Caso nenhum modelo do arquivo se adeque perfeitamente, faça a estruturação, correção e adequação livre do relato de forma impecável.
    - Mantenha integralmente todos os nomes, datas, valores, endereços e matrículas.
    - Organize débitos/bens em listas alfabéticas (a, b, c).""",
    
    "2": """Você é um assistente especializado na redação de CERTIDÕES PROCESSUAIS para o CEJUSC. Retorne APENAS o texto formal sem asteriscos. Finalize rigorosamente com a expressão: 'CERTIFICO e dou fé.'""",
    "3": """Você é um assistente especializado na redação de MINUTAS DE SENTENÇA E HOMOLOGAÇÕES para o CEJUSC. Retorne APENAS o texto final da minuta sem asteriscos. Utilize a estrutura formal (Relatório, Fundamentação e Dispositivo). Para homologação de acordo, utilize o Art. 487, III, 'b' do CPC.""",
    "4": """Você é um assistente especializado na redação de DESPACHOS E DECISÕES INTERLOCUTÓRIAS para o CEJUSC. Retorne APENAS a minuta final sem asteriscos.""",
    "5": """Você é um assistente especializado em REDAÇÃO DE E-MAILS INSTITUCIONAIS para o CEJUSC. Retorne APENAS o e-mail pronto para envio sem asteriscos.""",
    "6": """Você é um assistente especializado em NOTIFICAÇÕES VIA WHATSAPP para o CEJUSC. Retorne APENAS a mensagem. UTILIZE A SINTAXE DO WHATSAPP (*texto em negrito*, _texto em itálico_).""",
    "7": """Você é um assistente especialista de consulta e esclarecimento de DÚVIDAS GERAIS.""",
    "8": """Você é um assistente especializado na redação e estruturação de TERMOS DE AUDIÊNCIA para o CEJUSC. Retorne APENAS o texto formal do termo sem asteriscos.""",
    "9": """Você é um revisor de textos. Corrija a gramática e clareza preservando o estilo original.""",
    "10": """Você é um assistente objetivo para consulta rápida de documentos no atendimento do CEJUSC."""
}

def transcrever_audio(audio_bytes, mime_type):
    """Função exclusiva para converter o áudio falado em texto."""
    audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
    prompt = "Transcreva com máxima fidelidade o áudio a seguir para texto. Retorne APENAS a transcrição exata das palavras faladas, sem explicações ou comentários."
    
    modelos = ["gemini-flash-latest", "gemini-2.0-flash-lite", "gemini-flash-lite-latest"]
    for modelo in modelos:
        try:
            response = client.models.generate_content(model=modelo, contents=[prompt, audio_part])
            return response.text.strip()
        except errors.APIError:
            time.sleep(2)
    raise Exception("Não foi possível transcrever o áudio no momento.")

def processar_com_gemini(texto_bruto, opcao_menu):
    """Função que gera o documento jurídico baseado no texto de entrada."""
    prompt_sistema = PROMPTS.get(opcao_menu, PROMPTS["1"])
    
    if opcao_menu == "1":
        conteudo_banco = carregar_arquivo_texto(ARQUIVO_BANCO_MODELOS)
        prompt_completo = f"{prompt_sistema}\n\nBANCO DE DADOS DE MODELOS (ARQUIVO EXTERNO):\n{conteudo_banco}\n\nPEDIDO OU RELATO DO CASO FORNECIDO PELO USUÁRIO:\n{texto_bruto}"
    elif opcao_menu == "8":
        conteudo_termos = carregar_arquivo_texto(ARQUIVO_BANCO_TERMOS)
        prompt_completo = f"{prompt_sistema}\n\nBANCO DE DADOS DE TERMOS (ARQUIVO EXTERNO):\n{conteudo_termos}\n\nDADOS DA AUDIÊNCIA OU CASO FORNECIDO PELO USUÁRIO:\n{texto_bruto}"
    elif opcao_menu in ["7", "10"]:
        prompt_completo = f"{prompt_sistema}\n\nCASO OU DÚVIDA INFORMADA:\n{texto_bruto}"
    else:
        prompt_completo = f"{prompt_sistema}\n\nTEXTO BRUTO A SER PROCESSADO:\n{texto_bruto}"

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

    # Inicialização do estado de memória para o texto digitado/transcrito
    if "texto_entrada" not in st.session_state:
        st.session_state.texto_entrada = ""

    # Área de gravação de áudio opcional
    audio_usuario = st.audio_input("🎙️ Gravar relato falado (Opcional):")
    
    if audio_usuario is not None:
        if st.button("📝 Converter Áudio em Texto"):
            with st.spinner("Transcrevendo áudio para o campo de texto..."):
                try:
                    transcricao = transcrever_audio(audio_usuario.read(), audio_usuario.type)
                    # Adiciona ou atualiza o texto na caixa de entrada
                    if st.session_state.texto_entrada.strip():
                        st.session_state.texto_entrada += f"\n{transcricao}"
                    else:
                        st.session_state.texto_entrada = transcricao
                    st.success("Áudio transcrito com sucesso! Verifique o texto abaixo.")
                except Exception as e:
                    st.error(f"Erro na transcrição: {e}")

    # Campo de Texto que recebe o ditado ou a digitação direta
    st.session_state.texto_entrada = st.text_area(
        "Insira ou edite as informações do atendimento/rascunho abaixo:",
        value=st.session_state.texto_entrada,
        height=260,
        placeholder="Digite o relato aqui ou grave um áudio acima para transcrever..."
    )

    btn_processar = st.button("✨ Gerar Documento Jurídico", type="primary")

with col_direita:
    st.subheader("📄 Documento Gerado")
    
    if "resultado_texto" not in st.session_state:
        st.session_state.resultado_texto = ""

    if btn_processar:
        if not st.session_state.texto_entrada.strip():
            st.warning("⚠️ Insira ou transcreva um texto nos Dados de Entrada antes de gerar.")
        else:
            with st.spinner("Estruturando o documento jurídico com base nas normas do CEJUSC..."):
                try:
                    st.session_state.resultado_texto = processar_com_gemini(st.session_state.texto_entrada, opcao)
                except Exception as e:
                    st.error(f"Erro ao processar: {e}")

    st.text_area(
        "Documento Gerado:",
        value=st.session_state.resultado_texto,
        height=400,
        placeholder="O documento pronto para cópia aparecerá aqui..."
    )
