import streamlit as st

# ---------------------------------------------------------------------------
# BASE DE DADOS
# ---------------------------------------------------------------------------
DADOS = {
    "FORTALEZA": {
        "NOSSO PLANO": {
            "AMBULATORIAL": {
                "COM COPART": {
                    "S/ACOM": [
                        ("00 a 18 anos", 122.75),
                        ("19 a 23 anos", 137.48),
                        ("24 a 28 anos", 153.98),
                        ("29 a 33 anos", 177.08),
                        ("34 a 38 anos", 203.64),
                        ("39 a 43 anos", 242.33),
                        ("44 a 48 anos", 302.91),
                        ("49 a 53 anos", 388.54),
                        ("54 a 58 anos", 643.69),
                        ("59 anos ou mais", 720.93),
                    ]
                }
            }
        }
    }
}

CIDADES = list(DADOS.keys())


def formatar_moeda(valor):
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "§").replace(".", ",").replace("§", ".")
    return f"R$ {texto}"


def get_opcoes(cidade, nivel, tipo=None, seg=None, mod=None):
    try:
        d = DADOS[cidade]
        if nivel == "tipo":
            return list(d.keys())
        d = d[tipo]
        if nivel == "seg":
            return list(d.keys())
        d = d[seg]
        if nivel == "mod":
            return list(d.keys())
        d = d[mod]
        if nivel == "acom":
            return list(d.keys())
    except KeyError:
        return []
    return []


# ---------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA E CSS REVISADO
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Simulador de Plano de Saúde",
    page_icon="💙",
    layout="wide",
)

