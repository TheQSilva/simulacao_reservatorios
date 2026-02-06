import streamlit as st
import matplotlib.pyplot as plt

# --- Parâmetros ajustáveis ---
horas = st.slider("Duração da simulação (h)", 24, 168, 72)

vazao_poco = st.number_input("Vazão do Poço (m³/h)", min_value=0.0, value=10.0, step=0.5)
vazao_trat = st.number_input("Vazão do Tratamento (m³/h)", min_value=0.0, value=5.5, step=0.5)
vazao_recalque = st.number_input("Vazão do Recalque (m³/h)", min_value=0.0, value=7.5, step=0.5)

# Função de consumo dinâmico
def consumo_populacao(hora):
    if 0 <= hora <= 5:      return 2.0
    elif 6 <= hora <= 10:   return 4.5
    elif 11 <= hora <= 13:  return 6.0
    elif 14 <= hora <= 17:  return 4.0
    elif 18 <= hora <= 22:  return 5.5
    else:                   return 3.0

# Inicialização
A, B, C, Principal = 13, 15, 15, 100
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
    if A <= 10 and not poco_ligado:
        poco_ligado = True
        partidas_poco += 1
    if A >= 13 and poco_ligado:
        poco_ligado = False
    entrada_poco = vazao_poco if poco_ligado else 0
    if poco_ligado: horas_poco += 1

    # Tratamento
    if A <= 5 and tratamento_ligado:
        tratamento_ligado = False
    if A >= 6 and (B < 15 or C < 15) and not tratamento_ligado:
        tratamento_ligado = True
        partidas_tratamento += 1
    saida_trat = vazao_trat if tratamento_ligado else 0
    if tratamento_ligado: horas_tratamento += 1

    if tratamento_ligado:
        if B < 15 and C < 15:
            B += saida_trat/2; C += saida_trat/2
        elif B < 15: B += saida_trat
        elif C < 15: C += saida_trat

    # Retrolavagem
    if hora_do_dia in [0,1]: C -= 5; tratamento_ligado = False
    elif hora_do_dia == 12: C -= 8; tratamento_ligado = False
    if C < 5: C = 5

    # Balanço
    A += entrada_poco - saida_trat
    A = min(max(A,0),13); B = min(B,15); C = min(C,15)

    # Recalque
    if Principal <= 90 and B > 5 and boia_B_armada and not recalque_ligado:
        recalque_ligado = True
        partidas_recalque += 1

    if recalque_ligado:
        falta = 100 - Principal
        capacidade_b = max(0, B - 5)
        bombeado = min(vazao_recalque, falta, capacidade_b)
        Principal += bombeado; B -= bombeado
        if bombeado > 0: horas_recalque += 1
        if Principal >= 100: recalque_ligado = False
        if B <= 5:
            bloqueios_recalque.append((t, Principal))
            boia_B_armada = False; recalque_ligado = False

    if B >= 10: boia_B_armada = True

    # Histórico
    hist_A.append(A); hist_B.append(B); hist_C.append(C); hist_Principal.append(Principal)

# --- Gráfico ---
fig, ax = plt.subplots(figsize=(14,7))
ax.plot(hist_A, label="Reservatório A")
ax.plot(hist_B, label="Reservatório B")
ax.plot(hist_C, label="Reservatório C")
ax.plot(hist_Principal, label="Principal", color="red")

if bloqueios_recalque:
    bx, by = zip(*bloqueios_recalque)
    ax.scatter(bx, by, color="red", marker="o", label="Bloqueio Recalque")

ax.axhline(y=5, color="gray", linestyle="--", linewidth=1)
ax.axhline(y=13, color="gray", linestyle="--", linewidth=1)
ax.axhline(y=15, color="gray", linestyle="--", linewidth=1)

ax.legend(); ax.grid(True)
ax.set_xticks(range(0, horas+1, 5))
ax.set_yticks(sorted(set(list(range(0,101,10))+[5,13,15])))
ax.set_xlabel("Tempo (horas)")
ax.set_ylabel("Volume (m³)")
ax.set_title("Simulação Integrada - Consumo Dinamico")

texto = (f"Partidas ({horas}h): Poço={partidas_poco}, Recalque={partidas_recalque}, Tratamento={partidas_tratamento}\n"
         f"Horas ligadas ({horas}h): Poço={horas_poco}, Recalque={horas_recalque}, Tratamento={horas_tratamento}")
fig.text(0.5, 0.02, texto, ha="center", fontsize=10, bbox=dict(facecolor='white', alpha=0.7))

st.pyplot(fig)
