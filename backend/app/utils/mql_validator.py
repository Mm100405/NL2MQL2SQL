"""MQL Formula Validator"""
import re
from typing import Dict, List, Tuple


class MQLValidator:
    """Validates MQL formulas"""
    
    VALID_AGGREGATIONS = {'SUM', 'COUNT', 'AVG', 'MAX', 'MIN', 'COUNT_DISTINCT'}
    VALID_OPERATORS = {'+', '-', '*', '/', '(', ')'}
    
    def __init__(self, db_session=None):
        self.db_session = db_session
    
    def validate(self, formula: str) -> Tuple[bool, str]:
        """
        Validate MQL formula
        Returns: (is_valid, message)
        """
        if not formula or not formula.strip():
            return False, "Formula cannot be empty"
        
        formula = formula.strip()
        
        # Check balanced parentheses
        if not self._check_balanced_parentheses(formula):
            return False, "Unbalanced parentheses"
        
        # Check aggregation function syntax
        agg_valid, agg_msg = self._validate_aggregations(formula)
        if not agg_valid:
            return False, agg_msg
        
        # Check operators
        op_valid, op_msg = self._validate_operators(formula)
        if not op_valid:
            return False, op_msg
        
        # Check for common syntax errors
        if '//' in formula or '**' in formula:
            return False, "Invalid operator syntax"
        
        return True, "Formula is valid"
    
    def _check_balanced_parentheses(self, formula: str) -> bool:
        """Check if parentheses are balanced"""
        count = 0
        for char in formula:
            if char == '(':
                count += 1
            elif char == ')':
                count -= 1
            if count < 0:
                return False
        return count == 0
    
    def _validate_aggregations(self, formula: str) -> Tuple[bool, str]:
        """Validate aggregation functions"""
        # Find all aggregation function calls
        pattern = r'([A-Z_]+)\s*\('
        matches = re.findall(pattern, formula)
        
        for func in matches:
            if func not in self.VALID_AGGREGATIONS:
                return False, f"Invalid aggregation function: {func}"
        
        # Check that aggregations have closing parentheses
        for agg in self.VALID_AGGREGATIONS:
            if agg in formula:
                if f"{agg}(" not in formula.replace(" ", ""):
                    return False, f"Aggregation {agg} must be followed by parentheses"
        
        return True, ""
    
    def _validate_operators(self, formula: str) -> Tuple[bool, str]:
        """Validate mathematical operators"""
        # Remove valid parts (aggregations, numbers, parentheses, metric names)
        temp = re.sub(r'[A-Z_]+\([^)]+\)', '', formula)
        temp = re.sub(r'[a-zA-Z_][a-zA-Z0-9_]*', '', temp)
        temp = re.sub(r'\d+\.?\d*', '', temp)
        temp = re.sub(r'[\s()+\-*/]', '', temp)
        
        if temp:
            return False, f"Invalid characters in formula: {temp}"
        
        return True, ""
    
    def extract_referenced_metrics(self, formula: str) -> List[str]:
        """Extract metric names referenced in the formula"""
        # Remove aggregation functions
        temp = formula
        for agg in self.VALID_AGGREGATIONS:
            temp = re.sub(f'{agg}\\s*\\([^)]+\\)', '', temp)
        
        # Find remaining identifiers (metric names)
        pattern = r'[a-zA-Z_][a-zA-Z0-9_]*'
        metrics = re.findall(pattern, temp)
        
        return list(set(metrics))
