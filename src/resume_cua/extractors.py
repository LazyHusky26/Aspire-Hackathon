import re
from typing import Dict, Any, List, Optional, Tuple

from .standardize import standardize_phone, normalize_url, normalize_skills, join_list

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
# Enhanced phone pattern for international formats
PHONE_TEXT_RE = re.compile(r"(?:\+?[\d\s\-\(\)\.]{7,})", re.I)
# Enhanced URL pattern for more social profiles
URL_RE = re.compile(r"(https?://)?(www\.)?(linkedin\.com/in/[^\s]+|github\.com/[^\s]+)", re.I)
YEAR_RE = re.compile(r"\b(20\d{2}|19\d{2})\b")

# Enhanced patterns for better extraction
NAME_BLACKLIST = re.compile(r"\b(resume|cv|curriculum vitae|profile|contact|email|phone|address)\b", re.I)
DEGREE_PATTERNS = re.compile(r"\b(B\.?(?:A|S|Tech|E|Sc|Com|BA|BS|BE)?|Bachelor(?:'?s)?|M\.?(?:A|S|Tech|E|Sc|BA|MBA|MS|ME)?|Master(?:'?s)?|PhD|Ph\.?D\.?|Doctor(?:ate)?|Associate|Diploma|Certificate|BSc|MSc|BEng|MEng|LLB|LLM|MD|JD)\b", re.I)
UNIVERSITY_PATTERNS = re.compile(r"\b(University|College|Institute|School|Academy|IIT|IIIT|NIT|MIT|Stanford|Harvard|Berkeley|UCLA|USC|NYU|Columbia|Yale|Princeton|Cornell|Carnegie|Mellon|Georgia Tech|Caltech|Northwestern|Duke|Vanderbilt|Rice|Emory)\b", re.I)
JOB_TITLE_PATTERNS = re.compile(r"\b(Engineer|Developer|Programmer|Analyst|Manager|Director|Lead|Senior|Junior|Intern|Consultant|Architect|Designer|Specialist|Coordinator|Administrator|Executive|Officer|Associate|Assistant|Technician|Supervisor|Team Lead)\b", re.I)
COMPANY_INDICATORS = re.compile(r"\b(Inc\.?|LLC|Corp\.?|Corporation|Company|Co\.?|Ltd\.?|Limited|Technologies|Tech|Solutions|Systems|Services|Group|Consulting|Software|Digital|Labs?|Studio|Agency)\b", re.I)


def _maybe_spacy_ents(text: str, use_spacy: bool) -> Dict[str, List[str]]:
	if not use_spacy:
		return {"PERSON": [], "ORG": [], "GPE": [], "MONEY": [], "DATE": []}
	try:
		import spacy
		nlp = spacy.load("en_core_web_sm")
		doc = nlp(text)
		persons = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON" and len(ent.text.split()) <= 4]
		orgs = [ent.text.strip() for ent in doc.ents if ent.label_ == "ORG"]
		locations = [ent.text.strip() for ent in doc.ents if ent.label_ == "GPE"]
		money = [ent.text.strip() for ent in doc.ents if ent.label_ == "MONEY"]
		dates = [ent.text.strip() for ent in doc.ents if ent.label_ == "DATE"]
		return {"PERSON": persons, "ORG": orgs, "GPE": locations, "MONEY": money, "DATE": dates}
	except Exception:
		return {"PERSON": [], "ORG": [], "GPE": [], "MONEY": [], "DATE": []}


def _extract_email(text: str) -> str:
	m = EMAIL_RE.search(text)
	return m.group(0).strip() if m else ""


def _extract_phone(text: str) -> str:
	# Enhanced phone extraction with better international support
	candidates: List[str] = []
	
	# Look for phone patterns near contact keywords
	contact_context = re.compile(r"(?:phone|mobile|cell|tel|contact)[\s:]*([+\d\s\-\(\)\.]{7,})", re.I)
	for m in contact_context.finditer(text):
		phone_part = m.group(1).strip()
		digits = re.sub(r"\D+", "", phone_part)
		if 7 <= len(digits) <= 15:  # International phone range
			candidates.append(digits)
	
	# Fallback to general phone pattern
	if not candidates:
		for m in PHONE_TEXT_RE.finditer(text):
			digits = re.sub(r"\D+", "", m.group(0))
			if 7 <= len(digits) <= 15:
				candidates.append(digits)
	
	if not candidates:
		return ""
	
	# Score candidates: prefer US format (10-11 digits), then international
	def score_phone(digits: str) -> Tuple[int, int]:
		length_score = 0
		if len(digits) == 10:
			length_score = 3  # US format
		elif len(digits) == 11 and digits.startswith("1"):
			length_score = 2  # US with country code
		elif 7 <= len(digits) <= 15:
			length_score = 1  # International
		
		format_score = 1 if digits.startswith(("1", "91", "44", "33", "49")) else 0
		return (length_score, format_score)
	
	candidates.sort(key=score_phone, reverse=True)
	return standardize_phone(candidates[0])