CSS = """
<style>
    .stApp {
        background-color: #0b1530;
    }

    .titulo-app {
        color: #ffffff;
        font-size: 26px;
        font-weight: 700;
        text-align: center;
        padding: 6px 0 14px 0;
    }

    .field-label {
        color: #c9d3ee;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }

    .readonly-field {
        background-color: #16224a;
        color: #8ea1e0;
        border: 1px solid #2b3c72;
        border-radius: 8px;
        padding: 8px 10px;
        font-weight: 600;
        text-align: center;
    }

    /* Card de destaque do Valor Comercial */
    .total-card {
        background: linear-gradient(180deg, #16227a 0%, #0e1a5c 100%);
        border-top: 2px solid #4d6fe0;
        border-radius: 16px;
        padding: 18px 24px 20px 24px;
        text-align: center;
        margin-top: 20px;
        box-shadow: 0 -4px 28px rgba(0,0,0,0.4);
    }
    .total-caption {
        color: #9fb0e8;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 1.5px;
    }
    .total-value {
        font-size: 34px;
        font-weight: 800;
        color: #f2b134;
        margin: 4px 0;
    }
    .total-comparativo {
        font-size: 13px;
        font-weight: 600;
        padding-top: 2px;
    }

    /* Selects */
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        border-radius: 8px !important;
        border: 1px solid #c7cfe8 !important;
    }
    div[data-baseweb="select"] span {
        color: #12213f !important;
        font-weight: 600 !important;
    }

    /* Inputs gerais */
    .stTextInput input, .stNumberInput input {
        background-color: #16224a !important;
        color: #ffffff !important;
        border: 1px solid #2b3c72 !important;
        border-radius: 8px !important;
    }

    /* NOVO DESIGN DA TABELA DE PREÇOS */
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        border-radius: 12px;
        overflow: hidden;
        background-color: #111c3a;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        margin-bottom: 10px;
    }

    .custom-table th {
        background-color: #1c2a58;
        color: #c9d3ee;
        font-weight: 700;
        font-size: 13px;
        padding: 12px 14px;
        text-align: center;
        border-bottom: 2px solid #4d6fe0;
    }

    .custom-table td {
        padding: 10px 14px;
        color: #e2e8f0;
        font-size: 13px;
        text-align: center;
        border-bottom: 1px solid #1c2a58;
    }

    /* Efeito de listra e hover nas linhas */
    .custom-table tr:nth-child(even) {
        background-color: #16234b;
    }
    .custom-table tr:hover {
        background-color: #1e2d5e;
    }

    .subtotal-highlight {
        color: #3ddc84;
        font-weight: 700;
    }

    /* Ajuste para alinhar o input na tabela */
    div[data-testid="stColumn"] {
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* Botão Limpar Campos */
    div.stButton > button {
        background-color: #e15b4f;
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 8px 18px;
    }
    div.stButton > button:hover {
        background-color: #c94a3f;
        color: white;
    }

    hr {
        border-color: #23305c;
    }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# ESTADO INICIAL / LIMPAR CAMPOS
# ---------------------------------------------------------------------------
def limpar_campos():
    for key in list(st.session_state.keys()):
        if key.startswith("vidas_") or key in (
            "desconto_combo", "desconto_manual",
            "contrato_input", "contrato_slider",
        ):
            del st.session_state[key]


st.markdown('<div class="titulo-app">Simulador de Plano de Saúde</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# DESCONTO / CONTRATO ATUAL
# ---------------------------------------------------------------------------
col_desc, col_contrato = st.columns(2)

with col_desc:
    st.markdown('<div class="field-label">DESCONTO A SER APLICADO (%)</div>', unsafe_allow_html=True)
    desconto_opcao = st.selectbox(
        "Desconto", ["Selecione", "5%", "10%", "15%", "20%", "Manual"],
        key="desconto_combo", label_visibility="collapsed",
    )
    desconto_manual_txt = ""
    if desconto_opcao == "Manual":
        desconto_manual_txt = st.text_input(
            "Manual (%)", key="desconto_manual", placeholder="Ex: 12,5",
            label_visibility="collapsed",
        )

with col_contrato:
    st.markdown('<div class="field-label">VALOR DO CONTRATO ATUAL (R$)</div>', unsafe_allow_html=True)

    def _sync_from_input():
        st.session_state.contrato_slider = int(st.session_state.contrato_input)

    def _sync_from_slider():
        st.session_state.contrato_input = float(st.session_state.contrato_slider)

    if "contrato_input" not in st.session_state:
        st.session_state.contrato_input = 0.0
    if "contrato_slider" not in st.session_state:
        st.session_state.contrato_slider = 0

    st.number_input(
        "Valor do contrato atual", min_value=0.0, step=50.0, format="%.2f",
        key="contrato_input", on_change=_sync_from_input,
        label_visibility="collapsed",
    )
    st.slider(
        "Slider contrato atual", min_value=0, max_value=50000,
        key="contrato_slider", on_change=_sync_from_slider,
        label_visibility="collapsed",
    )

contrato_atual = st.session_state.contrato_input

st.markdown("<hr>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# FILTROS
# ---------------------------------------------------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="field-label">CIDADE</div>', unsafe_allow_html=True)
    cidade = st.selectbox("Cidade", CIDADES, key="cidade_combo", label_visibility="collapsed")
with col2:
    st.markdown('<div class="field-label">TIPO DO PLANO</div>', unsafe_allow_html=True)
    tipos = get_opcoes(cidade, "tipo")
    tipo = st.selectbox("Tipo", tipos, key="tipo_combo", label_visibility="collapsed")
with col3:
    st.markdown('<div class="field-label">SEGMENTAÇÃO</div>', unsafe_allow_html=True)
    segs = get_opcoes(cidade, "seg", tipo=tipo)
    seg = st.selectbox("Segmentação", segs, key="seg_combo", label_visibility="collapsed")

col4, col5 = st.columns(2)
with col4:
    st.markdown('<div class="field-label">MODALIDADE</div>', unsafe_allow_html=True)
    mods = get_opcoes(cidade, "mod", tipo=tipo, seg=seg)
    mod = st.selectbox("Modalidade", mods, key="mod_combo", label_visibility="collapsed")
with col5:
    st.markdown('<div class="field-label">ACOMODAÇÃO</div>', unsafe_allow_html=True)
    acoms = get_opcoes(cidade, "acom", tipo=tipo, seg=seg, mod=mod)
    acom = st.selectbox("Acomodação", acoms, key="acom_combo", label_visibility="collapsed")

col_btn = st.columns([4, 1])[1]
with col_btn:
    st.button("Limpar Campos", on_click=limpar_campos, use_container_width=True)

try:
    linhas = DADOS[cidade][tipo][seg][mod][acom]
except KeyError:
    linhas = []

st.markdown("<hr>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# TABELA REDESENHADA (Design Unificado e Limpo)
# ---------------------------------------------------------------------------
total_base = 0.0

if linhas:
    # 1. Estrutura do Cabeçalho da Tabela
    st.markdown("""
    <table class="custom-table">
        <thead>
            <tr>
                <th style="width: 15%;">Cidade</th>
                <th style="width: 15%;">Plano</th>
                <th style="width: 15%;">Segmentação</th>
                <th style="width: 15%;">Faixa Etária</th>
                <th style="width: 15%;">Valor Base</th>
                <th style="width: 10%;">Vidas</th>
                <th style="width: 15%;">Valor por Faixa</th>
            </tr>
        </thead>
    </table>
    """, unsafe_allow_html=True)

    # 2. Linhas de Dados Integrando os Inputs
    for i, (faixa, valor_base) in enumerate(linhas):
        row_key = f"vidas_{cidade}_{tipo}_{seg}_{mod}_{acom}_{faixa}"
        
        # Pega a quantidade de vidas salva no session_state
        vidas = st.session_state.get(row_key, 0)
        valor_faixa = valor_base * vidas
        total_base += valor_faixa

        cols = st.columns([1.5, 1.5, 1.5, 1.5, 1.5, 1.0, 1.5])
        
        cols[0].markdown(f'<div style="text-align:center; color:#e2e8f0; font-size:13px;">{cidade}</div>', unsafe_allow_html=True)
        cols[1].markdown(f'<div style="text-align:center; color:#e2e8f0; font-size:13px;">{tipo}</div>', unsafe_allow_html=True)
        cols[2].markdown(f'<div style="text-align:center; color:#e2e8f0; font-size:13px;">{seg}</div>', unsafe_allow_html=True)
        cols[3].markdown(f'<div style="text-align:center; color:#e2e8f0; font-size:13px;">{faixa}</div>', unsafe_allow_html=True)
        cols[4].markdown(f'<div style="text-align:center; color:#e2e8f0; font-size:13px;">{formatar_moeda(valor_base)}</div>', unsafe_allow_html=True)
        
        # Campo de input estilizado dentro do grid
        cols[5].number_input(
            f"Vidas {i}", min_value=0, max_value=9999, value=vidas, step=1,
            key=row_key, label_visibility="collapsed"
        )
        
        cols[6].markdown(f'<div style="text-align:center; color:#3ddc84; font-weight:700; font-size:13px;">{formatar_moeda(valor_faixa)}</div>', unsafe_allow_html=True)

else:
    st.info("Nenhuma faixa etária disponível para a combinação selecionada.")

# ---------------------------------------------------------------------------
# CÁLCULOS
# ---------------------------------------------------------------------------
def get_desconto_pct():
    if desconto_opcao == "Manual":
        texto = desconto_manual_txt.replace("%", "").replace(",", ".").strip()
        try:
            return float(texto)
        except ValueError:
            return 0.0
    if desconto_opcao.endswith("%"):
        try:
            return float(desconto_opcao.replace("%", ""))
        except ValueError:
            return 0.0
    return 0.0


desconto_pct = get_desconto_pct()
total_comercial = total_base * (1 - desconto_pct / 100)

st.markdown("<hr>", unsafe_allow_html=True)

col_dif, col_valdesc = st.columns(2)

if contrato_atual and contrato_atual > 0:
    diferenca = ((total_base - contrato_atual) / contrato_atual) * 100
    valor_com_desconto = contrato_atual * (1 - desconto_pct / 100)

    with col_dif:
        st.markdown('<div class="field-label">DIFERENÇA PERCENTUAL</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="readonly-field">{diferenca:.2f}%</div>', unsafe_allow_html=True)
    with col_valdesc:
        st.markdown('<div class="field-label">VALOR ATUAL COM DESCONTO</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="readonly-field">{formatar_moeda(valor_com_desconto)}</div>', unsafe_allow_html=True)

    diff_abs = total_comercial - contrato_atual
    diff_pct = (diff_abs / contrato_atual) * 100
    if diff_abs < -0.005:
        cor, seta, status = "#3ddc84", "▼", "a menos que o contrato atual"
    elif diff_abs > 0.005:
        cor, seta, status = "#ff6b6b", "▲", "a mais que o contrato atual"
    else:
        cor, seta, status = "#f2b134", "●", "igual ao contrato atual"

    comparativo_html = (
        f'<div class="total-comparativo" style="color:{cor};">'
        f'{seta} {formatar_moeda(abs(diff_abs))}  ({abs(diff_pct):.1f}%)  {status}</div>'
    )
    valor_cor = cor
else:
    with col_dif:
        st.markdown('<div class="field-label">DIFERENÇA PERCENTUAL</div>', unsafe_allow_html=True)
        st.markdown('<div class="readonly-field">--%</div>', unsafe_allow_html=True)
    with col_valdesc:
        st.markdown('<div class="field-label">VALOR ATUAL COM DESCONTO</div>', unsafe_allow_html=True)
        st.markdown('<div class="readonly-field">--</div>', unsafe_allow_html=True)
    comparativo_html = ""
    valor_cor = "#f2b134"

# ---------------------------------------------------------------------------
# RODAPÉ
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="total-card">
        <div class="total-caption">VALOR DO CONTRATO COMERCIAL</div>
        <div class="total-value" style="color:{valor_cor};">{formatar_moeda(total_comercial)}</div>
        {comparativo_html}
    </div>
    """,
    unsafe_allow_html=True,
)