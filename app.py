import pandas as pd
import streamlit as st
st.set_page_config(layout="wide")

# Função para estimar tempos nos pontos de interesse
def estimate_time_at_positions(df, positions):
    estimated_times = {pos: None for pos in positions}
    estimated_200 = 0
    for i in range(1, len(df)):
        current_pos = df.iloc[i]['Distância']
        previous_pos = df.iloc[i - 1]['Distância']
        if current_pos == 200:
            estimated_200 = (
                df.iloc[i - 1]['Min'] * 60 +
                df.iloc[i - 1]['Segundo'] +
                df.iloc[i - 1]['Milesimos'] / 1000
            )            
        if previous_pos < current_pos:
            for pos in positions:
                if previous_pos <= pos <= current_pos and estimated_times[pos] is None:
                    time_prev = (
                        df.iloc[i - 1]['Min'] * 60 +
                        df.iloc[i - 1]['Segundo'] +
                        df.iloc[i - 1]['Milesimos'] / 1000
                    )
                    time_current = (
                        df.iloc[i]['Min'] * 60 +
                        df.iloc[i]['Segundo'] +
                        df.iloc[i]['Milesimos'] / 1000
                    )
                    estimated_time = (
                        time_prev +
                        (pos - previous_pos) * (time_current - time_prev) / (current_pos - previous_pos)
                    )
                    estimated_times[pos] = estimated_time

    estimated_times[200] = estimated_200
    return estimated_times


def calculate_cycles_and_lost_strokes(df, trecho_positions):
    """
    Calcula os ciclos de remada e as remadas perdidas, atribuindo os ciclos aos trechos
    com base na maior distância percorrida dentro do trecho.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados de remadas.
        trecho_positions (dict): Dicionário cujas chaves representam os limites dos trechos (ex.: {0: 'Trecho 1', 25: 'Trecho 2', ...}).

    Returns:
        int: Total de ciclos de remada.
        int: Total de remadas perdidas.
        dict: Dicionário com a quantidade de ciclos atribuída a cada trecho.
    """
    # Inicializar contadores
    trecho_ciclos = {trecho: 0 for trecho in trecho_positions.values()}
    cycles = 0
    lost_strokes = 0
    used_indices = set()  # Para rastrear as remadas já usadas em ciclos

    i = 0
    while i < len(df) - 1:
        # Verificar se a remada atual forma um ciclo válido com a próxima
        if (
            df.iloc[i]['Ação'] == 'Entrada'
            and df.iloc[i + 1]['Ação'] == 'Saida'
            and i not in used_indices
        ):
            current_side = df.iloc[i]['Pá do remo']  # Identifica o lado da remada

            # Verificar se a próxima remada é do lado oposto
            if i + 3 < len(df) and df.iloc[i + 2]['Ação'] == 'Entrada' and df.iloc[i + 3]['Ação'] == 'Saida':
                if df.iloc[i + 2]['Pá do remo'] != current_side:
                    # Encontrou um ciclo: uma remada de cada lado consecutivas
                    cycles += 1
                    # Marcar essas remadas como usadas
                    used_indices.update({i, i + 1, i + 2, i + 3})

                    # Identificar as distâncias de início e fim do ciclo
                    start_dist = df.iloc[i]['Distância']
                    end_dist = df.iloc[i + 3]['Distância']

                    # Determinar qual trecho teve a maior sobreposição com o ciclo
                    max_overlap = 0
                    assigned_trecho = None
                    trecho_keys = sorted(trecho_positions.keys())  # Ordenar limites dos trechos
                    for j in range(len(trecho_keys)):
                        trecho_start = trecho_keys[j]
                        if trecho_start == 175:
                            trecho_end = 200
                        else:
                            trecho_end = trecho_keys[j + 1]
                        if start_dist < trecho_end and end_dist > trecho_start:
                            # Cálculo da sobreposição do ciclo com o trecho
                            trecho_overlap = min(end_dist, trecho_end) - max(start_dist, trecho_start)
                            if trecho_overlap > max_overlap:
                                max_overlap = trecho_overlap
                                assigned_trecho = trecho_positions[trecho_start]

                    if assigned_trecho:
                        trecho_ciclos[assigned_trecho] += 1

                    i += 4  # Avançar após o ciclo
                    continue

        # Caso não tenha encontrado um ciclo, marcar como remada perdida
        if i not in used_indices:
            lost_strokes += 1
            i += 2  # Saltar 2 porque contamos a remada de entrada e saída como perdida
        else:
            i += 1  # Caso a remada já tenha sido usada em outro ciclo, continuar para a próxima
    return cycles, lost_strokes, trecho_ciclos


