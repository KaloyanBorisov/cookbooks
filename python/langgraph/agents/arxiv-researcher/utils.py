import re
from typing import Dict, Any
import aiohttp
import fitz  # PyMuPDF


async def extract_arxiv_id(text: str) -> str:
    """Extract arXiv ID from text containing arXiv URL or ID."""
    arxiv_patterns = [
        r"arxiv\.org/abs/(\d+\.\d+)",
        r"arxiv\.org/pdf/(\d+\.\d+)",
        r"(\d{4}\.\d{4,5})",
    ]

    for pattern in arxiv_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    raise ValueError(f"Could not extract arXiv ID from text: {text}")


async def download_arxiv_pdf_text(arxiv_id: str) -> str:
    """Download the full text content of an arXiv paper as extracted from its PDF."""
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    try:
        # Download the PDF as bytes
        async with aiohttp.ClientSession() as session:
            async with session.get(pdf_url, timeout=30) as response:
                if response.status != 200:
                    raise Exception(f"Failed to download PDF: status {response.status}")
                pdf_bytes = await response.read()

        # Process PDF bytes using PyMuPDF
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            full_text = ""
            for page in doc:
                full_text += page.get_text("text") + "\n"

        # Basic validation
        if len(full_text) < 100:
            raise Exception("Extracted text appears too short or invalid.")

        # Truncate to avoid context window issues
        if len(full_text) > 70000:
            full_text = full_text[:70000] + "\n\n[Content truncated due to length...]"

        return full_text

    except Exception as e:
        raise Exception(f"Error extracting text from arXiv paper {arxiv_id}: {str(e)}")