def _extract_urls(text: str) -> Dict[str, str]:
	linkedin = ""
	github = ""
	for m in URL_RE.finditer(text):
		full = (m.group(0) or "").strip()
		if "linkedin.com" in full.lower() and not linkedin:
			linkedin = normalize_url(full)
		if "github.com" in full.lower() and not github:
			github = normalize_url(full)
	return {"LinkedIn": linkedin, "GitHub": github}


def _extract_name(text: str, spacy_ents: Dict[str, List[str]]) -> str:
	# Multi-strategy name extraction with confidence scoring
	candidates = []
	
	# Strategy 1: spaCy PERSON entities
	if spacy_ents.get("PERSON"):
		for person in spacy_ents["PERSON"][:3]:  # Check top 3
			if 2 <= len(person.split()) <= 4 and not NAME_BLACKLIST.search(person):
				candidates.append((person, 3))  # High confidence
	
	# Strategy 2: First few lines analysis
	lines = [l.strip() for l in text.splitlines() if l.strip()]
	for i, line in enumerate(lines[:5]):  # Check first 5 lines
		if i > 2:  # Lower confidence for lines further down
			break
			
		# Clean the line
		clean_line = line
		clean_line = EMAIL_RE.sub("", clean_line)
		clean_line = re.sub(PHONE_TEXT_RE, "", clean_line)
		clean_line = re.sub(r"[^\w\s]", " ", clean_line)
		
		words = [w for w in clean_line.split() if w and not NAME_BLACKLIST.search(w)]
		
		if 2 <= len(words) <= 4:
			# Check if it looks like a name (proper case, no numbers)
			if all(w[0].isupper() and w.isalpha() for w in words):
				confidence = 2 if i == 0 else 1
				candidates.append((" ".join(words), confidence))
	
	# Strategy 3: Look for "Name:" patterns
	name_pattern = re.compile(r"(?:name|full name)[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})", re.I)
	for m in name_pattern.finditer(text):
		candidates.append((m.group(1), 2))
	
	if not candidates:
		return ""
	
	# Return highest confidence candidate
	candidates.sort(key=lambda x: x[1], reverse=True)
	return candidates[0][0]


def _extract_education(text: str, spacy_ents: Dict[str, List[str]]) -> str:
	# Enhanced education extraction with better degree and institution matching
	lines = [l.strip() for l in text.splitlines()]
	edu_entries: List[Dict[str, str]] = []
	
	# Find education section boundaries
	edu_section_start = -1
	edu_section_end = len(lines)
	
	for i, line in enumerate(lines):
		if re.search(r"^\s*education\b", line, re.I):
			edu_section_start = i
		elif edu_section_start >= 0 and re.search(r"^\s*(experience|work|skills|projects|certifications)\b", line, re.I):
			edu_section_end = i
			break
	
	# Process education section or entire text if no section found
	search_lines = lines[edu_section_start+1:edu_section_end] if edu_section_start >= 0 else lines
	
	i = 0
	while i < len(search_lines):
		line = search_lines[i].strip()
		if not line:
			i += 1
			continue
			
		# Look for degree patterns
		degree_match = DEGREE_PATTERNS.search(line)
		if degree_match:
			entry = {"degree": "", "institution": "", "year": "", "gpa": "", "honors": ""}
			
			# Extract degree information
			entry["degree"] = line
			
			# Look for GPA
			gpa_match = re.search(r"(?:gpa|cgpa)[\s:]*(\d+\.?\d*(?:/\d+\.?\d*)?)", line, re.I)
			if gpa_match:
				entry["gpa"] = gpa_match.group(1)
			
			# Look for honors/distinctions
			honors_match = re.search(r"\b(summa cum laude|magna cum laude|cum laude|with honors|distinction|first class|dean'?s list)\b", line, re.I)
			if honors_match:
				entry["honors"] = honors_match.group(1)
			
			# Extract year from current line or nearby lines
			year_match = YEAR_RE.search(line)
			if year_match:
				entry["year"] = year_match.group(1)
			
			# Look for institution on same line or next few lines
			if UNIVERSITY_PATTERNS.search(line):
				entry["institution"] = line
			else:
				# Check next few lines for institution
				for j in range(i + 1, min(i + 4, len(search_lines))):
					next_line = search_lines[j].strip()
					if not next_line:
						continue
					if UNIVERSITY_PATTERNS.search(next_line):
						entry["institution"] = next_line
						if not entry["year"]:
							year_match = YEAR_RE.search(next_line)
							if year_match:
								entry["year"] = year_match.group(1)
						break
			
			# Format the entry
			formatted_entry = entry["degree"]
			if entry["institution"] and entry["institution"].lower() != entry["degree"].lower():
				# Clean institution name
				inst_clean = re.split(r"[\|\-–]", entry["institution"])[0].strip()
				formatted_entry += f" - {inst_clean}"
			
			if entry["year"]:
				formatted_entry += f" ({entry['year']})"
			
			if entry["gpa"]:
				formatted_entry += f" | GPA: {entry['gpa']}"
				
			if entry["honors"]:
				formatted_entry += f" | {entry['honors']}"
			
			edu_entries.append({"text": formatted_entry, "year": entry["year"]})
		
		i += 1
	
	# Remove duplicates and sort by year (most recent first)
	unique_entries = []
	seen = set()
	for entry in edu_entries:
		if entry["text"] not in seen:
			seen.add(entry["text"])
			unique_entries.append(entry)
	
	# Sort by year if available
	unique_entries.sort(key=lambda x: int(x["year"]) if x["year"].isdigit() else 0, reverse=True)
	
	return " | ".join([entry["text"] for entry in unique_entries])[:800]


