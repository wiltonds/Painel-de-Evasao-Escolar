"""
Radar de Evasão · SENAI-AL — MVP (Streamlit)
Lê a saída já escorada do modelo V15.2 (tabela wide + tabela long de detalhe)
e apresenta uma visão executiva e uma operacional com drill-down por indicador.

Fonte dos dados (nesta ordem):
  1) arquivo enviado na barra lateral;
  2) 'score_evasao_v15_powerbi.xlsx' na mesma pasta do app;
  3) dados sintéticos (para demonstração), caso nenhum arquivo seja encontrado.
"""

import unicodedata
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

# ------------------------------------------------------------------ config
st.set_page_config(page_title="Radar de Evasão · SENAI-AL", layout="wide", page_icon="🎓")

NAVY, BLUE, INK, MUTE, LINE, PANEL = "#0F3D5C", "#1E6091", "#20272E", "#63707C", "#DCE4EC", "#F4F7FA"
FAIXA_ORDER = ["Muito baixo", "Baixo", "Médio", "Alto", "Muito alto"]
FAIXA_COLOR = {"Muito baixo": "#2E7D45", "Baixo": "#6FA84F", "Médio": "#C98A00",
               "Alto": "#E8720C", "Muito alto": "#C4342B"}
STATUS_COLOR = {"OK": "#2E7D45", "Atenção": "#C98A00", "Crítico": "#C4342B"}
STATUS_LEVEL = {"OK": 22, "Atenção": 58, "Crítico": 86}
DEFAULT_FILE = "score_evasao_v15_powerbi.xlsx"

# ------------------------------------------------------------------ schema V15.2
INDICATORS = [
    dict(key="desempenho", nome="Desempenho", peso=20.53, status_col="STATUS_DESEMPENHO", vars=[
        dict(label="Média global do aluno", campo="nr_mediaglobal", peso="20,53%", fmt="media")]),
    dict(key="permanencia", nome="Permanência", peso=17.91, status_col="STATUS_PERMANENCIA", vars=[
        dict(label="Tempo como aluno (meses de casa)", campo="nr_mesesdecasa", peso="17,91%", fmt="meses")]),
    dict(key="financeiro", nome="Financeiro", peso=17.49, status_col="STATUS_FINANCEIRO", vars=[
        dict(label="Valor médio da parcela em dívida", campo="vl_dividamediaparcela", peso="6,28%", fmt="brl"),
        dict(label="Valor total em aberto", campo="vl_totalaberto", peso="3,26%", fmt="brl"),
        dict(label="Variação da dívida no último mês", campo="vl_deltadivida1m", peso="3,18%", fmt="brlDelta"),
        dict(label="Maior atraso registrado (dias)", campo="nr_maxdiasatraso", peso="1,93%", fmt="dias"),
        dict(label="Parcelas em aberto", campo="qt_parcelasaberto", peso="1,21%", fmt="int"),
        dict(label="Meses inadimplente (últ. 3m)", campo="nr_mesesinadimplenteult3m", peso="0,80%", fmt="int"),
        dict(label="Variação de parcelas no último mês", campo="nr_deltaparcelas1m", peso="0,62%", fmt="intDelta"),
        dict(label="Inadimplente atualmente", campo="fl_inadimplente", peso="0,21%", fmt="flag")]),
    dict(key="bolsa", nome="Bolsa/desconto", peso=17.31, status_col="STATUS_BOLSA", vars=[
        dict(label="Valor da bolsa", campo="vl_bolsa", peso="12,46%", fmt="brl"),
        dict(label="Quantidade de bolsas", campo="qt_bolsas", peso="4,26%", fmt="int"),
        dict(label="Possui bolsa", campo="fl_tembolsa", peso="0,58%", fmt="flag")]),
    dict(key="frequencia", nome="Frequência", peso=17.30, status_col="STATUS_FREQUENCIA", vars=[
        dict(label="Frequência global", campo="nr_freqglobal", peso="17,06%", fmt="pct"),
        dict(label="Queda de frequência no último mês", campo="nr_deltafreq1m", peso="0,09%", fmt="ppDelta"),
        dict(label="Frequência crítica", campo="fl_freqcritica", peso="0,08%", fmt="flag"),
        dict(label="Queda de frequência em 3 meses", campo="nr_deltafreq3m", peso="0,07%", fmt="ppDelta")]),
    dict(key="comportamento", nome="Comportamento", peso=9.46, status_col="STATUS_COMPORTAMENTO", vars=[
        dict(label="Ocorrências acumuladas", campo="qt_ocorrenciasacum", peso="5,53%", fmt="int"),
        dict(label="Ocorrências nos últimos 3 meses", campo="qt_ocorrenciasult3m", peso="2,65%", fmt="int"),
        dict(label="Tipos de ocorrência registrados", campo="qt_ocorrenciasnomes", peso="1,27%", fmt="int")]),
]
ACAO = {
    "desempenho": "Acompanhamento pedagógico e monitoria; conversa sobre dificuldades de aprendizagem.",
    "permanencia": "Aluno recente — reforçar acolhimento e integração nas primeiras semanas.",
    "financeiro": "Encaminhar para renegociação financeira e verificar elegibilidade a bolsa/desconto.",
    "bolsa": "Revisar apoio financeiro disponível e orientar sobre programas de bolsa.",
    "frequencia": "Contato para entender as ausências e montar plano de recuperação de frequência.",
    "comportamento": "Escuta com a coordenação sobre as ocorrências e encaminhamento de apoio.",
}

