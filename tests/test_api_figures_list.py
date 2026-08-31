"""
Figure List API Tests

Tests for GET /api/figures endpoint with filtering, pagination, and schema validation.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import Flask app
import GUI_DanceCreator_App as app_module


@pytest.fixture
def client():
    """Create test client."""
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as client:
        yield client


class TestFigureListEndpoint:
    """Test /api/figures endpoint."""
    
    def test_figures_endpoint_returns_200(self, client):
        """Test that endpoint returns 200 OK."""
        response = client.get('/api/figures')
        assert response.status_code == 200
    
    def test_figures_response_has_required_fields(self, client):
        """Test that response has all required fields."""
        response = client.get('/api/figures')
        data = response.get_json()
        
        assert 'status' in data
        assert data['status'] == 'ok'
        assert 'version' in data
        assert 'timestamp' in data
        assert 'count' in data
        assert 'total' in data
        assert 'offset' in data
        assert 'limit' in data
        assert 'filters_applied' in data
        assert 'figures' in data
    
    def test_figures_count_matches_array_length(self, client):
        """Test that count field matches figures array length."""
        response = client.get('/api/figures')
        data = response.get_json()
        
        assert data['count'] == len(data['figures'])
    
    def test_figures_default_limit_applied(self, client):
        """Test that default limit is 100."""
        response = client.get('/api/figures')
        data = response.get_json()
        
        assert data['limit'] == 100
        assert data['offset'] == 0
    
    def test_figures_pagination_limit(self, client):
        """Test pagination with limit."""
        response = client.get('/api/figures?limit=5')
        data = response.get_json()
        
        assert data['limit'] == 5
        assert data['count'] <= 5
    
    def test_figures_pagination_offset(self, client):
        """Test pagination with offset."""
        response = client.get('/api/figures?offset=2&limit=3')
        data = response.get_json()
        
        assert data['offset'] == 2
        assert data['limit'] == 3
    
    def test_figures_sort_by_name_asc(self, client):
        """Test sorting by name ascending."""
        response = client.get('/api/figures?sort=name&order=ASC&limit=3')
        data = response.get_json()
        
        if data['count'] > 1:
            names = [f['Name'] for f in data['figures']]
            assert names == sorted(names, key=str.lower)
    
    def test_figures_sort_by_name_desc(self, client):
        """Test sorting by name descending."""
        response = client.get('/api/figures?sort=name&order=DESC&limit=3')
        data = response.get_json()
        
        if data['count'] > 1:
            names = [f['Name'] for f in data['figures']]
            assert names == sorted(names, key=str.lower, reverse=True)
    
    def test_figures_filter_by_min_bars(self, client):
        """Test filtering by minimum bars."""
        response = client.get('/api/figures?minBars=4')
        data = response.get_json()
        
        assert 'minBars' in data['filters_applied']
        for figure in data['figures']:
            bars = figure.get('Bars')
            if bars is not None:
                bar_count = bars if isinstance(bars, int) else (bars[0] if bars else 0)
                assert bar_count >= 4
    
    def test_figures_filter_by_max_bars(self, client):
        """Test filtering by maximum bars."""
        response = client.get('/api/figures?maxBars=4')
        data = response.get_json()
        
        assert 'maxBars' in data['filters_applied']
        for figure in data['figures']:
            bars = figure.get('Bars')
            if bars is not None:
                bar_count = bars if isinstance(bars, int) else (bars[0] if bars else 0)
                assert bar_count <= 4
    
    def test_figures_filter_by_formation(self, client):
        """Test filtering by formation."""
        response = client.get('/api/figures?formation=reel')
        data = response.get_json()
        
        if data['count'] > 0:
            assert 'formation' in data['filters_applied']
            for figure in data['figures']:
                assert figure.get('Formation', '').lower() == 'reel'
    
    def test_figures_search_by_name(self, client):
        """Test search functionality."""
        response = client.get('/api/figures?search=reel')
        data = response.get_json()
        
        if data['count'] > 0:
            assert 'search' in data['filters_applied']
            for figure in data['figures']:
                name = figure.get('Name', '').lower()
                desc = figure.get('Desc', '').lower()
                assert 'reel' in name or 'reel' in desc
    
    def test_figures_invalid_limit_returns_400(self, client):
        """Test that invalid limit returns 400."""
        response = client.get('/api/figures?limit=5000')  # Max is 1000
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
        assert data['error'] == 'validation_error'
    
    def test_figures_invalid_formation_returns_400(self, client):
        """Test that invalid formation returns 400."""
        response = client.get('/api/figures?formation=invalid_formation')
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
    
    def test_figures_min_greater_than_max_returns_400(self, client):
        """Test that minBars > maxBars returns 400."""
        response = client.get('/api/figures?minBars=10&maxBars=5')
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'


class TestFigureSummaryFields:
    """Test figure summary objects have required fields."""
    
    def test_figure_has_required_fields(self, client):
        """Test that each figure has required fields."""
        response = client.get('/api/figures?limit=1')
        data = response.get_json()
        
        if data['count'] > 0:
            figure = data['figures'][0]
            assert 'key' in figure
            assert 'file' in figure
            assert 'Name' in figure
            assert 'Version' in figure


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
