import pyodbc
from pyodbc import Cursor
from pathlib import Path
import pandas as pd
from contextlib import contextmanager
from typing import Generator, Any
from unicodedata import combining, normalize
from athena_mvsh import CursorPython, Athena
import os
from datetime import datetime
import logging


FILE_LOGS = logging.FileHandler(
    'logs.txt',
    mode='a',
    encoding='utf_8'
)

logging.basicConfig(
    level=logging.INFO, 
    handlers=[FILE_LOGS],
    format='%(asctime)s - %(levelname)s - %(message)s', 
    datefmt='%d/%m/%Y %H:%M:%S'
)

driver_str = (
    'DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};'
    'DBQ={};'
)


@contextmanager
def do_connect(driver: str) -> Generator[Cursor, Any, None]:
    con = pyodbc.connect(driver)
    cursor = con.cursor()

    try:
        yield cursor
    except Exception:
        raise
    finally:
        cursor.close()
        con.close()


def date_criate(file: str) -> bool:
    if not os.path.isfile(file):
        return True

    metadados = os.stat(file)
    st_ctime = metadados.st_ctime

    dt_criacao = datetime.fromtimestamp(st_ctime).date()
    now = datetime.now().date()

    return now > dt_criacao


def categ_athena(**kwargs) -> pd.DataFrame:
    s3_location = kwargs.pop('s3_staging_dir')

    cursor = CursorPython(
        s3_location,
        result_reuse_enable=True,
        **kwargs
    )
    
    stmt = """
        SELECT 
            pm.prme_cd_produto,
            pm.prme_tx_descricao1 AS descprod,
            n1.capn_ds_categoria  AS nivel1,
            n2.capn_ds_categoria  AS nivel2,
            n3.capn_ds_categoria  AS nivel3,
            n4.capn_ds_categoria  AS nivel4
        FROM modelled.cosmos_v14b_dbo_produto_mestre AS pm
        INNER JOIN modelled.cosmos_v14b_dbo_categoria_produto_novo AS n1 
        ON substring(pm.capn_cd_categoria, 1, 1)  || '.000.000.00.00.00.00.00' = n1.capn_cd_categoria
        INNER JOIN modelled.cosmos_v14b_dbo_categoria_produto_novo AS n2 
        ON substring(pm.capn_cd_categoria, 1, 5)  || '.000.00.00.00.00.00' = n2.capn_cd_categoria
        INNER JOIN modelled.cosmos_v14b_dbo_categoria_produto_novo AS n3 
        ON substring(pm.capn_cd_categoria, 1, 9)  || '.00.00.00.00.00' = n3.capn_cd_categoria
        INNER JOIN modelled.cosmos_v14b_dbo_categoria_produto_novo AS n4 
        ON substring(pm.capn_cd_categoria, 1, 12) || '.00.00.00.00' = n4.capn_cd_categoria
    """

    with Athena(cursor=cursor) as cliente:
        cliente.execute(stmt)

        return (
            cliente.to_pandas()
            .pipe(rename_columns)
            .pipe(drop_columns_na)
            .pipe(converter_numeric_txt)
        )


def remove_accent(txt: str | None) -> str:

    if txt is None:
        return txt
    
    if pd.isna(txt):
        return txt
    
    nfd = normalize('NFD', txt)
    comb = ''.join(c for c in nfd if not combining(c))

    return normalize('NFC', comb)


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    def rename(col: str) -> str:
        return (
            '_'.join(
                remove_accent(
                    col.strip().lower()
                ).split(' ')
            )
        )
    
    return df.rename(rename, axis=1)


def converter_numeric_txt(df: pd.DataFrame) -> pd.DataFrame:
    numeros = ['number']
    inteiros = ['integer']
    ponto_flutuante = ['float']
    texto = ['object']

    return (
        df
        .pipe(lambda _df: _df.assign(**{c:_df[c].fillna(0) for c in _df.select_dtypes(numeros)}))
        .pipe(lambda _df: _df.assign(**{c:pd.to_numeric(_df[c], downcast='integer') for c in _df.select_dtypes(inteiros)}))
        .pipe(lambda _df: _df.assign(**{c:pd.to_numeric(_df[c], downcast='float') for c in _df.select_dtypes(ponto_flutuante)}))
        .pipe(lambda _df: _df.assign(**{c:_df[c].map(remove_accent) for c in _df.select_dtypes(texto)}))
    )


def drop_columns_na(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.dropna(axis=1, how='all')
    )


