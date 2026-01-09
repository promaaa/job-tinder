import json
from pathlib import Path
from typing import Dict, Any, List
from jinja2 import Environment, FileSystemLoader

class CVEngine:
    """Engine to adapt CVs to job offers using Jinja2 and LaTeX."""
    
    def __init__(self, templates_dir: str = "data/templates"):
        self.templates_dir = Path(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            block_start_string='\BLOCK{',
            block_end_string='}',
            variable_start_string='\VAR{',
            variable_end_string='}',
            comment_start_string='\#{',
            comment_end_string='}',
            line_statement_prefix='%%',
            line_comment_prefix='%#',
            trim_blocks=True,
            autoescape=False,
        )

    def adapt(self, master_profile: Dict[str, Any], job: Dict[str, Any]) -> str:
        """
        Adapt the profile to the job and return LaTeX source.
        """
        # 1. Analyse des mots-clés de l'offre
        offer_text = f"{job.get('title', '')} {job.get('description', '')} {' '.join(job.get('tags', []))}".lower()
        
        # 2. Sélection intelligente des projets (Scoring simple)
        selected_projects = []
        for project in master_profile.get("projects", []):
            score = 0
            for tag in project.get("tags", []):
                if tag.lower() in offer_text:
                    score += 10
            # Si un mot clé du projet est dans la description
            if any(kw.lower() in offer_text for kw in project.get("highlights", [])):
                score += 5
            
            project["_score"] = score
            selected_projects.append(project)
        
        # On garde les 3 meilleurs projets
        selected_projects.sort(key=lambda x: x["_score"], reverse=True)
        top_projects = selected_projects[:3]

        # 3. Adaptation des compétences
        # On peut réordonner les catégories de skills selon l'offre
        skills = master_profile.get("skills", [])
        
        # 4. Génération du contexte pour le template
        context = {
            "basics": master_profile.get("basics"),
            "skills": skills,
            "experience": master_profile.get("experience", []),
            "projects": top_projects,
            "education": master_profile.get("education", []),
            "target_job": job.get("title"),
            "target_company": job.get("company"),
        }

        template = self.env.get_template("cv_template.tex.j2")
        return template.render(**context)