# ------------------------------------------------------------------ helpers
def _norm(s):
    s = str(s).strip()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return s.upper().replace(" ", "").replace("-", "").replace("_", "")

def find_col(df, *candidates):
    norm_map = {_norm(c): c for c in df.columns}
    for cand in candidates:
        if _norm(cand) in norm_map:
            return norm_map[_norm(cand)]
    return None

def faixa_from_score(s):
    return ("Muito baixo" if s < 20 else "Baixo" if s < 40 else "Médio"
            if s < 60 else "Alto" if s < 80 else "Muito alto")

def prioridade_from_faixa(f):
    return {"Muito alto": "Prioridade crítica", "Alto": "Prioridade alta",
            "Médio": "Acompanhamento"}.get(f, "Monitoramento")

def norm_faixa(v):
    n = _norm(v)
    if "MUITOALTO" in n: return "Muito alto"
    if "MUITOBAIXO" in n: return "Muito baixo"
    if "ALTO" in n: return "Alto"
    if "MEDIO" in n: return "Médio"
    if "BAIXO" in n: return "Baixo"
    return "Médio"

def norm_status(v):
    n = _norm(v)
    if "CRIT" in n: return "Crítico"
    if any(k in n for k in ("ATEN", "ALERT", "MEDIO")): return "Atenção"
    if any(k in n for k in ("OK", "NORMAL", "BOM", "BAIXO")): return "OK"
    return "Atenção"

def status_from_risk(r):
    return "OK" if r < 0.34 else "Atenção" if r < 0.67 else "Crítico"

