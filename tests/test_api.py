from urllib.parse import quote

from GUI_DanceCreator_App import app


def _client():
    return app.test_client()


def test_api_figures_list():
    rv = _client().get('/api/figures')
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, dict)  # Now returns object with metadata
    assert 'status' in data
    assert data['status'] == 'ok'
    assert 'figures' in data
    assert isinstance(data['figures'], list)
    if data['figures']:  # If there are figures
        assert 'file' in data['figures'][0]
        assert 'key' in data['figures'][0]
        assert 'Name' in data['figures'][0]


def test_api_figure_detail():
    figures_response = _client().get('/api/figures').get_json()
    figures_list = figures_response['figures']  # Extract figures array
    if not figures_list:
        return  # Skip if no figures
    item = figures_list[0]
    rv = _client().get(f"/api/figures/{quote(item['key'])}")
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, dict)
    assert data.get('Name') or data.get('name')


def test_api_dances_list():
    rv = _client().get('/api/dances')
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, dict)  # Now returns object with metadata
    assert 'status' in data
    assert data['status'] == 'ok'
    assert 'dances' in data
    assert isinstance(data['dances'], list)
    if data['dances']:  # If there are dances
        assert 'file' in data['dances'][0]
        assert 'Name' in data['dances'][0]
        assert 'shape' in data['dances'][0]


def test_api_dance_detail():
    dances_response = _client().get('/api/dances').get_json()
    dances_list = dances_response['dances']  # Extract dances array
    if not dances_list:
        return  # Skip if no dances
    item = dances_list[0]
    identifier = quote(item['file'].removesuffix('.json'))
    rv = _client().get(f'/api/dances/{identifier}')
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, dict)
    assert 'dance' in data
    assert 'tree' in data
    assert isinstance(data['tree'], dict)
    assert data['tree'].get('children')
    assert _has_nested_figure_leaf(data['tree'])


def test_api_dance_detail_expands_modular_figures():
    rv = _client().get('/api/dances/Marries%20Wedding')
    assert rv.status_code == 200
    data = rv.get_json()
    tree = data['tree']
    assert tree['children']
    first_branch = tree['children'][0]
    assert first_branch['children']
    assert _has_nested_figure_leaf(first_branch)


def _has_nested_figure_leaf(node):
    if node.get('type') == 'figure' and not node.get('children'):
        return True
    for child in node.get('children', []):
        if _has_nested_figure_leaf(child):
            return True
    return False


def test_api_tree():
    figures_response = _client().get('/api/figures').get_json()
    figures_list = figures_response['figures']  # Extract figures array
    if not figures_list:
        return  # Skip if no figures
    item = figures_list[0]
    rv = _client().get('/api/tree', query_string={'file': item['file']})
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, list)
    if data:  # If tree has nodes
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
