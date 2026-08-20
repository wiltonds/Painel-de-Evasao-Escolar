# Radar de Evasão · SENAI-AL — MVP (Streamlit)

App de demonstração do modelo de risco de evasão **V15.2**. Mostra uma **visão executiva**
(KPIs, distribuição por faixa, Top 10%) e uma **visão operacional** (lista de alunos por
score + drill-down por indicador → variável), na mesma lógica prevista para o Power BI.

O app **já roda com dados sintéticos** por padrão, então dá para testar e publicar antes de
conectar a base real. Ao fornecer a planilha escorada, as telas continuam idênticas.

---

## 1. Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Abre em `http://localhost:8501`.

## 2. Conectar a base real

O app aceita a saída **já escorada** do modelo (a planilha `score_evasao_v15_powerbi.xlsx`).
Duas formas:

- **Upload:** clique em *Enviar planilha escorada (.xlsx)* na barra lateral; ou
- **Arquivo local:** coloque `score_evasao_v15_powerbi.xlsx` na mesma pasta do `app.py`.

### Colunas esperadas (tabela principal / *wide*)
O app reconhece os nomes do schema V15.2 e tolera variações (maiúsculas, acentos, `_`):

`cd_ra`, `dt_referencia`, `SCORE_EVASAO`, `PROBABILIDADE_RISCO`, `FAIXA_RISCO`,
`PRIORIDADE`, `STATUS_DESEMPENHO`, `STATUS_FINANCEIRO`, `STATUS_FREQUENCIA`,
`STATUS_PERMANENCIA`, `STATUS_BOLSA`, `STATUS_COMPORTAMENTO`, `ACAO_RECOMENDADA`.

- Só `cd_ra` e `SCORE_EVASAO` são obrigatórios. Faltando `FAIXA_RISCO`/`PRIORIDADE`,
  o app deriva a partir do score.

### Drill-down até a variável (opcional, recomendado)
Para abrir cada indicador nas 20 variáveis com valor, inclua **uma segunda aba** com a
tabela detalhada (*long*), contendo pelo menos: `cd_ra`, `VARIAVEL`, `VALOR`.
Se a tabela *wide* já trouxer as colunas das variáveis (`nr_mediaglobal`, `vl_bolsa`, …),
o app monta o drill-down a partir delas automaticamente.

> Se nenhuma coluna for reconhecida, o app cai no modo sintético e avisa no topo.

## 3. Publicar num URL (Streamlit Community Cloud — grátis)

1. Suba esta pasta para um repositório no GitHub (`app.py`, `requirements.txt`, `README.md`).
2. Acesse **share.streamlit.io** → *New app* → selecione o repositório e `app.py`.
3. *Deploy*. Em ~1 min você tem um link para compartilhar com a equipe.

Para dados sensíveis, evite subir a planilha real ao GitHub público — use o **upload** na
barra lateral, ou um repositório **privado**, ou publique num servidor interno
(`streamlit run` atrás da VPN da instituição).

## 4. Observações

- É um **MVP de demonstração**. O score prioriza a atenção; **não** é decisão automática.
- As métricas citadas (ROC AUC 0,91 · alcance de 75% no Top 20%) vêm da validação temporal
  da V15.2, descrita na documentação do modelo.
