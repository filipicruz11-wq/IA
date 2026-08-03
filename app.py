import time
import os
import streamlit as st
from google import genai
from google.genai import errors

# Configuração da página do Streamlit para ocupar a LARGURA TOTAL (wide)
st.set_page_config(
    page_title="IA DO CEJUSC", 
    page_icon="⚖️", 
    layout="wide"
)

# Estilização CSS personalizada para um visual moderno e fluido
st.markdown("""
    <style>
    /* Estilização do cabeçalho principal */
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.5rem;
    }
    
    .sub-header {
        font-size: 1rem;
        color: #4B5563;
        margin-bottom: 2rem;
    }

    /* Ajuste para justificativa e expansão do texto retornado */
    textarea {
        font-size: 0.95rem !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        line-height: 1.6 !important;
        text-align: justify !important;
    }

    /* Melhora visual dos botões */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: 600;
        font-size: 1rem;
    }

    /* Espaçamento elegante das seções */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }
    </style>
""", unsafe_allow_html=True)

# Captura segura da Chave de API
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    try:
        API_KEY = st.secrets["GEMINI_API_KEY"]
    except Exception:
        API_KEY = None

if not API_KEY:
    st.error("⚠️ A chave GEMINI_API_KEY não foi encontrada. Configure-a na aba Environment do Render.")
    st.stop()

# Inicialização do cliente oficial
client = genai.Client(api_key=API_KEY)

# Nomes dos arquivos de texto externos contendo os modelos
ARQUIVO_BANCO_MODELOS = "BANCO DE DADOS OBJETOS.txt"
ARQUIVO_BANCO_TERMOS = "BANCO DE DADOS TERMOS.txt"

