"""
Auto-apply service for automatic job applications.

When a user likes a job, this service can:
1. Send an email with CV + cover letter to the company
2. Open the application URL in browser
3. Track the application status
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import json
import re

logger = logging.getLogger(__name__)


class UserProfile:
    """User profile with CV and application info."""
    
    PROFILE_FILE = "data/user_profile.json"
    CV_DIR = "data/cv"
    
    DEFAULT_PROFILE = {
        "full_name": "",
        "email": "",
        "phone": "",
        "linkedin_url": "",
        "github_url": "",
        "portfolio_url": "",
        "location": "",
        "current_title": "",
        "years_experience": 0,
        "skills": [],
        "cv_filename": None,
        "cover_letter_template": """Bonjour,

Je suis très intéressé(e) par le poste de {job_title} chez {company}.

{custom_intro}

Vous trouverez mon CV en pièce jointe. Je serais ravi(e) de discuter de cette opportunité avec vous.

Cordialement,
{full_name}
{email}
{phone}""",
        "custom_intro": "Avec mon expérience en développement logiciel et ma passion pour l'innovation, je pense pouvoir apporter une réelle valeur à votre équipe.",
        "auto_apply_enabled": False,
        "smtp_configured": False,
        "smtp_host": "",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_password": "",
        "applications_count": 0,
    }
    
    @classmethod
    def load(cls) -> Dict[str, Any]:
        """Load user profile from disk."""
        if os.path.exists(cls.PROFILE_FILE):
            try:
                with open(cls.PROFILE_FILE, "r") as f:
                    saved = json.load(f)
                    # Merge with defaults for new fields
                    return {**cls.DEFAULT_PROFILE, **saved}
            except Exception as e:
                logger.error(f"Error loading profile: {e}")
        return cls.DEFAULT_PROFILE.copy()
    
    @classmethod
    def save(cls, profile: Dict[str, Any]) -> bool:
        """Save user profile to disk."""
        try:
            os.makedirs(os.path.dirname(cls.PROFILE_FILE), exist_ok=True)
            with open(cls.PROFILE_FILE, "w") as f:
                json.dump(profile, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            return False
    
    @classmethod
    def get_cv_path(cls) -> Optional[str]:
        """Get path to the user's CV file."""
        profile = cls.load()
        if profile.get("cv_filename"):
            cv_path = os.path.join(cls.CV_DIR, profile["cv_filename"])
            if os.path.exists(cv_path):
                return cv_path
        return None
    
    @classmethod
    def is_ready_for_auto_apply(cls) -> Dict[str, Any]:
        """Check if profile is configured for auto-apply."""
        profile = cls.load()
        issues = []
        
        if not profile.get("full_name"):
            issues.append("Full name not set")
        if not profile.get("email"):
            issues.append("Email not set")
        if not cls.get_cv_path():
            issues.append("CV not uploaded")
        if not profile.get("smtp_configured"):
            issues.append("Email (SMTP) not configured")
            
        return {
            "ready": len(issues) == 0,
            "issues": issues,
            "auto_apply_enabled": profile.get("auto_apply_enabled", False),
        }


