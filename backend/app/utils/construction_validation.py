"""
Construction-specific validation and guardrails for RAG responses
"""
import re
from typing import List, Dict, Any, Tuple, Optional


class ConstructionValidator:
    """Validates construction-related queries and responses for accuracy and safety"""
    
    def __init__(self):
        # N.T.S. detection patterns
        self.nts_patterns = [
            r'\bN\.T\.S\.?\b',
            r'\bNTS\b',
            r'\bNot\s+to\s+Scale\b',
            r'\bNOT\s+TO\s+SCALE\b',
            r'\bno\s+scale\b',
            r'\bNO\s+SCALE\b'
        ]
        
        # Scale patterns
        self.scale_patterns = [
            r'(\d+/\d+)"\s*=\s*(\d+)\'?-?(\d+)"?',  # 1/4" = 1'-0"
            r'(\d+)"\s*=\s*(\d+)\'?-?(\d+)"?',       # 3" = 1'-0"
            r'Scale\s*[:=]\s*([^,\n]+)',             # Scale: 1/4" = 1'-0"
            r'SCALE\s*[:=]\s*([^,\n]+)',             # SCALE: 1/4" = 1'-0"
        ]
        
        # Dimension patterns (explicit measurements)
        self.dimension_patterns = [
            r"(\d+)\'?\s*-?\s*(\d+)\"",              # 12'-6"
            r"(\d+)\'",                              # 12'
            r"(\d+)\"",                              # 6"
            r"(\d+\.\d+)\'",                         # 12.5'
            r"(\d+)\s*mm",                           # 300mm
            r"(\d+)\s*cm",                           # 30cm
            r"(\d+\.\d+)\s*m",                       # 3.5m
        ]
    
    def detect_nts_markings(self, text: str) -> List[str]:
        """Detect N.T.S. (Not To Scale) markings in text"""
        nts_found = []
        for pattern in self.nts_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            nts_found.extend(matches)
        return nts_found
    
    def extract_scales(self, text: str) -> List[str]:
        """Extract scale notations from text"""
        scales_found = []
        for pattern in self.scale_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            scales_found.extend([match if isinstance(match, str) else ' '.join(match) for match in matches])
        return scales_found
    
    def extract_dimensions(self, text: str) -> List[str]:
        """Extract explicit dimension measurements from text"""
        dimensions_found = []
        for pattern in self.dimension_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dimensions_found.extend([match if isinstance(match, str) else '-'.join(match) for match in matches])
        return dimensions_found
    
    def validate_measurement_query(self, query: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate queries asking for measurements against N.T.S. and scale availability
        """
        # Check if query is asking for measurements
        measurement_keywords = ['dimension', 'size', 'length', 'width', 'height', 'measure', 'how big', 'how long']
        is_measurement_query = any(keyword in query.lower() for keyword in measurement_keywords)
        
        if not is_measurement_query:
            return {"safe": True, "warnings": []}
        
        warnings = []
        nts_found = False
        scales_available = []
        explicit_dimensions = []
        
        # Check all sources for N.T.S. markings and scales
        for source in sources:
            text_content = source.get('text_content', '')
            
            # Check for N.T.S. markings
            nts_markings = self.detect_nts_markings(text_content)
            if nts_markings:
                nts_found = True
                warnings.append(f"Drawing {source.get('drawing_name', 'unknown')} contains N.T.S. markings: {nts_markings}")
            
            # Extract scales
            scales = self.extract_scales(text_content)
            scales_available.extend(scales)
            
            # Extract explicit dimensions
            dimensions = self.extract_dimensions(text_content)
            explicit_dimensions.extend(dimensions)
        
        # Determine safety level
        if nts_found:
            return {
                "safe": False,
                "warnings": warnings,
                "recommendation": "ABSTAIN - Drawings marked N.T.S. cannot be used for measurements",
                "confidence_override": "low"
            }
        
        if not scales_available and not explicit_dimensions:
            warnings.append("No scale information or explicit dimensions found - measurements may be unreliable")
            return {
                "safe": False,
                "warnings": warnings,
                "recommendation": "Request scale calibration or look for explicit dimensions",
                "confidence_override": "low"
            }
        
        return {
            "safe": True,
            "warnings": warnings,
            "scales_found": scales_available,
            "explicit_dimensions": explicit_dimensions
        }
    
    def enhance_response_with_validation(self, query: str, answer: str, sources: List[Dict[str, Any]]) -> Tuple[str, str]:
        """
        Enhance response with construction validation warnings and recommendations
        """
        validation = self.validate_measurement_query(query, sources)
        
        if not validation["safe"]:
            # Prepend safety warnings to answer
            warning_text = "\n".join([
                "⚠️ **CONSTRUCTION SAFETY WARNING:**",
                *[f"• {warning}" for warning in validation["warnings"]],
                f"• **Recommendation:** {validation['recommendation']}",
                "",
                "**Original Response:**"
            ])
            enhanced_answer = warning_text + "\n" + answer
            confidence_override = validation.get("confidence_override", "medium")
            return enhanced_answer, confidence_override
        
        elif validation["warnings"]:
            # Add informational notes
            info_text = "\n".join([
                "",
                "📋 **Construction Notes:**",
                *[f"• {warning}" for warning in validation["warnings"]],
            ])
            enhanced_answer = answer + info_text
            return enhanced_answer, "medium"
        
        return answer, "high"


# Global validator instance
construction_validator = ConstructionValidator()