def _extract_experience(text: str) -> str:
	# Enhanced experience extraction with better job parsing
	lines = [l.strip() for l in text.splitlines()]
	experiences: List[Dict[str, str]] = []
	
	# Find experience section
	exp_section_start = -1
	exp_section_end = len(lines)
	
	for i, line in enumerate(lines):
		if re.search(r"^\s*(experience|work experience|employment|professional experience)\b", line, re.I):
			exp_section_start = i
		elif exp_section_start >= 0 and re.search(r"^\s*(education|skills|projects|certifications)\b", line, re.I):
			exp_section_end = i
			break
	
	search_lines = lines[exp_section_start+1:exp_section_end] if exp_section_start >= 0 else lines
	
	i = 0
	while i < len(search_lines):
		line = search_lines[i].strip()
		if not line:
			i += 1
			continue
		
		# Look for job titles or company indicators
		has_job_title = JOB_TITLE_PATTERNS.search(line)
		has_company = COMPANY_INDICATORS.search(line)
		has_dates = re.search(r"\b(\d{4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b", line, re.I)
		
		if has_job_title or (has_company and has_dates):
			exp_entry = {"title": "", "company": "", "duration": "", "description": ""}
			
			# Extract job title and company from current line
			if has_job_title:
				exp_entry["title"] = line
			
			# Look for duration patterns
			duration_patterns = [
				r"(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\s*[-–]\s*(?:Present|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}))",
				r"(\d{4}\s*[-–]\s*(?:Present|\d{4}))",
				r"(\d{1,2}/\d{4}\s*[-–]\s*(?:Present|\d{1,2}/\d{4}))"
			]
			
			for pattern in duration_patterns:
				duration_match = re.search(pattern, line, re.I)
				if duration_match:
					exp_entry["duration"] = duration_match.group(1)
					break
			
			# Look for company name in current or next lines
			if has_company:
				exp_entry["company"] = line
			else:
				# Check next few lines for company
				for j in range(i + 1, min(i + 3, len(search_lines))):
					next_line = search_lines[j].strip()
					if COMPANY_INDICATORS.search(next_line):
						exp_entry["company"] = next_line
						break
			
			# Format experience entry (without descriptions to keep it clean)
			formatted_exp = ""
			if exp_entry["title"]:
				formatted_exp = exp_entry["title"]
			if exp_entry["company"] and exp_entry["company"] != exp_entry["title"]:
				company_clean = re.split(r"[\|\-–]", exp_entry["company"])[0].strip()
				if formatted_exp:
					formatted_exp += f" at {company_clean}"
				else:
					formatted_exp = company_clean
			if exp_entry["duration"]:
				formatted_exp += f" ({exp_entry['duration']})"
			
			if formatted_exp:
				experiences.append(formatted_exp)
		
		i += 1
	
	# Return clean experience entries without descriptions
	return " | ".join(experiences[:5])


