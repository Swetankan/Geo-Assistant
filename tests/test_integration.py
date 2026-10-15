"""Opt-in actual service tests. Missing services are explicitly skipped."""
import os
import pytest
from app.settings import load_settings
from es.client import ElasticStore
from geoserver.client import GeoServer

pytestmark=[pytest.mark.integration,pytest.mark.skipif(os.getenv('RUN_LOCAL_INTEGRATION')!='1',reason='Real services not explicitly enabled')]


def test_live_scoped_elasticsearch():
    store=ElasticStore(load_settings())
    assert store.authenticate()['roles']==['rag_app']
    denied=store.http.get('/_security/user')
    assert denied.status_code==403
    for index in store.settings['indices'].values():
        assert store.count(index)>=0


def test_live_geoserver_read_only_access():
    geo=GeoServer(load_settings())
    assert geo.access_check()['passed']
    assert len(geo.features('schools'))>0
