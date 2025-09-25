import re
from typing import List, Tuple


def standardize_phone(raw: str) -> str:
	if not raw:
		return ""
	digits = re.sub(r"\D+", "", raw)
	
	# Handle different phone number formats
	if len(digits) == 10:  # US format
		return f"(+1) {digits[0:3]}-{digits[3:6]}-{digits[6:]}"
	elif len(digits) == 11 and digits.startswith("1"):  # US with country code
		return f"(+1) {digits[1:4]}-{digits[4:7]}-{digits[7:]}"
	elif len(digits) == 12 and digits.startswith("91"):  # India
		return f"(+91) {digits[2:7]}-{digits[7:]}"
	elif len(digits) == 11 and digits.startswith("44"):  # UK
		return f"(+44) {digits[2:6]}-{digits[6:]}"
	elif len(digits) == 12 and digits.startswith("33"):  # France
		return f"(+33) {digits[2:3]}-{digits[3:5]}-{digits[5:7]}-{digits[7:9]}-{digits[9:]}"
	elif 7 <= len(digits) <= 15:  # International format
		return f"(+{digits[:2]}) {digits[2:]}"
	
	return digits if len(digits) >= 7 else ""


def normalize_url(url: str) -> str:
	if not url:
		return ""
	u = url.strip()
	if not re.match(r"^https?://", u, flags=re.I):
		u = "https://" + u
	return u


def normalize_skills(skills: List[str]) -> List[str]:
	# Enhanced skill normalization with synonym handling
	skill_synonyms = {
		"js": "JavaScript",
		"ts": "TypeScript", 
		"py": "Python",
		"nodejs": "Node.js",
		"reactjs": "React",
		"vuejs": "Vue.js",
		"angularjs": "Angular",
		"css3": "CSS",
		"html5": "HTML",
		"postgresql": "PostgreSQL",
		"mysql": "MySQL",
		"mongodb": "MongoDB",
		"aws": "Amazon Web Services",
		"gcp": "Google Cloud Platform",
		"k8s": "Kubernetes",
		"docker": "Docker",
		"git": "Git"
	}
	
	seen = set()
	normalized = []
	
	for s in skills:
		if not s or not s.strip():
			continue
			
		skill = s.strip()
		skill_lower = skill.lower()
		
		# Apply synonym mapping
		if skill_lower in skill_synonyms:
			skill = skill_synonyms[skill_lower]
			skill_lower = skill.lower()
		
		# Skip if already seen (case-insensitive)
		if skill_lower in seen:
			continue
			
		# Additional filtering
		if (len(skill) >= 2 and 
			not skill.isdigit() and 
			not re.match(r"^\d+[\.\d]*$", skill) and  # Skip version numbers
			len(skill.split()) <= 4):  # Skip very long phrases
			seen.add(skill_lower)
			normalized.append(skill)
	
	return normalized


def join_list(items: List[str]) -> str:
	return ", ".join(items)

