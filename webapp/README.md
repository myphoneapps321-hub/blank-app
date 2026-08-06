# Version en ligne multi‑comptes — Adductions DRPN (voie A)

Application web **hébergée** avec base de données **cloud**, **comptes** par utilisateur
et **consolidation temps réel** :
- chaque **agent SPN1…SPN4** ne saisit que **son secteur** ;
- le profil **DR** voit **tout, consolidé et en direct** (dès qu'un agent enregistre).

Backend : **Supabase** (Postgres + Authentification + Sécurité par ligne + Realtime) — offre gratuite suffisante.

---

## 1. Créer le projet Supabase (5 min)
1. Aller sur https://supabase.com → **New project** (choisir une région proche, ex. *Europe*).
2. Noter le **mot de passe** de la base (généré).
3. Menu **Project Settings → API** : copier **Project URL** et la clé **anon public**.

## 2. Créer les tables et la sécurité
1. Menu **SQL Editor → New query**.
2. Coller le contenu de **`schema.sql`** → **Run**.
3. Nouvelle requête : coller **`seed.sql`** (données de départ) → **Run**.

## 3. Configurer l'application
Dans **`index.html`**, en haut du script, remplacer :
```js
const SUPABASE_URL = "https://VOTRE-PROJET.supabase.co";
const SUPABASE_ANON_KEY = "VOTRE_CLE_ANON_PUBLIQUE";
```
par tes valeurs (étape 1). La clé *anon* est **publique** (pas secrète) : la sécurité est assurée par les règles RLS de la base.

## 4. Créer les comptes (agents + DR)
Menu **Authentication → Users → Add user** (email + mot de passe) pour :
- le responsable DR,
- chaque agent SPN1, SPN2, SPN3, SPN4.

Puis dans **SQL Editor**, affecter les rôles/secteurs (remplacer les e‑mails) :
```sql
update profiles set role='dr'                  where email='dr@onee.ma';
update profiles set role='agent', secteur=1    where email='spn1@onee.ma';
update profiles set role='agent', secteur=2    where email='spn2@onee.ma';
update profiles set role='agent', secteur=3    where email='spn3@onee.ma';
update profiles set role='agent', secteur=4    where email='spn4@onee.ma';
```
*(La ligne `profiles` est créée automatiquement à la première connexion ; si besoin, connecte chaque compte une fois, puis lance les `update`.)*

## 5. Publier l'application
`index.html` est un fichier statique : héberge‑le où tu veux (tout est gratuit) —
**Netlify (glisser‑déposer)**, **GitHub Pages**, **Vercel**, ou un intranet ONEE.
Chaque utilisateur ouvre l'URL, se connecte, et arrive **directement sur son périmètre**.

---

## Fonctionnement
| Profil | Accès |
|---|---|
| **Agent SPNx** | saisit uniquement les centres et flux **de son secteur** (production, ventes, pertes, achats/cessions autre DR, volumes de cessions internes) |
| **DR** | **résultats consolidés** (détail + synthèses par secteur et par type + rendement global), mise à jour **en temps réel** quand un agent enregistre |

- Sécurité : les règles **RLS** empêchent un agent de modifier un autre secteur, côté base (même s'il bricole le navigateur).
- Chaque saisie est **enregistrée immédiatement** (indicateur « ✓ enregistré »).

## Évolutions prévues (à la demande)
- Reprendre dans la version en ligne les onglets **Analyses**, **Synoptique**, **Historique** et l'**export/rapport PDF** (déjà présents dans la version hors‑ligne).
- **Synoptique sur carte** (fond satellite) pour SPN1 et les points de livraison.
