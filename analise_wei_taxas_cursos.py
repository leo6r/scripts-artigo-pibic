import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import glob
import matplotlib.ticker as mticker

# ================= CONFIGURAÇÕES DE FONTE (PADRÃO ARTIGO) =================
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['ps.fonttype'] = 42
plt.rcParams['font.family'] = 'sans-serif'

# ================= CONFIGURAÇÕES =================
CAMINHO_PASTA = 'C:/Users/meu_endereco' #adicione aqui o endereço onde os arquivos dos microdados estão salvos
PASTA_SAIDA = 'C:/Users/meu_endereco'   ##adicione aqui o endereço onde os serão salvos

os.makedirs(PASTA_SAIDA, exist_ok=True)

# ================= MAPA CINE (SIGLAS PARA ECONOMIZAR ESPAÇO) =================
MAPA_CINE = {
    '0011A06': 'ABI', '0681A01': 'Agro', '0617A01': 'Agro',
    '0612B01': 'BD', '0613C01': 'CC', '0614C01': 'CC',
    '0681C01': 'CD', '0617C01': 'CD', '0681C02': 'Comp. Saude',
    '0617C02': 'Comp. Saude', '0681C03': 'Criação Dig.', '0617C03': 'Criação Dig.',
    '0612D01': 'Def. Cib.', '0613E01': 'ES', '0714E04': 'EC',
    '0616E01': 'EC', '0612G01': 'GTI', '0613I01': 'IA',
    '0614I01': 'IA', '0613I02': 'IoT', '0616I01': 'IoT',
    '0681J01': 'Jogos', '0613J01': 'Jogos', '0114C05': 'Licenciatura',
    '0612R01': 'RC', '0688P01': 'Prog. Inter.',
    '0699P01': 'Prog. Def.', '0619P01': 'Prog. Def.',
    '0613S01': 'SI', '0615S02': 'SI', '0613S02': 'Sist. Int.',
    '0615S03': 'Sist. Int.', '0612S01': 'Seg. Inf.', '0615S01': 'Seg. Inf.',
    '0714S03': 'SE', '0616S01': 'SE', '0615C01': 'ADS'
}

def definir_nome_final(row):
    codigo_cine = str(row.get('CO_CINE_ROTULO', '')).split('.')[0].replace('"', '').strip().upper()
    nome_base = MAPA_CINE.get(codigo_cine, "OUTROS")
    if nome_base in ['SI', 'ADS']:
        try:
            grau = int(float(row.get('TP_GRAU_ACADEMICO', 0)))
            if grau == 3: return 'ADS'
            elif grau == 1: return 'SI'
        except: pass
    return nome_base

def carregar_dados():
    arquivos = glob.glob(os.path.join(CAMINHO_PASTA, "*.[cC][sS][vV]"))
    df_list = []
    colunas_necessarias = [
        'CO_CINE_ROTULO', 'CO_CINE_ROTULO2', 'CO_CINE_AREA_GERAL', 'TP_GRAU_ACADEMICO',
        'QT_ING_INDIGENA', 'QT_ING', 'QT_MAT_INDIGENA', 'QT_MAT', 'QT_CONC_INDIGENA', 'QT_CONC',
        'CO_REGIAO', 'IN_CAPITAL'
    ]
    for f in arquivos:
        try:
            ano = int(''.join(filter(str.isdigit, os.path.basename(f))))
            if ano > 10000: ano = int(str(ano)[-4:])
            if ano < 2013: continue 
            df = pd.read_csv(f, sep=';', encoding='latin1', usecols=lambda c: c in colunas_necessarias, low_memory=False)
            df['ano'] = ano
            if 'CO_CINE_ROTULO2' in df.columns and 'CO_CINE_ROTULO' not in df.columns:
                df.rename(columns={'CO_CINE_ROTULO2': 'CO_CINE_ROTULO'}, inplace=True)
            for col in ['QT_ING_INDIGENA', 'QT_ING', 'QT_MAT_INDIGENA', 'QT_MAT', 'QT_CONC_INDIGENA', 'QT_CONC']:
                df[col] = df[col].fillna(0) if col in df.columns else 0
            df_list.append(df)
        except: pass
    df_full = pd.concat(df_list, ignore_index=True)
    df_full['CURSO_SIGLA'] = df_full.apply(definir_nome_final, axis=1)
    dic_grau = {1: 'Bacharelado', 2: 'Licenciatura', 3: 'Tecnológico', 4: 'Bacharelado e Licenciatura'}
    df_full['Grau_Acadêmico'] = pd.to_numeric(df_full.get('TP_GRAU_ACADEMICO', np.nan), errors='coerce').map(dic_grau)
    return df_full

