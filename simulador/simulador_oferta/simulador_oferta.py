"""
Simulador de Plano de Saúde — Streamlit + Supabase (tabela tb_pricing)
Versão 4 — melhorias de UX:
  - Resultado sempre visível (painel fixo à direita)
  - Vidas preservadas ao trocar plano/acomodação (reaproveita por faixa etária)
  - Exportação: Excel e resumo em texto para copiar
  - Contrato atual em campo de texto (aceita 15.000,00)
  - Valor médio por vida e economia/acréscimo
  - Mensagem de orientação quando não há vidas informadas
  - Vigência exibida no rodapé

Instalação:
    pip install streamlit sqlalchemy psycopg2-binary pandas openpyxl

Rodar (de dentro da pasta do projeto):
    streamlit run simulador_plano_saude_supabase_v4.py

Conexão (ordem de prioridade):
  1) .streamlit/secrets.toml com [connections.supabase]
  2) Constantes DB_* abaixo
Se nenhuma funcionar, o app roda com dados de exemplo.
"""

import io
import re
import time
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO
# ---------------------------------------------------------------------------
TABELA = "tb_pricing"
FORMATO_DATA = "DD/MM/YYYY"  # formato de DATA_DE_VIGENCIA (ex.: 01/01/2026)

# Nome da coluna de coparticipação na tb_pricing (ajuste aqui se for diferente)
COL_COPART = "COPARTICIPACAO"
# Nome da coluna do código interno do produto na tb_pricing
COL_CODIGO = "CODIGO_PRODUTO_INTERNO"

CHAVES = ["FILIAL", "TIPO_PLANO", "PLANO", "SEGMENTACAO", COL_COPART, "ACOMODACAO", "FAIXA_ETARIA"]

# Usado só se não houver [connections.supabase] no secrets.toml
DB_USER = "postgres.wprmdpxczwqkjjhfpowd"
DB_PASS = "COLOQUE_SUA_SENHA_AQUI"
DB_HOST = "aws-0-us-east-1.pooler.supabase.com"
DB_PORT = 5432
DB_NAME = "postgres"
DB_URL = f"postgresql+psycopg2://{DB_USER}:{quote_plus(DB_PASS)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

