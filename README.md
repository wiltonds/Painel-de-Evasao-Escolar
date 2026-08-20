# Radar de Evasão · SENAI-AL — MVP (Streamlit)

App de demonstração do modelo de risco de evasão **V15.2**. Mostra uma **visão executiva**
(KPIs, distribuição por faixa, Top 10%) e uma **visão operacional** (lista de alunos por
score + drill-down por indicador → variável), na mesma lógica prevista para o Power BI.

Já foi testado com a saída real do modelo (`score_evasao_v15_powerbi.xlsx`, aba
`SCORE_ALUNOS`). Também roda com dados sintéticos caso nenhum arquivo seja encontrado,
então dá para publicar e depois apontar para a base.

---

## 1. Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Abre em `http://localhost:8501`.

## 2. Conectar a base real

Aceita a planilha **já escorada** (`score_evasao_v15_powerbi.xlsx`). Duas formas:

- **Upload:** botão *Enviar planilha escorada (.xlsx)* na barra lateral; ou
- **Arquivo local:** coloque a planilha ao lado do `app.py` **ou** na subpasta `dados/`
  (o app procura nos dois lugares automaticamente).

O que o app faz com o arquivo:
- Lê a aba principal (reconhece `SCORE_ALUNOS`; tolera outros nomes).
- Como a base é **aluno × referência**, mantém por padrão apenas a **última referência de
  cada aluno** (desmarque *Usar última referência por aluno* na barra lateral para ver o
  histórico completo).
- A planilha não traz colunas `STATUS_*`; o app **deriva o status de cada indicador** a
  partir da posição do aluno na população (leitura relativa das 20 variáveis). O **score**
  continua sendo o do modelo.

Colunas usadas (só `cd_ra` e `SCORE_EVASAO` são obrigatórias; o resto é derivado se faltar):
`dt_referencia`, `FAIXA_RISCO`, `PRIORIDADE`, `ACAO_RECOMENDADA` e as 20 variáveis
(`nr_mediaglobal`, `vl_totalaberto`, …).

## 3. Publicar num URL (Streamlit Community Cloud — grátis)

1. Suba esta pasta para um repositório **privado** no GitHub.
2. **share.streamlit.io** -> *New app* -> selecione o repositório e `app.py` -> *Deploy*.
3. Em ~1 min você tem um link para compartilhar com a equipe.

## 4. Privacidade (dados de alunos)

São dados sensíveis (RA + score de risco). Recomendações:
- Use repositório **privado**; e/ou
- **Não versione a planilha:** crie um arquivo `.gitignore` com a linha `dados/` e, na
  demonstração, carregue o xlsx pelo **upload** da barra lateral.

## 5. Observações

- É um **MVP de demonstração**. O score prioriza a atenção; **não** é decisão automática.
- Métricas do modelo (ROC AUC 0,91 · alcance de 75% no Top 20%) vêm da validação temporal
  da V15.2, descrita na documentação do modelo.