def calcular_taxas_cursos(df):
    cols_sum = ['QT_MAT', 'QT_ING', 'QT_CONC', 'QT_MAT_INDIGENA', 'QT_ING_INDIGENA', 'QT_CONC_INDIGENA']
    dados_curso = df.groupby(['ano', 'CURSO_SIGLA'])[cols_sum].sum().reset_index()
    dados_curso_grau = df.groupby(['ano', 'CURSO_SIGLA', 'Grau_Acadêmico'])[cols_sum].sum().reset_index()
    anos = sorted(df['ano'].unique())
    resultados = []
    cursos_foco = ['ADS', 'SI', 'CC', 'GTI', 'OUTROS']
    for curso in cursos_foco:
        for i in range(1, len(anos)):
            ano_atual = anos[i]
            d_ant = dados_curso[(dados_curso['ano'] == anos[i-1]) & (dados_curso['CURSO_SIGLA'] == curso)]
            d_atual = dados_curso[(dados_curso['ano'] == ano_atual) & (dados_curso['CURSO_SIGLA'] == curso)]
            if d_ant.empty or d_atual.empty: continue
            
            # Evasão (TE)
            den_ind = d_ant['QT_MAT_INDIGENA'].values[0] - d_ant['QT_CONC_INDIGENA'].values[0]
            num_ind = d_atual['QT_MAT_INDIGENA'].values[0] - d_atual['QT_ING_INDIGENA'].values[0]
            te_ind = (1 - (num_ind / den_ind)) * 100 if den_ind > 0 else np.nan
            
            den_ni = (d_ant['QT_MAT'].values[0] - d_ant['QT_MAT_INDIGENA'].values[0]) - (d_ant['QT_CONC'].values[0] - d_ant['QT_CONC_INDIGENA'].values[0])
            num_ni = (d_atual['QT_MAT'].values[0] - d_atual['QT_MAT_INDIGENA'].values[0]) - (d_atual['QT_ING'].values[0] - d_atual['QT_ING_INDIGENA'].values[0])
            te_ni = (1 - (num_ni / den_ni)) * 100 if den_ni > 0 else np.nan
            
            # Sucesso (TSG)
            ing_lag_ind, ing_lag_ni = 0, 0
            for grau in dados_curso_grau[dados_curso_grau['CURSO_SIGLA'] == curso]['Grau_Acadêmico'].dropna().unique():
                lag = 1 if grau == 'Tecnológico' else 3
                d_lag = dados_curso_grau[(dados_curso_grau['ano'] == ano_atual - lag) & (dados_curso_grau['CURSO_SIGLA'] == curso) & (dados_curso_grau['Grau_Acadêmico'] == grau)]
                if not d_lag.empty:
                    ing_lag_ind += d_lag['QT_ING_INDIGENA'].values[0]
                    ing_lag_ni += (d_lag['QT_ING'].values[0] - d_lag['QT_ING_INDIGENA'].values[0])
            
            resultados.append({
                'Curso': curso, 'Ano': ano_atual,
                'TSG_Ind': (d_atual['QT_CONC_INDIGENA'].values[0] / ing_lag_ind * 100) if ing_lag_ind > 0 else np.nan,
                'TSG_NI': ((d_atual['QT_CONC'].values[0] - d_atual['QT_CONC_INDIGENA'].values[0]) / ing_lag_ni * 100) if ing_lag_ni > 0 else np.nan,
                'TE_Ind': te_ind, 'TE_NI': te_ni
            })
    return pd.DataFrame(resultados)

def plotar_painel_compacto(df_plot, metrica_prefix, nome_arquivo, label_y, texto_ind, texto_ni):
    df_f = df_plot[df_plot['Ano'] >= 2019].copy()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.5, 3.2), sharey=True)
    
    # Dicionário mapeando cada curso à sua respectiva cor, marcador e estilo de linha
    estilos = {
        'ADS':    {'cor': '#1f77b4', 'marca': 'o', 'ls': '-'},
        'SI':     {'cor': '#ff7f0e', 'marca': 's', 'ls': '-'},
        'CC':     {'cor': '#2ca02c', 'marca': '^', 'ls': '-'},
        'GTI':    {'cor': '#d62728', 'marca': 'D', 'ls': '-'},
        'OUTROS': {'cor': '#7f7f7f', 'marca': 'X', 'ls': '--'}
    }
    
    for curso in df_f['Curso'].unique():
        d = df_f[df_f['Curso'] == curso].sort_values('Ano')
        estilo = estilos.get(curso, {'cor': 'black', 'marca': '.', 'ls': '-'})
        ax1.plot(d['Ano'], d[f'{metrica_prefix}_Ind'], marker=estilo['marca'], label=curso, 
                 color=estilo['cor'], linestyle=estilo['ls'], linewidth=1.5, markersize=4)
        ax2.plot(d['Ano'], d[f'{metrica_prefix}_NI'], marker=estilo['marca'], label=curso, 
                 color=estilo['cor'], linestyle=estilo['ls'], linewidth=1.5, markersize=4)

    # Títulos agora dinâmicos e adaptáveis à evasão ou sucesso
    ax1.set_title(f"Estudantes Indígenas {texto_ind}", fontsize=9, fontweight='bold', pad=5)
    ax2.set_title(f"Estudantes Não-Indígenas {texto_ni}", fontsize=9, fontweight='bold', pad=5)
    
    for ax in [ax1, ax2]:
        ax.set_ylim(0, 105)
        ax.tick_params(axis='both', labelsize=8)
        ax.grid(True, linestyle=':', alpha=0.5)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    ax1.set_ylabel(label_y, fontsize=8.5, fontweight='bold')
    handles, labels = ax1.get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=6, bbox_to_anchor=(0.5, -0.05), fontsize=8, frameon=False)
    
    plt.subplots_adjust(left=0.08, right=0.98, top=0.88, bottom=0.18, wspace=0.15)
    plt.savefig(os.path.join(PASTA_SAIDA, nome_arquivo), format='pdf', bbox_inches='tight')
    plt.close()

if __name__ == "__main__":
    df = carregar_dados()
    res = calcular_taxas_cursos(df)
    
    plotar_painel_compacto(res, 'TE', 'painel_taxa_evasao_cursos.pdf', 'Taxa de Evasão (%)', 
                           texto_ind="(Total Evadidos: 5.005)", 
                           texto_ni="(Total Evadidos: 1.308.047)")
    
    plotar_painel_compacto(res, 'TSG', 'painel_taxa_sucesso_cursos.pdf', 'Taxa de Sucesso (TSG)', 
                           texto_ind="(Total Formados: 1.390)", 
                           texto_ni="(Total Formados: 415.528)")
                           

    print(f"Arquivos salvos em: {PASTA_SAIDA}")
