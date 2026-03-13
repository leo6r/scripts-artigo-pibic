import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import glob

# ================= CONFIGURAÇÕES DE FONTE (PADRÃO ARTIGO) =================
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['ps.fonttype'] = 42
plt.rcParams['font.family'] = 'sans-serif' 

# ================= CONFIGURAÇÕES =================
CAMINHO_PASTA = 'C:/Users/meu_endereco' #adicione aqui o endereço onde os arquivos dos microdados estão salvos
PASTA_SAIDA = 'C:/Users/meu_endereco'   #adicione aqui o endereço onde os resultados serão salvos

os.makedirs(PASTA_SAIDA, exist_ok=True)

# ================= MAPA CINE (CONVERTIDO EM SIGLAS) =================
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

# ================= DICIONÁRIOS =================
dic_cod_regiao = {0: 'EaD sem polo', 1: 'N', 2: 'NE', 3: 'SE', 4: 'S', 5: 'CO'}
dic_capital = {0: 'Interior', 1: 'Capital', 2: 'EaD sem polo'}
dic_rede = {1: 'Pública', 2: 'Privada'}
dic_modalidade = {1: 'Presencial', 2: 'EaD'}

# ================= FUNÇÕES AUXILIARES =================

def definir_nome_final(row):
    codigo_cine = str(row.get('CO_CINE_ROTULO', '')).split('.')[0].replace('"', '').strip().upper()
    nome_base = MAPA_CINE.get(codigo_cine, "Outros")
    
    if nome_base in ['SI', 'ADS']:
        try: grau = int(float(row.get('TP_GRAU_ACADEMICO', 0)))
        except: grau = 0
        if grau == 3: return 'ADS'
        elif grau == 1: return 'SI'
    return nome_base

def carregar_dados_unificados(caminho):
    print("--- Carregando e Unificando Dados ---")
    arquivos = glob.glob(os.path.join(caminho, "*.[cC][sS][vV]"))
    df_list = []
    
    for f in arquivos:
        try:
            ano = int(''.join(filter(str.isdigit, os.path.basename(f))))
            if ano > 10000: ano = int(str(ano)[-4:])
            if ano < 2013: continue 
            print(f"A ler o ano: {ano}...")
            
            cols_possible = [
                'CO_CINE_ROTULO', 'CO_CINE_ROTULO2', 'CO_CINE_AREA_GERAL', 'TP_GRAU_ACADEMICO',
                'QT_ING_INDIGENA', 'QT_ING',
                'CO_REGIAO', 'IN_CAPITAL', 'TP_REDE', 'TP_MODALIDADE_ENSINO'
            ]
            
            df_header = pd.read_csv(f, sep=';', encoding='latin1', nrows=0)
            cols_to_use = [c for c in cols_possible if c in df_header.columns]
            
            df = pd.read_csv(f, sep=';', encoding='latin1', usecols=cols_to_use, low_memory=False)
            df['ano'] = ano
            
            if 'CO_CINE_ROTULO2' in df.columns and 'CO_CINE_ROTULO' not in df.columns:
                df.rename(columns={'CO_CINE_ROTULO2': 'CO_CINE_ROTULO'}, inplace=True)
            elif 'CO_CINE_ROTULO2' in df.columns and 'CO_CINE_ROTULO' in df.columns:
                df['CO_CINE_ROTULO'] = df['CO_CINE_ROTULO'].fillna(df['CO_CINE_ROTULO2'])

            for col in ['QT_ING_INDIGENA', 'QT_ING']:
                if col in df.columns: df[col] = df[col].fillna(0)
                else: df[col] = 0

            df_list.append(df)
        except Exception as e:
            print(f"Erro em {f}: {e}")

    if not df_list: return pd.DataFrame()
    df_full = pd.concat(df_list, ignore_index=True)
    
    filtro_cine = False
    if 'CO_CINE_AREA_GERAL' in df_full.columns:
        filtro_cine = df_full['CO_CINE_AREA_GERAL'].astype(str).str.replace('.0', '', regex=False) == '6'

    codigos_validos = list(MAPA_CINE.keys())
    filtro_texto = False
    if 'CO_CINE_ROTULO' in df_full.columns:
        df_full['CO_CINE_LIMPO'] = df_full['CO_CINE_ROTULO'].astype(str).str.split('.').str[0].str.replace('"', '').str.strip().str.upper()
        filtro_texto = df_full['CO_CINE_LIMPO'].isin(codigos_validos)
    
    df_comp = df_full[filtro_cine | filtro_texto].copy()

    print("A aplicar categorização por Códigos CINE e Grau Académico...")
    df_comp['NOME_PADRAO'] = df_comp.apply(definir_nome_final, axis=1)
    df_comp['QT_ING_NAO_INDIGENA'] = (df_comp['QT_ING'] - df_comp['QT_ING_INDIGENA']).clip(lower=0)

    print("A mapear Dicionários de Estratos...")
    
    if 'CO_REGIAO' in df_comp.columns:
        df_comp['CO_REGIAO'] = pd.to_numeric(df_comp['CO_REGIAO'], errors='coerce').fillna(0)
        df_comp['Região'] = df_comp['CO_REGIAO'].map(dic_cod_regiao)
        
    if 'IN_CAPITAL' in df_comp.columns:
        df_comp['IN_CAPITAL'] = pd.to_numeric(df_comp['IN_CAPITAL'], errors='coerce').fillna(2)
        df_comp['Localidade'] = df_comp['IN_CAPITAL'].map(dic_capital)
        
    if 'TP_REDE' in df_comp.columns:
        df_comp['Rede'] = pd.to_numeric(df_comp['TP_REDE'], errors='coerce').map(dic_rede)
        
    if 'TP_MODALIDADE_ENSINO' in df_comp.columns:
        df_comp['Modalidade'] = pd.to_numeric(df_comp['TP_MODALIDADE_ENSINO'], errors='coerce').map(dic_modalidade)

    df_comp = df_comp[(df_comp['Região'] != 'EaD sem polo') & (df_comp['Localidade'] != 'EaD sem polo')]

    return df_comp