st.set_page_config(
    page_title="Simulador de Plano de Saúde",
    page_icon="💙",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS = """
<style>
    .stApp { background-color: #0b1530; }
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] { display: none; }

    .titulo-app { color:#fff; font-size:26px; font-weight:700; text-align:center; padding:6px 0 14px 0; }
    .field-label { color:#c9d3ee; font-size:11px; font-weight:600; letter-spacing:.5px; margin-bottom:2px; }
    hr { border-color:#23305c; }

    /* Filtros e inputs */
    div[data-baseweb="select"] > div { background-color:#fff !important; border-radius:8px !important;
                                       border:1px solid #c7cfe8 !important; }
    div[data-baseweb="select"] span { color:#12213f !important; font-weight:600 !important; }
    .stTextInput input, .stNumberInput input { background-color:#16224a !important; color:#fff !important;
                                               border:1px solid #2b3c72 !important; border-radius:8px !important; }

    /* Botões neutros (Limpar) e de download */
    div.stButton > button { background-color:transparent; color:#c9d3ee; font-weight:600;
                            border:1px solid #3a4c85; border-radius:8px; padding:6px 16px; }
    div.stButton > button:hover { background-color:#16224a; color:#fff; border-color:#4d6fe0; }
    div.stDownloadButton > button { background-color:#2f54d4; color:#fff; font-weight:600; border:none;
                                    border-radius:8px; width:100%; }
    div.stDownloadButton > button:hover { background-color:#2543b0; color:#fff; }

    /* Resumo da seleção (pílulas) */
    .resumo-sel { display:flex; flex-wrap:wrap; gap:10px; margin:6px 0 14px 0; }
    .pill { background:#16224a; border:1px solid #2b3c72; border-radius:12px; padding:8px 14px; }
    .pill .k { color:#8ea1e0; font-size:10px; font-weight:700; letter-spacing:1px; display:block; }
    .pill .v { color:#fff; font-size:15px; font-weight:700; }

    /* Tabela */
    .st-key-tabela [data-testid="stVerticalBlock"] { gap: 0.3rem; }
    div[data-testid="stHorizontalBlock"]:has(.tabela-row),
    div[data-testid="stHorizontalBlock"]:has(.tabela-header),
    div[data-testid="stHorizontalBlock"]:has(.tabela-total) { align-items:center; gap:0.5rem; }
    .tabela-header { color:#c9d3ee; font-weight:700; font-size:12px; letter-spacing:1px; text-transform:uppercase;
                     background-color:#1c2a58; border-bottom:2px solid #4d6fe0; border-radius:8px 8px 0 0;
                     height:42px; display:flex; align-items:center; justify-content:center; }
    .tabela-row { background-color:#fff; color:#16224a; height:42px; display:flex; align-items:center;
                  justify-content:center; border-radius:6px; font-size:15px; font-weight:500; }
    .tabela-row.alt { background-color:#eef2ff; }
    .tabela-row.valor { font-weight:700; }
    .tabela-row.destaque { background-color:#dbe6ff; color:#0e1a5c; font-weight:800; }
    .tabela-total { background-color:#16227a; color:#f2b134; height:46px; display:flex; align-items:center;
                    justify-content:center; border-radius:8px; font-size:16px; font-weight:800; }
    .tabela-total.rotulo { color:#fff; letter-spacing:1px; }
    .st-key-tabela div[data-testid="stNumberInput"] { margin-bottom:0; }
    .st-key-tabela div[data-baseweb="input"] { height:42px; }
    .st-key-tabela .stNumberInput input { height:42px; text-align:center; font-size:15px; font-weight:700; }

    /* Painel de resultado fixo à direita */
    div[data-testid="stColumn"]:has(.st-key-resumo),
    div[data-testid="column"]:has(.st-key-resumo) { position:sticky; top:3.5rem; align-self:flex-start; }
    .total-card { background:linear-gradient(180deg,#16227a 0%,#0e1a5c 100%); border-top:2px solid #4d6fe0;
                  border-radius:16px; padding:18px 20px 18px 20px; text-align:center; margin:12px 0;
                  box-shadow:0 4px 24px rgba(0,0,0,.4); }
    .total-caption { color:#9fb0e8; font-size:12px; font-weight:700; letter-spacing:1.5px; }
    .total-value { font-size:32px; font-weight:800; color:#f2b134; margin:4px 0; }
    .total-vazio { color:#9fb0e8; font-size:14px; font-weight:600; padding:14px 0 8px 0; }
    .total-comparativo { font-size:13px; font-weight:700; padding:2px 0 8px 0; }
    .stats { border-top:1px solid #2b3c72; margin-top:8px; padding-top:8px; text-align:left; }
    .stat { display:flex; justify-content:space-between; color:#c9d3ee; font-size:13px; padding:3px 0; }
    .stat b { color:#fff; }
    .rodape-vigencia { color:#6f82b8; font-size:12px; text-align:center; padding:18px 0 4px 0; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------------------------
def formatar_moeda(valor):
    """1234.5 -> 'R$ 1.234,50'"""
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "§").replace(".", ",").replace("§", ".")
    return f"R$ {texto}"


def parse_moeda(txt):
    """Aceita '15000', '15.000', '15.000,50', 'R$ 15.000,50'. Retorna None se inválido."""
    t = str(txt).replace("R$", "").replace(" ", "").strip()
    if not t:
        return 0.0
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", t):
        t = t.replace(".", "")
    try:
        return max(float(t), 0.0)
    except ValueError:
        return None


def ordem_faixa(faixa):
    """Extrai o primeiro número da faixa ('19 a 23 anos' -> 19) para ordenar."""
    m = re.search(r"\d+", str(faixa))
    return int(m.group()) if m else 999


def dados_exemplo():
    faixas = [
        ("00 a 18 anos", 122.75), ("19 a 23 anos", 137.48), ("24 a 28 anos", 153.98),
        ("29 a 33 anos", 177.08), ("34 a 38 anos", 203.64), ("39 a 43 anos", 242.33),
        ("44 a 48 anos", 302.91), ("49 a 53 anos", 388.54), ("54 a 58 anos", 643.69),
        ("59 anos ou mais", 720.93),
    ]
    linhas = [
        ("FORTALEZA", "HMO", "PREMIUM FREE IN NAC", "AMBULATORIAL", cp, "S/ACOM", f, v * fator, cod)
        for cp, fator, cod in (("COM COPART", 1.0, 2737), ("SEM COPART", 1.35, 2738))
        for f, v in faixas
    ]
    linhas.append(("FORTALEZA", "HMO", "PREMIUM FREE IN NAC", "ODONTO", "SEM COPART", "S/ACOM", "00 a 99 anos", 24.5, 2739))
    return pd.DataFrame(linhas, columns=CHAVES + ["VALOR_PRODUTO", COL_CODIGO])


# Opções do SQLAlchemy para conexões mais resistentes a quedas do pooler:
#  - pool_pre_ping: testa a conexão antes de usar e reconecta se ela caiu
#  - pool_recycle: renova conexões paradas há mais de 5 minutos
#  - keepalives: mantém a conexão TCP viva enquanto o app está aberto
OPCOES_CONEXAO = dict(
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "connect_timeout": 15,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 3,
    },
)


def get_conn():
    """Usa o secrets.toml se existir [connections.supabase]; senão, usa DB_URL."""
    try:
        if "supabase" in st.secrets.get("connections", {}):
            return st.connection("supabase", type="sql", **OPCOES_CONEXAO)
    except Exception:
        pass
    return st.connection("supabase_url", type="sql", url=DB_URL, **OPCOES_CONEXAO)


def consultar(sql, params=None, tentativas=3):
    """Executa a consulta com reconexão automática se o servidor derrubar a conexão."""
    ultimo_erro = None
    for t in range(tentativas):
        try:
            return get_conn().query(sql, params=params, ttl=0)
        except Exception as e:
            ultimo_erro = e
            try:
                get_conn().reset()  # descarta a conexão antiga para abrir uma nova
            except Exception:
                pass
            time.sleep(1.5 * (t + 1))
    raise ultimo_erro


@st.cache_data(ttl=600, show_spinner="Consultando vigências...")
def listar_vigencias():
    df = consultar(
        f"""
        SELECT "DATA_DE_VIGENCIA" AS vigencia
        FROM {TABELA}
        GROUP BY "DATA_DE_VIGENCIA"
        ORDER BY TO_DATE("DATA_DE_VIGENCIA", '{FORMATO_DATA}') DESC
        """
    )
    return df["vigencia"].tolist()


@st.cache_data(ttl=600, show_spinner="Carregando tabela de preços...")
def carregar_precos(vigencia):
    return consultar(
        f"""
        SELECT "FILIAL", "TIPO_PLANO", "PLANO", "SEGMENTACAO", "{COL_COPART}", "ACOMODACAO",
               "FAIXA_ETARIA", "VALOR_PRODUTO", "{COL_CODIGO}"
        FROM {TABELA}
        WHERE "DATA_DE_VIGENCIA" = :v
        """,
        params={"v": vigencia},
    )


def _juntar_codigos(serie):
    """Junta os códigos distintos de um grupo em texto ('2737, 2738')."""
    return ", ".join(sorted({x for x in serie if x}, key=lambda c: (len(c), c)))


def preparar(df):
    """Limpa nulos, remove duplicatas e cria a coluna de ordenação das faixas."""
    df = df.copy()
    for c in CHAVES:
        df[c] = df[c].fillna("-").astype(str).str.strip()
    df["VALOR_PRODUTO"] = pd.to_numeric(df["VALOR_PRODUTO"], errors="coerce").fillna(0.0)
    df[COL_CODIGO] = pd.to_numeric(df[COL_CODIGO], errors="coerce").map(
        lambda v: "" if pd.isna(v) else str(int(v))
    )
    df = df.groupby(CHAVES, as_index=False).agg(
        VALOR_PRODUTO=("VALOR_PRODUTO", "first"),
        _codigo=(COL_CODIGO, _juntar_codigos),
    )
    df["_ord"] = df["FAIXA_ETARIA"].map(ordem_faixa)
    return df


def opcoes(df, coluna):
    return sorted(df[coluna].unique().tolist())


def limpar_campos():
    for key in list(st.session_state.keys()):
        if key.startswith("vidas_") or key in (
            "_vidas_backup", "desconto_combo", "desconto_manual", "contrato_input",
        ):
            del st.session_state[key]


def get_desconto_pct(opcao, manual_txt):
    if opcao == "Manual":
        texto = manual_txt.replace("%", "").replace(",", ".").strip()
        try:
            return max(float(texto), 0.0)
        except ValueError:
            return 0.0
    if opcao.endswith("%"):
        try:
            return float(opcao.replace("%", ""))
        except ValueError:
            return 0.0
    return 0.0


def gerar_excel(info, itens, resumo):
    """Gera o .xlsx em memória. Retorna None se o openpyxl não estiver instalado."""
    try:
        buf = io.BytesIO()
        df_itens = pd.DataFrame(itens, columns=["Faixa Etária", "Valor Base", "Vidas", "Valor por Faixa"])
        df_resumo = pd.DataFrame(list(info.items()) + list(resumo.items()), columns=["Campo", "Valor"])
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df_resumo.to_excel(writer, sheet_name="Resumo", index=False)
            df_itens.to_excel(writer, sheet_name="Faixas", index=False)
            for ws in writer.sheets.values():
                for col in ws.columns:
                    largura = max(len(str(c.value)) if c.value is not None else 0 for c in col)
                    ws.column_dimensions[col[0].column_letter].width = min(largura + 3, 45)
        return buf.getvalue()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# CARGA DOS DADOS (sempre a vigência mais recente)
# ---------------------------------------------------------------------------
st.markdown('<div class="titulo-app">Simulador de Plano de Saúde</div>', unsafe_allow_html=True)

usando_exemplo = False
vigencia_atual = "dados de exemplo"
try:
    vigencias = listar_vigencias()
    if not vigencias:
        raise ValueError("A tabela não retornou nenhuma vigência.")
    vigencia_atual = vigencias[0]
    df_raw = carregar_precos(vigencia_atual)
except Exception as e:
    usando_exemplo = True
    st.warning(f"Não consegui ler o Supabase, usando dados de exemplo. Detalhe: {e}")
    df_raw = dados_exemplo()

df_all = preparar(df_raw)

if df_all.empty:
    st.error("Nenhum dado de preço disponível.")
    st.stop()

# ---------------------------------------------------------------------------
# LAYOUT: esquerda = filtros + vidas | direita = desconto, contrato e resultado
# ---------------------------------------------------------------------------
col_esq, col_dir = st.columns([3, 1.25], gap="large")

total_base = 0.0
total_vidas = 0
itens = []  # faixas com vidas > 0 (para exportação)

with col_esq:
    # ---- Filtros em cascata ----
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="field-label">CIDADE (FILIAL)</div>', unsafe_allow_html=True)
        cidade = st.selectbox("Cidade", opcoes(df_all, "FILIAL"), key="cidade_combo", label_visibility="collapsed")
    df_c = df_all[df_all["FILIAL"] == cidade]

    with c2:
        st.markdown('<div class="field-label">TIPO DO PLANO</div>', unsafe_allow_html=True)
        tipo = st.selectbox("Tipo", opcoes(df_c, "TIPO_PLANO"), key="tipo_combo", label_visibility="collapsed")
    df_t = df_c[df_c["TIPO_PLANO"] == tipo]

    with c3:
        st.markdown('<div class="field-label">PLANO</div>', unsafe_allow_html=True)
        plano = st.selectbox("Plano", opcoes(df_t, "PLANO"), key="plano_combo", label_visibility="collapsed")
    df_p = df_t[df_t["PLANO"] == plano]

    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown('<div class="field-label">SEGMENTAÇÃO</div>', unsafe_allow_html=True)
        seg = st.selectbox("Segmentação", opcoes(df_p, "SEGMENTACAO"), key="seg_combo", label_visibility="collapsed")
    df_s = df_p[df_p["SEGMENTACAO"] == seg]

    with c5:
        st.markdown('<div class="field-label">COPARTICIPAÇÃO</div>', unsafe_allow_html=True)
        copart = st.selectbox("Coparticipação", opcoes(df_s, COL_COPART), key="copart_combo", label_visibility="collapsed")
    df_cp = df_s[df_s[COL_COPART] == copart]

    with c6:
        st.markdown('<div class="field-label">ACOMODAÇÃO</div>', unsafe_allow_html=True)
        acom = st.selectbox("Acomodação", opcoes(df_cp, "ACOMODACAO"), key="acom_combo", label_visibility="collapsed")

    linhas = df_cp[df_cp["ACOMODACAO"] == acom].sort_values("_ord")

    codigos = sorted(
        {c.strip() for s in linhas["_codigo"] for c in s.split(",") if c.strip()},
        key=lambda c: (len(c), c),
    )
    codigo_txt = ", ".join(codigos) if codigos else "—"

    st.markdown("<hr>", unsafe_allow_html=True)

    # ---- Resumo da seleção ----
    st.markdown(
        f"""
        <div class="resumo-sel">
            <div class="pill"><span class="k">CIDADE</span><span class="v">{cidade}</span></div>
            <div class="pill"><span class="k">TIPO</span><span class="v">{tipo}</span></div>
            <div class="pill"><span class="k">PLANO</span><span class="v">{plano}</span></div>
            <div class="pill"><span class="k">SEGMENTAÇÃO</span><span class="v">{seg}</span></div>
            <div class="pill"><span class="k">COPARTICIPAÇÃO</span><span class="v">{copart}</span></div>
            <div class="pill"><span class="k">ACOMODAÇÃO</span><span class="v">{acom}</span></div>
            <div class="pill" style="border-color:#4d6fe0;"><span class="k">CÓD. PRODUTO</span><span class="v">{codigo_txt}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Tabela de faixas / vidas ----
    larguras = [2.5, 2, 1.6, 2.5]
    backup = st.session_state.setdefault("_vidas_backup", {})

    with st.container(key="tabela"):
        for c, h in zip(st.columns(larguras), ["Faixa Etária", "Valor Base", "Vidas", "Valor por Faixa"]):
            c.markdown(f'<div class="tabela-header">{h}</div>', unsafe_allow_html=True)

        for i, r in enumerate(linhas.itertuples(index=False)):
            faixa, valor_base = r.FAIXA_ETARIA, float(r.VALOR_PRODUTO)
            alt = " alt" if i % 2 else ""

            # A chave depende só da faixa: as vidas são reaproveitadas ao trocar de plano.
            wkey = f"vidas_{faixa}"
            if wkey not in st.session_state:
                st.session_state[wkey] = backup.get(faixa, 0)

            cols = st.columns(larguras)
            cols[0].markdown(f'<div class="tabela-row{alt}">{faixa}</div>', unsafe_allow_html=True)
            cols[1].markdown(
                f'<div class="tabela-row valor{alt}">{formatar_moeda(valor_base)}</div>', unsafe_allow_html=True
            )
            vidas = cols[2].number_input(
                f"Vidas {faixa}", min_value=0, max_value=9999, step=1,
                key=wkey, label_visibility="collapsed",
            )
            backup[faixa] = vidas

            valor_faixa = valor_base * vidas
            total_base += valor_faixa
            total_vidas += vidas
            if vidas > 0:
                itens.append((faixa, valor_base, vidas, valor_faixa))

            classe_valor = "destaque" if vidas > 0 else f"valor{alt}"
            cols[3].markdown(
                f'<div class="tabela-row {classe_valor}">{formatar_moeda(valor_faixa)}</div>',
                unsafe_allow_html=True,
            )

        if not linhas.empty:
            tcols = st.columns(larguras)
            tcols[0].markdown('<div class="tabela-total rotulo">TOTAL</div>', unsafe_allow_html=True)
            tcols[1].markdown('<div class="tabela-total"></div>', unsafe_allow_html=True)
            tcols[2].markdown(f'<div class="tabela-total">{total_vidas}</div>', unsafe_allow_html=True)
            tcols[3].markdown(f'<div class="tabela-total">{formatar_moeda(total_base)}</div>', unsafe_allow_html=True)

    if linhas.empty:
        st.info("Nenhuma faixa etária disponível para a combinação selecionada.")

    _, col_limpar = st.columns([4, 1.3])
    with col_limpar:
        st.button("Limpar campos", on_click=limpar_campos, use_container_width=True)

# ---------------------------------------------------------------------------
# PAINEL DA DIREITA: desconto, contrato atual, resultado e exportação
# ---------------------------------------------------------------------------
with col_dir:
    with st.container(key="resumo"):
        st.markdown('<div class="field-label">DESCONTO A SER APLICADO (%)</div>', unsafe_allow_html=True)
        desconto_opcao = st.selectbox(
            "Desconto", ["Sem desconto", "5%", "10%", "15%", "20%", "Manual"],
            key="desconto_combo", label_visibility="collapsed",
        )
        desconto_manual_txt = ""
        if desconto_opcao == "Manual":
            desconto_manual_txt = st.text_input(
                "Manual (%)", key="desconto_manual", placeholder="Ex: 12,5", label_visibility="collapsed",
            )

        st.markdown('<div class="field-label" style="margin-top:8px;">VALOR DO CONTRATO ATUAL (R$)</div>',
                    unsafe_allow_html=True)
        contrato_txt = st.text_input(
            "Contrato atual", key="contrato_input", placeholder="Ex: 15.000,00", label_visibility="collapsed",
        )
        contrato_atual = parse_moeda(contrato_txt)
        if contrato_atual is None:
            st.caption("⚠️ Valor inválido. Use o formato 15.000,00")
            contrato_atual = 0.0

        # ---- Cálculos ----
        desconto_pct = get_desconto_pct(desconto_opcao, desconto_manual_txt)
        total_comercial = total_base * (1 - desconto_pct / 100)
        media_vida = total_comercial / total_vidas if total_vidas else 0.0

        # ---- Card de resultado ----
        if total_vidas == 0:
            card_corpo = '<div class="total-vazio">Informe as vidas na tabela<br>para calcular o contrato</div>'
            valor_cor = "#9fb0e8"
            valor_txt = "—"
            comparativo_html = ""
            stats_html = ""
        else:
            valor_txt = formatar_moeda(total_comercial)
            valor_cor = "#f2b134"
            comparativo_html = ""
            stats = [
                ("Total de vidas", str(total_vidas)),
                ("Valor médio por vida", formatar_moeda(media_vida)),
                ("Valor de tabela (sem desconto)", formatar_moeda(total_base)),
            ]
            if desconto_pct > 0:
                stats.append(("Desconto aplicado", f"{desconto_pct:.1f}%".replace(".", ",")))

            if contrato_atual > 0:
                diff_abs = total_comercial - contrato_atual
                diff_pct = (diff_abs / contrato_atual) * 100
                if diff_abs < -0.005:
                    cor, seta, status = "#3ddc84", "▼", "de economia vs. contrato atual"
                elif diff_abs > 0.005:
                    cor, seta, status = "#ff6b6b", "▲", "a mais que o contrato atual"
                else:
                    cor, seta, status = "#f2b134", "●", "igual ao contrato atual"
                valor_cor = cor
                comparativo_html = (
                    f'<div class="total-comparativo" style="color:{cor};">'
                    f'{seta} {formatar_moeda(abs(diff_abs))} ({abs(diff_pct):.1f}%) {status}</div>'
                )
                stats.append(("Contrato atual", formatar_moeda(contrato_atual)))
                if desconto_pct > 0:
                    stats.append(("Contrato atual c/ desconto", formatar_moeda(contrato_atual * (1 - desconto_pct / 100))))
                dif_tabela = ((total_base - contrato_atual) / contrato_atual) * 100
                stats.append(("Tabela vs. contrato atual", f"{dif_tabela:+.2f}%".replace(".", ",")))

            stats_html = '<div class="stats">' + "".join(
                f'<div class="stat"><span>{k}</span><b>{v}</b></div>' for k, v in stats
            ) + "</div>"
            card_corpo = (
                f'<div class="total-value" style="color:{valor_cor};">{valor_txt}</div>'
                f"{comparativo_html}{stats_html}"
            )

        st.markdown(
            f"""
            <div class="total-card">
                <div class="total-caption">VALOR DO CONTRATO COMERCIAL</div>
                {card_corpo}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ---- Exportação ----
        if total_vidas > 0:
            info = {
                "Cidade": cidade, "Tipo do plano": tipo, "Plano": plano,
                "Segmentação": seg, "Coparticipação": copart, "Acomodação": acom,
                "Código do produto": codigo_txt,
                "Tabela vigente em": vigencia_atual,
            }
            resumo = {
                "Total de vidas": total_vidas,
                "Valor de tabela": round(total_base, 2),
                "Desconto (%)": desconto_pct,
                "Valor do contrato comercial": round(total_comercial, 2),
                "Valor médio por vida": round(media_vida, 2),
            }
            if contrato_atual > 0:
                resumo["Contrato atual"] = round(contrato_atual, 2)

            xlsx = gerar_excel(info, itens, resumo)
            if xlsx:
                st.download_button(
                    "⬇️ Baixar Excel", data=xlsx, file_name="simulacao_plano_saude.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            with st.expander("📋 Resumo para copiar"):
                linhas_txt = [
                    "SIMULAÇÃO DE PLANO DE SAÚDE",
                    f"Cidade: {cidade} | Tipo: {tipo}",
                    f"Plano: {plano}",
                    f"Segmentação: {seg} | Coparticipação: {copart}",
                    f"Acomodação: {acom}",
                    f"Código do produto: {codigo_txt}",
                    f"Tabela vigente em: {vigencia_atual}",
                    "",
                ]
                for faixa, vb, v, vf in itens:
                    linhas_txt.append(f"{faixa}: {v} vida(s) x {formatar_moeda(vb)} = {formatar_moeda(vf)}")
                linhas_txt += [
                    "",
                    f"Total de vidas: {total_vidas}",
                    f"Valor de tabela: {formatar_moeda(total_base)}",
                ]
                if desconto_pct > 0:
                    linhas_txt.append(f"Desconto: {desconto_pct:.1f}%".replace(".", ","))
                linhas_txt.append(f"VALOR DO CONTRATO COMERCIAL: {formatar_moeda(total_comercial)}")
                linhas_txt.append(f"Valor médio por vida: {formatar_moeda(media_vida)}")
                if contrato_atual > 0:
                    linhas_txt.append(f"Contrato atual: {formatar_moeda(contrato_atual)}")
                st.code("\n".join(linhas_txt), language=None)

# ---------------------------------------------------------------------------
# RODAPÉ
# ---------------------------------------------------------------------------
st.markdown(
    f'<div class="rodape-vigencia">Tabela vigente em {vigencia_atual}</div>',
    unsafe_allow_html=True,
)