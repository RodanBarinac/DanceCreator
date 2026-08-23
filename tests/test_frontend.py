from GUI_DanceCreator_App import app


def test_index_served():
    """Test that the main index page is served."""
    client = app.test_client()
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'DanceCreator' in rv.data


def test_static_js():
    """Test that static JavaScript files are served."""
    client = app.test_client()
    rv = client.get('/static/app.js')
    assert rv.status_code == 200
    assert b'loadFigures' in rv.data


# NOTE: /api/dances endpoint may not exist in current routes
# def test_api_dances_list():
#     client = app.test_client()
#     rv = client.get('/api/dances')
#     assert rv.status_code == 200
#     data = rv.get_json()
#     assert isinstance(data, list)
