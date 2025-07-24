"""
Canvas Content Scanner Utilities

Adapted from the original CanvasURLScanner script for use with the QA framework.
Provides HTML parsing and URL replacement functionality using BeautifulSoup.
"""

import logging
import re
from typing import Dict, List, Tuple, Optional
from bs4 import BeautifulSoup

from ..base.data_models import FindReplaceConfig

logger = logging.getLogger(__name__)


async def replace_urls_in_content(
    content: str, 
    url_mappings: List[Dict[str, str]], 
    config: FindReplaceConfig
) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Replace multiple target URLs with their replacements in content using BeautifulSoup.
    
    Args:
        content: HTML content to process
        url_mappings: List of URL mapping dictionaries with 'find' and 'replace' keys
        config: Task configuration for replacement options
        
    Returns:
        Tuple of (modified_content, list_of_replacements)
    """
    if not content:
        logger.info("Content is empty, skipping replacement")
        return content, []

    replacements = []
    
    try:
        # Convert url_mappings to dictionary for easier processing
        url_map = {mapping['find']: mapping['replace'] for mapping in url_mappings}
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find and replace URLs in href attributes
        for link in soup.find_all('a', href=True):
            href = link['href']
            original_href = href
            
            for target_url, replacement_url in url_map.items():
                if _should_replace_url(href, target_url, config):
                    logger.info(f"Found target URL in href: {href}")
                    
                    if config.whole_word_only:
                        # Use word boundary matching
                        pattern = r'\b' + re.escape(target_url) + r'\b'
                        flags = 0 if config.case_sensitive else re.IGNORECASE
                        new_href = re.sub(pattern, replacement_url, href, flags=flags)
                    else:
                        # Simple string replacement
                        if config.case_sensitive:
                            new_href = href.replace(target_url, replacement_url)
                        else:
                            # Case-insensitive replacement
                            pattern = re.escape(target_url)
                            new_href = re.sub(pattern, replacement_url, href, flags=re.IGNORECASE)
                    
                    if new_href != href:
                        link['href'] = new_href
                        replacements.append((target_url, replacement_url))
                        href = new_href  # Update for potential multiple replacements
        
        # Find and replace URLs in src attributes (images, videos, etc.)
        for element in soup.find_all(attrs={"src": True}):
            src = element['src']
            original_src = src
            
            for target_url, replacement_url in url_map.items():
                if _should_replace_url(src, target_url, config):
                    logger.info(f"Found target URL in src: {src}")
                    
                    if config.whole_word_only:
                        pattern = r'\b' + re.escape(target_url) + r'\b'
                        flags = 0 if config.case_sensitive else re.IGNORECASE
                        new_src = re.sub(pattern, replacement_url, src, flags=flags)
                    else:
                        if config.case_sensitive:
                            new_src = src.replace(target_url, replacement_url)
                        else:
                            pattern = re.escape(target_url)
                            new_src = re.sub(pattern, replacement_url, src, flags=re.IGNORECASE)
                    
                    if new_src != src:
                        element['src'] = new_src
                        replacements.append((target_url, replacement_url))
                        src = new_src
        
        # Find and replace URLs in data-api-endpoint attributes (Canvas-specific)
        for element in soup.find_all(attrs={"data-api-endpoint": True}):
            endpoint = element['data-api-endpoint']
            original_endpoint = endpoint
            
            for target_url, replacement_url in url_map.items():
                if _should_replace_url(endpoint, target_url, config):
                    logger.info(f"Found target URL in data-api-endpoint: {endpoint}")
                    
                    if config.whole_word_only:
                        pattern = r'\b' + re.escape(target_url) + r'\b'
                        flags = 0 if config.case_sensitive else re.IGNORECASE
                        new_endpoint = re.sub(pattern, replacement_url, endpoint, flags=flags)
                    else:
                        if config.case_sensitive:
                            new_endpoint = endpoint.replace(target_url, replacement_url)
                        else:
                            pattern = re.escape(target_url)
                            new_endpoint = re.sub(pattern, replacement_url, endpoint, flags=re.IGNORECASE)
                    
                    if new_endpoint != endpoint:
                        element['data-api-endpoint'] = new_endpoint
                        replacements.append((target_url, replacement_url))
                        endpoint = new_endpoint
        
        # Find and replace URLs in other common attributes
        common_url_attributes = ['action', 'formaction', 'poster', 'background']
        for attr in common_url_attributes:
            for element in soup.find_all(attrs={attr: True}):
                attr_value = element[attr]
                original_value = attr_value
                
                for target_url, replacement_url in url_map.items():
                    if _should_replace_url(attr_value, target_url, config):
                        logger.info(f"Found target URL in {attr}: {attr_value}")
                        
                        if config.whole_word_only:
                            pattern = r'\b' + re.escape(target_url) + r'\b'
                            flags = 0 if config.case_sensitive else re.IGNORECASE
                            new_value = re.sub(pattern, replacement_url, attr_value, flags=flags)
                        else:
                            if config.case_sensitive:
                                new_value = attr_value.replace(target_url, replacement_url)
                            else:
                                pattern = re.escape(target_url)
                                new_value = re.sub(pattern, replacement_url, attr_value, flags=re.IGNORECASE)
                        
                        if new_value != attr_value:
                            element[attr] = new_value
                            replacements.append((target_url, replacement_url))
                            attr_value = new_value
        
        # Also check for URLs in plain text nodes (if include_html_attributes is True)
        if config.include_html_attributes:
            text_nodes = soup.find_all(string=True)
            for text_node in text_nodes:
                # Skip script and style tags
                if text_node.parent.name not in ['script', 'style']:
                    original_text = str(text_node)
                    new_text = original_text
                    
                    for target_url, replacement_url in url_map.items():
                        if _should_replace_url(new_text, target_url, config):
                            logger.info(f"Found target URL in text: {text_node}")
                            
                            if config.whole_word_only:
                                pattern = r'\b' + re.escape(target_url) + r'\b'
                                flags = 0 if config.case_sensitive else re.IGNORECASE
                                replaced_text = re.sub(pattern, replacement_url, new_text, flags=flags)
                            else:
                                if config.case_sensitive:
                                    replaced_text = new_text.replace(target_url, replacement_url)
                                else:
                                    pattern = re.escape(target_url)
                                    replaced_text = re.sub(pattern, replacement_url, new_text, flags=re.IGNORECASE)
                            
                            if replaced_text != new_text:
                                replacements.append((target_url, replacement_url))
                                new_text = replaced_text
                    
                    # Replace the text node if it was modified
                    if new_text != original_text:
                        text_node.replace_with(new_text)

        new_content = str(soup)
        
        if replacements:
            logger.info(f"Made {len(replacements)} replacements in content")
        
        return new_content, replacements

    except Exception as e:
        logger.error(f"Error during URL replacement: {str(e)}")
        return content, []


def _should_replace_url(content: str, target_url: str, config: FindReplaceConfig) -> bool:
    """
    Determine if a URL should be replaced based on configuration.
    
    Args:
        content: Content to check
        target_url: URL to search for
        config: Replacement configuration
        
    Returns:
        True if URL should be replaced
    """
    if not content or not target_url:
        return False
    
    if config.case_sensitive:
        return target_url in content
    else:
        return target_url.lower() in content.lower()


def extract_urls_from_content(content: str) -> List[str]:
    """
    Extract all URLs from HTML content.
    
    Args:
        content: HTML content to scan
        
    Returns:
        List of unique URLs found in content
    """
    if not content:
        return []
    
    urls = set()
    
    try:
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract URLs from common attributes
        url_attributes = ['href', 'src', 'action', 'formaction', 'poster', 'background', 'data-api-endpoint']
        
        for attr in url_attributes:
            for element in soup.find_all(attrs={attr: True}):
                url = element[attr]
                if url and url.startswith(('http://', 'https://', '//')):
                    urls.add(url)
        
        # Extract URLs from text using regex
        text_content = soup.get_text()
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        text_urls = re.findall(url_pattern, text_content)
        urls.update(text_urls)
        
    except Exception as e:
        logger.error(f"Error extracting URLs from content: {e}")
    
    return list(urls)


def validate_html_content(content: str) -> Dict[str, any]:
    """
    Validate HTML content and return structure information.
    
    Args:
        content: HTML content to validate
        
    Returns:
        Dictionary with validation results and content statistics
    """
    if not content:
        return {
            "is_valid": False,
            "error": "Content is empty",
            "stats": {}
        }
    
    try:
        soup = BeautifulSoup(content, 'html.parser')
        
        # Count different types of elements
        stats = {
            "total_elements": len(soup.find_all()),
            "links": len(soup.find_all('a')),
            "images": len(soup.find_all('img')),
            "forms": len(soup.find_all('form')),
            "tables": len(soup.find_all('table')),
            "lists": len(soup.find_all(['ul', 'ol'])),
            "headings": len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])),
            "paragraphs": len(soup.find_all('p')),
            "divs": len(soup.find_all('div')),
            "spans": len(soup.find_all('span'))
        }
        
        # Check for common issues
        issues = []
        
        # Check for links without href
        empty_links = soup.find_all('a', href='')
        if empty_links:
            issues.append(f"Found {len(empty_links)} links with empty href attributes")
        
        # Check for images without alt text
        images_without_alt = soup.find_all('img', alt='')
        if images_without_alt:
            issues.append(f"Found {len(images_without_alt)} images without alt text")
        
        # Check for broken HTML structure
        if not soup.find('html') and (soup.find('head') or soup.find('body')):
            issues.append("HTML structure may be incomplete (missing html tag)")
        
        return {
            "is_valid": True,
            "stats": stats,
            "issues": issues,
            "content_length": len(content),
            "text_length": len(soup.get_text()),
            "has_forms": stats["forms"] > 0,
            "has_tables": stats["tables"] > 0,
            "has_media": stats["images"] > 0
        }
        
    except Exception as e:
        return {
            "is_valid": False,
            "error": f"HTML parsing error: {str(e)}",
            "stats": {}
        }


def sanitize_content_for_canvas(content: str) -> str:
    """
    Sanitize HTML content for Canvas compatibility.
    
    Args:
        content: HTML content to sanitize
        
    Returns:
        Sanitized HTML content
    """
    if not content:
        return content
    
    try:
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remove potentially problematic elements
        for script in soup.find_all('script'):
            script.decompose()
        
        for style in soup.find_all('style'):
            # Keep basic styles but remove potentially problematic ones
            if style.string and any(danger in style.string.lower() for danger in ['javascript:', '@import', 'expression(']):
                style.decompose()
        
        # Clean up attributes that might cause issues
        for element in soup.find_all():
            # Remove potentially dangerous attributes
            dangerous_attrs = ['onload', 'onerror', 'onclick', 'onmouseover', 'onmouseout']
            for attr in dangerous_attrs:
                if element.has_attr(attr):
                    del element[attr]
            
            # Clean up style attributes
            if element.has_attr('style'):
                style_value = element['style']
                if any(danger in style_value.lower() for danger in ['javascript:', 'expression(', '@import']):
                    del element['style']
        
        return str(soup)
        
    except Exception as e:
        logger.error(f"Error sanitizing content: {e}")
        return content 