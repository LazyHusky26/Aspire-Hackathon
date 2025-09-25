import argparse
import os
import sys
from typing import List, Dict, Any

import pandas as pd
from tqdm import tqdm

from src.resume_cua.readers import read_text_from_file
from src.resume_cua.extractors import extract_resume_fields
from src.resume_cua.scoring import compute_relevancy_score


SUPPORTED_EXTS = {".pdf", ".docx", ".txt"}


def list_resume_files(folder: str) -> List[str]:
	files: List[str] = []
	for root, _, filenames in os.walk(folder):
		for name in filenames:
			ext = os.path.splitext(name)[1].lower()
			if ext in SUPPORTED_EXTS:
				files.append(os.path.join(root, name))
	return sorted(files)


def process_folder(folder: str, use_spacy: bool, keywords: List[str]) -> List[Dict[str, Any]]:
	rows: List[Dict[str, Any]] = []
	for path in tqdm(list_resume_files(folder), desc="Parsing resumes", unit="file"):
		try:
			text = read_text_from_file(path)
			data = extract_resume_fields(text, use_spacy=use_spacy)
			if keywords:
				score = compute_relevancy_score(text, keywords)
				data["RelevancyScore"] = score
			data["SourceFile"] = os.path.basename(path)
			rows.append(data)
		except Exception as e:
			rows.append({
				"Name": "",
				"Email": "",
				"Phone": "",
				"LinkedIn": "",
				"GitHub": "",
				"Education": "",
				"Experience": "",
				"Skills": "",
				"RelevancyScore": None,
				"SourceFile": os.path.basename(path),
				"Error": str(e),
			})
	return rows


def export_rows(rows: List[Dict[str, Any]], output_path: str) -> None:
	df = pd.DataFrame(rows)
	if output_path.lower().endswith(".xlsx"):
		df.to_excel(output_path, index=False)
	else:
		df.to_csv(output_path, index=False)


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="AI-Powered Resume Parser (CUA)")
	parser.add_argument("--input", default=".", help="Folder path containing resumes (default: current folder)")
	parser.add_argument("--output", default="candidates.csv", help="Output CSV/XLSX path (default: candidates.csv)")
	parser.add_argument("--use-spacy", action="store_true", help="Enable spaCy-enhanced entity detection")
	parser.add_argument("--keywords", default="", help="Comma-separated keywords for relevancy scoring")
	parser.add_argument("--open", action="store_true", help="Open the output file after export")
	return parser.parse_args()


def main() -> None:
	args = parse_args()
	folder = args.input
	if not os.path.isdir(folder):
		print(f"Input is not a folder: {folder}")
		sys.exit(1)
	keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
	rows = process_folder(folder, use_spacy=args.use_spacy, keywords=keywords)
	output_path = args.output
	export_rows(rows, output_path)
	print(f"Wrote {len(rows)} rows to {output_path}")
	if args.open:
		try:
			os.startfile(output_path)  # Windows
		except Exception:
			pass


if __name__ == "__main__":
	main()

