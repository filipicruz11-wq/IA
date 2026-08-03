if st.button("Processar com IA", type="primary"):
    if not texto_usuario.strip():
        st.warning("⚠️ Nenhum texto foi inserido!")
    else:
        # DIAGNÓSTICO DOS ARQUIVOS
        banco_obj = carregar_arquivo_texto(ARQUIVO_BANCO_MODELOS)
        banco_ter = carregar_arquivo_texto(ARQUIVO_BANCO_TERMOS)
        
        st.write("🔍 **Status da leitura dos arquivos no Render:**")
        if "[Aviso:" in banco_obj:
            st.error(f"Erro Modelos: {banco_obj}")
        else:
            st.success("✅ 'BANCO DE DADOS OBJETOS.TXT' foi carregado com sucesso!")
            
        if "[Aviso:" in banco_ter:
            st.error(f"Erro Termos: {banco_ter}")
        else:
            st.success("✅ 'BANCO DE DADOS TERMOS.TXT' foi carregado com sucesso!")

        with st.spinner("Processando com a IA, aguarde um instante..."):
            try:
                resultado = processar_com_gemini(texto_usuario, opcao)
                st.subheader("================ RESULTADO DA ANÁLISE ================")
                st.text_area("Resultado gerado:", value=resultado, height=350)
            except Exception as e:
                st.error(f"Erro ao processar: {e}")