def get_table(
    file: Path | str, 
    table_name: str,
    dtype: dict | None = None,
    parse_dates: list[tuple] | None = None
) -> pd.DataFrame:
    
    driver = driver_str.format(file)

    with do_connect(driver) as c:
        rst = c.execute(f"""select * from {table_name}""")
        cols = [col[0] for col in rst.description]
        data = [dict(zip(cols, row)) for row in rst.fetchall()]

        df = pd.DataFrame(data)
        
        if dtype:
            df = df.astype(dtype)

        if parse_dates:
            df = df.assign(**{
                col: lambda _df, c=col,d=days: pd.to_datetime(_df[c], dayfirst=d) 
                for col, days in parse_dates
                }
            )

        return(
            df
            .pipe(rename_columns)
            .pipe(drop_columns_na)
            .pipe(converter_numeric_txt)
        )


def conds_sub_estoque(df: pd.DataFrame) -> pd.Series:
    """condicoes para o subestoque"""

    return (
        (df['prme_vl_conffinal'] == df['qtde_subestoque']) 
        & 
        (df['qtde_subestoque'] > 0)
    )


def transform_produto(file_path: Path | str) -> pd.DataFrame:
    # NOTE: Retorna tabela do kardex
    kardex = (
        get_table(file_path, "KARDEX_FILIAL") 
        .loc[lambda _df: _df['kafi_tp_mov'] == 'SV', :]
        .assign(valor = lambda _df: _df['kafi_qt_saldo'].mul(_df['kafi_vl_cmpg']))
        .groupby(['kafi_cd_produto', pd.Grouper(key='kafi_dt_mov', freq='MS')])
        .agg({'kafi_qt_saldo': 'sum', 'valor': 'sum'})
        .reset_index()
        .sort_values(['kafi_cd_produto', 'kafi_dt_mov'])
        .assign(vendas = lambda _df: (
            _df.sort_values(['kafi_cd_produto'])
               .groupby(['kafi_cd_produto'])
               ['valor']
               .transform('sum')
            )
        )
        .assign(kafi_dt_mov = lambda _df: _df['kafi_dt_mov'].dt.strftime('%Y-%m-%d'))
        .pivot_table(
            values='kafi_qt_saldo', 
            index=['kafi_cd_produto', 'vendas'], 
            columns='kafi_dt_mov', 
            aggfunc='sum',
            fill_value=0
        )
        .reset_index()
        .loc[:, lambda _df: sorted(_df.columns.to_list(), key=lambda k: 10 if k == 'vendas' else 1)]
        .rename({'kafi_cd_produto': 'prme_cd_produto'}, axis=1)
    )

    mestre = (
        get_table(file_path, 'PRODUTO_MESTRE', dtype={'PRFI_VL_CMPG': 'float', 'PRFI_VL_PRECOVENDA': 'float'})
         .join(get_table(file_path, "PARAMETRO_GERAL", parse_dates=[('PAGE_DH_INCLUSAO', True)]), how='cross')
         .loc[lambda _df: conds_sub_estoque(_df) , :]
         .assign(valor_total = lambda _df: _df['prfi_vl_cmpg'] * _df['prme_vl_conffinal'])
         .loc[:, ['page_dh_inclusao', 'page_cd_filial', 'prfi_vl_cmpg', 'prme_cd_produto', 'prme_vl_conffinal', 'valor_total']]
    )

    return (
        mestre.merge(
            kardex, 
            on=['prme_cd_produto'],
            how='left'
        )
        .fillna(0)
        .pipe(lambda _df: _df.assign(**{col: _df[col].astype('int32') for col in _df.columns if '-' in col}))
    )


def transform_ruptura(file_path: Path | str) -> pd.DataFrame:

    mestre = (
        get_table(file_path, 'PRODUTO_MESTRE', dtype={'PRFI_VL_CMPG': 'float', 'PRFI_VL_PRECOVENDA': 'float'})
        .join(get_table(file_path, "PARAMETRO_GERAL", parse_dates=[('PAGE_DH_INCLUSAO', True)]), how='cross')
        .assign(
            qtd_sku_estq_init = lambda df: df['prfi_qt_estoqatual'].where(df['prfi_qt_estoqatual'] > 0),
            valor_estq_init   = lambda df: df['prfi_qt_estoqatual'] * df['prfi_vl_cmpg'],
            qtd_sku_estq      = lambda df: df['prme_vl_conffinal'].where(df['prme_vl_conffinal'] > 0),
            valor_estq        = lambda df: df['prme_vl_conffinal'] * df['prfi_vl_cmpg'],
            qtd_sku_rup       = lambda df: df['qtde_subestoque'].where(conds_sub_estoque(df)),
        )
        .assign(valor_rup    = lambda df: df['qtd_sku_rup'] * df['prfi_vl_cmpg'])
        .groupby(['page_cd_filial', 'page_dh_inclusao'], as_index=False)
        .agg(
            qtd_sku_estq_init  = ('qtd_sku_estq_init', 'count'),
            unidades_estq_init = ('prfi_qt_estoqatual', 'sum'),
            valor_estq_init    = ('valor_estq_init', 'sum'),
            qtd_sku_estq       = ('qtd_sku_estq', 'count'),
            unidades_estq      = ('prme_vl_conffinal', 'sum'),
            valor_estq         = ('valor_estq', 'sum'),
            qtd_sku_rup        = ('qtd_sku_rup', 'count'),
            unidades_rup       = ('qtd_sku_rup', 'sum'),
            valor_rup          = ('valor_rup', 'sum')
        )
        .assign(
            ind_rup_unid  = lambda df: df['unidades_rup'].div(df['unidades_estq']),
            ind_rup_valor = lambda df: df['valor_rup'].div(df['valor_estq'])
        )
    )

    return mestre


