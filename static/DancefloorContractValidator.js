/**
 * Dancefloor Contract Validator
 * 
 * JavaScript/TypeScript module for validating dancefloor data
 * against the Dancefloor Renderer Contract.
 * 
 * The contract is defined in:
 * - DANCEFLOOR_RENDERER_CONTRACT.md (specification)
 * - dancefloor_contract.schema.json (JSON Schema)
 */

class DancefloorContractError extends Error {
  constructor(message) {
    super(message);
    this.name = 'DancefloorContractError';
  }
}

class DancefloorValidator {
  constructor() {
    this.schema = null;
    this.schemaLoaded = false;
  }

  /**
   * Load the JSON schema from the server.
   * @returns {Promise<void>}
   */
  async loadSchema() {
    if (this.schemaLoaded) return;
    
    try {
      const response = await fetch('/schema/dancefloor_contract.schema.json');
      if (!response.ok) {
        throw new Error(`Failed to load schema: ${response.status}`);
      }
      this.schema = await response.json();
      this.schemaLoaded = true;
    } catch (err) {
      console.error('Failed to load dancefloor contract schema:', err);
      throw new DancefloorContractError(`Cannot load schema: ${err.message}`);
    }
  }

  /**
   * Validate dancefloor data against the contract schema.
   * @param {Object} dancefloorData - The dancefloor data to validate
   * @throws {DancefloorContractError} If validation fails
   */
  async validate(dancefloorData) {
    await this.loadSchema();
    
    const errors = this.getValidationErrors(dancefloorData);
    if (errors.length > 0) {
      throw new DancefloorContractError(
        `Dancefloor data violates contract:\n${errors.join('\n')}`
      );
    }
  }

  /**
   * Get all validation errors without throwing.
   * @param {Object} dancefloorData - The dancefloor data to validate
   * @returns {string[]} Array of error messages
   */
  getValidationErrors(dancefloorData) {
    if (!this.schema) {
      console.warn('Schema not loaded, skipping validation');
      return [];
    }

    const errors = [];

    // Validate root object
    if (typeof dancefloorData !== 'object' || dancefloorData === null) {
      return ['Root must be an object'];
    }

    // Check required fields
    const requiredFields = ['name', 'couples', 'tick', 'positions'];
    for (const field of requiredFields) {
      if (!(field in dancefloorData)) {
        errors.push(`Missing required field: ${field}`);
      }
    }

    // Validate name
    if ('name' in dancefloorData) {
      if (typeof dancefloorData.name !== 'string') {
        errors.push('name must be a string');
      } else if (dancefloorData.name.length === 0 || dancefloorData.name.length > 255) {
        errors.push('name must be between 1 and 255 characters');
      }
    }

    // Validate couples
    if ('couples' in dancefloorData) {
      if (!Number.isInteger(dancefloorData.couples)) {
        errors.push('couples must be an integer');
      } else if (dancefloorData.couples < 1 || dancefloorData.couples > 16) {
        errors.push('couples must be between 1 and 16');
      }
    }

    // Validate tick
    if ('tick' in dancefloorData) {
      if (!Number.isInteger(dancefloorData.tick)) {
        errors.push('tick must be an integer');
      } else if (dancefloorData.tick < 0 || dancefloorData.tick > 999) {
        errors.push('tick must be between 0 and 999');
      }
    }

    // Validate positions
    if ('positions' in dancefloorData) {
      const positions = dancefloorData.positions;
      
      if (typeof positions !== 'object' || positions === null || Array.isArray(positions)) {
        errors.push('positions must be an object (not an array)');
      } else {
        const positionKeys = Object.keys(positions);
        
        if (positionKeys.length < 2) {
          errors.push('positions must have at least 2 dancers');
        }

        for (const key of positionKeys) {
          // Validate position key format
          const validKeyPattern = /^[1-9]\d*(?:\.\d+)?[mwMW]$|^[1-9]\d*(?:\.\d+)?:-?\d+(?:\.\d+)?$/;
          if (!validKeyPattern.test(key)) {
            errors.push(`Invalid position key: '${key}' (expected format like '1m', '2w', '3:1')`);
          }

          const position = positions[key];
          const positionErrors = this.validatePosition(position, key);
          errors.push(...positionErrors);
        }
      }
    }

    // Check for extra properties
    const allowedProps = ['name', 'couples', 'tick', 'positions'];
    for (const key in dancefloorData) {
      if (!allowedProps.includes(key)) {
        errors.push(`Unexpected property: '${key}'`);
      }
    }

    return errors;
  }

