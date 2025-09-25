import re
from typing import List, Dict


def compute_relevancy_score(text: str, keywords: List[str]) -> float:
	if not text or not keywords:
		return 0.0
	
	content = text.lower()
	terms = [k.strip().lower() for k in keywords if k.strip()]
	if not terms:
		return 0.0
	
	# Enhanced scoring with section weighting
	sections = _identify_sections(text)
	
	total_score = 0.0
	max_possible_score = 0.0
	
	for term in terms:
		term_score = 0.0
		base_weight = 2.0 if any(x in term for x in ["+", "year", "experience"]) else 1.0
		max_possible_score += base_weight
		
		# Exact matches (higher weight)
		pattern = r"\b" + re.escape(term) + r"\b"
		exact_matches = len(re.findall(pattern, content))
		
		# Partial matches (lower weight)
		partial_pattern = re.escape(term)
		partial_matches = len(re.findall(partial_pattern, content)) - exact_matches
		
		# Weight matches by section
		for section_name, section_text in sections.items():
			section_weight = _get_section_weight(section_name)
			section_content = section_text.lower()
			
			section_exact = len(re.findall(pattern, section_content))
			section_partial = len(re.findall(partial_pattern, section_content)) - section_exact
			
			term_score += (section_exact * 1.0 + section_partial * 0.5) * section_weight
		
		# Add base score for any matches not in identified sections
		term_score += exact_matches * 0.8 + partial_matches * 0.3
		
		total_score += min(term_score * base_weight, base_weight * 3)  # Cap individual term scores
	
	# Normalize score
	if max_possible_score > 0:
		normalized_score = (total_score / max_possible_score) * 100
		return round(min(normalized_score, 100.0), 2)
	
	return 0.0


def _identify_sections(text: str) -> Dict[str, str]:
	# Identify different resume sections for weighted scoring
	sections = {}
	lines = text.splitlines()
	current_section = "general"
	section_content = []
	
	section_patterns = {
		"skills": re.compile(r"^\s*(?:technical\s+)?skills?|technologies|tech\s*stack\b", re.I),
		"experience": re.compile(r"^\s*(?:work\s+)?experience|employment|professional\s+experience\b", re.I),
		"education": re.compile(r"^\s*education|academic\s+background\b", re.I),
		"projects": re.compile(r"^\s*projects?\b", re.I),
		"summary": re.compile(r"^\s*(?:professional\s+)?summary|objective|profile\b", re.I)
	}
	
	for line in lines:
		l = line.strip()
		if not l:
			continue
		
		# Check if line starts a new section
		section_found = False
		for section_name, pattern in section_patterns.items():
			if pattern.search(l):
				if section_content:
					sections[current_section] = "\n".join(section_content)
				current_section = section_name
				section_content = []
				section_found = True
				break
		
		if not section_found:
			section_content.append(l)
	
	# Add final section
	if section_content:
		sections[current_section] = "\n".join(section_content)
	
	return sections


def _get_section_weight(section_name: str) -> float:
	# Weight different sections based on relevance for keyword matching
	weights = {
		"skills": 2.0,
		"experience": 1.8,
		"projects": 1.5,
		"summary": 1.3,
		"education": 1.0,
		"general": 0.8
	}
	return weights.get(section_name, 1.0)