def main_produtos(
    raiz: list[Path], 
    export: str,
    progress_callback,
    **kwargs
) -> pd.DataFrame:

    # TODO: Verificar data de criacao do arquivo

    # TODO: Categoria athena -- Se arquivo for do dia anterior criar novamente
    # se não utilizar o que foi gerado
    file_categ = 'categ.parquet'

    if date_criate(file_categ):
        progress_callback.emit((1, 'Download Base Categoria'))
        categ = (
            categ_athena(**kwargs)
            .astype({'prme_cd_produto': 'int64'})
        )
        categ.to_parquet(file_categ, index=False)
    else:
        progress_callback.emit((1, 'Load Base Categoria'))
        categ = pd.read_parquet(file_categ)

    pre_dfs = []
    for valor, file in enumerate(raiz, 2):
        out_file_log = '/'.join(file.parts[-2:])

        try:
            df = transform_produto(file)
            pre_dfs.append(df)

            progress_callback.emit((valor, f"Transformando, {out_file_log}"))

        except Exception as e:
            progress_callback.emit((valor, f"Error, {out_file_log}"))
            logging.warning(f"{e} @{file}")
            continue

    else:

        if not pre_dfs:
            msg_error = "Erro em todas os bancos listados !"
            logging.warning(f"{msg_error}")
            raise ValueError(msg_error)
        
        dfs = (
            pd.concat(pre_dfs, ignore_index=True)
            .loc[:, lambda _df: sorted(_df.columns.to_list(), key=lambda k: 10 if k == 'vendas' else 1)]
            .fillna(0)
            .pipe(lambda _df: _df.assign(**{col: _df[col].astype('int32') for col in _df.columns if '-' in col}))
            .astype({'prme_cd_produto': 'int64'})
            .merge(categ, on=["prme_cd_produto"])
        )

        now = f'{datetime.now():%d%m%Y_%H%M%S}'
        nome_saida = f'Produtos_{now}.{export}'

        progress_callback.emit((valor + 1, f'Produtos Consolidado: {nome_saida}'))

        if export == 'xlsx':
           dfs.to_excel(nome_saida, index=False)
        elif export == 'csv':
           dfs.to_csv(nome_saida, sep=';', encoding='utf-8', index=False)
        else:
            dfs.to_parquet(nome_saida, index=False)

    return dfs


def main_ruptura(
    raiz: list[Path], 
    export: str,
    progress_callback
) -> pd.DataFrame:

    pre_dfs = []
    for valor, file in enumerate(raiz, 2):
        out_file_log = '/'.join(file.parts[-2:])

        try:
            progress_callback.emit((valor, f"Transformando, {out_file_log}"))
            df = transform_ruptura(file)
            pre_dfs.append(df)

        except Exception as e:
            progress_callback.emit((valor, f"Error, {out_file_log}"))
            logging.warning(f"{e} @{file}")
            continue

    else:
        if not pre_dfs:
            msg_error = "Erro em todas os bancos listados !"
            logging.warning(f"{msg_error}")
            raise ValueError(msg_error)
        
        dfs = pd.concat(pre_dfs, ignore_index=True)

        now = f'{datetime.now():%d%m%Y_%H%M%S}'        
        nome_saida = f'Ruptura_{now}.{export}'

        progress_callback.emit((valor + 1, f'Ruptura Consolidada: {nome_saida}'))

        if export == 'xlsx':
           dfs.to_excel(nome_saida, index=False)
        elif export == 'csv':
           dfs.to_csv(nome_saida, sep=';', encoding='utf-8', index=False)
        else:
            dfs.to_parquet(nome_saida, index=False)

    return dfs