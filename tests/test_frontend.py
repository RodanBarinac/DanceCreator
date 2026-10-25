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
    assert b'export async function api(' in rv.data
    assert b'export function renderTree(' in rv.data
    assert b'TracePlayback' in rv.data


def test_figure_detail_panels_present():
    """Test that the figure detail placeholders exist in the HTML."""
    client = app.test_client()
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'id="figure-name"' in rv.data
    assert b'id="figure-meta"' in rv.data
    assert b'id="addon-controls"' in rv.data
    assert b'id="figure-preview-status"' in rv.data


def test_dance_detail_panels_present():
    """Test that the dance detail placeholders exist in the HTML."""
    client = app.test_client()
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'id="dance-title"' in rv.data
    assert b'id="dance-floor-canvas"' in rv.data
    assert b'id="floor-status"' in rv.data
    assert b'id="dance-tree"' in rv.data


def test_workspace_contains_accessible_column_resizers():
    client = app.test_client()
    rv = client.get('/')
    assert rv.status_code == 200
    assert rv.data.count(b'class="column-resizer"') == 2
    assert b'role="separator"' in rv.data
    assert b'data-resizer-index="0"' in rv.data
    assert b'data-resizer-index="1"' in rv.data


def test_figure_preview_and_inspector_diagram_containers_are_present():
    client = app.test_client()
    rv = client.get('/')
    assert rv.status_code == 200
    snapshot = rv.data.index(b'class="trace-inspector"')
    preview_status = rv.data.index(b'id="figure-preview-status"')
    instructions = rv.data.index(b'class="crips-inspector"')
    crips = rv.data.index(b'id="figure-crips"')
    floors = rv.data.index(b'class="floor-snapshots"')
    incoming = rv.data.index(b'<h4>Incoming dancefloor</h4>')
    outgoing = rv.data.index(b'<h4>Outgoing dancefloor</h4>')
    assert snapshot < preview_status < instructions < crips < floors < incoming < outgoing
    assert b'id="incoming-floor"' in rv.data
    assert b'id="outgoing-floor"' in rv.data


def test_inspector_floor_snapshots_share_equal_responsive_columns():
    client = app.test_client()
    page = client.get('/')
    css = client.get('/static/style.css')
    assert page.status_code == 200
    assert css.status_code == 200

    markup = page.data
    snapshots = markup.index(b'class="floor-snapshots"')
    incoming = markup.index(b'<h4>Incoming dancefloor</h4>')
    outgoing = markup.index(b'<h4>Outgoing dancefloor</h4>')
    assert markup.index(b'id="figure-crips"') < snapshots < incoming < outgoing
    assert b'class="incoming-snapshot"' in markup
    assert b'class="outgoing-snapshot"' in markup

    styles = css.data
    assert b'.floor-snapshots {' in styles
    assert b'grid-template-columns: repeat(2, minmax(0, 1fr));' in styles
    assert b'gap: 0;' in styles
    assert b'.preview-floor svg {' in styles
    assert b'width: 100%;' in styles
    assert b'height: auto;' in styles


# NOTE: /api/dances endpoint may not exist in current routes
# def test_api_dances_list():
#     client = app.test_client()
#     rv = client.get('/api/dances')
#     assert rv.status_code == 200
#     data = rv.get_json()
#     assert isinstance(data, list)
