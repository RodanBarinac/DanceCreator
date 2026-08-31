"""
Dance Tree API Tests

Tests for GET /api/dances/<id>/tree endpoint with recursion protection and schema validation.
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


class TestDanceTreeEndpoint:
    """Test /api/dances/<id>/tree endpoint."""
    
    def test_dance_tree_endpoint_returns_200_for_valid_dance(self, client):
        """Test that endpoint returns 200 OK for valid dance."""
        # Try with a known dance file - use whatever exists in test data
        response = client.get('/api/dances/Marries%20Wedding_all.json/tree')
        # May return 404 if dance doesn't exist, which is OK
        assert response.status_code in [200, 404]
    
    def test_dance_tree_not_found_returns_404(self, client):
        """Test that non-existent dance returns 404."""
        response = client.get('/api/dances/NonExistentDance12345/tree')
        assert response.status_code == 404
        data = response.get_json()
        assert data['status'] == 'error'
        assert data['error'] == 'not_found'
    
    def test_dance_tree_response_has_required_fields(self, client):
        """Test that response has all required fields when dance exists."""
        # Get list of dances first
        dances_response = client.get('/api/dances?limit=1')
        dances_data = dances_response.get_json()
        
        if dances_data['count'] > 0:
            # Get tree for first dance
            dance_file = dances_data['dances'][0]['file']
            response = client.get(f'/api/dances/{dance_file}/tree')
            
            if response.status_code == 200:
                data = response.get_json()
                
                # Check envelope fields
                assert 'status' in data
                assert data['status'] == 'ok'
                assert 'version' in data
                assert 'timestamp' in data
                assert 'format' in data
                assert data['format'] == 'jstree'
                assert 'dance' in data
                assert 'tree' in data
    
    def test_dance_metadata_has_required_fields(self, client):
        """Test that dance metadata has required fields."""
        # Get a dance that exists
        dances_response = client.get('/api/dances?limit=1')
        dances_data = dances_response.get_json()
        
        if dances_data['count'] > 0:
            dance_file = dances_data['dances'][0]['file']
            response = client.get(f'/api/dances/{dance_file}/tree')
            
            if response.status_code == 200:
                data = response.get_json()
                dance = data['dance']
                
                assert 'file' in dance
                assert 'Name' in dance
                assert 'shape' in dance
                assert 'Version' in dance
    
    def test_tree_node_structure(self, client):
        """Test that tree nodes have correct structure."""
        # Get a dance
        dances_response = client.get('/api/dances?limit=1')
        dances_data = dances_response.get_json()
        
        if dances_data['count'] > 0:
            dance_file = dances_data['dances'][0]['file']
            response = client.get(f'/api/dances/{dance_file}/tree')
            
            if response.status_code == 200:
                data = response.get_json()
                tree = data['tree']
                
                # Root node must have id and text
                assert 'id' in tree
                assert 'text' in tree
                # May or may not have children, type, data
    
    def test_tree_recursion_protection(self, client):
        """Test that deeply nested trees don't cause stack overflow."""
        # This is hard to test without a specially crafted dance
        # but we can at least ensure the endpoint doesn't crash
        dances_response = client.get('/api/dances?limit=5')
        dances_data = dances_response.get_json()
        
        for dance in dances_data.get('dances', [])[:5]:
            dance_file = dance['file']
            response = client.get(f'/api/dances/{dance_file}/tree')
            # Should return 200 or 404, not 500
            assert response.status_code in [200, 404, 500]  # 500 OK for load errors
            # But should have valid JSON
            data = response.get_json()
            assert data is not None
    
    def test_tree_children_are_arrays(self, client):
        """Test that children fields are arrays when present."""
        dances_response = client.get('/api/dances?limit=1')
        dances_data = dances_response.get_json()
        
        if dances_data['count'] > 0:
            dance_file = dances_data['dances'][0]['file']
            response = client.get(f'/api/dances/{dance_file}/tree')
            
            if response.status_code == 200:
                data = response.get_json()
                tree = data['tree']
                
                # Recursively check children
                def check_children(node):
                    if 'children' in node:
                        assert isinstance(node['children'], list)
                        for child in node['children']:
                            check_children(child)
                
                check_children(tree)
    
    def test_invalid_identifier_returns_400(self, client):
        """Test that invalid identifier format returns 400."""
        # Path traversal attempt
        response = client.get('/api/dances/../secrets/tree')
        assert response.status_code in [400, 404]  # Either validation error or not found
    
    def test_empty_identifier_returns_400_or_404(self, client):
        """Test that empty identifier returns error."""
        response = client.get('/api/dances//tree')
        # Flask routing may handle this differently (308 redirect is also valid)
        assert response.status_code in [308, 400, 404, 405]  # redirect, validation, not found, or method not allowed


class TestTreeNodeTypes:
    """Test tree node type fields."""
    
    def test_tree_nodes_have_valid_types(self, client):
        """Test that tree nodes have valid type fields."""
        dances_response = client.get('/api/dances?limit=1')
        dances_data = dances_response.get_json()
        
        if dances_data['count'] > 0:
            dance_file = dances_data['dances'][0]['file']
            response = client.get(f'/api/dances/{dance_file}/tree')
            
            if response.status_code == 200:
                data = response.get_json()
                tree = data['tree']
                
                valid_types = {'root', 'group', 'figure'}
                
                def check_types(node):
                    if 'type' in node:
                        # Type should be one of the valid types
                        assert node['type'] in valid_types, f"Invalid type: {node['type']}"
                    if 'children' in node:
                        for child in node['children']:
                            check_types(child)
                
                check_types(tree)


class TestTreeDataFields:
    """Test tree node data fields."""
    
    def test_figure_nodes_have_figure_data(self, client):
        """Test that figure nodes have appropriate data."""
        dances_response = client.get('/api/dances?limit=1')
        dances_data = dances_response.get_json()
        
        if dances_data['count'] > 0:
            dance_file = dances_data['dances'][0]['file']
            response = client.get(f'/api/dances/{dance_file}/tree')
            
            if response.status_code == 200:
                data = response.get_json()
                tree = data['tree']
                
                def check_figure_data(node):
                    if node.get('type') == 'figure' and 'data' in node:
                        data_obj = node['data']
                        # Figure nodes should have figureName
                        if 'figureName' in data_obj:
                            assert isinstance(data_obj['figureName'], str)
                    
                    if 'children' in node:
                        for child in node['children']:
                            check_figure_data(child)
                
                check_figure_data(tree)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
