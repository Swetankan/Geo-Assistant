"""Allowlist submission packaging; requires user-supplied mobile number."""
import argparse
import re
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FOLDERS={'app','ingest','retrieve','evalsuite','es','geoserver','tests','evidence','diagram','config','docs','scripts'}
FILES={'README.md','PROJECT DOCUMENT.md','requirements.txt','.env.example','.gitignore','pytest.ini'}


def package(mobile,output):
    if not re.fullmatch(r'[0-9]{10,15}',mobile):
        raise ValueError('Provide your explicit mobile number (10–15 digits)')
    output.mkdir(parents=True,exist_ok=True)
    target=output/(mobile+'_geoassistant.zip')
    if target.exists():
        raise FileExistsError('Archive already exists; choose a different output directory')
    paths=[]
    for path in ROOT.rglob('*'):
        relative=path.relative_to(ROOT)
        if not path.is_file() or path.is_symlink():
            continue
        if relative.parts[0] not in FOLDERS and relative.as_posix() not in FILES:
            continue
        if any(x in ('__pycache__','.pytest_cache','.cache') for x in relative.parts) or path.suffix in ('.pyc','.key','.pem','.zip') or path.name=='.env':
            continue
        paths.append(path)
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            archive.write(path,path.relative_to(ROOT))
    return target


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--mobile',required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'output')
    args=parser.parse_args()
    print(package(args.mobile,args.output))