# ================= GERAÇÃO DOS GRÁFICOS =================

def calcular_distribuicao(df, coluna_valor, coluna_atributo):
    soma_cursos = df.groupby('NOME_PADRAO')[coluna_valor].sum()
    top4_cursos = soma_cursos.sort_values(ascending=False).head(4).index.tolist()

    df_temp = df.copy()
    df_temp['NOME_RANKING'] = df_temp['NOME_PADRAO'].apply(lambda x: x if x in top4_cursos else 'Outros')

    grupo = df_temp.groupby(['NOME_RANKING', coluna_atributo])[coluna_valor].sum().reset_index()
    pivot = grupo.pivot(index='NOME_RANKING', columns=coluna_atributo, values=coluna_valor).fillna(0)
    
    categorias_esperadas = {
        'Região': ['N', 'NE', 'SE', 'S', 'CO'],
        'Localidade': ['Capital', 'Interior'],
        'Rede': ['Pública', 'Privada'],
        'Modalidade': ['Presencial', 'EaD']
    }
    
    if coluna_atributo in categorias_esperadas:
        esperadas = categorias_esperadas[coluna_atributo]
        for cat in esperadas:
            if cat not in pivot.columns:
                pivot[cat] = 0
        colunas_presentes = [c for c in esperadas if c in pivot.columns]
        pivot = pivot[colunas_presentes]

    ordem_desejada = top4_cursos + ['Outros']
    pivot = pivot.reindex(ordem_desejada).fillna(0)
    pivot = pivot.iloc[::-1] 
    
    pct = pivot.div(pivot.sum(axis=1).replace(0, 1), axis=0) * 100
    return pct.fillna(0)