def calculate_metrics_by_trecho(df, trecho_positions):
    positions = sorted(trecho_positions.keys())
    metrics = {
        'Trecho': [],
        'Ciclos': [],
        'Remadas': [], 
        'Rem Esq': [],
        'Rem Dir': [],
        '% Rem Esq': [],
        '% Rem Dir': [],
        'Vel Média (m/s)': [],
        'Tempo (s)': [],
        'Freq de Rem (r/min)' : [],
        'Comp Médio Rem (m/remada)': [],
        'Índice de Remada': [],

        'Freq de Ciclo (r/min)' : [],
        'Comp Médio Ciclo (m/ciclo)': [],
        'Índice de Ciclo': [],


        # 'Ações Totais': [],
    }

    total_cycles, total_lost_strokes, trecho_ciclos = calculate_cycles_and_lost_strokes(df, trecho_positions)
    estimated_times = estimate_time_at_positions(df, positions)
    total_remadas = 0
    total_ciclos = 0
    total_tempo = 0
    total_distancia = 0
    total_perdidas = 0
    i = 0
    for start, label in trecho_positions.items():
        ciclos = trecho_ciclos.get(label, 0)

        metrics['Trecho'].append(label)
        metrics['Ciclos'].append(ciclos)

        if start == 175:
            end = 200
        else: 
            end = positions[i + 1]
        trecho_label = f'{start}-{end}m'

        # Filtrar os dados para cada trecho
        trecho_df = df[(df['Distância'] >= start) & (df['Distância'] <= end)]  # Ajuste na filtragem

        if trecho_df.empty:  # Verificação adicional se o DataFrame está vazio
            print(f"Aviso: Não há dados para o trecho {trecho_label}")
            continue  # Pular para o próximo trecho, se o DataFrame estiver vazio

        remadas = len(trecho_df[trecho_df['Ação'] == 'Saida'])
        remadas_esquerda = len(trecho_df[(trecho_df['Ação'] == 'Saida') & (trecho_df['Pá do remo'] == 'Esquerda')])
        remadas_direita = len(trecho_df[(trecho_df['Ação'] == 'Saida') & (trecho_df['Pá do remo'] == 'Direita')])

        tempo_start = estimated_times[start]
        tempo_end = estimated_times[end]

        tempo = tempo_end - tempo_start
        distancia = end - start
        if tempo > 0:
            velocidade_media = distancia / tempo
            frequencia_remadas = 60 * (remadas / tempo )
            frequencia_ciclos = 60 * (ciclos / tempo)
        else:
            velocidade_media = 0
            frequencia_remadas = 0
            frequencia_ciclos = 0

        comprimento_remada = distancia / remadas if remadas > 0 else 0
        comprimento_ciclo = distancia / ciclos if ciclos > 0 else 0

        indice_remada = velocidade_media * comprimento_remada
        indice_ciclos = velocidade_media * comprimento_ciclo



        perc_esquerda = (remadas_esquerda / remadas) * 100 if remadas > 0 else 0
        perc_direita = (remadas_direita / remadas) * 100 if remadas > 0 else 0
        total_acoes = len(trecho_df)

        metrics['Remadas'].append(remadas)
        metrics['Rem Esq'].append(remadas_esquerda)
        metrics['Rem Dir'].append(remadas_direita)

        metrics['Vel Média (m/s)'].append(velocidade_media)
        metrics['Tempo (s)'].append(tempo)
        metrics['Freq de Rem (r/min)'].append(frequencia_remadas)
        metrics['Comp Médio Rem (m/remada)'].append(comprimento_remada)
        metrics['Índice de Remada'].append(indice_remada)
        metrics['% Rem Esq'].append(perc_esquerda)
        metrics['% Rem Dir'].append(perc_direita)


        metrics['Freq de Ciclo (r/min)'].append(frequencia_ciclos)
        metrics['Comp Médio Ciclo (m/ciclo)'].append(comprimento_ciclo)
        metrics['Índice de Ciclo'].append(indice_ciclos)

        # metrics['Ações Totais'].append(total_acoes)

        total_remadas += remadas
        total_ciclos += ciclos
        total_tempo += tempo
        total_distancia += distancia
        i+=1

    # Adicionar totais
    metrics['Trecho'].append('0-200m')
    metrics['Ciclos'].append(total_ciclos)
    metrics['Remadas'].append(total_remadas)
    metrics['Rem Esq'].append(sum(metrics['Rem Esq']))
    metrics['Rem Dir'].append(sum(metrics['Rem Dir']))
    metrics['Vel Média (m/s)'].append(total_distancia / total_tempo if total_tempo > 0 else 0)
    metrics['Tempo (s)'].append(total_tempo)
    metrics['Freq de Rem (r/min)'].append((total_remadas / total_tempo * 60) if total_tempo > 0 else 0)
    metrics['Comp Médio Rem (m/remada)'].append(total_distancia / total_remadas if total_remadas > 0 else 0)
    metrics['Índice de Remada'].append(metrics['Vel Média (m/s)'][-1] * metrics['Comp Médio Rem (m/remada)'][-1])


    metrics['Freq de Ciclo (r/min)'].append((total_ciclos / total_tempo * 60) if total_tempo > 0 else 0)
    metrics['Comp Médio Ciclo (m/ciclo)'].append(total_distancia / total_ciclos if total_ciclos > 0 else 0)
    metrics['Índice de Ciclo'].append(metrics['Vel Média (m/s)'][-1] * metrics['Comp Médio Ciclo (m/ciclo)'][-1])

    metrics['% Rem Esq'].append((sum(metrics['Rem Esq']) / total_remadas) * 100 if total_remadas > 0 else 0)
    metrics['% Rem Dir'].append((sum(metrics['Rem Dir']) / total_remadas) * 100 if total_remadas > 0 else 0)
    # metrics['Ações Totais'].append(len(df))

    return pd.DataFrame(metrics)





def display_results(df):
    df_pre = df[df['Teste'] == 'Pre']
    df_pos = df[df['Teste'] == 'Pos']

    trecho_positions = {0: '0-25m', 25: '25-50m', 50: '50-75m', 75: '75-100m', 100: '100-125m', 125: '125-150m', 150: '150-175m', 175: '175-200m'}

    metrics_pre = calculate_metrics_by_trecho(df_pre, trecho_positions)
    metrics_pos = calculate_metrics_by_trecho(df_pos, trecho_positions)

    st.subheader("Métricas Calculadas no Pré-Teste")
    st.write(metrics_pre)

    st.subheader("Métricas Calculadas no Pós-Teste")
    st.write(metrics_pos)


def main():
    st.title("Análise de Remadas em Caiaque")
    file_path = "lb.csv"

    df = pd.read_csv(file_path)

    if df['Distância'].dtype == 'object':
        df['Distância'] = df['Distância'].str.replace(',', '.')

    df['Distância'] = pd.to_numeric(df['Distância'], errors='coerce')

    display_results(df)


if __name__ == "__main__":
    main()
