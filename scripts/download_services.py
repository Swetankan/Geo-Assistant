"""Download portable upstream service distributions into ignored services/.

No installer runs and no system PATH is changed. Existing archives are reused.
"""
import concurrent.futures
from pathlib import Path
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'services'
ASSETS={
 'elasticsearch-8.19.0-windows-x86_64.zip':'https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.19.0-windows-x86_64.zip',
 'kibana-8.19.0-windows-x86_64.zip':'https://artifacts.elastic.co/downloads/kibana/kibana-8.19.0-windows-x86_64.zip',
 'geoserver-2.27.2-bin.zip':'https://sourceforge.net/projects/geoserver/files/GeoServer/2.27.2/geoserver-2.27.2-bin.zip/download',
 'jre17.zip':'https://api.adoptium.net/v3/binary/latest/17/ga/windows/x64/jre/hotspot/normal/eclipse',
}


def fetch(item):
    name,url=item
    target=DEST/name
    if not target.exists():
        print('Downloading '+name,flush=True)
        temporary=target.with_suffix('.partial')
        urllib.request.urlretrieve(url,temporary)
        temporary.rename(target)
    with zipfile.ZipFile(target) as archive:
        # Reject archive paths escaping the intended service directory.
        for member in archive.infolist():
            resolved=(DEST/member.filename).resolve()
            if not resolved.is_relative_to(DEST.resolve()):
                raise ValueError('Unsafe archive path')
        archive.extractall(DEST/('geoserver-2.27.2' if name.startswith('geoserver') else '.'))
    print('Ready '+name,flush=True)


if __name__=='__main__':
    DEST.mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for future in [pool.submit(fetch,item) for item in ASSETS.items()]:
            try:
                future.result()
            except Exception as error:
                print(type(error).__name__+': '+str(error),flush=True)
