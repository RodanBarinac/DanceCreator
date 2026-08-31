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
