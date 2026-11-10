#!/usr/bin/env python3
"""
Small prototype: scan a directory of supplementary files and extract machine-readable datasets.
- Detect CSV and JSON files and record schema and counts
- Try to parse HTML files for simple tables and write CSVs
- For plain text, try to detect TSV/CSV rows
- Produce metadata.json with filename, mime_hint, schema, row_count, md5, source_url

No network activity. Standard library only.
"""
import sys, os, hashlib, json, csv, html.parser
from typing import List, Dict

OUT_DIR = 'out'

class TableHTMLParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_tr = False
        self.in_td = False
        self.rows = []
        self.cur_row = []
        self.cur_cell = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'table':
            self.in_table = True
        if not self.in_table:
            return
        if tag.lower() == 'tr':
            self.in_tr = True
            self.cur_row = []
        if tag.lower() in ('td','th'):
            self.in_td = True
            self.cur_cell = []

    def handle_endtag(self, tag):
        if tag.lower() == 'table':
            self.in_table = False
        if not self.in_table:
            return
        if tag.lower() in ('td','th') and self.in_td:
            self.in_td = False
            self.cur_row.append(''.join(self.cur_cell).strip())
        if tag.lower() == 'tr' and self.in_tr:
            self.in_tr = False
            if self.cur_row:
                self.rows.append(self.cur_row)

    def handle_data(self, data):
        if self.in_td:
            self.cur_cell.append(data)


def md5_of_file(path):
    h = hashlib.md5()
    with open(path,'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def is_likely_csv_text(s: str):
    # heuristic: many commas and consistent column counts
    lines = [l for l in s.splitlines() if l.strip()]
    if len(lines) < 2:
        return False
    counts = [line.count(',') for line in lines[:10]]
    return max(counts) >= 1 and min(counts) >= 0

def sniff_tsv(s: str):
    lines = [l for l in s.splitlines() if l.strip()]
    if len(lines) < 2:
        return None
    parts = [line.split('\t') for line in lines[:10]]
    colcounts = set(len(p) for p in parts)
    if len(colcounts) == 1 and next(iter(colcounts)) > 1:
        return parts
    return None

def process_file(path, outdir) -> Dict:
    name = os.path.basename(path)
    meta = {'filename': name, 'mime_hint': None, 'schema': None, 'row_count': None, 'md5': md5_of_file(path), 'source_url': ''}
    lower = name.lower()
    with open(path, 'rb') as fbin:
        raw = fbin.read()
    # try JSON
    if lower.endswith('.json'):
        meta['mime_hint'] = 'application/json'
        try:
            obj = json.loads(raw.decode('utf-8'))
            # if it's a list of records
            if isinstance(obj, list) and obj and isinstance(obj[0], dict):
                meta['schema'] = list(obj[0].keys())
                meta['row_count'] = len(obj)
            # write a pretty JSON copy into out
            outpath = os.path.join(outdir, name)
            with open(outpath, 'w', encoding='utf-8') as g:
                json.dump(obj, g, indent=2, ensure_ascii=False)
        except Exception:
            meta['mime_hint'] = 'application/json (invalid)'
        return meta
    # try CSV
    if lower.endswith('.csv'):
        meta['mime_hint'] = 'text/csv'
        s = raw.decode('utf-8', errors='replace')
        reader = csv.reader(s.splitlines())
        rows = list(reader)
        if rows:
            meta['schema'] = rows[0]
            meta['row_count'] = max(0, len(rows)-1)
        # copy
        outpath = os.path.join(outdir, name)
        with open(outpath,'w',encoding='utf-8') as g:
            g.write(s)
        return meta
    # try HTML table extraction
    text = raw.decode('utf-8', errors='replace')
    if '<table' in text.lower():
        parser = TableHTMLParser()
        parser.feed(text)
        if parser.rows:
            # assume first row is header if length >1
            header = parser.rows[0]
            rows = parser.rows[1:]
            meta['mime_hint'] = 'text/html (contains table)'
            meta['schema'] = header
            meta['row_count'] = len(rows)
            # write CSV
            outname = name + '.extracted.csv'
            outpath = os.path.join(outdir, outname)
            with open(outpath,'w',encoding='utf-8', newline='') as g:
                writer = csv.writer(g)
                writer.writerow(header)
                for r in rows:
                    writer.writerow(r)
            return meta
    # try TSV detection
    tsv = sniff_tsv(text)
    if tsv:
        meta['mime_hint'] = 'text/tab-separated-values'
        header = tsv[0]
        rows = tsv[1:]
        meta['schema'] = header
        meta['row_count'] = len(rows)
        outname = name + '.extracted.csv'
        outpath = os.path.join(outdir, outname)
        with open(outpath,'w',encoding='utf-8', newline='') as g:
            writer = csv.writer(g)
            writer.writerow(header)
            for r in rows:
                writer.writerow(r)
        return meta
    # fallback: record as binary or unknown text
    meta['mime_hint'] = 'application/octet-stream'
    return meta


def main(folder):
    if not os.path.isdir(folder):
        print('Provide a directory of downloaded supplement files.')
        return
    os.makedirs(OUT_DIR, exist_ok=True)
    metas = []
    for fn in sorted(os.listdir(folder)):
        path = os.path.join(folder, fn)
        if not os.path.isfile(path):
            continue
        print('Processing', fn)
        m = process_file(path, OUT_DIR)
        metas.append(m)
    meta_out = {'files': metas}
    with open(os.path.join(OUT_DIR,'metadata.json'),'w',encoding='utf-8') as g:
        json.dump(meta_out, g, indent=2, ensure_ascii=False)
    print('Done. Outputs in', OUT_DIR)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 main.py <supplement-folder>')
    else:
        main(sys.argv[1])
