import streamlit as st
import matplotlib.pyplot as plt

# --- Parâmetros ajustáveis ---
horas = st.slider("Duração da simulação (h)", 24, 168, 72)

vazao_poco = st.number_input("Vazão do Poço (m³/h)", min_value=0.0, value=10.0, step=0.5)
vazao_trat = st.number_input("Vazão do Tratamento (m³/h)", min_value=0.0, value=5.5, step=0.5)
vazao_recalque = st.number_input("Vazão do Recalque (m³/h)", min_value=0.0, value=7.5, step=0.5)

# --- Configuração das boias ---
with st.expander("Reservatório Água Bruta"):
    boia_poco_on = st.number_input("Poço (Água Bruta) - ARME (m³)", value=10.0, step=0.5)
    boia_poco_off = st.number_input("Poço (Água Bruta) - DESARME (m³)", value=13.0, step=0.5)
    boia_trat_on_bruta = st.number_input("Tratamento (Água Bruta) - ARME (m³)", value=6.0, step=0.5)
    boia_trat_off_bruta = st.number_input("Tratamento (Água Bruta) - DESARME (m³)", value=5.0, step=0.5)

with st.expander("Reservatório Água Tratada"):
    boia_trat_on_tratada = st.number_input("Tratamento (Água Tratada) - ARME (m³)", value=6.0, step=0.5)
    boia_trat_off_tratada = st.number_input("Tratamento (Água Tratada) - DESARME (m³)", value=5.0, step=0.5)
    boia_recalque_on = st.number_input("Recalque (Água Tratada) - ARME (m³)", value=10.0, step=0.5)
    boia_recalque_off = st.number_input("Recalque (Água Tratada) - DESARME (m³)", value=5.0, step=0.5)

with st.expander("Reservatório Principal"):
    boia_principal_on = st.number_input("Recalque (Principal) - ARME (m³)", value=90.0, step=0.5)
    boia_principal_off = st.number_input("Recalque (Principal) - DESARME (m³)", value=100.0, step=0.5)

with st.expander("Reservatório C (Retrolavagem)"):
    boia_C_on = st.number_input("Retrolavagem - ARME (m³)", value=5.0, step=0.5)
    boia_C_off = st.number_input("Retrolavagem - DESARME (m³)", value=15.0, step=0.5)

# --- Função de consumo dinâmico ---
def consumo_populacao(hora):
    if 0 <= hora <= 5:      return 2.0
    elif 6 <= hora <= 10:   return 4.5
    elif 11 <= hora <= 13:  return 6.0
    elif 14 <= hora <= 17:  return 4.0
    elif 18 <= hora <= 22:  return 5.5
    else:                   return 3.0

# --- Inicialização ---
A, B, C, Principal = boia_poco_off, boia_recalque_on, boia_C_off, 100
poco_ligado = False
tratamento_ligado = False
recalque_ligado = False

# Histórico
hist_A, hist_B, hist_C, hist_Principal = [A], [B], [C], [Principal]
bloqueios_recalque = []

# Contadores
horas_poco = horas_tratamento = horas_recalque = 0
partidas_poco = partidas_tratamento = partidas_recalque = 0

# --- Simulação ---
for t in range(1, horas+1):
    hora_do_dia = t % 24

    # Consumo
    Principal -= consumo_populacao(hora_do_dia)
    if Principal < 0: Principal = 0

    # Poço
    if A <= boia_poco_on and not poco_ligado:
        poco_ligado = True
        partidas_poco += 1
    if A >= boia_poco_off and poco_ligado:
        poco_ligado = False
    entrada_poco = vazao_poco if poco_ligado else 0
    if poco_ligado: horas_poco += 1

    # Tratamento
    if A <= boia_trat_off_bruta and tratamento_ligado:
        tratamento_ligado = False
    if A >= boia_trat_on_bruta and (B < boia_recalque_on or C < boia_C_off) and not tratamento_ligado:
        tratamento_ligado = True
        partidas_tratamento += 1
    saida_trat = vazao_trat if tratamento_ligado else 0
    if tratamento_ligado: horas_tratamento += 1

    if tratamento_ligado:
        if B < boia_recalque_on and C < boia_C_off:
            B += saida_trat/2; C += saida_trat/2
        elif B < boia_recalque_on: B += saida_trat
        elif C < boia_C_off: C += saida_trat

    # Retrolavagem
    if hora_do_dia in [0,1]: C -= 5; tratamento_ligado = False
    elif hora_do_dia == 12: C -= 8; tratamento_ligado = False
    if C < boia_C_on: C = boia_C_on

    # Balanço
    A += entrada_poco - saida_trat
    A = min(max(A,0), boia_poco_off); B = min(B, boia_recalque_on); C = min(C, boia_C_off)

    # Recalque
    if Principal <= boia_principal_on and B > boia_recalque_off and not recalque_ligado:
        recalque_ligado = True
        partidas_recalque += 1

    if recalque_ligado:
        falta = boia_principal_off - Principal
        capacidade_b = max(0, B - boia_recalque_off)
        bombeado = min(vazao_recalque, falta, capacidade_b)
        Principal += bombeado; B -= bombeado
        if bombeado > 0: horas_recalque += 1
        if Principal >= boia_principal_off: recalque_ligado = False
        if B <= boia_recalque_off:
            bloqueios_recalque.append((t, Principal))
            recalque_ligado = False

    # Histórico
    hist_A.append(A); hist_B.append(B); hist_C.append(C); hist_Principal.append(Principal)

# --- Gráfico ---
fig, ax = plt.subplots(figsize=(14,7))
ax.plot(hist_A, label="Reservatório A (Água Bruta)")
ax.plot(hist_B, label="Reservatório B (Água Tratada)")
ax.plot(hist_C, label="Reservatório C (Retrolavagem)")
ax.plot(hist_Principal, label="Principal", color="red")

if bloqueios_recalque:
    bx, by = zip(*bloqueios_recalque)
    ax.scatter(bx, by, color="red", marker="o", label="Bloqueio Recalque")

ax.legend(); ax.grid(True)
ax.set_xticks(range(0, horas+1, 5))
ax.set_xlabel("Tempo (horas)")
ax.set_ylabel("Volume (m³)")
ax.set_title("Simulação Integrada - Consumo Dinamico")

plt.subplots_adjust(bottom=0.25)

# Texto com contadores
texto = (
    f"Partidas ({horas}h): Poço={partidas_poco}, Recalque={partidas_recalque}, Tratamento={partidas_tratamento}\n"
    f"Horas ligadas ({horas}h): Poço={horas_poco}, Recalque={horas_recalque}, Tratamento={horas_tratamento}"
)
fig.text(0.5, 0.12, texto, ha="center", fontsize=10, bbox=dict(facecolor='white', alpha=0.7))

st.pyplot(fig)