def carregar_arquivo_texto(nome_arquivo):
    """Procura e lê os arquivos .txt testando maiúsculas/minúsculas e pastas no Linux do Render."""
    diretorios = [
        os.getcwd(),
        os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd(),
    ]
    
    for pasta in diretorios:
        caminho_direto = os.path.join(pasta, nome_arquivo)
        if os.path.exists(caminho_direto):
            try:
                with open(caminho_direto, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception as e:
                return f"[Aviso: Erro ao ler {nome_arquivo}: {e}]"
        
        if os.path.exists(pasta):
            for arq in os.listdir(pasta):
                if arq.lower() == nome_arquivo.lower():
                    try:
                        with open(os.path.join(pasta, arq), "r", encoding="utf-8", errors="ignore") as f:
                            return f.read()
                    except Exception as e:
                        return f"[Aviso: Erro ao ler {arq}: {e}]"

    return f"[Aviso: O arquivo '{nome_arquivo}' não foi encontrado na pasta.]"

# Prompts estruturados para o CEJUSC (Fase Pré-processual)
PROMPTS = {
    "1": """
    Você é um assistente especialista na redação de RELATOS DE CASOS para o CEJUSC.
    REGRAS DE SAÍDA E FORMATAÇÃO:
    - Retorne APENAS o texto final do relato. NÃO inclua saudações, explicações, metadados ou tópicos informando as correções feitas.
    - NÃO use símbolos de markdown como asteriscos (** ou *) para negrito. Devolva texto limpo pronto para colar em editores oficiais.
    - OBRIGATÓRIO: Mantenha ou utilize sempre as nomenclaturas Reclamante(s) e Reclamado(a)(s). NUNCA substitua por Requerente(s) ou Requerido(a)(s).
    - INSTRUÇÃO DE MODELO: Analise o Banco de Dados de Modelos Oficiais fornecido abaixo. Se o caso trazido pelo usuário se encaixar em algum deles, utilize a estrutura daquele modelo preenchendo-o com os dados concretos fornecidos. Caso nenhum modelo do arquivo se adeque perfeitamente, faça a estruturação, correção e adequação livre do relato de forma impecável.
    - Mantenha integralmente todos os nomes, datas, valores, endereços e matrículas.
    - Organize débitos/bens em listas alfabéticas (a, b, c).
    """,
    
    "2": """
    Você é um assistente especializado na redação de CERTIDÕES PROCESSUAIS para o CEJUSC.
    REGRAS DE SAÍDA E FORMATAÇÃO:
    - Retorne APENAS o texto formal da certidão processual, pronto para inserção nos autos.
    - NÃO use símbolos de markdown como asteriscos (** ou *). Devolva texto limpo.
    - OBRIGATÓRIO: Utilize estritamente as nomenclaturas Reclamante(s) e Reclamado(a)(s). Proibida a alteração para Requerente/Requerido.
    - NÃO inclua introduções, explicações ou notas adicionais.
    - Mantenha datas, prazos, nomes e documentos informados.
    - Finalize rigorosamente com a expressão: "CERTIFICO e dou fé."
    """,
    
    "3": """
    Você é um assistente especializado na redação de MINUTAS DE SENTENÇA E HOMOLOGAÇÕES para o CEJUSC.
    REGRAS DE SAÍDA E FORMATAÇÃO:
    - Retorne APENAS o texto final da minuta de sentença/homologação de acordo.
    - NÃO use símbolos de markdown como asteriscos (** ou *). Devolva texto limpo para o editor oficial.
    - OBRIGATÓRIO: Utilize rigorosamente os termos Reclamante(s) e Reclamado(a)(s). Não use Requerente ou Requerido.
    - NÃO inclua mensagens da IA ou notas explicativas no final.
    - Utilize a estrutura formal (Relatório sucinto, Fundamentação e Dispositivo).
    - Para homologação de acordo, utilize o Art. 487, III, 'b' do CPC como base legal.
    """,
    
    "4": """
    Você é um assistente especializado na redação de DESPACHOS E DECISÕES INTERLOCUTÓRIAS para o CEJUSC.
    REGRAS DE SAÍDA E FORMATAÇÃO:
    - Retorne APENAS a minuta final do despacho/decisão pronta para o magistrado assinar.
    - NÃO use símbolos de markdown como asteriscos (** ou *). Devolva texto limpo.
    - OBRIGATÓRIO: Mantenha sempre as nomenclaturas Reclamante(s) e Reclamado(a)(s). NUNCA utilize Requerente ou Requerido.
    - NÃO adicione saudações ou explicações da IA.
    - Mantenha tom imperativo e estrutura clara de determinações (1. Designe-se pauta; 2. Intimem-se...).
    """,
    
    "5": """
    Você é um assistente especializado em REDAÇÃO DE E-MAILS INSTITUCIONAIS para o CEJUSC.
    REGRAS DE SAÍDA E FORMATAÇÃO:
    - Retorne APENAS o e-mail pronto para cópia e envio.
    - NÃO use símbolos de markdown como asteriscos (** ou *).
    - OBRIGATÓRIO: Utilize as nomenclaturas corretas Reclamante(s) e Reclamado(a)(s).
    - NÃO use rótulos como "ASSUNTO:", "VOCATIVO FORMAL:", "CORPO DO TEXTO:" ou "ASSINATURA INSTITUCIONAL:".
    - Na primeira linha do texto gerado, escreva diretamente: Assunto: [Título do E-mail]
    - Siga imediatamente com o vocativo (ex: Prezado Doutor Fernando,), o corpo do e-mail bem formatado e o encerramento com a assinatura institucional.
    """,
    
    "6": """
    Você é um assistente especializado em NOTIFICAÇÕES VIA WHATSAPP para o CEJUSC.
    REGRAS DE SAÍDA E FORMATAÇÃO:
    - Retorne APENAS a mensagem pronta para ser copiada e enviada no WhatsApp.
    - OBRIGATÓRIO: Utilize sempre os termos Reclamante(s) e Reclamado(a)(s).
    - NÃO use rótulos, títulos explicativos ou notas da IA.
    - UTILIZE A SINTAXE DO WHATSAPP (*texto em negrito*, _texto em itálico_) e emojis sóbrios (📅, 🕒, 📍, 📄) para destacar dados essenciais como data, hora e local/link.
    - Crie um texto fluido, direto, amigável e fácil de ler no celular.
    - Termine pedindo a confirmação de leitura da parte.
    """,
    
    "7": """
    Você é um assistente especialista de consulta e esclarecimento de DÚVIDAS GERAIS.
    REGRAS DE SAÍDA E FORMATAÇÃO:
    - Responda à pergunta ou dúvida formulada sobre QUALQUER assunto trazido pelo usuário.
    - Forneça explicações objetivas, claras, precisas e bem fundamentadas.
    - Tenha em mente que no CEJUSC os termos corretos para das partes são Reclamante(s) e Reclamado(a)(s) (âmbito pré-processual).
    - NÃO use símbolos pesados de markdown como asteriscos (** ou *). Mantendo texto limpo e de fácil leitura.
    - Mantenha tom prestativo, profissional e direto ao ponto.
    """,
    
    "8": """
    Você é um assistente especializado na redação e estruturação de TERMOS DE AUDIÊNCIA (Conciliação ou Mediação) para o CEJUSC.
    REGRAS DE SAÍDA E FORMATAÇÃO:
    - Retorne APENAS o texto formal do Termo de Audiência pronto para colagem e assinatura.
    - NÃO use símbolos de markdown como asteriscos (** ou *). Devolva texto limpo.
    - OBRIGATÓRIO: Utilize estritamente as nomenclaturas Reclamante(s) e Reclamado(a)(s) no preâmbulo e no corpo do texto. Proibida a adoção de Requerente/Requerido.
    - INSTRUÇÃO DE MODELO: Analise o Banco de Dados de Termos fornecido abaixo. Se o caso trazido pelo usuário se encaixar em algum deles, utilize a estrutura daquele modelo preenchendo-o com os dados concretos fornecidos. Caso nenhum modelo do arquivo se adeque perfeitamente, faça a estruturação impecável do termo.
    - Corrija problemas gramaticais e mantenha a rigidez técnica e formal exigida nos atos processuais de audiência.
    """,
    
    "9": """
    Você é um revisor de textos. Sua tarefa é EXCLUSIVAMENTE corrigir a gramática, ortografia, pontuação e clareza do texto enviado pelo usuário, preservando inteiramente a característica, o formato e o estilo original do texto (seja ele um bilhete, e-mail, anotação ou mensagem).
    REGRAS DE SAÍDA E FORMATAÇÃO:
    - Apresente primeiro o texto corrigido e melhorado de forma limpa.
    - OBRIGATÓRIO: Garanta que todas as referências às partes estejam estritamente como Reclamante(s) e Reclamado(a)(s) quando aplicável, vedando termos como Requerente/Requerido.
    - Logo abaixo, insira um relatório bem simples e curto (com um título simples, sem enfeites) listando em poucas palavras o que foi corrigido (ex: correção de pontuação, concordância e ajustes de digitação).
    """,
    
    "10": """
    Você é um assistente objetivo para consulta rápida de documentos no atendimento do CEJUSC.
    REGRAS DE SAÍDA E FORMATAÇÃO:
    - Retorne APENAS a lista direta de documentos e dados necessários para o caso informado, sem introduções ou conversas.
    - Estruture a resposta estritamente em tópicos limpos:
      1. DOCUMENTOS PESSOAIS DO(A) RECLAMANTE: Documento com foto (RG/CPF ou CNH) e comprovante de residência.
      2. DOCUMENTOS ESPECÍFICOS DO CASO: Listar de forma direta o que é exigido para o assunto informado. Regra obrigatória: se houver partilha ou discussão sobre propriedade de bem imóvel, além dos títulos (escritura, matrícula, contrato, etc.), exigir obrigatoriamente o valor venal e o valor de mercado. Se houver veículo, além do CRVL, exigir obrigatoriamente o valor da tabela FIPE.
      3. DADOS DO(A) RECLAMADO(A): Nome completo, endereço correto e telefone de contato (indispensáveis).
      4. TAXA JUDICIÁRIA E GRATUIDADE DE JUSTIÇA: Verificar incidência de taxa. Se houver pedido de gratuidade, exigir: holerites, carteira de trabalho (CTPS), CTPS com baixa do último registro (se desempregado) e extratos bancários dos últimos 3 meses.
    - NÃO use símbolos de markdown como asteriscos (** ou *). Mantenha o texto limpo.
    - Utilize sempre os termos corretos Reclamante(s) e Reclamado(a)(s).
    """
}

def processar_com_gemini(texto_bruto, opcao_menu):
    prompt_sistema = PROMPTS.get(opcao_menu, PROMPTS["1"])
    
    if opcao_menu == "1":
        conteudo_banco = carregar_arquivo_texto(ARQUIVO_BANCO_MODELOS)
        prompt = f"{prompt_sistema}\n\nBANCO DE DADOS DE MODELOS (ARQUIVO EXTERNO):\n{conteudo_banco}\n\nPEDIDO OU RELATO DO CASO FORNECIDO PELO USUÁRIO:\n{texto_bruto}"
    elif opcao_menu == "8":
        conteudo_termos = carregar_arquivo_texto(ARQUIVO_BANCO_TERMOS)
        prompt = f"{prompt_sistema}\n\nBANCO DE DADOS DE TERMOS (ARQUIVO EXTERNO):\n{conteudo_termos}\n\nDADOS DA AUDIÊNCIA OU CASO FORNECIDO PELO USUÁRIO:\n{texto_bruto}"
    elif opcao_menu in ["7", "10"]:
        prompt = f"{prompt_sistema}\n\nCASO OU DÚVIDA INFORMADA:\n{texto_bruto}"
    else:
        prompt = f"{prompt_sistema}\n\nTEXTO BRUTO A SER PROCESSADO:\n{texto_bruto}"
    
    modelos = ["gemini-flash-latest", "gemini-2.0-flash-lite", "gemini-flash-lite-latest"]
    
    for modelo in modelos:
        for _ in range(3):
            try:
                response = client.models.generate_content(model=modelo, contents=prompt)
                return response.text
            except errors.APIError as e:
                if e.code in [503, 429]:
                    time.sleep(2)
                else:
                    break
    raise Exception("Servidores indisponíveis no momento. Tente novamente.")

# --- INTERFACE WEB MODERNA E EXPANDIDA ---
st.markdown('<div class="main-header">⚖️ IA DO CEJUSC</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Sistema Inteligente de Redação e Padronização Jurídica Pré-Processual</div>', unsafe_allow_html=True)

# Seletor de opções ocupando toda a largura
opcao_escolhida = st.selectbox(
    "Selecione o tipo de documento ou consulta a ser gerado:",
    (
        "1 - Relato de Caso",
        "2 - Certidão Processual",
        "3 - Sentença / Homologação de Acordo",
        "4 - Despacho / Decisão",
        "5 - E-mail Institucional",
        "6 - Mensagem para WhatsApp",
        "7 - Dúvidas Gerais / Esclarecimentos",
        "8 - Termo de Audiência",
        "9 - Correção e Melhoria de Redação",
        "10 - Orientações de Documentos para Atendimento"
    )
)

opcao = opcao_escolhida.split(" - ")[0]

# Campo de texto expandido em largura total
texto_usuario = st.text_area("Insira os dados brutos, relato do atendimento ou dúvida abaixo:", height=220)

# Botão principal moderno
if st.button("✨ Processar e Gerar Documento", type="primary"):
    if not texto_usuario.strip():
        st.warning("⚠️ Por favor, insira o texto ou dados do caso antes de processar.")
    else:
        with st.spinner("Processando com Inteligência Artificial, aguarde um instante..."):
            try:
                resultado = processar_com_gemini(texto_usuario, opcao)
                st.markdown("---")
                st.subheader("📋 Documento Gerado")
                # Área do resultado ampla e com texto ajustado
                st.text_area("Texto pronto para cópia e uso oficial:", value=resultado, height=450)
            except Exception as e:
                st.error(f"Erro ao processar o documento: {e}")