class AutoApplyService:
    """Service to automatically apply to jobs."""
    
    APPLICATIONS_FILE = "data/applications.json"
    
    def __init__(self):
        self.profile = UserProfile.load()
        self.applications = self._load_applications()
    
    def _load_applications(self) -> Dict[str, Any]:
        """Load application history."""
        if os.path.exists(self.APPLICATIONS_FILE):
            try:
                with open(self.APPLICATIONS_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"applications": [], "total_sent": 0}
    
    def _save_applications(self):
        """Save application history."""
        try:
            os.makedirs(os.path.dirname(self.APPLICATIONS_FILE), exist_ok=True)
            with open(self.APPLICATIONS_FILE, "w") as f:
                json.dump(self.applications, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving applications: {e}")
    
    def _extract_email_from_job(self, job: Dict[str, Any]) -> Optional[str]:
        """Try to extract application email from job data."""
        # Check raw_data for email
        description = job.get("description", "") or ""
        url = job.get("url", "") or ""
        
        # Common email patterns
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        
        # Look in description
        emails = re.findall(email_pattern, description)
        if emails:
            # Filter out common non-application emails
            for email in emails:
                if not any(x in email.lower() for x in ['noreply', 'no-reply', 'donotreply', 'unsubscribe']):
                    return email
        
        # Check if URL is mailto:
        if url.startswith("mailto:"):
            return url.replace("mailto:", "").split("?")[0]
        
        return None
    
    def _generate_cover_letter(self, job: Dict[str, Any]) -> str:
        """Generate personalized cover letter from template."""
        template = self.profile.get("cover_letter_template", "")
        
        # Replace placeholders
        replacements = {
            "{job_title}": job.get("title", "ce poste"),
            "{company}": job.get("company", "votre entreprise"),
            "{full_name}": self.profile.get("full_name", ""),
            "{email}": self.profile.get("email", ""),
            "{phone}": self.profile.get("phone", ""),
            "{linkedin_url}": self.profile.get("linkedin_url", ""),
            "{github_url}": self.profile.get("github_url", ""),
            "{portfolio_url}": self.profile.get("portfolio_url", ""),
            "{current_title}": self.profile.get("current_title", ""),
            "{custom_intro}": self.profile.get("custom_intro", ""),
            "{location}": job.get("location", ""),
        }
        
        result = template
        for key, value in replacements.items():
            result = result.replace(key, str(value) if value else "")
        
        return result
    
    def _send_email(
        self, 
        to_email: str, 
        subject: str, 
        body: str, 
        cv_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send application email with CV attachment."""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.profile.get("email", "")
            msg["To"] = to_email
            msg["Subject"] = subject
            
            # Body
            msg.attach(MIMEText(body, "plain", "utf-8"))
            
            # Attach CV
            if cv_path and os.path.exists(cv_path):
                with open(cv_path, "rb") as f:
                    cv_attachment = MIMEApplication(f.read(), Name=os.path.basename(cv_path))
                    cv_attachment["Content-Disposition"] = f'attachment; filename="{os.path.basename(cv_path)}"'
                    msg.attach(cv_attachment)
            
            # Send via SMTP
            smtp_host = self.profile.get("smtp_host", "")
            smtp_port = self.profile.get("smtp_port", 587)
            smtp_user = self.profile.get("smtp_user", "")
            smtp_password = self.profile.get("smtp_password", "")
            
            if not all([smtp_host, smtp_user, smtp_password]):
                return {"success": False, "error": "SMTP not configured"}
            
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {"success": False, "error": str(e)}
    
    def apply_to_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempt to auto-apply to a job.
        
        Returns status of the application attempt.
        """
        job_id = job.get("id", "")
        job_title = job.get("title", "Unknown Position")
        company = job.get("company", "Unknown Company")
        job_url = job.get("url", "")
        
        result = {
            "job_id": job_id,
            "job_title": job_title,
            "company": company,
            "applied_at": datetime.now().isoformat(),
            "method": None,
            "status": "pending",
            "details": None,
        }
        
        # Check if already applied
        for app in self.applications.get("applications", []):
            if app.get("job_id") == job_id:
                return {
                    "success": False,
                    "already_applied": True,
                    "message": f"Already applied to {job_title} at {company}",
                }
        
        # Try to find application email
        app_email = self._extract_email_from_job(job)
        
        if app_email:
            # Send email application
            cv_path = UserProfile.get_cv_path()
            cover_letter = self._generate_cover_letter(job)
            subject = f"Candidature - {job_title} - {self.profile.get('full_name', '')}"
            
            email_result = self._send_email(
                to_email=app_email,
                subject=subject,
                body=cover_letter,
                cv_path=cv_path,
            )
            
            result["method"] = "email"
            result["email_sent_to"] = app_email
            
            if email_result["success"]:
                result["status"] = "sent"
                result["details"] = f"Email sent to {app_email}"
            else:
                result["status"] = "failed"
                result["details"] = email_result.get("error", "Unknown error")
        
        elif job_url:
            # No email found, provide URL for manual application
            result["method"] = "manual_url"
            result["status"] = "action_required"
            result["details"] = f"Apply manually at: {job_url}"
            result["url"] = job_url
        
        else:
            result["method"] = "none"
            result["status"] = "no_method"
            result["details"] = "No application method found"
        
        # Save to history
        self.applications["applications"].append(result)
        if result["status"] == "sent":
            self.applications["total_sent"] = self.applications.get("total_sent", 0) + 1
            # Update profile counter
            profile = UserProfile.load()
            profile["applications_count"] = profile.get("applications_count", 0) + 1
            UserProfile.save(profile)
        
        self._save_applications()
        
        return {
            "success": result["status"] in ("sent", "action_required"),
            "application": result,
        }
    
    def get_application_history(self, limit: int = 50) -> Dict[str, Any]:
        """Get recent application history."""
        apps = self.applications.get("applications", [])
        return {
            "total": len(apps),
            "total_sent": self.applications.get("total_sent", 0),
            "recent": apps[-limit:][::-1],  # Most recent first
        }


def trigger_auto_apply(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for auto-apply.
    Called when a user likes a job.
    """
    # Check if auto-apply is ready
    readiness = UserProfile.is_ready_for_auto_apply()
    
    if not readiness["ready"]:
        return {
            "success": False,
            "auto_applied": False,
            "reason": "Profile not ready",
            "issues": readiness["issues"],
        }
    
    if not readiness["auto_apply_enabled"]:
        return {
            "success": True,
            "auto_applied": False,
            "reason": "Auto-apply is disabled",
        }
    
    # Attempt auto-apply
    service = AutoApplyService()
    result = service.apply_to_job(job)
    
    return {
        "success": True,
        "auto_applied": True,
        "result": result,
    }