  /**
   * Validate a single position object.
   * @param {Object} position - The position to validate
   * @param {string} positionKey - The position identifier (for error messages)
   * @returns {string[]} Array of error messages
   * @private
   */
  validatePosition(position, positionKey) {
    const errors = [];
    const prefix = `positions.${positionKey}`;

    if (typeof position !== 'object' || position === null || Array.isArray(position)) {
      return [`${prefix} must be an object`];
    }

    // Check required fields
    const requiredFields = ['dancer', 'coord', 'facing'];
    for (const field of requiredFields) {
      if (!(field in position)) {
        errors.push(`${prefix}.${field} is required`);
      }
    }

    // Check for extra properties
    const allowedProps = ['dancer', 'coord', 'facing'];
    for (const key in position) {
      if (!allowedProps.includes(key)) {
        errors.push(`${prefix}.${key} is not allowed`);
      }
    }

    // Validate dancer
    if ('dancer' in position) {
      const dancerErrors = this.validateDancer(position.dancer, `${prefix}.dancer`);
      errors.push(...dancerErrors);
    }

    // Validate coord
    if ('coord' in position) {
      const coordErrors = this.validateCoordinate(position.coord, `${prefix}.coord`);
      errors.push(...coordErrors);
    }

    // Validate facing
    if ('facing' in position) {
      const facingErrors = this.validateCoordinate(position.facing, `${prefix}.facing`);
      errors.push(...facingErrors);
    }

    return errors;
  }

  /**
   * Validate a dancer object.
   * @param {Object} dancer - The dancer to validate
   * @param {string} path - The JSON path (for error messages)
   * @returns {string[]} Array of error messages
   * @private
   */
  validateDancer(dancer, path) {
    const errors = [];

    if (typeof dancer !== 'object' || dancer === null || Array.isArray(dancer)) {
      return [`${path} must be an object`];
    }

    // Check required fields
    if (!('name' in dancer)) {
      errors.push(`${path}.name is required`);
    } else if (typeof dancer.name !== 'string') {
      errors.push(`${path}.name must be a string`);
    } else if (dancer.name.length === 0 || dancer.name.length > 255) {
      errors.push(`${path}.name must be between 1 and 255 characters`);
    }

    if (!('gender' in dancer)) {
      errors.push(`${path}.gender is required`);
    } else if (typeof dancer.gender !== 'string') {
      errors.push(`${path}.gender must be a string`);
    } else if (!['M', 'F'].includes(dancer.gender)) {
      errors.push(`${path}.gender must be 'M' or 'F' (got '${dancer.gender}')`);
    }

    // Check for extra properties
    const allowedProps = ['name', 'gender'];
    for (const key in dancer) {
      if (!allowedProps.includes(key)) {
        errors.push(`${path}.${key} is not allowed`);
      }
    }

    return errors;
  }

  /**
   * Validate a coordinate array [row, col].
   * @param {Array} coord - The coordinate to validate
   * @param {string} path - The JSON path (for error messages)
   * @returns {string[]} Array of error messages
   * @private
   */
  validateCoordinate(coord, path) {
    const errors = [];

    if (!Array.isArray(coord)) {
      return [`${path} must be an array`];
    }

    if (coord.length !== 2) {
      errors.push(`${path} must have exactly 2 elements (got ${coord.length})`);
    }

    for (let i = 0; i < 2; i++) {
      if (typeof coord[i] !== 'number') {
        errors.push(`${path}[${i}] must be a number (got ${typeof coord[i]})`);
      } else if (!isFinite(coord[i])) {
        errors.push(`${path}[${i}] must be a finite number`);
      } else if (i === 0 && coord[i] < 1) {
        errors.push(`${path}[0] row must be at least 1`);
      }
    }

    return errors;
  }
}

// Export for use as module
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { DancefloorValidator, DancefloorContractError };
}

// Helper functions for quick validation
async function validateDancefloor(dancefloorData) {
  const validator = new DancefloorValidator();
  await validator.validate(dancefloorData);
}

async function getDancefloorErrors(dancefloorData) {
  const validator = new DancefloorValidator();
  await validator.loadSchema();
  return validator.getValidationErrors(dancefloorData);
}
