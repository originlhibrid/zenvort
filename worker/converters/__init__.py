# worker/converters/__init__.py
# Four responsibility-based converters.  Routes table decides which category
# handles each format pair; the converter handles internal library routing.

from worker.converters import documents
from worker.converters import images
from worker.converters import media
from worker.converters import ocr
