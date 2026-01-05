# Stratégie ingestion & anti-scraping

## Préférences
1) Utiliser d'abord les APIs officielles/feeds (RSS/Atom/JSON) et partenaires.
2) Scraping seulement en dernier recours, limité et respectueux.
3) Cacher et dédupliquer les réponses pour éviter la charge inutile.

## Bonnes pratiques anti-scraping
- Respecter `robots.txt` et conditions d'utilisation avant tout accès.
- Rotation User-Agent et pool de proxies résidentiels/dc; rafraîchir les sessions fréquemment.
- Navigation headless "stealth" (Playwright) pour pages JS lourdes; attendre les sélecteurs clés puis extraire.
- Rate limiting adaptatif + backoff exponentiel; circuit breaker sur HTTP 429/403/5xx.
- Randomiser délais entre requêtes et chemins d'accès; éviter le parallélisme massif sur un même domaine.
- Surveiller les empreintes (cookies, localStorage); réinitialiser contexte navigateur périodiquement.
- Détecter et résoudre les captchas via service tiers seulement si légalement permis; sinon abandonner la source.
- Empaqueter les requêtes via sorties réseau neutres (proxies) et éviter IPs réutilisées.
- Journaliser les codes HTTP, latence, blocages et taux de succès par domaine.

## Pipelines recommandés
- `fetch -> normalize -> dedupe -> enrich -> store` avec traces par run (`ingestion_runs` / `job_ingestions`).
- Stocker le HTML/JSON brut chiffré si légalement autorisé pour audit/debug.
- Normalisation: extraire `title`, `company`, `location`, `url`, `description`, `published_at`, tags.
- Dédoublonnage: clé `(source_id, source_job_id)` + fuzzy match (titre+entreprise+ville) en secours.

## Mitigation et fallback
- Si 403/429 répétés: allonger le backoff, changer d'IP, réduire le parallélisme, vérifier robots.
- Si blocage durable: basculer vers import manuel ou sourcing alternatif.

## Légalité & éthique
- Vérifier les CGU de chaque site; cesser l'accès si interdit.
- Ne pas contourner les protections fortes (paywalls, auth) sans droit explicite.
- Informer les utilisateurs des sources et respecter la vie privée (pas de données perso non nécessaires).