def _collect_skill_tokens_from_section(section_text: str) -> List[str]:
	# Clean skill token collection - focus on concise technical skills
	candidates: List[str] = []
	
	# Split by various delimiters
	for raw in re.split(r"[\u2022•·|/;,\n\t]", section_text):
		item = raw.strip().strip("-•\u2022•·*•()[]{}").strip()
		if not item or len(item) < 2:
			continue
			
		# Clean up common artifacts
		item = re.sub(r"^\d+[\.\)]\s*", "", item)  # Remove numbering
		item = re.sub(r"\s+", " ", item)  # Normalize whitespace
		
		# Filter out long descriptions and keep only concise skills (max 25 chars)
		if (re.search(r"[A-Za-z0-9]", item) and 
			len(item) <= 25 and 
			len(item.split()) <= 3 and  # Max 3 words
			not re.search(r"\b(implemented|developed|created|designed|built|used|worked|experience|project|detection|filtering|sorting|classification|parsing|recommendations|lookups|listings|fatigue)\b", item, re.I)):
			
			# Split compound skills like "Python/Java" or "HTML & CSS"
			if "/" in item and len(item.split("/")) <= 3:
				for subskill in item.split("/"):
					subskill = subskill.strip()
					if subskill and 2 <= len(subskill) <= 15:
						candidates.append(subskill)
			elif " & " in item and len(item.split(" & ")) <= 3:
				for subskill in item.split(" & "):
					subskill = subskill.strip()
					if subskill and 2 <= len(subskill) <= 15:
						candidates.append(subskill)
			else:
				candidates.append(item)
	
	return candidates


def _extract_skills_from_experience(text: str) -> List[str]:
	# Extract only core technical skills mentioned in experience/project descriptions
	tech_keywords = [
		r"\b(?:Python|Java|JavaScript|TypeScript|C\+\+|C#|PHP|Ruby|Go|Rust|Swift|Kotlin|Scala|C)\b",
		r"\b(?:React|Angular|Vue|Node\.js|Express|Django|Flask|Spring|Laravel|Rails)\b",
		r"\b(?:MySQL|PostgreSQL|MongoDB|Redis|SQLite|Oracle)\b",
		r"\b(?:AWS|Azure|GCP|Docker|Kubernetes|Git|GitHub)\b",
		r"\b(?:HTML|CSS|Bootstrap|jQuery|REST|API)\b",
		r"\b(?:Linux|Windows|Ubuntu|Nginx|Apache)\b"
	]
	
	skills = []
	for pattern in tech_keywords:
		matches = re.finditer(pattern, text, re.I)
		for match in matches:
			skill = match.group(0)
			if skill.lower() not in [s.lower() for s in skills]:  # Case-insensitive dedup
				skills.append(skill)
	
	return skills


def _extract_skills(text: str, use_spacy: bool) -> List[str]:
	lines = text.splitlines()
	skills_blocks: List[str] = []
	all_skills: List[str] = []
	
	# Enhanced skill section detection
	skill_headers = re.compile(r"^\s*(technical\s+)?skills?|technologies|tech\s*stack|tools?|programming|software|platforms|frameworks|languages\b", re.I)
	section_headers = re.compile(r"^\s*(experience|work|education|projects?|summary|certifications?|achievements?|awards?)\b", re.I)
	
	# Find explicit skills sections
	capture = False
	buffer: List[str] = []
	
	for line in lines:
		l = line.strip()
		if skill_headers.search(l):
			if buffer:
				skills_blocks.append("\n".join(buffer))
				buffer = []
			capture = True
			continue
		
		if capture:
			if not l:
				if buffer:
					skills_blocks.append("\n".join(buffer))
					buffer = []
				capture = False
				continue
			if section_headers.search(l):
				if buffer:
					skills_blocks.append("\n".join(buffer))
					buffer = []
				capture = False
				continue
			buffer.append(l)
	
	if capture and buffer:
		skills_blocks.append("\n".join(buffer))
	
	# Extract skills from identified sections
	for block in skills_blocks:
		all_skills.extend(_collect_skill_tokens_from_section(block))
	
	# Extract skills from experience descriptions as fallback
	if len(all_skills) < 5:  # If we didn't find many skills in dedicated sections
		exp_skills = _extract_skills_from_experience(text)
		all_skills.extend(exp_skills)
	
	# Enhanced spaCy extraction for technical terms
	if use_spacy and len(all_skills) < 10:
		try:
			import spacy
			nlp = spacy.load("en_core_web_sm")
			doc = nlp(text)
			
			# Look for technical noun phrases
			for chunk in doc.noun_chunks:
				candidate = chunk.text.strip()
				if (2 <= len(candidate) <= 30 and 
					re.search(r"[A-Za-z0-9]", candidate) and
					not re.search(r"\b(experience|education|university|college|company|project|team|role|position)\b", candidate, re.I)):
					all_skills.append(candidate)
		except Exception:
			pass
	
	# Normalize and deduplicate
	normalized_skills = normalize_skills(all_skills)
	
	# Filter out common non-skills and verbose descriptions
	filtered_skills = []
	non_skills = re.compile(r"\b(experience|years?|months?|team|project|company|university|college|degree|bachelor|master|phd|work|job|role|position|responsibilities|duties|tasks|achievements?|awards?|certifications?|summary|profile|objective|references?|available|upon|request|implemented|developed|created|designed|built|used|worked|detection|filtering|sorting|classification|parsing|recommendations|lookups|listings|fatigue|good|average|based|personalized|genre|score|category|top|character|manga|search|api|jikan)\b", re.I)
	
	for skill in normalized_skills:
		if (2 <= len(skill) <= 20 and  # Reasonable skill name length
			not non_skills.search(skill) and 
			not skill.isdigit() and
			len(skill.split()) <= 2 and  # Max 2 words for skills
			not re.search(r"[.,(){}[\]]", skill) and  # No punctuation artifacts
			not skill.lower().startswith(('e.g', 'etc', 'and', 'or', 'the', 'to', 'for'))):
			filtered_skills.append(skill)
	
	return filtered_skills[:15]  # Limit to top 15 clean skills


