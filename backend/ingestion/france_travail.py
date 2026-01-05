"""
France Travail (ex Pôle Emploi) API connector.

API Documentation: https://francetravail.io/
Requires: Client ID and Client Secret (free registration)
"""

import os
import httpx
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from .base import JobSource, JobData


class FranceTravailSource(JobSource):
    """France Travail (Pôle Emploi) job source."""
    
    name = "france_travail"
    
    AUTH_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
    API_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2"
    
    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id or os.getenv("FRANCE_TRAVAIL_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET")
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        """Get or refresh OAuth token."""
        if self._token and self._token_expires and datetime.now() < self._token_expires:
            return self._token

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "France Travail credentials required. "
                "Set FRANCE_TRAVAIL_CLIENT_ID and FRANCE_TRAVAIL_CLIENT_SECRET env vars. "
                "Register at https://francetravail.io/"
            )

        response = await client.post(
            self.AUTH_URL,
            params={"realm": "/partenaire"},
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": f"api_offresdemploiv2 o2dsoffre",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        data = response.json()
        
        self._token = data["access_token"]
        expires_in = data.get("expires_in", 1500)
        self._token_expires = datetime.now() + timedelta(seconds=expires_in - 60)
        
        return self._token

    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 25,
        **kwargs
    ) -> List[JobData]:
        """Search France Travail job listings."""
        async with httpx.AsyncClient(timeout=30) as client:
            token = await self._get_token(client)
            
            params = {
                "motsCles": query,
                "range": f"0-{min(limit - 1, 149)}",  # Max 150 results
            }
            
            # Location can be department code (e.g., "75" for Paris)
            if location:
                # Try to detect if it's a department code or city name
                if location.isdigit() and len(location) <= 3:
                    params["departement"] = location
                else:
                    params["commune"] = location
            
            # Additional filters
            if kwargs.get("remote"):
                params["typeContrat"] = "CDI"  # Remote filter not directly available
            
            if kwargs.get("contract_type"):
                params["typeContrat"] = kwargs["contract_type"]

            response = await client.get(
                f"{self.API_URL}/offres/search",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            
            if response.status_code == 204:
                return []  # No results
            
            response.raise_for_status()
            data = response.json()
            
            results = data.get("resultats", [])
            return [self._parse_job(job) for job in results]

    async def fetch_details(self, job_id: str) -> Optional[JobData]:
        """Fetch full job details by ID."""
        async with httpx.AsyncClient(timeout=30) as client:
            token = await self._get_token(client)
            
            response = await client.get(
                f"{self.API_URL}/offres/{job_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            return self._parse_job(response.json())

    def _parse_job(self, data: Dict[str, Any]) -> JobData:
        """Parse France Travail job data to normalized format."""
        # Extract location
        lieu = data.get("lieuTravail", {})
        location_parts = []
        if lieu.get("libelle"):
            location_parts.append(lieu["libelle"])
        location = ", ".join(location_parts) or "France"
        
        # Extract salary
        salary = None
        salary_min = None
        salary_max = None
        salaire = data.get("salaire", {})
        if salaire:
            if salaire.get("libelle"):
                salary = salaire["libelle"]
            if salaire.get("min"):
                salary_min = int(float(salaire["min"]))
            if salaire.get("max"):
                salary_max = int(float(salaire["max"]))
        
        # Extract contract type
        contract = data.get("typeContrat")
        emp_type = self.normalize_employment_type(contract) if contract else None
        
        # Check if remote
        is_remote = False
        if lieu.get("codePostal") == "00000" or "télétravail" in data.get("description", "").lower():
            is_remote = True
        
        # Extract tags from description and qualifications
        description = data.get("description", "")
        competences = data.get("competences", [])
        skill_names = [c.get("libelle", "") for c in competences if c.get("libelle")]
        tags = self.extract_tags(description + " ".join(skill_names))
        
        # Add explicit competences as tags
        for comp in competences[:5]:
            if comp.get("libelle") and comp["libelle"].lower() not in [t.lower() for t in tags]:
                tags.append(comp["libelle"])
        
        return JobData(
            title=data.get("intitule", "Sans titre"),
            company=data.get("entreprise", {}).get("nom", "Entreprise confidentielle"),
            location=location,
            description=description,
            url=data.get("origineOffre", {}).get("urlOrigine", f"https://candidat.francetravail.fr/offres/recherche/detail/{data.get('id')}"),
            source=self.name,
            source_id=data.get("id", ""),
            salary=salary,
            salary_min=salary_min,
            salary_max=salary_max,
            employment_type=emp_type,
            seniority=self.normalize_seniority(data.get("experienceExige", "")),
            is_remote=is_remote,
            tags=tags[:10],
            published_at=data.get("dateCreation"),
            expires_at=data.get("dateActualisation"),
            raw_data=data,
        )
