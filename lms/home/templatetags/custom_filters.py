# templatetags/custom_filters.py
from django import template
import re

register = template.Library()

@register.filter
def extract_video_id(value):
    """
    Extracts the YouTube video ID from both full and short URLs.
    """
    # Check for full YouTube URL (https://www.youtube.com/watch?v=video_id)
    match = re.match(r'https://(?:www\.)?youtube\.com/watch\?v=([^&]+)', value)
    if match:
        return match.group(1)
    
    # Check for short YouTube URL (https://youtu.be/video_id)
    match = re.match(r'https://youtu\.be/([^?]+)', value)
    if match:
        return match.group(1)
    
    return value  # Return the original value if no match
