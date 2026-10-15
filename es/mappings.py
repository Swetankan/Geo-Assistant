"""Explicit mappings. Validate accepted options against the actual server before ingest."""
def mappings(dimensions=384,index_type='hnsw',m=16,ef_construction=100):
    if index_type not in ('hnsw','int8_hnsw') or dimensions<=0:
        raise ValueError('Unsupported vector configuration')
    keyword=lambda:{'type':'keyword'}
    text=lambda:{'type':'text','analyzer':'english'}
    span={'start':{'type':'integer'},'end':{'type':'integer'}}
    common={'id':keyword()}
    chunk={**common,'document_id':keyword(),'source':keyword(),'page':{'type':'integer'},**span,
           'text':text(),'synthetic':{'type':'boolean'},'board':keyword(),'school_ids':keyword(),
           'locations':{'type':'geo_point'},'embedding':{'type':'dense_vector','dims':dimensions,'element_type':'float',
           'similarity':'cosine','index':True,'index_options':{'type':index_type,'m':m,'ef_construction':ef_construction}}}
    entity={**common,'type':keyword(),'canonical_name':{'type':'text','fields':{'raw':keyword()}},
            'mentions':{'type':'nested','properties':{'chunk_id':keyword(),**span}},
            'attributes':{'properties':{'date':{'type':'date'},'count':{'type':'integer'},'value':{'type':'float'},
            'unit':keyword(),'location':{'type':'geo_point'},'osm_id':keyword(),'board':keyword(),'locality':keyword(),'synthetic':{'type':'boolean'}}}}
    relation={**common,'source_id':keyword(),'target_id':keyword(),'type':keyword(),'weight':{'type':'float'},
              'evidence':keyword(),'method':keyword()}
    return {name:{'settings':{'number_of_shards':1,'number_of_replicas':0},'mappings':{'dynamic':'strict','properties':props}}
            for name,props in [('chunks',chunk),('entities',entity),('relations',relation)]}
