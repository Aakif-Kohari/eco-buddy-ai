"""
src.utils.xss_security_handler.py
====================================
XSS Security Handler Module
Version: 1.0.0

This module provides comprehensive XSS prevention including:
- HTML sanitization and filtering
- Input validation and escaping
- Content Security Policy (CSP) headers
- Safe rendering utilities
- XSS detection and prevention

Author: Carbon Footprint Team
Date: 2026-08-27
"""

import re
import html
import json
import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from html.parser import HTMLParser
import hashlib
import base64
from urllib.parse import urlparse, urljoin
import bleach
from bleach.sanitizer import Cleaner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class XSSRiskLevel(Enum):
    """Enumeration of XSS risk levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SanitizationStrategy(Enum):
    """Enumeration of sanitization strategies."""
    STRICT = "strict"
    MODERATE = "moderate"
    PERMISSIVE = "permissive"
    CUSTOM = "custom"


class OutputContext(Enum):
    """Enumeration of output contexts for escaping."""
    HTML = "html"
    HTML_ATTRIBUTE = "html_attribute"
    HTML_ATTRIBUTE_SINGLE_QUOTED = "html_attribute_single_quoted"
    HTML_ATTRIBUTE_DOUBLE_QUOTED = "html_attribute_double_quoted"
    JAVASCRIPT = "javascript"
    CSS = "css"
    URL = "url"
    JSON = "json"
    PLAIN = "plain"


@dataclass
class SanitizationConfig:
    """Data class for sanitization configuration."""
    strategy: SanitizationStrategy
    allowed_tags: List[str] = field(default_factory=list)
    allowed_attributes: Dict[str, List[str]] = field(default_factory=dict)
    allowed_protocols: List[str] = field(default_factory=list)
    strip_comments: bool = True
    strip_scripts: bool = True
    strip_styles: bool = True
    strip_events: bool = True
    strip_iframes: bool = True
    strip_forms: bool = True
    max_length: Optional[int] = None


@dataclass
class ValidationResult:
    """Data class for validation results."""
    is_valid: bool
    sanitized_content: Optional[str] = None
    risk_level: XSSRiskLevel = XSSRiskLevel.NONE
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class SecurityHeaders:
    """Data class for security headers."""
    content_security_policy: str
    x_frame_options: str = "DENY"
    x_content_type_options: str = "nosniff"
    x_xss_protection: str = "1; mode=block"
    referrer_policy: str = "strict-origin-when-cross-origin"
    permissions_policy: str = "geolocation=(), microphone=(), camera=()"


class XSSDetectionEngine:
    """
    Engine for detecting XSS vulnerabilities in content.
    """
    
    def __init__(self):
        self._xss_patterns = self._initialize_xss_patterns()
        self._suspicious_patterns = self._initialize_suspicious_patterns()
    
    def _initialize_xss_patterns(self) -> List[Dict[str, Any]]:
        """
        Initializes XSS detection patterns.
        
        Returns:
            List of XSS patterns
        """
        return [
            # Script tags
            {
                "pattern": r"<script[^>]*>.*?</script>",
                "risk": XSSRiskLevel.CRITICAL,
                "description": "Script tag detected"
            },
            {
                "pattern": r"<\s*script",
                "risk": XSSRiskLevel.CRITICAL,
                "description": "Script tag start detected"
            },
            
            # Event handlers
            {
                "pattern": r"on\w+\s*=",
                "risk": XSSRiskLevel.HIGH,
                "description": "Event handler detected"
            },
            {
                "pattern": r"on\w+\s*:",
                "risk": XSSRiskLevel.HIGH,
                "description": "Event handler with colon detected"
            },
            
            # JavaScript URLs
            {
                "pattern": r"javascript\s*:",
                "risk": XSSRiskLevel.CRITICAL,
                "description": "JavaScript URI detected"
            },
            {
                "pattern": r"data\s*:.*?;base64",
                "risk": XSSRiskLevel.HIGH,
                "description": "Base64 data URI detected"
            },
            
            # HTML entities
            {
                "pattern": r"&[#\w]+;",
                "risk": XSSRiskLevel.MEDIUM,
                "description": "HTML entity detected"
            },
            
            # Encoded characters
            {
                "pattern": r"%[0-9a-fA-F]{2}",
                "risk": XSSRiskLevel.MEDIUM,
                "description": "URL encoded characters detected"
            },
            
            # Vector markers
            {
                "pattern": r"<[^>]*on\w+[^>]*>",
                "risk": XSSRiskLevel.HIGH,
                "description": "Event handler in tag"
            },
            {
                "pattern": r"<[^>]*iframe[^>]*>",
                "risk": XSSRiskLevel.HIGH,
                "description": "Iframe detected"
            },
            {
                "pattern": r"<[^>]*object[^>]*>",
                "risk": XSSRiskLevel.HIGH,
                "description": "Object tag detected"
            },
            {
                "pattern": r"<[^>]*embed[^>]*>",
                "risk": XSSRiskLevel.HIGH,
                "description": "Embed tag detected"
            },
            {
                "pattern": r"<[^>]*applet[^>]*>",
                "risk": XSSRiskLevel.HIGH,
                "description": "Applet tag detected"
            },
            
            # CSS expressions
            {
                "pattern": r"expression\s*\(",
                "risk": XSSRiskLevel.HIGH,
                "description": "CSS expression detected"
            },
            
             # Dynamic attributes
             {
                 "pattern": r'dynamic\s*=\s*["\']',
                 "risk": XSSRiskLevel.MEDIUM,
                 "description": "Dynamic attribute detected"
             },
            
            # Meta refresh
            {
                "pattern": r"<meta[^>]*http-equiv\s*=\s*[\"']?refresh",
                "risk": XSSRiskLevel.MEDIUM,
                "description": "Meta refresh detected"
            },
            
            # Styles with URLs
            {
                "pattern": r"background\s*:\s*url\s*\(",
                "risk": XSSRiskLevel.MEDIUM,
                "description": "URL in style detected"
            },
            
            # Unusual characters
            {
                "pattern": r"[<>{}]+",
                "risk": XSSRiskLevel.LOW,
                "description": "Unusual characters detected"
            }
        ]
    
    def _initialize_suspicious_patterns(self) -> List[Dict[str, Any]]:
        """
        Initializes suspicious pattern detection.
        
        Returns:
            List of suspicious patterns
        """
        return [
            {
                "pattern": r"alert\s*\(",
                "risk": XSSRiskLevel.HIGH,
                "description": "Alert function detected"
            },
            {
                "pattern": r"confirm\s*\(",
                "risk": XSSRiskLevel.HIGH,
                "description": "Confirm function detected"
            },
            {
                "pattern": r"prompt\s*\(",
                "risk": XSSRiskLevel.HIGH,
                "description": "Prompt function detected"
            },
            {
                "pattern": r"document\.cookie",
                "risk": XSSRiskLevel.CRITICAL,
                "description": "Cookie access detected"
            },
            {
                "pattern": r"window\.location",
                "risk": XSSRiskLevel.HIGH,
                "description": "Location manipulation detected"
            },
            {
                "pattern": r"eval\s*\(",
                "risk": XSSRiskLevel.CRITICAL,
                "description": "Eval function detected"
            },
            {
                "pattern": r"innerHTML\s*=",
                "risk": XSSRiskLevel.HIGH,
                "description": "innerHTML assignment detected"
            },
            {
                "pattern": r"outerHTML\s*=",
                "risk": XSSRiskLevel.HIGH,
                "description": "outerHTML assignment detected"
            },
            {
                "pattern": r"document\.write",
                "risk": XSSRiskLevel.HIGH,
                "description": "Document write detected"
            },
            {
                "pattern": r"fromCharCode",
                "risk": XSSRiskLevel.MEDIUM,
                "description": "fromCharCode detected"
            }
        ]
    
    def detect_xss(self, content: str) -> ValidationResult:
        """
        Detects XSS vulnerabilities in content.
        
        Args:
            content: Content to check
            
        Returns:
            ValidationResult with findings
        """
        issues = []
        warnings = []
        risk_level = XSSRiskLevel.NONE
        
        if not content:
            return ValidationResult(
                is_valid=True,
                sanitized_content=content,
                risk_level=XSSRiskLevel.NONE,
                issues=[],
                warnings=[]
            )
        
        # Check XSS patterns
        for pattern_info in self._xss_patterns:
            if re.search(pattern_info["pattern"], content, re.IGNORECASE | re.DOTALL):
                issues.append(pattern_info["description"])
                if pattern_info["risk"].value in ["high", "critical"]:
                    risk_level = max(risk_level, pattern_info["risk"])
        
        # Check suspicious patterns
        for pattern_info in self._suspicious_patterns:
            if re.search(pattern_info["pattern"], content, re.IGNORECASE):
                warnings.append(pattern_info["description"])
                if pattern_info["risk"].value in ["high", "critical"]:
                    risk_level = max(risk_level, pattern_info["risk"])
        
        # Check for encoded XSS
        if self._detect_encoded_xss(content):
            issues.append("Encoded XSS patterns detected")
            risk_level = XSSRiskLevel.HIGH
        
        # Determine validity
        is_valid = risk_level == XSSRiskLevel.NONE or risk_level == XSSRiskLevel.LOW
        
        return ValidationResult(
            is_valid=is_valid,
            sanitized_content=content,
            risk_level=risk_level,
            issues=issues,
            warnings=warnings
        )
    
    def _detect_encoded_xss(self, content: str) -> bool:
        """
        Detects encoded XSS patterns.
        
        Args:
            content: Content to check
            
        Returns:
            True if encoded XSS detected
        """
        # Check for hex encoded
        hex_pattern = r"&#x[0-9a-fA-F]+;"
        if re.search(hex_pattern, content):
            return True
        
        # Check for decimal encoded
        dec_pattern = r"&#\d+;"
        if re.search(dec_pattern, content):
            return True
        
        # Check for double encoded
        double_pattern = r"%25[0-9a-fA-F]{2}"
        if re.search(double_pattern, content):
            return True
        
        return False


class HTMLSanitizer:
    """
    HTML sanitizer for safe content rendering.
    """
    
    def __init__(self, config: Optional[SanitizationConfig] = None):
        self.config = config or self._get_default_config()
        self._cleaner = self._create_cleaner()
    
    def _get_default_config(self) -> SanitizationConfig:
        """
        Gets default sanitization configuration.
        
        Returns:
            SanitizationConfig object
        """
        return SanitizationConfig(
            strategy=SanitizationStrategy.MODERATE,
            allowed_tags=[
                'p', 'br', 'strong', 'em', 'u', 'span', 'div', 'h1', 'h2', 'h3',
                'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'pre', 'code',
                'a', 'img', 'table', 'thead', 'tbody', 'tr', 'td', 'th'
            ],
            allowed_attributes={
                'a': ['href', 'title', 'target'],
                'img': ['src', 'alt', 'title', 'width', 'height'],
                'span': ['class', 'style'],
                'div': ['class', 'style'],
                'p': ['class', 'style'],
                '*': ['class']
            },
            allowed_protocols=['http', 'https', 'mailto', 'tel', 'ftp'],
            strip_comments=True,
            strip_scripts=True,
            strip_styles=False,
            strip_events=True,
            strip_iframes=True,
            strip_forms=True,
            max_length=100000
        )
    
    def _create_cleaner(self) -> Cleaner:
        """
        Creates a bleach cleaner instance.
        
        Returns:
            Cleaner object
        """
        # Use bleach for safe HTML cleaning
        cleaner = Cleaner(
            tags=self.config.allowed_tags,
            attributes=self.config.allowed_attributes,
            protocols=self.config.allowed_protocols,
            strip_comments=self.config.strip_comments,
            strip_script_tags=self.config.strip_scripts
        )
        
        return cleaner
    
    def sanitize_html(self, content: str) -> str:
        """
        Sanitizes HTML content.
        
        Args:
            content: HTML content to sanitize
            
        Returns:
            Sanitized HTML content
        """
        if not content:
            return ""
        
        # Truncate if too long
        if self.config.max_length and len(content) > self.config.max_length:
            content = content[:self.config.max_length]
        
        # Use bleach for cleaning
        try:
            sanitized = self._cleaner.clean(content)
        except Exception as e:
            logger.error(f"Error sanitizing HTML: {str(e)}")
            # Fallback to basic escaping
            sanitized = html.escape(content)
        
        # Additional strip of dangerous content
        if self.config.strip_events:
            sanitized = self._strip_event_handlers(sanitized)
        
        if self.config.strip_iframes:
            sanitized = self._strip_iframes(sanitized)
        
        if self.config.strip_forms:
            sanitized = self._strip_forms(sanitized)
        
        return sanitized
    
    def _strip_event_handlers(self, content: str) -> str:
        """
        Strips event handlers from HTML.
        
        Args:
            content: HTML content
            
        Returns:
            Content with event handlers removed
        """
        event_pattern = r'on\w+\s*=\s*(["\']).*?\1'
        return re.sub(event_pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
    
    def _strip_iframes(self, content: str) -> str:
        """
        Strips iframes from HTML.
        
        Args:
            content: HTML content
            
        Returns:
            Content with iframes removed
        """
        iframe_pattern = r'<iframe[^>]*>.*?</iframe>'
        return re.sub(iframe_pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
    
    def _strip_forms(self, content: str) -> str:
        """
        Strips forms from HTML.
        
        Args:
            content: HTML content
            
        Returns:
            Content with forms removed
        """
        form_pattern = r'<form[^>]*>.*?</form>'
        return re.sub(form_pattern, '', content, flags=re.IGNORECASE | re.DOTALL)


class OutputEscaper:
    """
    Handles proper output escaping for different contexts.
    """
    
    def __init__(self):
        self._context_escaper = {
            OutputContext.HTML: self._escape_html,
            OutputContext.HTML_ATTRIBUTE: self._escape_html_attribute,
            OutputContext.HTML_ATTRIBUTE_SINGLE_QUOTED: self._escape_html_attribute_single,
            OutputContext.HTML_ATTRIBUTE_DOUBLE_QUOTED: self._escape_html_attribute_double,
            OutputContext.JAVASCRIPT: self._escape_javascript,
            OutputContext.CSS: self._escape_css,
            OutputContext.URL: self._escape_url,
            OutputContext.JSON: self._escape_json,
            OutputContext.PLAIN: self._escape_plain
        }
    
    def escape(self, content: Any, context: OutputContext = OutputContext.HTML) -> str:
        """
        Escapes content for a specific context.
        
        Args:
            content: Content to escape
            context: Output context
            
        Returns:
            Escaped content
        """
        if content is None:
            return ""
        
        # Convert to string if not already
        if not isinstance(content, str):
            content = str(content)
        
        escaper = self._context_escaper.get(context, self._escape_html)
        return escaper(content)
    
    def _escape_html(self, content: str) -> str:
        """
        Escapes content for HTML context.
        
        Args:
            content: Content to escape
            
        Returns:
            HTML-escaped content
        """
        return html.escape(content, quote=True)
    
    def _escape_html_attribute(self, content: str) -> str:
        """
        Escapes content for HTML attribute context.
        
        Args:
            content: Content to escape
            
        Returns:
            Attribute-escaped content
        """
        # First, HTML escape
        escaped = html.escape(content, quote=True)
        # Then escape additional attribute characters
        return escaped.replace("'", "&#39;").replace('"', '&quot;')
    
    def _escape_html_attribute_single(self, content: str) -> str:
        """
        Escapes content for single-quoted HTML attribute.
        
        Args:
            content: Content to escape
            
        Returns:
            Single-quoted attribute-escaped content
        """
        return self._escape_html_attribute(content).replace("'", "&#39;")
    
    def _escape_html_attribute_double(self, content: str) -> str:
        """
        Escapes content for double-quoted HTML attribute.
        
        Args:
            content: Content to escape
            
        Returns:
            Double-quoted attribute-escaped content
        """
        return self._escape_html_attribute(content).replace('"', '&quot;')
    
    def _escape_javascript(self, content: str) -> str:
        """
        Escapes content for JavaScript context.
        
        Args:
            content: Content to escape
            
        Returns:
            JavaScript-escaped content
        """
        # Escape special characters for JavaScript
        replacements = {
            '\\': '\\\\',
            "'": "\\'",
            '"': '\\"',
            '\n': '\\n',
            '\r': '\\r',
            '\t': '\\t',
            '\x00': '\\0'
        }
        
        escaped = ''
        for char in content:
            escaped += replacements.get(char, char)
        
        return escaped
    
    def _escape_css(self, content: str) -> str:
        """
        Escapes content for CSS context.
        
        Args:
            content: Content to escape
            
        Returns:
            CSS-escaped content
        """
        # Simple CSS escaping
        return content.replace('\\', '\\\\').replace('"', '\\"')
    
    def _escape_url(self, content: str) -> str:
        """
        Escapes content for URL context.
        
        Args:
            content: Content to escape
            
        Returns:
            URL-escaped content
        """
        from urllib.parse import quote
        return quote(content, safe='')
    
    def _escape_json(self, content: str) -> str:
        """
        Escapes content for JSON context.
        
        Args:
            content: Content to escape
            
        Returns:
            JSON-escaped content
        """
        return json.dumps(content)[1:-1]  # Remove quotes
    
    def _escape_plain(self, content: str) -> str:
        """
        Returns content as plain text without escaping.
        
        Args:
            content: Content
            
        Returns:
            Plain content
        """
        return content


class XSSSecurityHandler:
    """
    Main XSS security handler.
    """
    
    def __init__(self):
        self.detection_engine = XSSDetectionEngine()
        self.sanitizer = HTMLSanitizer()
        self.escaper = OutputEscaper()
        self._xss_log: List[Dict[str, Any]] = []
        self._max_log_size = 1000
    
    def validate_input(self, content: str, context: Optional[OutputContext] = None) -> ValidationResult:
        """
        Validates input for XSS vulnerabilities.
        
        Args:
            content: Content to validate
            context: Output context for validation
            
        Returns:
            ValidationResult
        """
        # Detect XSS
        result = self.detection_engine.detect_xss(content)
        
        # Log if issues found
        if result.issues or result.warnings:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "content": content[:100],  # Truncate for logging
                "issues": result.issues,
                "warnings": result.warnings,
                "risk_level": result.risk_level.value
            }
            self._xss_log.append(log_entry)
            if len(self._xss_log) > self._max_log_size:
                self._xss_log.pop(0)
            
            logger.warning(f"XSS detected: {result.issues} - {result.warnings}")
        
        return result
    
    def sanitize_content(self, content: str, context: OutputContext = OutputContext.HTML) -> str:
        """
        Sanitizes content based on context.
        
        Args:
            content: Content to sanitize
            context: Output context
            
        Returns:
            Sanitized content
        """
        if not content:
            return ""
        
        # First validate
        validation = self.validate_input(content, context)
        
        if validation.risk_level == XSSRiskLevel.NONE:
            # Safe content, just escape if needed
            if context == OutputContext.HTML:
                return self.escaper.escape(content, context)
            return content
        
        # For HTML context, use HTML sanitizer
        if context == OutputContext.HTML:
            sanitized = self.sanitizer.sanitize_html(content)
        else:
            # For other contexts, escape
            sanitized = self.escaper.escape(content, context)
        
        return sanitized
    
    def render_safe(self, content: str, context: OutputContext = OutputContext.HTML) -> str:
        """
        Renders content safely.
        
        Args:
            content: Content to render
            context: Output context
            
        Returns:
            Safe rendered content
        """
        # Validate
        validation = self.validate_input(content, context)
        
        if not validation.is_valid and validation.risk_level == XSSRiskLevel.CRITICAL:
            # Critical XSS risk, return safe error message
            logger.error(f"Critical XSS blocked: {validation.issues}")
            return f"Content blocked for security reasons - {validation.issues[0] if validation.issues else 'Potential XSS'}"
        
        # Sanitize
        sanitized = self.sanitize_content(content, context)
        
        return sanitized
    
    def get_security_headers(self, csp_config: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Gets security headers for responses.
        
        Args:
            csp_config: CSP configuration
            
        Returns:
            Dictionary of security headers
        """
        headers = SecurityHeaders(
            content_security_policy=self._generate_csp(csp_config)
        )
        
        return {
            "Content-Security-Policy": headers.content_security_policy,
            "X-Frame-Options": headers.x_frame_options,
            "X-Content-Type-Options": headers.x_content_type_options,
            "X-XSS-Protection": headers.x_xss_protection,
            "Referrer-Policy": headers.referrer_policy,
            "Permissions-Policy": headers.permissions_policy
        }
    
    def _generate_csp(self, config: Optional[Dict[str, Any]] = None) -> str:
        """
        Generates Content Security Policy header.
        
        Args:
            config: CSP configuration
            
        Returns:
            CSP header string
        """
        if not config:
            config = {
                "default_src": ["'self'"],
                "script_src": ["'self'"],
                "style_src": ["'self'", "'unsafe-inline'"],
                "img_src": ["'self'", "data:", "https:"],
                "font_src": ["'self'"],
                "connect_src": ["'self'"],
                "frame_src": ["'none'"],
                "object_src": ["'none'"],
                "base_uri": ["'self'"],
                "form_action": ["'self'"],
                "frame_ancestors": ["'none'"]
            }
        
        # Build CSP header
        csp_parts = []
        for directive, sources in src.core.config.items():
            source_str = " ".join(sources)
            csp_parts.append(f"{directive} {source_str}")
        
        return "; ".join(csp_parts)
    
    def get_xss_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Gets XSS detection log.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of log entries
        """
        return self._xss_log[-limit:]
    
    def clear_xss_log(self) -> None:
        """Clears the XSS log."""
        self._xss_log.clear()
    
    def validate_url(self, url: str) -> bool:
        """
        Validates a URL for safety.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is safe
        """
        if not url:
            return False
        
        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception:
            return False
        
        # Check for javascript: protocol
        if parsed.scheme == 'javascript':
            return False
        
        # Check for data: protocol with dangerous content
        if parsed.scheme == 'data':
            if 'base64' in url.lower():
                # Try to decode and check
                try:
                    content = url.split(',')[1] if ',' in url else ''
                    decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                    # Check for XSS in decoded content
                    validation = self.validate_input(decoded)
                    if validation.risk_level in [XSSRiskLevel.HIGH, XSSRiskLevel.CRITICAL]:
                        return False
                except Exception:
                    return False
        
        # Check for dangerous protocols
        dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:']
        for protocol in dangerous_protocols:
            if url.lower().startswith(protocol):
                return False
        
        return True
    
    def sanitize_html_attribute(self, name: str, value: Any) -> Tuple[str, str]:
        """
        Sanitizes HTML attribute name and value.
        
        Args:
            name: Attribute name
            value: Attribute value
            
        Returns:
            Tuple of (sanitized_name, sanitized_value)
        """
        # Sanitize attribute name
        safe_name = re.sub(r'[^a-zA-Z0-9\-_:]', '', name)
        
        # Check for dangerous attributes
        dangerous_attributes = ['on', 'onload', 'onclick', 'onmouse', 'onerror']
        for attr in dangerous_attributes:
            if safe_name.lower().startswith(attr):
                return '', ''
        
        # Sanitize value
        safe_value = self.escaper.escape(str(value), OutputContext.HTML_ATTRIBUTE)
        
        return safe_name, safe_value
