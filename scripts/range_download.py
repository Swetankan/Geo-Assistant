"""Resumable small-range downloads with bounded retries and SHA-512 validation."""
import argparse
import concurrent.futures
import hashlib
from pathlib import Path
import time
import httpx


def download(url,target,workers=6):
    target=Path(target)
    target.parent.mkdir(parents=True,exist_ok=True)
    with httpx.Client(timeout=60,follow_redirects=True) as client:
        head=client.head(url,headers={'Range':'bytes=0-0'})
        head.raise_for_status()
        total=int(head.headers.get('content-range','/0').split('/')[-1]) or int(head.headers['content-length'])
    parts=target.parent/(target.name+'.parts')
    parts.mkdir(exist_ok=True)
    size=2*1024*1024
    def fetch(start):
        end=min(total,start+size)-1
        part=parts/str(start)
        if part.exists() and part.stat().st_size==end-start+1:
            return
        for attempt in range(5):
            try:
                with httpx.Client(timeout=90,follow_redirects=True) as client:
                    response=client.get(url,headers={'Range':f'bytes={start}-{end}'})
                    response.raise_for_status()
                    if response.status_code!=206 or len(response.content)!=end-start+1:
                        raise ValueError('Server did not return requested range')
                    if response.headers.get('content-range','').split('/')[0]!=f'bytes {start}-{end}':
                        raise ValueError('Incorrect content range')
                    part.write_bytes(response.content)
                    return
            except Exception:
                if attempt==4:
                    raise
                time.sleep(attempt+1)
    starts=list(range(0,total,size))
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        for i,_ in enumerate(pool.map(fetch,starts),1):
            if i%20==0 or i==len(starts):
                print(f'{target.name}: {i}/{len(starts)} ranges',flush=True)
    with target.open('wb') as output:
        for start in starts:
            output.write((parts/str(start)).read_bytes())
    if 'artifacts.elastic.co/' in url:
        expected=httpx.get(url+'.sha512',timeout=30).text.split()[0]
        digest=hashlib.sha512(target.read_bytes()).hexdigest()
        if digest!=expected:
            raise ValueError('SHA-512 verification failed')
        print('Verified upstream SHA-512 for '+target.name,flush=True)
    return target


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('target')
    args=parser.parse_args()
    print(download(args.url,args.target))
