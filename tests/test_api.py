"""
API Endpoint Tests

NOTE: These tests require the Flask application to be running on localhost:5000

To enable these tests:
1. Start the Flask server: .\.venv\Scripts\python.exe GUI_DanceCreator_App.py
2. Run pytest: .\.venv\Scripts\python.exe -m pytest tests/test_api.py -v

Current status: DISABLED (Flask server not running)
"""

# from GUI_DanceCreator_App import app
#
# def test_figures():
#     client = app.test_client()
#     rv = client.get('/api/figures')
#     assert rv.status_code == 200
#     data = rv.get_json()
#     assert isinstance(data, list)
#
#
# def test_dance():
#     client = app.test_client()
#     rv = client.get('/api/dances/Marries_Wedding_full_v3')
#     assert rv.status_code == 200
#     j = rv.get_json()
#     assert 'dance' in j and 'tree' in j
#
#
# def test_init_floor():
#     client = app.test_client()
#     rv = client.post('/api/dancefloor/init', json={'couples': 2})
#     assert rv.status_code == 200
#     j = rv.get_json()
#     assert j.get('couples') == 2

