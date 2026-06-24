# MAKORA — Module Auth, Profil & Utilitaires — Spécification d'implémentation
> **Document :** MAKORA_MODULE_AUTH_PROFIL.md
> **Chantier :** 2 — Zoom module
> **Date :** Juin 2026
> **Auteur :** ATABONG EFON STEPHANE FRITZ
> **Rôles concernés :** Public (auth) · Tous (profil, utilitaires)
> **Pages :** 8 · **Priorité :** 🔴 FE-2 (auth) / 🟡 FE-12 (profil)

> Conventions communes : voir `MAKORA_MODULE_DASHBOARD.md`.

---

## Vue d'ensemble

Ce fichier couvre les pages d'entrée (authentification), les pages personnelles (profil, sécurité), les pages système (403, 404), et la page explicative "À propos de MAKORA". L'authentification utilise le pattern **JWT + refresh token** : access token stateless (15 min), refresh token stocké en base (7 jours) pour permettre la révocation.

### Pages

| # | Route | Titre | Rôles | Priorité |
|---|---|---|---|---|
| 1 | `/login` | Connexion | Public | 🔴 |
| 2 | `/forgot-password` | Mot de passe oublié | Public | 🟠 |
| 3 | `/reset-password` | Réinitialiser le mot de passe | Public | 🟠 |
| 4 | `/profile` | Mon profil | Tous | 🟡 |
| 5 | `/profile/security` | Sessions actives | Tous | 🟡 |
| 6 | `/unauthorized` | 403 — Accès refusé | Tous | 🟡 |
| 7 | `/not-found` | 404 — Introuvable | Tous | 🟡 |
| 8 | `/about` | À propos de MAKORA | Public / Tous | 🟡 |

---

## Page 1 — Connexion (`/login`)

### Rôles : Public

### Layout

Page centrée, sans AppShell (groupe `(auth)`). Branding MAKORA (logo + or + bleu nuit). Formulaire simple.

### Champs

- Username ou email
- Mot de passe (avec toggle visibilité)
- Lien "Mot de passe oublié ?" → `/forgot-password`

### Comportement

- Validation Zod côté client avant soumission
- Au succès : stocke access + refresh token, redirige vers `/dashboard`
- Au premier login : déclenche le guided tour (flag `localStorage('makora-tour-done')`)
- Gestion d'erreur : message clair sur identifiants invalides (sans révéler si c'est le user ou le mdp)

### Endpoints consommés

- `POST /auth/login` — retourne access + refresh token
- `GET /auth/me` — charge le profil et les rôles après login

### UX décisions