def _extract_additional_sections(text: str) -> Dict[str, str]:
	# Extract additional resume sections
	sections = {"Projects": "", "Certifications": "", "Languages": "", "Awards": ""}
	
	lines = text.splitlines()
	current_section = None
	section_content = []
	
	section_patterns = {
		"Projects": re.compile(r"^\s*projects?\b", re.I),
		"Certifications": re.compile(r"^\s*certifications?|licenses?\b", re.I),
		"Languages": re.compile(r"^\s*languages?\b", re.I),
		"Awards": re.compile(r"^\s*(?:awards?|achievements?|honors?)\b", re.I)
	}
	
	end_patterns = re.compile(r"^\s*(?:experience|education|skills|references?)\b", re.I)
	
	for line in lines:
		l = line.strip()
		if not l:
			if current_section and section_content:
				sections[current_section] = " | ".join(section_content[:5])
				section_content = []
				current_section = None
			continue
		
		# Check if this line starts a new section we care about
		section_found = False
		for section_name, pattern in section_patterns.items():
			if pattern.search(l):
				if current_section and section_content:
					sections[current_section] = " | ".join(section_content[:5])
				current_section = section_name
				section_content = []
				section_found = True
				break
		
		if section_found:
			continue
		
		# Check if this line ends the current section
		if current_section and end_patterns.search(l):
			if section_content:
				sections[current_section] = " | ".join(section_content[:5])
			current_section = None
			section_content = []
			continue
		
		# Add content to current section
		if current_section:
			# Clean and add the line
			clean_line = re.sub(r"^[•\-\*◦]\s*", "", l)
			if clean_line and len(clean_line) > 3:
				section_content.append(clean_line)
	
	# Handle any remaining content
	if current_section and section_content:
		sections[current_section] = " | ".join(section_content[:5])
	
	return sections


def _calculate_extraction_confidence(extracted_data: Dict[str, Any]) -> float:
	# Calculate confidence score based on successfully extracted fields
	weights = {
		"Name": 0.2,
		"Email": 0.15,
		"Phone": 0.1,
		"Education": 0.2,
		"Experience": 0.2,
		"Skills": 0.15
	}
	
	confidence = 0.0
	for field, weight in weights.items():
		if extracted_data.get(field) and str(extracted_data[field]).strip():
			confidence += weight
	
	return round(confidence, 2)


def extract_resume_fields(text: str, use_spacy: bool = False) -> Dict[str, Any]:
	# Core extraction for essential resume fields only
	spacy_ents = _maybe_spacy_ents(text, use_spacy)
	
	# Extract core fields
	email = _extract_email(text)
	phone = _extract_phone(text)
	urls = _extract_urls(text)
	name = _extract_name(text, spacy_ents)
	education = _extract_education(text, spacy_ents)
	experience = _extract_experience(text)
	skills_list = _extract_skills(text, use_spacy)
	
	# Return only requested fields
	return {
		"Name": name,
		"Email": email,
		"Phone": phone,
		"LinkedIn": urls.get("LinkedIn", ""),
		"GitHub": urls.get("GitHub", ""),
		"Education": education,
		"Experience": experience,
		"Skills": join_list(skills_list)
	}

