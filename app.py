import streamlit as st
import matplotlib.pyplot as plt

# --- Parâmetros ajustáveis ---
horas = st.slider("Duração da simulação (h)", 24, 168, 72)

vazao_poco = st.number_input("Vazão do Poço (m³/h)", min_value=0.0, value=10.0, step=0.5)
vazao_trat = st.number_input("Vazão do Tratamento (m³/h)", min_value=0.0, value=5.5, step=0.5)
vazao_recalque = st.number_input("Vazão do Recalque (m³/h)", min_value=0.0, value=7.5, step=0.5)

# --- Configuração das boias ---
with st.expander("Reservatório Água Bruta"):
    boia_A_on = st.number_input("Boia do Poço - nível de ARME (m³)", min_value=0.0, value=10.0, step=0.5)
    boia_A_off = st.number_input("Boia do Poço - nível de DESARME (m³)", min_value=0.0, value=13.0, step=0.5)

with st.expander("Boia do Tratamento"):
    boia_trat_on = st.number_input("Boia Tratamento - nível de ARME (m³)", min_value=0.0, value=6.0, step=0.5)
    boia_trat_off = st.number_input("Boia Tratamento - nível de DESARME (m³)", min_value=0.0, value=5.0, step=0.5)

with st.expander("Reservatório B (Recalque)"):
    boia_B_min = st.number_input("Boia B - mínimo para recalque (m³)", min_value=0.0, value=5.0, step=0.5)
    boia_B_armar = st.number_input("Boia B - armar recalque (m³)", min_value=0.0, value=10.0, step=0.5)

with st.expander("Reservatório C"):
    boia_C_min = st.number_input("Boia C - mínimo (m³)", min_value=0.0, value=5.0, step=0.5)
    boia_C_max = st.number_input("Boia C - máximo (m³)", min_value=0.0, value=15.0, step=0.5)

# --- Função de consumo dinâmico ---
def consumo_populacao(hora):
    if 0 <= hora <= 5:      return 2.0
    elif 6 <= hora <= 10:   return 4.5
    elif 11 <= hora <= 13:  return 6.0
    elif 14 <= hora <= 17:  return 4.0
    elif 18 <= hora <= 22:  return 5.5
    else:                   return 3.0

# --- Inicialização ---
A, B, C, Principal = boia_A_off, boia_B_armar, boia_C_max, 100
poco_ligado = False
tratamento_ligado = False
boia_B_armada = True
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
    if A <= boia_A_on and not poco_ligado:
        poco_ligado = True
        partidas_poco += 1
    if A >= boia_A_off and poco_ligado:
        poco_ligado = False
    entrada_poco = vazao_poco if poco_ligado else 0
    if poco_ligado: horas_poco += 1

    # Tratamento
    if A <= boia_trat_off and tratamento_ligado:
        tratamento_ligado = False
    if A >= boia_trat_on and (B < boia_B_armar or C < boia_C_max) and not tratamento_ligado:
        tratamento_ligado = True
        partidas_tratamento += 1
    saida_trat = vazao_trat if tratamento_ligado else 0
    if tratamento_ligado: horas_tratamento += 1

    if tratamento_ligado:
        if B < boia_B_armar and C < boia_C_max:
            B += saida_trat/2; C += saida_trat/2
        elif B < boia_B_armar: B += saida_trat
        elif C < boia_C_max: C += saida_trat

    # Retrolavagem
    if hora_do_dia in [0,1]: C -= 5; tratamento_ligado = False
    elif hora_do_dia == 12: C -= 8; tratamento_ligado = False
    if C < boia_C_min: C = boia_C_min

    # Balanço
    A += entrada_poco - saida_trat
    A = min(max(A,0), boia_A_off); B = min(B, boia_B_armar); C = min(C, boia_C_max)

    # Recalque
    if Principal <= 90 and B > boia_B_min and boia_B_armada and not recalque_ligado:
        recalque_ligado = True
        partidas_recalque += 1

    if recalque_ligado:
        falta = 100 - Principal
        capacidade_b = max(0, B - boia_B_min)
        bombeado = min(vazao_recalque, falta, capacidade_b)
        Principal += bombeado; B -= bombeado
        if bombeado > 0: horas_recalque += 1
        if Principal >= 100: recalque_ligado = False
        if B <= boia_B_min:
            bloqueios_recalque.append((t, Principal))
            boia_B_armada = False; recalque_ligado = False

    if B >= boia_B_armar: boia_B_armada = True

    # Histórico
    hist_A.append(A); hist_B.append(B); hist_C.append(C); hist_Principal.append(Principal)

# --- Gráfico ---
fig, ax = plt.subplots(figsize=(14,7))
ax.plot(hist_A, label="Reservatório A (Água Bruta)")
ax.plot(hist_B, label="Reservatório B")
ax.plot(hist_C, label="Reservatório C")
ax.plot(hist_Principal, label="Principal", color="red")

if bloqueios_recalque:
    bx, by = zip(*bloqueios_recalque)
    ax.scatter(bx, by, color="red", marker="o", label="Bloqueio Recalque")

# Linhas de referência das boias
ax.axhline(y=boia_A_on, color="gray", linestyle="--", linewidth=1)
ax.axhline(y=boia_A_off, color="gray", linestyle="--", linewidth=1)
ax.axhline(y=boia_trat_on, color="blue", linestyle="--", linewidth=1)
ax.axhline(y=boia_trat_off, color="blue", linestyle="--", linewidth=1)
ax.axhline(y=boia_B_min, color="orange", linestyle="--", linewidth=1)
ax.axhline(y=boia_B_armar, color="orange", linestyle="--", linewidth=1)
ax.axhline(y=boia_C_min, color="green", linestyle="--", linewidth=1)
ax.axhline(y=boia_C_max, color="green", linestyle="--", linewidth=1)

ax.legend(); ax.grid(True)
ax.set_xticks(range(0, horas+1, 5))
ax.set_xlabel("Tempo (horas)")
ax.set_ylabel("Volume (m³)")
ax.set_title("Simulação Integrada - Consumo Dinamico")

# Ajusta margens para não sobrepor o eixo X
plt.subplots_adjust(bottom=0.25)

texto = (f"Partidas ({horas}h): Poço={partidas_poco}, Recalque={partidas_recalque}, Tratamento={partidas_tratamento}\n"
         f"Horas ligadas ({horas}h): Poço={horas_poco}, Re
