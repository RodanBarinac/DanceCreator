"""
API Request Validator

Provides validation for query parameters and request data for all API endpoints.
Validates types, bounds, allowed characters, and ensures safe input.
"""

from typing import Dict, Any, Optional, List, Tuple
import re


class ApiValidationError(Exception):
    """Raised when API request validation fails."""
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"{field}: {message}")


class ApiRequestValidator:
    """Validates API request parameters against contract specifications."""
    
    # Allowed formations for figure filtering
    ALLOWED_FORMATIONS = {
        'turn', 'reel', 'hey', 'cast', 'set', 'circle', 'allemande',
        'balance', 'swing', 'chain', 'star', 'right_and_left'
    }
    
    # Allowed sort fields
    FIGURE_SORT_FIELDS = {'name', 'bars', 'version'}
    DANCE_SORT_FIELDS = {'name', 'couples', 'version', 'bars'}
    
    # Allowed sort orders
    SORT_ORDERS = {'ASC', 'DESC', 'asc', 'desc'}
    
    # Limits
    DEFAULT_LIMIT = 100
    MAX_LIMIT = 1000
    DEFAULT_OFFSET = 0
    MAX_OFFSET = 100000
    
    # Search term constraints
    MAX_SEARCH_LENGTH = 200
    SAFE_SEARCH_PATTERN = re.compile(r'^[\w\s\-\.\,\'\(\)]+$', re.UNICODE)
    
    @classmethod
    def validate_figure_list_params(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate query parameters for GET /api/figures.
        
        Args:
            params: Raw query parameters from request
            
        Returns:
            Validated and normalized parameters
            
        Raises:
            ApiValidationError: If validation fails
        """
        validated = {}
        
        # Version (optional integer)
        if 'version' in params:
            validated['version'] = cls._validate_integer(
                params['version'], 'version', min_val=1, max_val=1000
            )
        
        # Formation (optional string from allowed list)
        if 'formation' in params:
            formation = params['formation'].lower().strip()
            if formation not in cls.ALLOWED_FORMATIONS:
                raise ApiValidationError(
                    'formation',
                    f"Invalid formation. Allowed: {', '.join(sorted(cls.ALLOWED_FORMATIONS))}",
                    formation
                )
            validated['formation'] = formation
        
        # minBars and maxBars (optional integers)
        if 'minBars' in params:
            validated['minBars'] = cls._validate_integer(
                params['minBars'], 'minBars', min_val=1, max_val=1000
            )
        
        if 'maxBars' in params:
            validated['maxBars'] = cls._validate_integer(
                params['maxBars'], 'maxBars', min_val=1, max_val=1000
            )
        
        # Ensure minBars <= maxBars if both present
        if 'minBars' in validated and 'maxBars' in validated:
            if validated['minBars'] > validated['maxBars']:
                raise ApiValidationError(
                    'minBars',
                    'minBars must be less than or equal to maxBars',
                    validated['minBars']
                )
        
        # Search term (optional safe string)
        if 'search' in params:
            validated['search'] = cls._validate_search_term(params['search'])
        
        # Pagination
        validated['limit'] = cls._validate_limit(params.get('limit'))
        validated['offset'] = cls._validate_offset(params.get('offset'))
        
        # Sorting
        if 'sort' in params:
            sort_field = params['sort'].lower().strip()
            if sort_field not in cls.FIGURE_SORT_FIELDS:
                raise ApiValidationError(
                    'sort',
                    f"Invalid sort field. Allowed: {', '.join(sorted(cls.FIGURE_SORT_FIELDS))}",
                    sort_field
                )
            validated['sort'] = sort_field
        else:
            validated['sort'] = 'name'
        
        if 'order' in params:
            order = params['order'].upper().strip()
            if order not in {'ASC', 'DESC'}:
                raise ApiValidationError('order', "Order must be 'ASC' or 'DESC'", order)
            validated['order'] = order
        else:
            validated['order'] = 'ASC'
        
        return validated
    
    @classmethod
    def validate_dance_list_params(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate query parameters for GET /api/dances.
        
        Args:
            params: Raw query parameters from request
            
        Returns:
            Validated and normalized parameters
            
        Raises:
            ApiValidationError: If validation fails
        """
        validated = {}
        
        # Version (optional integer)
        if 'version' in params:
            validated['version'] = cls._validate_integer(
                params['version'], 'version', min_val=1, max_val=1000
            )
        
        # minCouples and maxCouples (optional integers)
        if 'minCouples' in params:
            validated['minCouples'] = cls._validate_integer(
                params['minCouples'], 'minCouples', min_val=1, max_val=100
            )
        
        if 'maxCouples' in params:
            validated['maxCouples'] = cls._validate_integer(
                params['maxCouples'], 'maxCouples', min_val=1, max_val=100
            )
        
        # Ensure minCouples <= maxCouples if both present
        if 'minCouples' in validated and 'maxCouples' in validated:
            if validated['minCouples'] > validated['maxCouples']:
                raise ApiValidationError(
                    'minCouples',
                    'minCouples must be less than or equal to maxCouples',
                    validated['minCouples']
                )
        
        # Search term (optional safe string)
        if 'search' in params:
            validated['search'] = cls._validate_search_term(params['search'])
        
        # Pagination
        validated['limit'] = cls._validate_limit(params.get('limit'))
        validated['offset'] = cls._validate_offset(params.get('offset'))
        
        # Sorting
        if 'sort' in params:
            sort_field = params['sort'].lower().strip()
            if sort_field not in cls.DANCE_SORT_FIELDS:
                raise ApiValidationError(
                    'sort',
                    f"Invalid sort field. Allowed: {', '.join(sorted(cls.DANCE_SORT_FIELDS))}",
                    sort_field
                )
            validated['sort'] = sort_field
        else:
            validated['sort'] = 'name'
        
        if 'order' in params:
            order = params['order'].upper().strip()
            if order not in {'ASC', 'DESC'}:
                raise ApiValidationError('order', "Order must be 'ASC' or 'DESC'", order)
            validated['order'] = order
        else:
            validated['order'] = 'ASC'
        
        return validated
    
    @classmethod
    def validate_dance_tree_identifier(cls, identifier: str) -> str:
        """
        Validate dance identifier for tree endpoint.
        
        Args:
            identifier: Dance ID/filename from URL path
            
        Returns:
            Validated identifier
            
        Raises:
            ApiValidationError: If validation fails
        """
        if not identifier or not identifier.strip():
            raise ApiValidationError('identifier', 'Identifier cannot be empty')
        
        identifier = identifier.strip()
        
        # Check length
        if len(identifier) > 500:
            raise ApiValidationError('identifier', 'Identifier too long (max 500 chars)')
        
        # Disallow path traversal attempts
        if '..' in identifier or identifier.startswith('/') or identifier.startswith('\\'):
            raise ApiValidationError('identifier', 'Invalid identifier format')
        
        return identifier
    
    @classmethod
    def validate_dance_update_request(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate request body for PUT /api/dances/<id>.
        
        Args:
            data: Request body as dictionary
            
        Returns:
            Validated data dictionary
            
        Raises:
            ApiValidationError: If validation fails
        """
        if not isinstance(data, dict):
            raise ApiValidationError('body', 'Request body must be a JSON object')
        
        # Validate required fields
        required_fields = ['Name', 'Desc', 'FigureList', 'Version']
        for field in required_fields:
            if field not in data:
                raise ApiValidationError(field, f'Missing required field: {field}')
        
        # Validate Name
        name = data['Name']
        if not isinstance(name, str) or not name.strip():
            raise ApiValidationError('Name', 'Name must be a non-empty string')
        if len(name) > 255:
            raise ApiValidationError('Name', 'Name too long (max 255 chars)')
        
        # Validate Desc
        desc = data['Desc']
        if not isinstance(desc, str) or not desc.strip():
            raise ApiValidationError('Desc', 'Description must be a non-empty string')
        if len(desc) > 5000:
            raise ApiValidationError('Desc', 'Description too long (max 5000 chars)')
        
        # Validate Version
        version = data['Version']
        if version != 3:
            raise ApiValidationError('Version', 'Version must be 3 for current schema')
        
        # Validate shape if present
        if 'shape' in data:
            shape = data['shape']
            if not isinstance(shape, str):
                raise ApiValidationError('shape', 'Shape must be a string')
            if not re.match(r'^[1-9][0-9]*/[1-9][0-9]*$', shape):
                raise ApiValidationError('shape', 'Shape must be in format N/M (e.g., "3/32")')
        
        # Validate FigureList structure
        cls._validate_dance_group(data['FigureList'], 'FigureList')
        
        return data
    
    @classmethod
    def validate_dance_create_request(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate request body for POST /api/dances.
        Same validation as update, plus uniqueness check (done at endpoint level).
        
        Args:
            data: Request body as dictionary
            
        Returns:
            Validated data dictionary
            
        Raises:
            ApiValidationError: If validation fails
        """
        # Use same validation as update
        return cls.validate_dance_update_request(data)
    
    @classmethod
    def validate_tree_update_request(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate request body for PUT /api/dances/<id>/tree.
        
        Args:
            data: Request body containing jsTree structure
            
        Returns:
            Validated data dictionary
            
        Raises:
            ApiValidationError: If validation fails
        """
        if not isinstance(data, dict):
            raise ApiValidationError('body', 'Request body must be a JSON object')
        
        # Validate required 'tree' key
        if 'tree' not in data:
            raise ApiValidationError('tree', 'Missing required field: tree')
        
        tree = data['tree']
        if not isinstance(tree, dict):
            raise ApiValidationError('tree', 'Tree must be a JSON object')
        
        # Validate tree node structure
        cls._validate_tree_node(tree, 'tree')
        
        return data
    
    @classmethod
    def _validate_tree_node(cls, node: Dict[str, Any], path: str):
        """
        Recursively validate jsTree node structure.
        
        Args:
            node: Tree node to validate
            path: Current path in tree (for error messages)
            
        Raises:
            ApiValidationError: If node structure is invalid
        """
        # Validate required node fields
        required_fields = ['id', 'text', 'type']
        for field in required_fields:
            if field not in node:
                raise ApiValidationError(f'{path}.{field}', f'Missing required field: {field}')
        
        # Validate node type
        node_type = node['type']
        if node_type not in ['figure', 'group', 'root']:
            raise ApiValidationError(f'{path}.type', f'Invalid node type: {node_type}')
        
        # Validate text is non-empty
        if not isinstance(node['text'], str) or not node['text'].strip():
            raise ApiValidationError(f'{path}.text', 'Node text must be a non-empty string')
        
        # Validate children if present
        if 'children' in node:
            children = node['children']
            if not isinstance(children, list):
                raise ApiValidationError(f'{path}.children', 'Children must be an array')
            
            for i, child in enumerate(children):
                if not isinstance(child, dict):
                    raise ApiValidationError(f'{path}.children[{i}]', 'Child must be an object')
                cls._validate_tree_node(child, f'{path}.children[{i}]')
    
    @classmethod
    def validate_figure_update_request(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate request body for PUT /api/figures/<id>.
        
        Args:
            data: Request body as dictionary
            
        Returns:
            Validated data dictionary
            
        Raises:
            ApiValidationError: If validation fails
        """
        if not isinstance(data, dict):
            raise ApiValidationError('body', 'Request body must be a JSON object')
        
        # Validate required fields
        required_fields = ['Name', 'Desc', 'Formation', 'Version']
        for field in required_fields:
            if field not in data:
                raise ApiValidationError(field, f'Missing required field: {field}')
        
        # Validate Name
        name = data['Name']
        if not isinstance(name, str) or not name.strip():
            raise ApiValidationError('Name', 'Name must be a non-empty string')
        if len(name) > 255:
            raise ApiValidationError('Name', 'Name too long (max 255 chars)')
        
        # Validate Desc
        desc = data['Desc']
        if not isinstance(desc, str) or not desc.strip():
            raise ApiValidationError('Desc', 'Description must be a non-empty string')
        if len(desc) > 5000:
            raise ApiValidationError('Desc', 'Description too long (max 5000 chars)')
        
        # Validate Formation
        formation = data['Formation']
        if not isinstance(formation, str) or not formation.strip():
            raise ApiValidationError('Formation', 'Formation must be a non-empty string')
        if len(formation) > 100:
            raise ApiValidationError('Formation', 'Formation too long (max 100 chars)')
        
        # Validate Version
        version = data['Version']
        if not isinstance(version, (int, float)) or version < 1:
            raise ApiValidationError('Version', 'Version must be a positive number')
        
        # Check if atomic or complex figure
        atomic_fields = ['Addons', 'Bars', 'StartPos', 'EndPos', 'CriptDesc']
        is_atomic = any(field in data for field in atomic_fields)
        is_complex = 'FigureList' in data
        
        if is_atomic and is_complex:
            raise ApiValidationError(
                'FigureList',
                'Figure cannot have both atomic fields (Bars, StartPos, EndPos) and FigureList'
            )
        
        if not is_atomic and not is_complex:
            raise ApiValidationError(
                'Bars',
                'Figure must have either atomic fields (Bars, StartPos, EndPos) or FigureList'
            )
        
        # Validate atomic figure fields
        if is_atomic:
            for field in atomic_fields:
                if field not in data:
                    raise ApiValidationError(field, f'Atomic figure must have {field} field')

            bars = data['Bars']
            if not isinstance(bars, (int, float)) or bars < 1:
                raise ApiValidationError('Bars', 'Bars must be a positive number')

        if is_complex:
            figure_list = data['FigureList']
            if not isinstance(figure_list, list):
                raise ApiValidationError('FigureList', 'FigureList must be an array')
            if len(figure_list) == 0:
                raise ApiValidationError('FigureList', 'FigureList must not be empty')
        
        return data
    
    # Helper methods
    
    @classmethod
    def _validate_integer(
        cls,
        value: Any,
        field: str,
        min_val: Optional[int] = None,
        max_val: Optional[int] = None
    ) -> int:
        """Validate and convert to integer with bounds checking."""
        try:
            int_val = int(value)
        except (ValueError, TypeError):
            raise ApiValidationError(field, f"Must be an integer", value)
        
        if min_val is not None and int_val < min_val:
            raise ApiValidationError(field, f"Must be >= {min_val}", int_val)
        
        if max_val is not None and int_val > max_val:
            raise ApiValidationError(field, f"Must be <= {max_val}", int_val)
        
        return int_val
    
    @classmethod
    def _validate_limit(cls, value: Any) -> int:
        """Validate pagination limit."""
        if value is None:
            return cls.DEFAULT_LIMIT
        
        limit = cls._validate_integer(value, 'limit', min_val=1, max_val=cls.MAX_LIMIT)
        return limit
    
    @classmethod
    def _validate_offset(cls, value: Any) -> int:
        """Validate pagination offset."""
        if value is None:
            return cls.DEFAULT_OFFSET
        
        offset = cls._validate_integer(value, 'offset', min_val=0, max_val=cls.MAX_OFFSET)
        return offset
    
    @classmethod
    def _validate_search_term(cls, term: Any) -> str:
        """Validate search term for safety and length."""
        if not isinstance(term, str):
            raise ApiValidationError('search', 'Must be a string', term)
        
        term = term.strip()
        
        if not term:
            raise ApiValidationError('search', 'Search term cannot be empty')
        
        if len(term) > cls.MAX_SEARCH_LENGTH:
            raise ApiValidationError(
                'search',
                f"Search term too long (max {cls.MAX_SEARCH_LENGTH} chars)"
            )
        
        # Check for safe characters only
        if not cls.SAFE_SEARCH_PATTERN.match(term):
            raise ApiValidationError(
                'search',
                'Search term contains invalid characters. Use only letters, numbers, spaces, and basic punctuation.'
            )
        
        return term

    @classmethod
    def _validate_dance_group(cls, group: Any, path: str):
        """Validate a Dance.FigureList-style group recursively."""
        if not isinstance(group, list):
            raise ApiValidationError(path, 'FigureList must be an array')
        if len(group) != 2:
            raise ApiValidationError(path, 'FigureList must be [groupType, elements]')

        group_type = group[0]
        if group_type not in ['s', 'p']:
            raise ApiValidationError(path, 'Group type must be "s" (series) or "p" (parallel)')

        elements = group[1]
        if not isinstance(elements, list):
            raise ApiValidationError(path, 'FigureList elements must be an array')
        if len(elements) == 0:
            raise ApiValidationError(path, 'FigureList elements must not be empty')

        for i, element in enumerate(elements):
            cls._validate_dance_element(element, f'{path}[1][{i}]')

    @classmethod
    def _validate_dance_element(cls, element: Any, path: str):
        """Validate either a figure call or nested dance group."""
        if not isinstance(element, list):
            raise ApiValidationError(path, 'Dance element must be an array')
        if len(element) != 2:
            raise ApiValidationError(path, 'Dance element must have exactly two items')

        first_item = element[0]
        second_item = element[1]

        if isinstance(first_item, str):
            cls._validate_dance_group(element, path)
            return

        cls._validate_figure_call(element, path)

    @classmethod
    def _validate_figure_call(cls, figure_call: List[Any], path: str):
        """Validate a single figure call entry."""
        position = figure_call[0]
        target = figure_call[1]

        if not isinstance(position, list) or len(position) != 2:
            raise ApiValidationError(path, 'Figure call position must be [x, y]')
        if not all(isinstance(coord, (int, float)) for coord in position):
            raise ApiValidationError(path, 'Figure call position values must be numbers')

        if isinstance(target, str):
            if not target.strip():
                raise ApiValidationError(path, 'Figure call target must be a non-empty string')
            return

        if not isinstance(target, list) or len(target) != 2:
            raise ApiValidationError(path, 'Figure call target must be a string or [name, addons]')
        if not isinstance(target[0], str) or not target[0].strip():
            raise ApiValidationError(path, 'Figure call target name must be a non-empty string')
        if not isinstance(target[1], list):
            raise ApiValidationError(path, 'Figure call target addons must be an array')
