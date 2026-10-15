import os
import httpx
from app.settings import local_url


class GeoServer:
    def __init__(self,settings):
        self.url=local_url(settings['geoserver_url'])
        self.workspace=settings['workspace']
        user,password=os.getenv('GEO_USER',''),os.getenv('GEO_PASSWORD','')
        if user!='rag_geo' or not password:
            raise ValueError('Read-only rag_geo credentials required')
        self.auth=(user,password)

    def features(self,layer):
        if layer not in ('schools','roads','landuse'):
            raise ValueError('Unapproved layer')
        all_features=[]
        with httpx.Client(auth=self.auth,timeout=30,trust_env=False) as client:
            start=0
            while True:
                response=client.get(self.url+'/'+self.workspace+'/ows',params=dict(service='WFS',version='2.0.0',request='GetFeature',
                       typeNames=self.workspace+':'+layer,outputFormat='application/json',srsName='EPSG:4326',count=500,startIndex=start,sortBy='osm_id'))
                response.raise_for_status()
                data=response.json()
                if data.get('type')!='FeatureCollection':
                    raise ValueError('Expected GeoJSON FeatureCollection')
                batch=data['features']
                all_features.extend(batch)
                if len(batch)<500:
                    break
                start+=len(batch)
        ids=[f['id'] for f in all_features]
        if len(set(ids))!=len(ids):
            raise ValueError('Unstable WFS paging produced duplicate features')
        return all_features

    def access_check(self):
        params=dict(service='WFS',version='2.0.0',request='GetFeature',typeNames=self.workspace+':schools',outputFormat='application/json',count=1)
        with httpx.Client(timeout=30,trust_env=False) as client:
            anonymous=client.get(self.url+'/'+self.workspace+'/ows',params=params)
            authenticated=client.get(self.url+'/'+self.workspace+'/ows',params=params,auth=self.auth)
        denied=anonymous.status_code in (401,403)
        allowed=authenticated.status_code==200 and authenticated.headers.get('content-type','').startswith('application/json')
        if allowed:
            allowed=authenticated.json().get('type')=='FeatureCollection'
        return dict(anonymous_status=anonymous.status_code,authenticated_status=authenticated.status_code,passed=denied and allowed)
