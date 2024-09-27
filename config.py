from pathlib import Path
import json


DEFAULT_RAIZ = Path(__file__).parent
CONFIG_FILE = DEFAULT_RAIZ / 'start.json'

ICON = str(DEFAULT_RAIZ.joinpath('img/armazem.png'))
IMG = str(DEFAULT_RAIZ.joinpath('img/troca.png'))
IMG_PROD = str(DEFAULT_RAIZ.joinpath('img/produto.png'))
IMG_RUP = str(DEFAULT_RAIZ.joinpath('img/ruptura.png'))


def read_start_json() -> dict:
    with CONFIG_FILE.open('r') as fp:
        file = json.load(fp)
    
    return file


def is_start_json():
    is_file = CONFIG_FILE.is_file()
    
    if is_file:
        file = read_start_json()
    
        keys = [
            's3_staging_dir', 
            'aws_access_key_id', 
            'aws_secret_access_key', 
            'region_name'
        ]

        return (
            all([k in keys for k in file.keys()])
            and
            len(file.keys()) == len(keys)
        )
    
    return False


def init_start_json(
    s3_staging_dir: str, 
    aws_access_key_id: str,
    aws_secret_access_key: str,
    region_name: str
):
    data = {
         's3_staging_dir': s3_staging_dir, 
         'aws_access_key_id': aws_access_key_id,
         'aws_secret_access_key': aws_secret_access_key,
         'region_name': region_name 
    }

    try:
       DEFAULT_RAIZ.mkdir(exist_ok=True)

       with CONFIG_FILE.open('w') as fp:
            json.dump(data, fp, indent=4)

    except OSError:
        return
            
    return CONFIG_FILE