def fmt_value(fmt, v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    def brl(x): return f"R$ {x:,.0f}".replace(",", ".")
    try:
        if fmt == "media": return f"{float(v):.1f}"
        if fmt == "meses": return f"{int(round(float(v)))} m"
        if fmt == "brl": return brl(float(v))
        if fmt == "brlDelta": return ("+" if v >= 0 else "") + brl(float(v))
        if fmt == "dias": return f"{int(round(float(v)))} d"
        if fmt == "int": return f"{int(round(float(v)))}"
        if fmt == "intDelta": return ("+" if v >= 0 else "") + f"{int(round(float(v)))}"
        if fmt == "flag": return "Sim" if float(v) >= 0.5 else "Não"
        if fmt == "pct": return f"{int(round(float(v)))}%"
        if fmt == "ppDelta": return ("+" if v >= 0 else "") + f"{int(round(float(v)))} pp"
    except (ValueError, TypeError):
        return str(v)
    return str(v)

# ------------------------------------------------------------------ synthetic data (fallback)
def raw_value(fmt, rv, rng):
    if fmt == "media": return round(9.4 - rv * 6.6 + (rng.random() - .5) * .4, 1)
    if fmt == "meses": return int(round(3 + (1 - rv) * 44 + (rng.random() - .5) * 4))
    if fmt == "brl": return int(round((120 + rv * 950) / 10) * 10)
    if fmt == "brlDelta": return int(round(((rv - .4) * 700) / 10) * 10)
    if fmt == "dias": return max(0, int(round(rv * 115)))
    if fmt == "int": return max(0, int(round(rv * 7 + (rng.random() - .5))))
    if fmt == "intDelta": return int(round((rv - .4) * 4))
    if fmt == "flag": return 1 if rv > .55 else 0
    if fmt == "pct": return int(round(min(100, max(30, 97 - rv * 58))))
    if fmt == "ppDelta": return int(round((.25 - rv) * 22))
    return int(round(rv * 5))

@st.cache_data
def make_synthetic(n=176, seed=20250820):
    rng = np.random.default_rng(seed)
    wsum = sum(i["peso"] for i in INDICATORS)
    wide_rows, long_rows = [], []
    for i in range(n):
        base = rng.random() ** 1.7
        risco = {ind["key"]: float(np.clip(base + (rng.random() - .5) * .85, 0, 1)) for ind in INDICATORS}
        if rng.random() < .18:
            k = INDICATORS[rng.integers(len(INDICATORS))]["key"]
            risco[k] = float(np.clip(.72 + rng.random() * .25, 0, 1))
        score = float(np.clip(sum(ind["peso"] / wsum * risco[ind["key"]] for ind in INDICATORS) * 100
                              + (rng.random() - .5) * 6, 1, 99))
        faixa = faixa_from_score(score)
        ra = int(20250000 + rng.integers(90000) + i)
        worst = max(INDICATORS, key=lambda ind: risco[ind["key"]])
        row = dict(cd_ra=ra, dt_referencia="30/11/2025", SCORE_EVASAO=round(score, 1),
                   PROBABILIDADE_RISCO=round(score / 100, 3), FAIXA_RISCO=faixa,
                   PRIORIDADE=prioridade_from_faixa(faixa), ACAO_RECOMENDADA=ACAO[worst["key"]])
        for ind in INDICATORS:
            row[ind["status_col"]] = status_from_risk(risco[ind["key"]])
            for idx, vr in enumerate(ind["vars"]):
                tight = .12 if idx == 0 else .34
                rv = float(np.clip(risco[ind["key"]] + (rng.random() - .5) * tight, 0, 1))
                val = raw_value(vr["fmt"], rv, rng)
                row[vr["campo"]] = val
                long_rows.append(dict(cd_ra=ra, DIMENSAO=ind["nome"], VARIAVEL=vr["campo"],
                                      LABEL=vr["label"], VALOR=val, PESO=vr["peso"]))
        wide_rows.append(row)
    dw = pd.DataFrame(wide_rows).sort_values("SCORE_EVASAO", ascending=False).reset_index(drop=True)
    return dw, pd.DataFrame(long_rows)

# ------------------------------------------------------------------ loader
def normalize_wide(df):
    """Map an arbitrary scored table to the standard column names used by the app."""
    out = pd.DataFrame()
    c_ra = find_col(df, "cd_ra", "ra", "matricula")
    c_score = find_col(df, "SCORE_EVASAO", "score", "score_risco")
    if c_ra is None or c_score is None:
        return None
    out["cd_ra"] = df[c_ra]
    out["SCORE_EVASAO"] = pd.to_numeric(df[c_score], errors="coerce")
    c_ref = find_col(df, "dt_referencia", "referencia", "data_ref")
    out["dt_referencia"] = df[c_ref] if c_ref else ""
    c_faixa = find_col(df, "FAIXA_RISCO", "faixa")
    out["FAIXA_RISCO"] = (df[c_faixa].map(norm_faixa) if c_faixa
                          else out["SCORE_EVASAO"].map(faixa_from_score))
    c_prio = find_col(df, "PRIORIDADE", "prioridade")
    out["PRIORIDADE"] = df[c_prio] if c_prio else out["FAIXA_RISCO"].map(prioridade_from_faixa)
    c_acao = find_col(df, "ACAO_RECOMENDADA", "acao")
    out["ACAO_RECOMENDADA"] = df[c_acao] if c_acao else ""
    for ind in INDICATORS:
        c = find_col(df, ind["status_col"], "STATUS_" + ind["key"])
        out[ind["status_col"]] = df[c].map(norm_status) if c else None
        for vr in ind["vars"]:
            c = find_col(df, vr["campo"])
            if c is not None:
                out[vr["campo"]] = df[c]
    return out.sort_values("SCORE_EVASAO", ascending=False).reset_index(drop=True)

def build_long_from_wide(dw):
    rows = []
    for _, r in dw.iterrows():
        for ind in INDICATORS:
            for vr in ind["vars"]:
                if vr["campo"] in dw.columns:
                    rows.append(dict(cd_ra=r["cd_ra"], DIMENSAO=ind["nome"], VARIAVEL=vr["campo"],
                                     LABEL=vr["label"], VALOR=r[vr["campo"]], PESO=vr["peso"]))
    return pd.DataFrame(rows) if rows else None

def normalize_long(df):
    c_ra = find_col(df, "cd_ra", "ra")
    c_var = find_col(df, "VARIAVEL", "variavel", "feature")
    c_val = find_col(df, "VALOR", "valor", "value")
    if c_ra is None or c_var is None or c_val is None:
        return None
    out = pd.DataFrame({"cd_ra": df[c_ra], "VARIAVEL": df[c_var], "VALOR": df[c_val]})
    return out

def load_data(uploaded):
    """Returns (df_wide, df_long, source_label)."""
    src, sheets = None, None
    if uploaded is not None:
        sheets = pd.read_excel(uploaded, sheet_name=None)
        src = f"arquivo enviado: {uploaded.name}"
    else:
        try:
            sheets = pd.read_excel(DEFAULT_FILE, sheet_name=None)
            src = f"arquivo local: {DEFAULT_FILE}"
        except FileNotFoundError:
            dw, dl = make_synthetic()
            return dw, dl, "dados sintéticos (demonstração)"

    wide, long = None, None
    for _, sheet in sheets.items():
        if wide is None:
            wide = normalize_wide(sheet)
        if long is None:
            long = normalize_long(sheet)
    if wide is None:
        dw, dl = make_synthetic()
        return dw, dl, "dados sintéticos (arquivo sem colunas reconhecidas)"
    if long is None:
        long = build_long_from_wide(wide)
    return wide, long, src

def var_value(df_long, ra, campo, fmt):
    if df_long is None or "VARIAVEL" not in df_long.columns:
        return "—"
    hit = df_long[(df_long["cd_ra"] == ra) & (df_long["VARIAVEL"] == campo)]
    if hit.empty:
        return "—"
    raw = hit.iloc[0]["VALOR"]
    if isinstance(raw, str):
        return raw
    return fmt_value(fmt, raw)

# ------------------------------------------------------------------ CSS
st.markdown(f"""
<style>
  .block-container {{ padding-top: 1rem; max-width: 1180px; }}
  .rv-hdr {{ background:{NAVY}; border-radius:12px; padding:16px 20px; display:flex;
             align-items:center; gap:14px; margin-bottom:6px; }}
  .rv-hdr h1 {{ color:#fff; font-size:19px; margin:0; }}
  .rv-hdr p  {{ color:#ffffff99; font-size:12.5px; margin:2px 0 0; }}
  .rv-note {{ background:#FFF4E2; color:#8A5A00; font-size:12.5px;
              padding:7px 14px; border-radius:8px; border:1px solid #F0D9AE; margin-bottom:14px; }}
  .rv-bar {{ height:9px; background:#EDF1F5; border-radius:6px; overflow:hidden; }}
  .rv-bar > span {{ display:block; height:100%; border-radius:6px; }}
  .chip {{ display:inline-block; padding:2px 10px; border-radius:999px; font-size:12px; font-weight:600; }}
  div[data-testid="stMetricValue"] {{ font-size:32px; }}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ sidebar
st.sidebar.markdown("### Fonte de dados")
uploaded = st.sidebar.file_uploader("Enviar planilha escorada (.xlsx)", type=["xlsx"])
df_wide, df_long, source = load_data(uploaded)
st.sidebar.caption(f"Fonte atual: **{source}**")
st.sidebar.markdown("---")
st.sidebar.markdown("### Filtros (operacional)")
q = st.sidebar.text_input("Buscar por RA")
faixa_sel = st.sidebar.multiselect("Faixa de risco", FAIXA_ORDER, default=[])
top20_only = st.sidebar.checkbox("Somente Top 20%")

# ------------------------------------------------------------------ header
st.markdown(f"""
<div class="rv-hdr">
  <div style="width:34px;height:34px;border-radius:8px;background:#ffffff1a;
       display:flex;align-items:center;justify-content:center;font-size:18px;">🎓</div>
  <div><h1>Radar de Evasão · SENAI-AL</h1>
  <p>Modelo V15.2 · HistGradientBoosting · score 0–100</p></div>
</div>
""", unsafe_allow_html=True)
if "sintétic" in source:
    st.markdown('<div class="rv-note">Protótipo de demonstração — dados sintéticos no schema da V15.2. '
                'Envie sua planilha escorada na barra lateral para ver com os dados reais.</div>',
                unsafe_allow_html=True)

total = len(df_wide)
top10_n = max(1, round(total * 0.10))
top20_n = max(1, round(total * 0.20))

tab_exec, tab_op = st.tabs(["📊 Visão executiva", "👥 Operacional"])

# ------------------------------------------------------------------ executive
with tab_exec:
    altos = int((df_wide["SCORE_EVASAO"] >= 60).sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Alunos monitorados", total)
    c2.metric("Em risco Alto+", altos, f"{round(altos/total*100)}% do total")
    c3.metric("Top 10% — foco imediato", top10_n)
    c4.metric("Score médio", f"{df_wide['SCORE_EVASAO'].mean():.1f}")

    g1, g2 = st.columns([1.15, 1])
    with g1:
        st.markdown("**Distribuição por faixa de risco**")
        dist = (df_wide["FAIXA_RISCO"].value_counts()
                .reindex(FAIXA_ORDER).fillna(0).reset_index())
        dist.columns = ["faixa", "alunos"]
        chart = (alt.Chart(dist).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
                 .encode(
                     x=alt.X("faixa:N", sort=FAIXA_ORDER, title=None,
                             axis=alt.Axis(labelAngle=0, labelFontSize=11)),
                     y=alt.Y("alunos:Q", title=None),
                     color=alt.Color("faixa:N", scale=alt.Scale(domain=FAIXA_ORDER,
                             range=[FAIXA_COLOR[f] for f in FAIXA_ORDER]), legend=None),
                     tooltip=["faixa", "alunos"])
                 .properties(height=250))
        st.altair_chart(chart, use_container_width=True)
    with g2:
        st.markdown("**Top 10% mais críticos**")
        top = df_wide.head(top10_n)[["cd_ra", "SCORE_EVASAO", "FAIXA_RISCO", "PRIORIDADE"]].copy()
        top.columns = ["RA", "Score", "Faixa", "Prioridade"]
        st.dataframe(
            top.style.format({"Score": "{:.0f}"})
               .apply(lambda col: [f"color:{FAIXA_COLOR.get(v,'')};font-weight:700"
                                   for v in top["Faixa"]] if col.name == "Faixa" else ["" for _ in col], axis=0),
            hide_index=True, use_container_width=True, height=250)

# ------------------------------------------------------------------ operational
with tab_op:
    view = df_wide.copy()
    if top20_only:
        view = view.head(top20_n)
    if faixa_sel:
        view = view[view["FAIXA_RISCO"].isin(faixa_sel)]
    if q.strip():
        view = view[view["cd_ra"].astype(str).str.contains(q.strip())]

    left, right = st.columns([1, 1.05])

    with left:
        st.markdown(f"**{len(view)} aluno(s)** — ordenados por score")
        show = view[["cd_ra", "SCORE_EVASAO", "FAIXA_RISCO", "PRIORIDADE"]].copy()
        show.columns = ["RA", "Score", "Faixa", "Prioridade"]
        st.dataframe(
            show.style.format({"Score": "{:.0f}"})
                .apply(lambda col: [f"background-color:{FAIXA_COLOR.get(v,'')}22;color:{FAIXA_COLOR.get(v,'')};font-weight:700"
                                    for v in show["Faixa"]] if col.name == "Faixa" else ["" for _ in col], axis=0),
            hide_index=True, use_container_width=True, height=430)

        options = view["cd_ra"].tolist()
        sel_ra = st.selectbox("Abrir aluno (RA)", options,
                              index=0 if options else None,
                              format_func=lambda r: f"RA {r}") if options else None

    with right:
        if sel_ra is None:
            st.info("Nenhum aluno no filtro atual.")
        else:
            s = df_wide[df_wide["cd_ra"] == sel_ra].iloc[0]
            faixa = s["FAIXA_RISCO"]
            fc = FAIXA_COLOR.get(faixa, NAVY)
            st.markdown(
                f"<div style='color:{MUTE};font-size:12px;font-weight:600'>RA {sel_ra} · ref. {s['dt_referencia']}</div>"
                f"<div style='display:flex;align-items:baseline;gap:12px;margin:2px 0 6px'>"
                f"<span style='font-size:44px;font-weight:800;color:{fc};line-height:1'>{s['SCORE_EVASAO']:.0f}</span>"
                f"<span style='font-size:12.5px;color:{MUTE}'>score de risco (0–100)</span></div>"
                f"<span class='chip' style='background:{fc};color:#fff'>{faixa}</span> "
                f"<span class='chip' style='background:{NAVY}18;color:{NAVY}'>{s['PRIORIDADE']}</span>",
                unsafe_allow_html=True)

            st.markdown(f"<div style='color:{MUTE};font-size:12px;font-weight:700;"
                        f"text-transform:uppercase;letter-spacing:.4px;margin:14px 0 6px'>"
                        f"Por que este aluno está neste nível</div>", unsafe_allow_html=True)

            worst_key, worst_lvl = None, -1
            for ind in INDICATORS:
                stv = s.get(ind["status_col"])
                status = norm_status(stv) if isinstance(stv, str) else "Atenção"
                lvl = STATUS_LEVEL[status]
                if lvl > worst_lvl:
                    worst_lvl, worst_key = lvl, ind["key"]
                color = STATUS_COLOR[status]
                with st.expander(f"{ind['nome']}  ·  peso {ind['peso']:.2f}%  —  {status}".replace(".", ",", 1)):
                    st.markdown(f"<div class='rv-bar'><span style='width:{lvl}%;background:{color}'></span></div>",
                                unsafe_allow_html=True)
                    rows = [{"O que é observado": vr["label"],
                             "Valor": var_value(df_long, sel_ra, vr["campo"], vr["fmt"]),
                             "Campo": vr["campo"], "Peso": vr["peso"]} for vr in ind["vars"]]
                    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

            acao = s.get("ACAO_RECOMENDADA") or ACAO.get(worst_key, "")
            st.markdown(
                f"<div style='display:flex;gap:10px;background:{NAVY}0D;border:1px solid {NAVY}22;"
                f"border-radius:10px;padding:12px 14px;margin-top:10px'>"
                f"<div style='font-size:18px'>⚠️</div><div>"
                f"<div style='font-weight:700;color:{NAVY};font-size:13px'>Ação recomendada</div>"
                f"<div style='font-size:13px;color:{INK};margin-top:2px'>{acao}</div></div></div>",
                unsafe_allow_html=True)

st.caption("MVP para demonstração · as métricas do modelo (ROC AUC 0,91 · alcance 75% no Top 20%) "
           "referem-se à validação temporal da V15.2. O score prioriza a atenção; não é decisão automática.")