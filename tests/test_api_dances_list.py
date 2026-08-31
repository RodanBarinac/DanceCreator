"""
Dance List API Tests

Tests for GET /api/dances endpoint with filtering, pagination, and metadata.
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


class TestDanceListEndpoint:
    """Test /api/dances endpoint."""
    
    def test_dances_endpoint_returns_200(self, client):
        """Test that endpoint returns 200 OK."""
        response = client.get('/api/dances')
        assert response.status_code == 200
    
    def test_dances_response_has_required_fields(self, client):
        """Test that response has all required fields."""
        response = client.get('/api/dances')
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
        assert 'dances' in data
    
    def test_dances_count_matches_array_length(self, client):
        """Test that count field matches dances array length."""
        response = client.get('/api/dances')
        data = response.get_json()
        
        assert data['count'] == len(data['dances'])
    
    def test_dances_default_limit_applied(self, client):
        """Test that default limit is 100."""
        response = client.get('/api/dances')
        data = response.get_json()
        
        assert data['limit'] == 100
        assert data['offset'] == 0
    
    def test_dances_pagination_limit(self, client):
        """Test pagination with limit."""
        response = client.get('/api/dances?limit=2')
        data = response.get_json()
        
        assert data['limit'] == 2
        assert data['count'] <= 2
    
    def test_dances_pagination_offset(self, client):
        """Test pagination with offset."""
        response = client.get('/api/dances?offset=1&limit=2')
        data = response.get_json()
        
        assert data['offset'] == 1
        assert data['limit'] == 2
    
    def test_dances_sort_by_name_asc(self, client):
        """Test sorting by name ascending."""
        response = client.get('/api/dances?sort=name&order=ASC&limit=3')
        data = response.get_json()
        
        if data['count'] > 1:
            names = [d['Name'] for d in data['dances']]
            assert names == sorted(names, key=str.lower)
    
    def test_dances_sort_by_name_desc(self, client):
        """Test sorting by name descending."""
        response = client.get('/api/dances?sort=name&order=DESC&limit=3')
        data = response.get_json()
        
        if data['count'] > 1:
            names = [d['Name'] for d in data['dances']]
            assert names == sorted(names, key=str.lower, reverse=True)
    
    def test_dances_filter_by_min_couples(self, client):
        """Test filtering by minimum couples."""
        response = client.get('/api/dances?minCouples=3')
        data = response.get_json()
        
        if data['count'] > 0:
            assert 'minCouples' in data['filters_applied']
            for dance in data['dances']:
                couples = dance.get('Couples')
                if couples is not None:
                    couple_count = int(couples) if isinstance(couples, (int, str)) and str(couples).isdigit() else 1
                    assert couple_count >= 3
    
    def test_dances_filter_by_max_couples(self, client):
        """Test filtering by maximum couples."""
        response = client.get('/api/dances?maxCouples=3')
        data = response.get_json()
        
        if data['count'] > 0:
            assert 'maxCouples' in data['filters_applied']
            for dance in data['dances']:
                couples = dance.get('Couples')
                if couples is not None:
                    couple_count = int(couples) if isinstance(couples, (int, str)) and str(couples).isdigit() else 1
                    assert couple_count <= 3
    
    def test_dances_search_by_name(self, client):
        """Test search functionality."""
        response = client.get('/api/dances?search=Wedding')
        data = response.get_json()
        
        if data['count'] > 0:
            assert 'search' in data['filters_applied']
            for dance in data['dances']:
                name = dance.get('Name', '').lower()
                desc = dance.get('Desc', '').lower()
                assert 'wedding' in name or 'wedding' in desc
    
    def test_dances_invalid_limit_returns_400(self, client):
        """Test that invalid limit returns 400."""
        response = client.get('/api/dances?limit=5000')  # Max is 1000
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
        assert data['error'] == 'validation_error'
    
    def test_dances_min_greater_than_max_returns_400(self, client):
        """Test that minCouples > maxCouples returns 400."""
        response = client.get('/api/dances?minCouples=5&maxCouples=2')
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'


class TestDanceSummaryFields:
    """Test dance summary objects have required fields."""
    
    def test_dance_has_required_fields(self, client):
        """Test that each dance has required fields."""
        response = client.get('/api/dances?limit=1')
        data = response.get_json()
        
        if data['count'] > 0:
            dance = data['dances'][0]
            assert 'file' in dance
            assert 'Name' in dance
            assert 'shape' in dance
            assert 'Version' in dance
    
    def test_dance_has_couples_metadata(self, client):
        """Test that dances have Couples metadata."""
        response = client.get('/api/dances?limit=5')
        data = response.get_json()
        
        if data['count'] > 0:
            for dance in data['dances']:
                assert 'Couples' in dance
                couples = dance['Couples']
                # Should be int or string
                assert isinstance(couples, (int, str))
    
    def test_dance_has_estimated_bars(self, client):
        """Test that dances optionally have EstimatedBars."""
        response = client.get('/api/dances?limit=5')
        data = response.get_json()
        
        if data['count'] > 0:
            # At least some dances should have EstimatedBars
            has_bars = any('EstimatedBars' in d for d in data['dances'])
            # This is OK if none have it - EstimatedBars is optional
            # but if present, must be integer
            for dance in data['dances']:
                if 'EstimatedBars' in dance:
                    assert isinstance(dance['EstimatedBars'], int)
                    assert dance['EstimatedBars'] >= 0
    
    def test_dance_shape_format(self, client):
        """Test that shape follows required pattern."""
        response = client.get('/api/dances?limit=5')
        data = response.get_json()
        
        if data['count'] > 0:
            import re
            shape_pattern = re.compile(r'^[1-9][0-9]*/[1-9][0-9]*$')
            for dance in data['dances']:
                shape = dance['shape']
                assert shape_pattern.match(shape), f"Shape '{shape}' doesn't match pattern"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
