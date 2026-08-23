from urllib.parse import quote

from GUI_DanceCreator_App import app


def _client():
    return app.test_client()


def test_api_figures_list():
    rv = _client().get('/api/figures')
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, list)
    assert data
    assert 'file' in data[0]
    assert 'key' in data[0]
    assert 'Name' in data[0]


def test_api_figure_detail():
    figures = _client().get('/api/figures').get_json()
    item = figures[0]
    rv = _client().get(f"/api/figures/{quote(item['key'])}")
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, dict)
    assert data.get('Name') or data.get('name')


def test_api_dances_list():
    rv = _client().get('/api/dances')
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, list)
    assert data
    assert 'file' in data[0]
    assert 'Name' in data[0]
    assert 'shape' in data[0]


def test_api_dance_detail():
    dances = _client().get('/api/dances').get_json()
    item = dances[0]
    identifier = quote(item['file'].removesuffix('.json'))
    rv = _client().get(f'/api/dances/{identifier}')
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, dict)
    assert 'dance' in data
    assert 'tree' in data
    assert isinstance(data['tree'], dict)


def test_api_tree():
    figures = _client().get('/api/figures').get_json()
    item = figures[0]
    rv = _client().get('/api/tree', query_string={'file': item['file']})
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, list)
    assert data
    assert 'id' in data[0]
    assert 'meta' in data[0]


def test_api_dancefloor_init():
    rv = _client().post('/api/dancefloor/init', json={'couples': 2, 'name': 'test'})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['name'] == 'test'
    assert data['couples'] == 2
    assert data['tick'] == 1
    assert isinstance(data['positions'], dict)


def test_api_dancefloor_execute():
    rv = _client().post('/api/dancefloor/execute', json={
        'figure': '1cCast1p',
        'couples': 3,
        'anchor': [1, 1]
    })
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['status'] == 'ok'
    assert 'floor' in data
    assert 'crips' in data
    assert isinstance(data['floor'], dict)
