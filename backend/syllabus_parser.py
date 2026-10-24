import re
import os
from typing import Dict, List, Any, Optional

try:
    import pypdf
except ImportError:
    pypdf = None

class SyllabusParser:
    @staticmethod
    def extract_text_from_file(file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ('.txt', '.md', '.markdown'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        elif ext == '.pdf':
            if pypdf is None:
                raise RuntimeError("pypdf is not installed. Please install pypdf to process PDF files.")
            text = []
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text.append(t)
            return "\n".join(text)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Supported formats are .pdf, .txt, .md")

    @staticmethod
    def parse_syllabus_text(text: str, source_filename: str = "Uploaded Document") -> Dict[str, Any]:
        """
        Extracts course code, course title, units, topics, and subtopics from text.
        Identifies duplicates and missing section markers.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        course_code = "CSN " + str(1000 + (abs(hash(source_filename)) % 8999))
        course_name = os.path.splitext(os.path.basename(source_filename))[0].replace("_", " ").title()
        
        # Check if course code or name is mentioned in text
        code_match = re.search(r'\b([A-Z]{2,4}\s*\d{3,4})\b', text)
        if code_match:
            course_code = code_match.group(1).strip()

        title_match = re.search(r'(?:Course(?:\s+Title)?|Subject(?:\s+Name)?|Paper)\s*[:\-]\s*([^\n\r]+)', text, re.IGNORECASE)
        if title_match:
            course_name = title_match.group(1).strip()
        elif lines:
            first_line = lines[0]
            if len(first_line) < 80 and not first_line.lower().startswith("unit"):
                course_name = first_line

        units: List[Dict[str, Any]] = []
        current_unit = None
        current_unit_number = 0
        detected_topics_set = set()
        duplicates = []

        unit_regex = re.compile(r'^(?:Unit|Module|Chapter|Section)\s*([0-9IVXLCDM]+)?\s*[:\-]?\s*(.*)', re.IGNORECASE)
        topic_bullet_regex = re.compile(r'^(?:[\*\-\•\+]|\d+\.|\([a-z0-9]\))\s*(.*)')

        for line in lines:
            # Check if line is course header metadata
            if re.match(r'^(?:Course(?:\s+(?:Code|Title))?|Subject(?:\s+Name)?|Paper|Credits|Total\s+Lectures)\s*[:\-]', line, re.IGNORECASE):
                continue

            unit_match = unit_regex.match(line)
            if unit_match and len(line) < 120:
                # New unit started
                current_unit_number += 1
                raw_title = unit_match.group(2).strip() or f"Unit {current_unit_number}"
                current_unit = {
                    "unit_number": current_unit_number,
                    "title": raw_title,
                    "lecture_allocation": 6,
                    "topics": []
                }
                units.append(current_unit)
                continue

            if current_unit is None:
                # Create a default Unit 1 if content appears before explicit unit header
                current_unit_number = 1
                current_unit = {
                    "unit_number": 1,
                    "title": "Core Topics",
                    "lecture_allocation": 6,
                    "topics": []
                }
                units.append(current_unit)

            bullet_match = topic_bullet_regex.match(line)
            candidate_topic = bullet_match.group(1).strip() if bullet_match else line

            # Avoid headers or short noise
            if len(candidate_topic) >= 3 and not candidate_topic.lower().startswith(("syllabus", "course code", "credits:", "total lectures")):
                # Check for subtopics separated by colon or commas or semicolons
                parts = re.split(r'[:;]\s*', candidate_topic, maxsplit=1)
                topic_title = parts[0].strip()
                subtopics = []
                if len(parts) > 1:
                    subtopics = [s.strip() for s in re.split(r'[,|]\s*', parts[1]) if s.strip()]

                clean_title_key = topic_title.lower()
                if clean_title_key in detected_topics_set:
                    duplicates.append(topic_title)
                else:
                    detected_topics_set.add(clean_title_key)

                current_unit["topics"].append({
                    "title": topic_title,
                    "estimated_minutes": 60,
                    "subtopics": subtopics,
                    "is_mandatory": True,
                    "source_doc": source_filename
                })

        # Section validation: check if expected numbers match
        missing_sections = []
        if len(units) < 2:
            missing_sections.append("Syllabus contains very few units; check if document has missing modules or unparsed tables.")

        return {
            "course_name": course_name,
            "course_code": course_code,
            "credits": 4,
            "total_lectures": max(30, len(units) * 7),
            "units": units,
            "detected_duplicates": list(set(duplicates)),
            "potential_missing_sections": missing_sections,
            "source_filename": source_filename
        }
