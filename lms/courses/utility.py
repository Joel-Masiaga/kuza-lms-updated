import io
import os
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from django.conf import settings
from datetime import date
import traceback

# --- CERTIFICATE CONFIGURATION ---
CERTIFICATE_TEMPLATE_PATH = os.path.join(settings.BASE_DIR, 'home', 'static', 'home', 'template.pdf')
PAGE_SIZE = landscape(letter)  # 11" x 8.5" landscape

# Page dimensions
PAGE_WIDTH = 11.0 * inch
PAGE_HEIGHT = 8.5 * inch



# Horizontal center (adjusted)
X_CENTER = (PAGE_WIDTH / 2) + (0.3 * inch)

# --- PRECISE Y COORDINATES (based on certificate template analysis) ---
# Student name: goes on the blank line after "This is awarded to"
STUDENT_NAME_Y = 4.0 * inch

# Course name: replaces the text area below (where course details go)
COURSE_NAME_Y = 2.8 * inch

# Date: positioned below, near the signature area
DATE_Y = 2.45 * inch

# --- FONT SETTINGS ---
FONT_NAME_BOLD = 'Helvetica-Bold'
FONT_NAME_REGULAR = 'Helvetica'

FONT_SIZE_NAME = 32       # Prominent for student name
FONT_SIZE_COURSE = 20     # Bold for course title
FONT_SIZE_DATE = 11       # Subtle for date

# --- COLORS (matching template's teal theme) ---
TEXT_COLOR_NAME = HexColor("#1a5490")     # Teal for student name
TEXT_COLOR_COURSE = HexColor("#1a5490")   # Teal for course name
TEXT_COLOR_DATE = HexColor("#1a5490")     # Blue for date


def generate_certificate_pdf(user, course):
    """
    Generates a PDF certificate by overlaying text onto the Kuza Ndoto Academy template.
    
    Args:
        user: User object containing student information
        course: Course object containing course details
        
    Returns:
        bytes: PDF content as bytes, or None if an error occurs
    """
    if not os.path.exists(CERTIFICATE_TEMPLATE_PATH):
        print(f"Error: Certificate template not found at {CERTIFICATE_TEMPLATE_PATH}")
        return None

    try:
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=PAGE_SIZE)

        # --- 1. STUDENT NAME (on the line after "This is awarded to") ---
        student_name = get_student_name(user)
        c.setFillColor(TEXT_COLOR_NAME)
        c.setFont(FONT_NAME_BOLD, FONT_SIZE_NAME)
        c.drawCentredString(X_CENTER, STUDENT_NAME_Y, student_name)

        # --- 2. COURSE NAME (in the designated course area) ---
        course_name = course.title
        c.setFillColor(TEXT_COLOR_COURSE)
        c.setFont(FONT_NAME_BOLD, FONT_SIZE_COURSE)
        c.drawCentredString(X_CENTER, COURSE_NAME_Y, course_name.upper())

        # --- 3. COMPLETION DATE (near signature area) ---
        completion_date = date.today().strftime("%B %d, %Y")
        c.setFillColor(TEXT_COLOR_DATE)
        c.setFont(FONT_NAME_REGULAR, FONT_SIZE_DATE)
        c.drawCentredString(X_CENTER, DATE_Y, f"Awarded on: {completion_date}")

        c.save()
        packet.seek(0)

        # Merge overlay with template
        overlay_pdf = PdfReader(packet)
        if not overlay_pdf.pages:
            print("Error: Overlay PDF has no pages.")
            return None

        with open(CERTIFICATE_TEMPLATE_PATH, "rb") as template_file:
            template_pdf = PdfReader(template_file)
            if not template_pdf.pages:
                print("Error: Template PDF has no pages.")
                return None

            output_writer = PdfWriter()
            template_page = template_pdf.pages[0]
            overlay_page = overlay_pdf.pages[0]

            template_page.merge_page(overlay_page)
            output_writer.add_page(template_page)

            output_buffer = io.BytesIO()
            output_writer.write(output_buffer)
            output_buffer.seek(0)

            return output_buffer.getvalue()

    except Exception as e:
        print(f"Error during PDF generation for user {user.id}, course {course.id}: {e}")
        traceback.print_exc()
        return None


def get_student_name(user):
    """
    Extract and format student name from user profile.
    
    Args:
        user: User object
        
    Returns:
        str: Formatted student name in Title Case
    """
    student_name = "Guest"
    
    if hasattr(user, 'profile') and user.profile:
        first = (user.profile.first_name or '').strip()
        last = (user.profile.last_name or '').strip()
        if first or last:
            student_name = f"{first} {last}".strip()
    
    if not student_name or student_name == "Guest":
        email_username = user.email.split('@')[0]
        student_name = email_username.replace('.', ' ').replace('_', ' ')
    
    return student_name.title()