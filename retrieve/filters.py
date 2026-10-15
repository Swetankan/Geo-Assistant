from dataclasses import dataclass, field
from pyproj import Geod


@dataclass
class QueryFilter:
    metadata: dict = field(default_factory=dict)
    latitude: float | None = None
    longitude: float | None = None
    distance_m: float | None = None

    def __post_init__(self):
        if set(self.metadata)-{'board','synthetic','document_id','school_ids'}:
            raise ValueError('Unsupported metadata filter')
        geo=(self.latitude,self.longitude,self.distance_m)
        if any(x is not None for x in geo):
            if any(x is None for x in geo) or not -90<=self.latitude<=90 or not -180<=self.longitude<=180 or self.distance_m<0:
                raise ValueError('Invalid distance filter')

    def accepts(self,chunk):
        for key,value in self.metadata.items():
            actual=getattr(chunk,key)
            if (value not in actual if isinstance(actual,list) else value!=actual):
                return False
        if self.distance_m is not None:
            geod=Geod(ellps='WGS84')
            return any(geod.inv(self.longitude,self.latitude,p.lon,p.lat)[2]<=self.distance_m for p in chunk.locations)
        return True

    def elastic(self):
        filters=[{'term':{key:value}} for key,value in sorted(self.metadata.items())]
        if self.distance_m is not None:
            filters.append({'geo_distance':{'distance':f'{self.distance_m}m','locations':{'lat':self.latitude,'lon':self.longitude}}})
        return filters
