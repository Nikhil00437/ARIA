"""
Security utilities for ARIA.
Provides input sanitization, XSS prevention, and safe output rendering.
"""

import re
import html
from typing import Optional
from dataclasses import dataclass


@dataclass
class SanitizeResult:
    """Result of sanitization operation."""
    text: str
    was_modified: bool
    warnings: list[str]


class InputSanitizer:
    """Sanitizes user input and LLM output to prevent XSS and injection attacks."""
    
    # Patterns that indicate potentially malicious content
    DANGEROUS_PATTERNS = [
        (r'<script[^>]*>.*?</script>', 'script tag'),
        (r'javascript:', 'javascript protocol'),
        (r'on\w+\s*=', 'inline event handler'),
        (r'<iframe[^>]*>.*?</iframe>', 'iframe tag'),
        (r'<object[^>]*>.*?</object>', 'object tag'),
        (r'<embed[^>]*>', 'embed tag'),
        (r'eval\s*\(', 'eval() call'),
        (r'exec\s*\(', 'exec() call'),
        (r'setTimeout\s*\(\s*["\']', 'setTimeout with string'),
        (r'setInterval\s*\(\s*["\']', 'setInterval with string'),
    ]
    
    # Markdown characters to escape for safe HTML rendering
    HTML_ESCAPE_MAP = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
    }
    
    @classmethod
    def sanitize_markdown(cls, text: str, allow_links: bool = True) -> SanitizeResult:
        """
        Sanitize markdown text for safe display.
        Removes potentially dangerous HTML while preserving formatting.
        """
        if not text:
            return SanitizeResult(text="", was_modified=False, warnings=[])
        
        original = text
        warnings = []
        
        # Check for dangerous patterns
        for pattern, description in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                warnings.append(f"Removed {description}")
                text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # If links are allowed, be more permissive but still sanitize
        if allow_links:
            # Allow markdown links but validate URLs
            text = cls._sanitize_links(text)
        else:
            # Remove all links
            text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
            text = re.sub(r'https?://\S+', '[link removed]', text)
        
        # Escape remaining HTML characters
        for char, escaped in cls.HTML_ESCAPE_MAP.items():
            text = text.replace(char, escaped)
        
        was_modified = text != original or len(warnings) > 0
        return SanitizeResult(text=text, was_modified=was_modified, warnings=warnings)
    
    @classmethod
    def _sanitize_links(cls, text: str) -> str:
        """Validate and sanitize URLs in markdown links."""
        def validate_url(match):
            full_match = match.group(0)
            url = match.group(1) if match.lastindex >= 1 else ""
            
            # Only allow http, https, mailto protocols
            if url:
                # Check for dangerous protocols
                url_lower = url.lower()
                if url_lower.startswith(('javascript:', 'data:', 'vbscript:')):
                    return match.group(2) if match.lastindex >= 2 else full_match
            
            return full_match
        
        # Pattern: [text](url)
        text = re.sub(
            r'\[([^\]]*)\]\(([^)]*)\)',
            validate_url,
            text
        )
        
        return text
    
    @classmethod
    def sanitize_user_input(cls, text: str) -> SanitizeResult:
        """
        Sanitize raw user input before processing.
        More strict than markdown sanitization.
        """
        if not text:
            return SanitizeResult(text="", was_modified=False, warnings=[])
        
        original = text
        warnings = []
        
        # Remove or escape control characters
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
        
        # Check for dangerous patterns
        for pattern, description in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                warnings.append(f"Blocked {description}")
                text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Trim whitespace
        text = text.strip()
        
        was_modified = text != original or len(warnings) > 0
        return SanitizeResult(text=text, was_modified=was_modified, warnings=warnings)
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize a filename to prevent path traversal attacks."""
        if not filename:
            return "unnamed"
        
        # Remove path separators
        filename = filename.replace('/', '').replace('\\', '')
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*]', '', filename)
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            max_name = 255 - len(ext) - 1
            filename = name[:max_name] + ('.' + ext if ext else '')
        
        return filename or "unnamed"
    
    @classmethod
    def validate_api_key(cls, key: Optional[str]) -> bool:
        """Validate that an API key is present and properly formatted."""
        if not key:
            return False
        
        # Basic validation - key should be a reasonable length
        if len(key) < 8:
            return False
        
        # Check for obviously invalid keys
        if key in ('null', 'undefined', 'your-key-here', 'placeholder'):
            return False
        
        return True


class OutputFormatter:
    """Formats output for safe display in the UI."""
    
    @staticmethod
    def format_code_block(code: str, language: str = "") -> str:
        """Format code block with syntax highlighting hints."""
        # Escape HTML in code
        safe_code = html.escape(code)
        lang_attr = f' class="language-{language}"' if language else ''
        return f'<pre><code{lang_attr}>{safe_code}</code></pre>'
    
    @staticmethod
    def format_error(message: str, include_details: bool = True) -> str:
        """Format error message for display."""
        # Don't expose internal details to users
        safe_message = html.escape(str(message))
        
        if not include_details:
            return "An error occurred. Please try again."
        
        return f"Error: {safe_message}"
    
    @staticmethod
    def format_success(message: str) -> str:
        """Format success message for display."""
        return f"✓ {html.escape(str(message))}"
    
    @staticmethod
    def format_warning(message: str) -> str:
        """Format warning message for display."""
        return f"⚠ {html.escape(str(message))}"


# Rate limiting utilities
class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}
    
    def is_allowed(self, key: str) -> bool:
        """Check if a request is allowed under rate limits."""
        import time
        current_time = time.time()
        
        if key not in self._requests:
            self._requests[key] = []
        
        # Clean old requests outside the window
        self._requests[key] = [
            t for t in self._requests[key]
            if current_time - t < self._window_seconds
        ]
        
        # Check if under limit
        if len(self._requests[key]) >= self._max_requests:
            return False
        
        # Record this request
        self._requests[key].append(current_time)
        return True
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests in current window."""
        import time
        current_time = time.time()
        
        if key not in self._requests:
            return self._max_requests
        
        recent = [
            t for t in self._requests[key]
            if current_time - t < self._window_seconds
        ]
        
        return max(0, self._max_requests - len(recent))
    
    def reset(self, key: str):
        """Reset rate limit for a key."""
        if key in self._requests:
            del self._requests[key]


# Global rate limiter instance
_global_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter()
    return _global_limiter