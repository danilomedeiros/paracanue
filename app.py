import pandas as pd
import streamlit as st
import plotly.express as px

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


def calculate_phases_with_total_times_and_percentages(df, trecho_positions, estimated_times):
    """
    Calcula o tempo total das fases aérea e aquática, dividindo os tempos entre os trechos,
    calcula os percentuais de cada fase em cada trecho, além dos totais e percentuais gerais
    para cada fase (aérea e aquática).

    Args:
        df (pd.DataFrame): DataFrame contendo os dados de remadas.
        trecho_positions (list): Lista ordenada das posições que delimitam os trechos.
        estimated_times (dict): Dicionário com os tempos estimados para cada posição.

    Returns:
        tuple: Quatro dicionários contendo:
            1. Tempo total das fases aérea e aquática por trecho.
            2. Percentuais das fases aérea e aquática por trecho.
            3. Tempo total das fases aérea e aquática no total (sem divisão por trecho).
            4. Percentual total das fases aérea e aquática (sem divisão por trecho).
    """
    # Inicializar tempos totais por trecho
    trecho_positions = [0, 25, 50, 75, 100, 125, 150, 175, 200]
    # Inicializar tempos totais por trecho
    air_phase_times = {trecho_positions[i]: 0 for i in range(len(trecho_positions) - 1)}
    water_phase_times = {trecho_positions[i]: 0 for i in range(len(trecho_positions) - 1)}

    # Inicializar tempos totais por trecho para o cálculo de percentuais
    total_trecho_times = {trecho_positions[i]: 0 for i in range(len(trecho_positions) - 1)}

    # Inicializar variáveis para os tempos totais gerais
    total_air_time = 0
    total_water_time = 0
    total_time = 0

    for i in range(1, len(df)):
        # Determinar a fase atual
        current_action = df.iloc[i - 1]['Ação']
        next_action = df.iloc[i]['Ação']

        # Determinar os tempos do início e fim do intervalo
        start_time = (df.iloc[i - 1]['Min'] * 60 +
                      df.iloc[i - 1]['Segundo'] +
                      df.iloc[i - 1]['Milesimos'] / 1000)
        end_time = (df.iloc[i]['Min'] * 60 +
                    df.iloc[i]['Segundo'] +
                    df.iloc[i]['Milesimos'] / 1000)

        # Determinar a distância do início e fim do intervalo
        start_dist = df.iloc[i - 1]['Distância']
        end_dist = df.iloc[i]['Distância']

        # Identificar o tipo de fase
        if current_action == 'Saida' and next_action == 'Entrada':
            phase_type = "Fase Aérea"
        elif current_action == 'Entrada' and next_action == 'Saida':
            phase_type = "Fase Aquática"
        else:
            print('INVALIDA')
            continue  # Ignorar ações que não correspondem a uma fase válida

        # Dividir o tempo entre trechos, se necessário
        trecho_keys = sorted(trecho_positions)
        trecho_started = False
        for j in range(len(trecho_keys) - 1):
            trecho_start = trecho_keys[j]
            trecho_end = trecho_keys[j + 1]

            if start_dist < trecho_end and end_dist > trecho_start:
                # Calcular a proporção de tempo no trecho
                overlap_start = max(start_dist, trecho_start)
                overlap_end = min(end_dist, trecho_end)

                if overlap_start < overlap_end:  # Verificar se há sobreposição
                    trecho_duration = (overlap_end - overlap_start) * (end_time - start_time) / (end_dist - start_dist)
                    trecho_label = f"{trecho_start}-{trecho_end}m"

                    # Atualizar o tempo total no trecho
                    total_trecho_times[trecho_start] += trecho_duration

                    # Atualizar o dicionário correspondente
                    if phase_type == "Fase Aérea":
                        air_phase_times[trecho_start] += trecho_duration
                        total_air_time += trecho_duration
                    elif phase_type == "Fase Aquática":
                        water_phase_times[trecho_start] += trecho_duration
                        total_water_time += trecho_duration

                    # Atualizar o tempo total geral
                    total_time += trecho_duration

                    trecho_started = True

        # Caso o remador permaneça no mesmo trecho sem transição
        if not trecho_started:
            # Se o remador não transitar de trecho, conta o tempo para o trecho atual
            current_trecho = trecho_start
            
            trecho_duration = (end_time - start_time)
            
            total_trecho_times[current_trecho] += trecho_duration

            if phase_type == "Fase Aérea":
                air_phase_times[current_trecho] += trecho_duration
                total_air_time += trecho_duration
            elif phase_type == "Fase Aquática":
                water_phase_times[current_trecho] += trecho_duration
                total_water_time += trecho_duration
            total_time += trecho_duration

    # Calcular os percentuais para cada fase em cada trecho
    air_phase_percentages = {key: (air_phase_times[key] / total_trecho_times[key]) * 100
                             if total_trecho_times[key] > 0 else 0
                             for key in air_phase_times}
    
    water_phase_percentages = {key: (water_phase_times[key] / total_trecho_times[key]) * 100
                               if total_trecho_times[key] > 0 else 0
                               for key in water_phase_times}

    # Calcular os percentuais gerais para as fases
    total_air_percentage = (total_air_time / total_time) * 100 if total_time > 0 else 0
    total_water_percentage = (total_water_time / total_time) * 100 if total_time > 0 else 0

    return air_phase_times, water_phase_times, air_phase_percentages, water_phase_percentages, total_air_time, total_water_time, total_air_percentage, total_water_percentage


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

        'Freq de Rem (r/min)' : [],
        'Comp Médio Rem (m/remada)': [],
        'Índice de Remada': [],

        'Freq de Ciclo (r/min)' : [],
        'Comp Médio Ciclo (m/ciclo)': [],
        'Índice de Ciclo': [],

        'Tempo (s)': [],        
        'Fase aérea': [],
        'Fase aquática': [],
        'Fase aérea %' : [],
        'Fase aquática %': [],
    }
    
    totais = {
        'Trecho': [],
        'Ciclos': [],
        'Remadas': [], 
        'Rem Esq': [],
        'Rem Dir': [],
        '% Rem Esq': [],
        '% Rem Dir': [],
        'Vel Média (m/s)': [],
        'Freq de Rem (r/min)' : [],
        'Comp Médio Rem (m/remada)': [],
        'Índice de Remada': [],

        'Freq de Ciclo (r/min)' : [],
        'Comp Médio Ciclo (m/ciclo)': [],
        'Índice de Ciclo': [],

        'Tempo (s)': [],        
        'Fase aérea': [],
        'Fase aquática': [],
        'Fase aérea %' : [],
        'Fase aquática %': [],

    }
    

    total_cycles, total_lost_strokes, trecho_ciclos = calculate_cycles_and_lost_strokes(df, trecho_positions)
    estimated_times = estimate_time_at_positions(df, positions)

    fase_aerea, fase_aquatica, fase_aerea_per, fase_aquatica_per, fase_aerea_total, fase_aquatica_total, fase_aerea_total_per, fase_aquatica_total_per = calculate_phases_with_total_times_and_percentages(df, trecho_positions, estimated_times) 

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
        metrics['Fase aérea'].append(fase_aerea[start])
        metrics['Fase aquática'].append(fase_aquatica[start])
        metrics['Fase aérea %'].append(fase_aerea_per[start])
        metrics['Fase aquática %'].append(fase_aquatica_per[start])
        
        # metrics['Ações Totais'].append(total_acoes)

        total_remadas += remadas
        total_ciclos += ciclos
        total_tempo += tempo
        total_distancia += distancia
        i+=1

    # Adicionar totais
    totais['Trecho'].append('0-200m')
    totais['Ciclos'].append(total_ciclos)
    totais['Remadas'].append(total_remadas)
    totais['Rem Esq'].append(sum(metrics['Rem Esq']))
    totais['Rem Dir'].append(sum(metrics['Rem Dir']))
    totais['Vel Média (m/s)'].append(total_distancia / total_tempo if total_tempo > 0 else 0)
    totais['Tempo (s)'].append(total_tempo)
    totais['Freq de Rem (r/min)'].append((total_remadas / total_tempo * 60) if total_tempo > 0 else 0)
    totais['Comp Médio Rem (m/remada)'].append(total_distancia / total_remadas if total_remadas > 0 else 0)
    totais['Índice de Remada'].append(totais['Vel Média (m/s)'][-1] * totais['Comp Médio Rem (m/remada)'][-1])


    totais['Freq de Ciclo (r/min)'].append((total_ciclos / total_tempo * 60) if total_tempo > 0 else 0)
    totais['Comp Médio Ciclo (m/ciclo)'].append(total_distancia / total_ciclos if total_ciclos > 0 else 0)
    totais['Índice de Ciclo'].append(totais['Vel Média (m/s)'][-1] * totais['Comp Médio Ciclo (m/ciclo)'][-1])

    totais['% Rem Esq'].append((sum(metrics['Rem Esq']) / total_remadas) * 100 if total_remadas > 0 else 0)
    totais['% Rem Dir'].append((sum(metrics['Rem Dir']) / total_remadas) * 100 if total_remadas > 0 else 0)
    
    totais['Fase aérea'].append(fase_aerea_total)
    totais['Fase aquática'].append(fase_aquatica_total)
    totais['Fase aérea %'].append(fase_aerea_total_per)
    totais['Fase aquática %'].append(fase_aquatica_total_per)    
    
    return pd.DataFrame(metrics), pd.DataFrame(totais)