def plot_distribuicao_comparativa(df, coluna_atributo, nome_arquivo, estrato_titulo):
    print(f"A gerar gráfico padronizado com fontes MAIORES para: {estrato_titulo}...")
    
    pct_ind = calcular_distribuicao(df, 'QT_ING_INDIGENA', coluna_atributo)
    pct_ni = calcular_distribuicao(df, 'QT_ING_NAO_INDIGENA', coluna_atributo)

    total_ind = df['QT_ING_INDIGENA'].sum()
    total_ni = df['QT_ING_NAO_INDIGENA'].sum()
    
    str_total_ind = f"{int(total_ind):,}".replace(',', '.')
    str_total_ni = f"{int(total_ni):,}".replace(',', '.')

    # Mantemos a largura de 11.0 para dar espaço
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 3.0))

    cmap = plt.get_cmap('Set2') 
    cores = cmap(np.linspace(0, 1, len(pct_ind.columns)))

    pct_ind.plot(kind='barh', stacked=True, ax=ax1, edgecolor='white', linewidth=0.5, color=cores)
    pct_ni.plot(kind='barh', stacked=True, ax=ax2, edgecolor='white', linewidth=0.5, color=cores)

    # Títulos maiores (11)
    ax1.set_title(f"Indígenas (Total = {str_total_ind})", fontsize=11, fontweight='bold', pad=4)
    ax2.set_title(f"Não-Indígenas (Total = {str_total_ni})", fontsize=11, fontweight='bold', pad=4)
    
    ax1.set_ylabel("")
    ax2.set_ylabel("")
    
    # Siglas dos cursos maiores (10)
    ax1.tick_params(axis='y', labelsize=10)
    ax2.tick_params(axis='y', labelsize=10)
    
    for ax in [ax1, ax2]:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(True)   
        ax.spines['bottom'].set_visible(False) 
        ax.set_xticks([]) 
        ax.get_legend().remove() 

    for ax, df_pct in zip([ax1, ax2], [pct_ind, pct_ni]):
        for n, x in enumerate(df_pct.index):
            soma_x = 0
            x_texts = []
            
            for col in df_pct.columns:
                valor = df_pct.loc[x, col]
                if valor > 0:
                    x_center = soma_x + valor / 2
                    
                    if x_center < 3.5:
                        x_center = 3.5
                    
                    if len(x_texts) > 0:
                        distancia = x_center - x_texts[-1]
                        if distancia < 7.5:
                            x_center = x_texts[-1] + 7.5
                    
                    if x_center > 96.5:
                        x_center = 96.5
                        
                    x_texts.append(x_center)
                    ax.text(x_center, n, f'{valor:.1f}%'.replace('.', ','), 
                            ha='center', va='center', color='black', 
                            fontsize=10, fontweight='bold')
                soma_x += valor

    handles, labels = ax1.get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=len(labels), 
               bbox_to_anchor=(0.5, -0.02), fontsize=10, frameon=False)

    plt.subplots_adjust(left=0.08, right=0.98, top=0.88, bottom=0.15, wspace=0.15)
    
    nome_arquivo_pdf = nome_arquivo.replace('.png', '.pdf')
    caminho_salvar = os.path.join(PASTA_SAIDA, nome_arquivo_pdf)
    plt.savefig(caminho_salvar, format='pdf', bbox_inches='tight')
    plt.close()

if __name__ == "__main__":
    df_base = carregar_dados_unificados(CAMINHO_PASTA)
    
    if not df_base.empty:
        plot_distribuicao_comparativa(df_base, 'Região', 'distribuicao_regiao.pdf', 'Região do Brasil')
        plot_distribuicao_comparativa(df_base, 'Localidade', 'distribuicao_localidade.pdf', 'Localidade do curso')
        plot_distribuicao_comparativa(df_base, 'Rede', 'distribuicao_rede.pdf', 'Rede de Ensino')
        plot_distribuicao_comparativa(df_base, 'Modalidade', 'distribuicao_modalidade.pdf', 'Modalidade de Ensino')
        

        print(f"\nProcesso finalizado! Todos os PDFs com FONTES MAIORES e ANTI-SOBREPOSIÇÃO foram salvos em: {PASTA_SAIDA}")