- Page épurée, identité visuelle forte (c'est la première impression).
- Toggle thème et langue disponibles même avant connexion.

---

## Page 2 — Mot de passe oublié (`/forgot-password`)

### Rôles : Public

### Champs

- Email

### Comportement

- Envoie un email avec lien de réinitialisation (token JWT 30 min en query param)
- Message de confirmation neutre (ne révèle pas si l'email existe — sécurité)

### Endpoint consommé

- `POST /auth/forgot-password`

---

## Page 3 — Réinitialiser le mot de passe (`/reset-password`)

### Rôles : Public

### Champs

- Nouveau mot de passe (avec indicateur de complexité)
- Confirmation

### Comportement

- Token JWT (30 min) lu depuis le query param
- Validation de complexité côté client (longueur, majuscule, chiffre, caractère spécial)
- Au succès : redirige vers `/login` avec message de confirmation

### Endpoint consommé

- `POST /auth/reset-password`

---

## Page 4 — Mon profil (`/profile`)

### Rôles : Tous

### Sections

- Informations personnelles (nom, email) — éditable → `PATCH /auth/me`
- Mes rôles (lecture seule, pills)
- Changer mon mot de passe → `POST /auth/change-password`
- Préférences : langue (FR/EN), thème (clair/sombre)

### Endpoints consommés

- `GET /auth/me`
- `PATCH /auth/me`
- `POST /auth/change-password`

### UX décisions

- Les préférences langue/thème sont aussi accessibles depuis la topbar, mais centralisées ici.
- Changement de mot de passe : demande le mot de passe actuel + nouveau + confirmation.

---

## Page 5 — Sessions actives (`/profile/security`)

### Rôles : Tous

### Rôle métier

Visualiser et révoquer les sessions actives (sécurité utilisateur).

### Layout

Tableau des sessions.

### Colonnes

| Colonne | Source |
|---|---|
| IP | `ip_address` |
| Navigateur | `user_agent` (parsé lisiblement) |
| Créée le | `created_at` |
| Expire le | `expires_at` |
| Action | `Révoquer` |

### Endpoints consommés

- `GET /auth/sessions`
- `DELETE /auth/sessions/{session_id}`

### UX décisions

- La session courante est marquée "Session actuelle" et ne peut pas être révoquée depuis ici (utiliser la déconnexion).
- Révoquer une session demande confirmation.

---

## Page 6 — 403 Accès refusé (`/unauthorized`)

### Rôles : Tous

### Contenu

- Illustration sobre + message clair : *"Vous n'avez pas les droits pour accéder à cette page."*
- Mention du rôle requis (si pertinent et non sensible)
- Bouton "Retour au tableau de bord"

### UX décisions

- Page atteinte quand un utilisateur force une URL non autorisée (le middleware/layout le redirige ici). Ton bienveillant, pas culpabilisant.

---

## Page 7 — 404 Introuvable (`/not-found`)

### Rôles : Tous

### Contenu

- Illustration sobre + message : *"Cette page n'existe pas ou a été déplacée."*
- Bouton "Retour au tableau de bord" + champ de recherche (command palette)

---

## Page 8 — À propos de MAKORA (`/about`)

### Rôles : Public / Tous

### Rôle

Page explicative présentant le framework. Utile pour les décideurs, nouveaux arrivants, et soutenance.

### Sections (pages explicatives, pas de données live)

- **Qu'est-ce que MAKORA** — framework générique de détection de fraude en assurance (Santé + Auto), contexte camerounais
- **Architecture Kernel** — schéma des niveaux d'abstraction (Kernel / Modules / API / Frontend), principe de généricité
- **Les modules** — Santé et Auto en production, Vie et Agricole en conception (extensibilité)
- **L'hypothèse H0** — explication vulgarisée du trade-off généricité/précision, avec lien vers `/ml/models/compare`
- **La contribution africaine** — nomenclature ASAC, mercuriale CIMA, détection du cachet humide, XAF
- **L'IA explicable** — Isolation Forest + SHAP + narration LLM Mistral 7B

### UX décisions

- Page éditoriale, mise en page aérée, ton pédagogique. Peut servir de support de présentation.
- Accessible sans authentification (utile pour partager un lien de démonstration).

---

## Composants à créer

| Composant | Chemin |
|---|---|
| `<LoginForm>` | `features/auth/LoginForm.tsx` |
| `<ForgotPasswordForm>` | `features/auth/ForgotPasswordForm.tsx` |
| `<ResetPasswordForm>` | `features/auth/ResetPasswordForm.tsx` |
| `<PasswordStrengthMeter>` | `features/auth/PasswordStrengthMeter.tsx` |
| `<ProfileForm>` | `features/profile/ProfileForm.tsx` |
| `<ChangePasswordForm>` | `features/profile/ChangePasswordForm.tsx` |
| `<SessionsTable>` | `features/profile/SessionsTable.tsx` |
| `<PreferencesPanel>` | `features/profile/PreferencesPanel.tsx` |
| `<GuidedTour>` | `common/GuidedTour.tsx` |
| `<ErrorPage403>` | `app/(app)/unauthorized/page.tsx` |
| `<ErrorPage404>` | `app/not-found.tsx` |
| `<AboutSections>` | `features/about/AboutSections.tsx` |

---

## Query keys & stores

```typescript
export const AUTH_KEYS = {
  all: ['auth'] as const,
  me: () => [...AUTH_KEYS.all, 'me'] as const,
  sessions: () => [...AUTH_KEYS.all, 'sessions'] as const,
};

// Zustand store
interface AuthStore {
  user: User | null;
  roles: Role[];
  accessToken: string | null;
  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
}
interface PreferencesStore {
  theme: 'light' | 'dark';   // défaut: 'light'
  locale: 'fr' | 'en';        // défaut: 'fr'
  toggleTheme: () => void;
  setLocale: (l: 'fr' | 'en') => void;
}
```

---

## Flux de navigation

```
/ ──(non authentifié)──► /login
/login ──(succès)──► /dashboard (+ guided tour si 1er login)
/login ──► /forgot-password ──► (email) ──► /reset-password ──► /login
/profile ──► /profile/security
(URL non autorisée) ──► /unauthorized
(URL inexistante) ──► /not-found
(lien public) ──► /about
```

---

*MAKORA_MODULE_AUTH_PROFIL.md — Juin 2026 — ATABONG EFON STEPHANE FRITZ*
