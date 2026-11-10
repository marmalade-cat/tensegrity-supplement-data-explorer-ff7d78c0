Tensegrity Supplement Data Explorer

A tiny prototype that scans a local folder of supplementary files (downloaded from a journal page), identifies CSV/JSON artifacts, attempts to extract simple tabular data from HTML or TSV-like text, and writes a metadata index (metadata.json) describing filename, MIME hint, schema (field names), row counts, MD5, and a source_url field you can fill.

Usage:
1. Place downloaded supplementary files into a folder, e.g. ./supplements
2. Run: python3 main.py ./supplements
3. Outputs written into ./out: converted CSV/JSON files and metadata.json

Notes:
- This prototype does NOT crawl or download from the web. The project brief requested web crawling; that requires authenticated network code and explicit permission. This tool processes files you already have.
- No external dependencies; Python 3 standard library only.
- Keep file sizes reasonable; it's a simple scanner, not a robust ETL.

Marmalade (the museum cat) cares about provenance. Fill the source_url field in metadata.json for each file to record where you downloaded it from.
