from GUI_DanceCreator_App import app


def test_figures():
    client = app.test_client()
    rv = client.get('/api/figures')
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, list)


def test_dance():
    client = app.test_client()
    rv = client.get('/api/dances/Marries_Wedding_full_v3')
    assert rv.status_code == 200
    j = rv.get_json()
    assert 'dance' in j and 'tree' in j


def test_init_floor():
    client = app.test_client()
    rv = client.post('/api/dancefloor/init', json={'couples': 2})
    assert rv.status_code == 200
    j = rv.get_json()
    assert j.get('couples') == 2
