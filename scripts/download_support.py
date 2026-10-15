import concurrent.futures
from pathlib import Path
import httpx
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ASSETS=[
 ('llama.zip','https://github.com/ggml-org/llama.cpp/releases/download/b11640/llama-b11640-bin-win-cpu-x64.zip','llama'),
 ('jre17.zip','https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.20.1%2B1/OpenJDK17U-jre_x64_windows_hotspot_17.0.20.1_1.zip','java'),
 ('geoserver-2.27.2-bin.zip','https://downloads.sourceforge.net/project/geoserver/GeoServer/2.27.2/geoserver-2.27.2-bin.zip','geoserver-2.27.2')]

def fetch(asset):
    name,url,folder=asset
    target=ROOT/'services'/name
    try:
        with httpx.Client(timeout=120,follow_redirects=True) as client:
            with client.stream('GET',url) as response:
                response.raise_for_status()
                with target.open('wb') as out:
                    for block in response.iter_bytes():
                        out.write(block)
        with zipfile.ZipFile(target) as archive:
            destination=ROOT/'services'/folder
            for item in archive.infolist():
                if not (destination/item.filename).resolve().is_relative_to(destination.resolve()):
                    raise ValueError('Unsafe zip path')
            archive.extractall(destination)
        print('Ready '+name,flush=True)
    except Exception as exc:
        print(name,type(exc).__name__,str(exc)[:160],flush=True)

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(3) as pool:
        list(pool.map(fetch,ASSETS))
