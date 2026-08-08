import re
import io
import gc
import logging
import tracemalloc
from typing import BinaryIO
from PIL import Image
from cache import cached
from cache_config import CACHE_CATEGORY_SESSION

logger = logging.getLogger(__name__)

MAX_OCR_IMAGE_DIMENSION = 1800


def __getattr__(name):
    if name in ("pdfplumber", "pytesseract"):
        return __import__(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def optimize_image_for_ocr(image: Image.Image, max_dim: int = MAX_OCR_IMAGE_DIMENSION) -> Image.Image:
    """
    Optimizes a PIL Image for OCR processing to reduce memory consumption:
    1. Converts multi-channel (RGBA, CMYK, Palette) images to Grayscale ('L') or RGB,
       saving memory (1 byte/pixel vs 4 bytes/pixel).
    2. Resizes oversized images to a maximum dimension while maintaining aspect ratio.
    """
    if image is None:
        return None

    # Convert mode to grayscale or RGB if needed
    processed_image = image
    mode = getattr(image, "mode", None)
    if isinstance(mode, str):
        if mode in ("RGBA", "LA", "P", "CMYK"):
            processed_image = image.convert("L")
        elif mode not in ("L", "RGB"):
            processed_image = image.convert("RGB")

    # Downscale image if dimensions exceed max_dim
    size = getattr(processed_image, "size", None)
    if isinstance(size, (tuple, list)) and len(size) == 2:
        w, h = size
        if isinstance(w, (int, float)) and isinstance(h, (int, float)) and (w > max_dim or h > max_dim):
            scale = max_dim / float(max(w, h))
            new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
            
            resample = getattr(Image, "Resampling", Image).LANCZOS
            resized_img = processed_image.resize((new_w, new_h), resample=resample)
            if processed_image is not image and hasattr(processed_image, "close"):
                processed_image.close()
            processed_image = resized_img

    return processed_image


def extract_text_from_bytes(file_bytes: bytes, file_type: str) -> str:
    """
    Extracts text from raw file bytes (PDF or Image).
    Pure, thread-safe function suitable for background processing.
    Efficiently releases resources after processing to minimize peak memory usage.
    """
    import pdfplumber
    import pytesseract

    if not file_bytes:
        return ""
    text = ""
    file_type_lower = (file_type or "").lower()

    if "pdf" in file_type_lower:
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    if hasattr(page, "flush_cache"):
                        page.flush_cache()
        except Exception as e:
            logger.warning(f"Error reading PDF bytes: {e}")

    elif "image" in file_type_lower:
        try:
            with Image.open(io.BytesIO(file_bytes)) as raw_image:
                opt_image = optimize_image_for_ocr(raw_image)
                try:
                    text = pytesseract.image_to_string(opt_image)
                finally:
                    if opt_image is not raw_image and hasattr(opt_image, "close"):
                        opt_image.close()
        except Exception as e:
            logger.warning(f"Error reading image bytes: {e}")
        finally:
            gc.collect()

    return text


@cached(category=CACHE_CATEGORY_SESSION)
def extract_text_from_file(uploaded_file: BinaryIO) -> str:
    """
    Extracts text from a Streamlit UploadedFile object or file mock.
    Uses caching to avoid re-running OCR on identical files.
    Optimizes image memory and releases resources efficiently.
    """
    import pdfplumber
    import pytesseract

    if uploaded_file is None:
        return ""

    text = ""
    file_type = getattr(uploaded_file, "type", "")

    if "pdf" in file_type:
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    if hasattr(page, "flush_cache"):
                        page.flush_cache()
        except Exception as e:
            logger.warning(f"Error reading PDF: {e}")

    elif "image" in file_type:
        try:
            raw_image = Image.open(uploaded_file)
            opt_image = optimize_image_for_ocr(raw_image)
            try:
                text = pytesseract.image_to_string(opt_image)
            finally:
                if opt_image is not raw_image and hasattr(opt_image, "close"):
                    opt_image.close()
                if hasattr(raw_image, "close"):
                    raw_image.close()
        except Exception as e:
            logger.warning(f"Error reading image: {e}")
        finally:
            gc.collect()

    return text


@cached(category=CACHE_CATEGORY_SESSION)
def parse_energy_consumption(text: str | None) -> float | None:
    """
    Parses energy consumption values from text.
    Looks for patterns like '350 kWh', 'Total Consumption: 400', etc.
    Returns the float value if found, else None.
    """
    if not text:
        return None

    # Common regex patterns for utility bills
    patterns = [
        # Match 'Number kWh' or 'Numberkwh' e.g. 350 kWh, 1,200.5 kWh, -100 kWh
        r'(-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(?:kWh|kwh|KWH)',
        # Match 'Total Consumption ... Number' or 'Total ... Number' or 'Usage ... Number'
        r'(?:total\s+consumption|total|usage|total\s+usage|electricity\s+usage).*?(-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(?:kWh|kwh)?'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            val_str = matches[0].replace(',', '')
            try:
                return float(val_str)
            except ValueError:
                continue

    return None


def benchmark_ocr_memory(image_bytes: bytes) -> dict:
    """
    Benchmarks memory usage during OCR processing of an image.
    Returns peak memory allocated (in KB) and reduction statistics.
    """
    import pytesseract

    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()
    
    try:
        with Image.open(io.BytesIO(image_bytes)) as raw_img:
            opt_img = optimize_image_for_ocr(raw_img)
            _ = pytesseract.image_to_string(opt_img)
            if opt_img is not raw_img and hasattr(opt_img, "close"):
                opt_img.close()
    except Exception as e:
        logger.warning(f"Benchmark OCR error: {e}")
            
    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()
    
    stats = snapshot_after.compare_to(snapshot_before, 'lineno')
    total_allocated_kb = sum(stat.size for stat in stats) / 1024.0
    
    gc.collect()
    return {
        "allocated_kb": round(total_allocated_kb, 2),
        "status": "success"
    }
