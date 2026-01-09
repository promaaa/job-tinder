from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader

class EmailGenerator:
    """Generates cold outreach emails using Jinja2 templates."""
    
    def __init__(self):
        # Resolve path relative to this file: backend/outreach/generator.py -> ... -> data/templates
        root = Path(__file__).resolve().parents[2]
        self.templates_dir = root / "data" / "templates"
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def generate(self, contact: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate email subject and body using the 'email_cold.j2' template.
        
        Args:
            contact: Contact dictionary (name, company, field...)
            profile: User profile dictionary (name, skills...)
            
        Returns:
            Dict with 'subject' and 'body'
        """
        # Prepare context with defaults
        context = {
            "contact": {
                "name": contact.get("name", "there"),
                "company": contact.get("company", "your company"),
                "field": contact.get("field", "your field"),
                **contact
            },
            "profile": {
                "name": profile.get("name", "An Engineer"),
                "title": profile.get("title", "Engineer"),
                "skills": profile.get("skills", []),
                **profile
            }
        }
        
        template = self.env.get_template("email_cold.j2")
        rendered = template.render(**context)
        
        # Parse subject (assumed to be the first line starting with "Subject: ")
        lines = rendered.splitlines()
        subject = "Inquiry"
        body_lines = []
        
        if lines and lines[0].lower().startswith("subject:"):
            subject = lines[0].split(":", 1)[1].strip()
            body_lines = lines[1:]
        else:
            body_lines = lines
            
        body = "\n".join(body_lines).strip()
        
        return {"subject": subject, "body": body}
