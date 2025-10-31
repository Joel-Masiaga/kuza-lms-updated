from django import template
import re

register = template.Library()

# This new regex is more robust and finds the 11-character ID
# from all common YouTube URL formats.
YOUTUBE_ID_PATTERN = re.compile(
    r"""
    (?:https?://)?                  # Optional http(s)://
    (?:www\.)?                      # Optional www.
    (?:
        youtube\.com/               # Standard domain
        (?:
            watch\?v=([a-zA-Z0-9_-]{11})     # ?v=VIDEO_ID
            |
            embed/([a-zA-Z0-9_-]{11})      # /embed/VIDEO_ID
            |
            shorts/([a-zA-Z0-9_-]{11})     # /shorts/VIDEO_ID
            |
            v/([a-zA-Z0-9_-]{11})          # /v/VIDEO_ID
        )
        |
        youtu\.be/([a-zA-Z0-9_-]{11})     # Short domain youtu.be/VIDEO_ID
    )
    """, 
    re.VERBOSE
)

@register.filter
def extract_video_id(value):
    """
    Extracts the 11-character YouTube video ID from various common URL formats.
    Returns the ID string if found, otherwise returns None.
    """
    if not isinstance(value, str):
        return None

    match = YOUTUBE_ID_PATTERN.search(value)
    
    if match:
        # The ID will be in one of the capturing groups.
        # We iterate through the groups to find the one that captured the ID.
        for group in match.groups():
            if group:
                return group  # This is the 11-character ID
    return None