def display_results(df):
    
    
    # Definir a ordem dos trechos
    trecho_order = [
        "0-25m", "25-50m", "50-75m", "75-100m",
        "100-125m", "125-150m", "150-175m", "175-200m"
    ]


    
    df_pre = df[df['Teste'] == 'Pre']
    df_pos = df[df['Teste'] == 'Pos']

    trecho_positions = {0: '0-25m', 25: '25-50m', 50: '50-75m', 75: '75-100m', 100: '100-125m', 125: '125-150m', 150: '150-175m', 175: '175-200m'}

    metrics_pre, totais_pre = calculate_metrics_by_trecho(df_pre, trecho_positions)
    metrics_pos, totais_pro = calculate_metrics_by_trecho(df_pos, trecho_positions)

    # Exibir os resultados no Streamlit
    st.subheader("Métricas Calculadas")

    # Combinar os resultados de pré e pós para facilitar os gráficos
    metrics_pre['Tipo de Teste'] = 'Pré-Teste'
    metrics_pos['Tipo de Teste'] = 'Pós-Teste'

    st.subheader("Métricas CalculaSdas no Pré-Teste")
    st.write(metrics_pre)

    st.subheader("Métricas Calculadas no Pós-Teste")
    st.write(metrics_pos)

    combined_metrics = pd.concat([metrics_pre, metrics_pos])
    
    totais_combinados = pd.concat([totais_pre, totais_pro])
    
    # Exibir as tabelas de métricas para referência
    st.subheader("Geral pré e pós")
    st.write(totais_combinados)
    
    # Criar uma coluna de categorias ordenadas para a coluna 'Trecho'
    combined_metrics['Trecho'] = pd.Categorical(
        combined_metrics['Trecho'],
        categories=trecho_order,
        ordered=True
    )

    # Reordenar o DataFrame com base na nova ordem
    combined_metrics = combined_metrics.sort_values('Trecho')    
        
    # combined_metrics = combined_metrics[combined_metrics['Trecho']!='0-200m']
    # Definir as variáveis para os gráficos
    variaveis = [
        'Ciclos',
        'Remadas', 
        'Rem Esq',
        'Rem Dir',
        '% Rem Esq',
        '% Rem Dir',
        'Vel Média (m/s)',
        'Tempo (s)',
        'Freq de Rem (r/min)' ,
        'Comp Médio Rem (m/remada)',
        'Índice de Remada',
        'Freq de Ciclo (r/min)' ,
        'Comp Médio Ciclo (m/ciclo)',
        'Índice de Ciclo',
    ]


    # Criar gráficos para cada variável
    for variavel in variaveis:
        st.subheader(f"Gráfico: {variavel}")

        # Filtrar os dados para o gráfico
        fig_data = combined_metrics[['Trecho', 'Tipo de Teste', variavel]].pivot(
            index='Trecho', columns='Tipo de Teste', values=variavel
        )

        # Criar o gráfico
        fig = px.line(
            fig_data,
            x=fig_data.index,
            y=fig_data.columns,
            markers=True,
            title=f'{variavel} - Comparação Pré e Pós-Teste',
            labels={'value': variavel, 'x': 'Trecho', 'variable': 'Teste'}
        )

        # Adicionar o gráfico no Streamlit
        st.plotly_chart(fig)


 
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


