# 🎓 Lingua Coach — Assistant d'apprentissage de l'anglais


## 📌 Présentation du projet

Lingua Coach est un système multi-agents conçu pour aider des francophones à apprendre l'anglais. L'utilisateur interagit avec un assistant intelligent qui diagnostique son niveau CECRL, lui propose des exercices adaptés, simule des conversations avec un locuteur natif, corrige ses erreurs, et lui fournit un rapport de progression.

>Le projet est développé avec **Google Agent Development Kit (ADK)** dans le cadre d'un projet individuel de 15h en M2 IA2 MIAGE.


## 🏗️ Architecture multi-agents

<img width="1100" height="667" alt="image" src="https://github.com/user-attachments/assets/2abb62f5-454b-4f11-b4e0-d1c612e31fe3" />


Le système est composé de **5 LlmAgents**, **2 Workflow Agents** et **1 agent orchestrateur**.

### Description des agents

| Agent | Rôle | Tools associés |
|---|---|---|
| **OrchestratorAgent** | Agent racine. Accueille l'utilisateur et le dirige vers le bon workflow selon son choix. | `save_persona` |
| **LevelAgent** | Diagnostique le niveau CECRL via 3 questions | `extract_user_level`, `correction_agent_tool` |
| **CorrectionAgent** | Expert linguistique. Corrige les erreurs de l'utilisateur et fournit des explications en français. | `get_word_definition` |
| **ExerciseAgent** | Génère un exercice adapté au niveau | `generate_exercise`, `correction_agent_tool`, `save_progress` |
| **ConversationAgent** | Simule un locuteur natif [british, american, australian] sur un thème donné. | `get_topic_info`, `correction_agent_tool`, `save_conversation_turn` |
| **ProgressAgent** | Génére un rapport de progression basé sur l'historique des exercices | `calculate_progress_score` |

## Workflow Agents

- **`SessionPipeline`** — `SequentialAgent` : enchaîne `LevelAgent` puis `ExerciseAgent` pour une session d'apprentissage complète.
- **`ConversationLoop`** — `LoopAgent` : Exécute `ConversationAgent` en boucle (max 10 tours) ou jusqu'à ce que l'utilisateur dise "stop".


### Le State partagé
Le state est la mémoire de travail de la session. Il est accessible par tous les agents.

```python
state = {
    "level": None,      # Niveau CECRL écrit par extract_user_level
    "persona": None,    # Persona choisi par l'utilisateur 
    "progress": [],     # Historique des exercices (save_progress)
    "history": [],      # Historique de la conversation 
}
```

> **Note importante :** `adk web` démarre avec un state vide `{}`. Toutes les valeurs sont écrites pendant la session, soit via `output_key` soit via `tool_context.state[key] = value` dans les tools.



## 📁 Structure du projet

```
LINGUA-COACH/
├── my_agent/
│   ├── __init__.py
│   ├── agent.py           # Définition de TOUS les agents 
│   ├── callbacks.py       # Nos 3 callbacks 
│   └── tools/
│       ├── __init__.py
│       └── my_tools.py    # Nos tools 
├── .env                   # Configuration du modèle
├── main.py                # Lanceur programmatique (Runner + Session)
└── README.md             
```

---

## 🤔 Comment ça marche ?
Lorsque vous lancez une conversation, le système fonctionne comme une chaîne de production :

1. Votre message est envoyé à l'`OrchestratorAgent`.
2. L'orchestrateur analyse votre intention.
3. **Si vous choisissez l'option 1 (Exercices)** :
    - Il transfère le contrôle au `SessionPipeline`.
    - `LevelAgent` vous pose 3 questions, puis appelle `CorrectionAgent` pour analyser vos réponses.
    - `LevelAgent` utilise `extract_user_level` pour sauvegarder votre niveau.
    - `ExerciseAgent` utilise `generate_exercise` pour vous proposer un exercice.
    - Quand vous répondez, `ExerciseAgent` appelle `CorrectionAgent` et sauvegarde votre score avec `save_progress`.
4. **Si vous choisissez l'option 2 (Conversation)** :
    - Il vous demande de choisir un persona et un thème, et utilise `save_persona` et `save_topic`.
    - Il passe la main à `ConversationLoop`.
    - `ConversationAgent` appelle `get_topic_info` pour se documenter.
    - À chaque tour, il appelle `CorrectionAgent` pour corriger votre message, puis `save_conversation_turn` pour mémoriser l'échange.
5. **Si vous choisissez l'option 3 (Rapport)** :
    - Il appelle directement ProgressAgent, qui utilise calculate_progress_score et génère un bilan.


## Guide d'installation et d'utilisation

### Prérequis
- Python 3.10+
- Ollama (ollama.ai)
- Google ADK

### Installation
```bash
# Cloner le dépôt
git clone [url-du-projet]
cd tp-adk

# Créer l'environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Installer les dépendances
pip install google-adk python-dotenv requests

# Télécharger le modèle
ollama pull qwen2.5:7b

# Configurer l'environnement
echo "ADK_MODEL_PROVIDER=ollama" > .env
echo "ADK_MODEL_NAME=ollama/qwen2.5:7b" > .env
```
### Lancement
Interface web
```bash
adk web
```
Ouvrir `http://localhost:8000` et sélectionner "my_agent"



## 🚧 Problèmes rencontrés et améliorations apportées
oici les principaux défis rencontrés et comment j'ai itéré pour les résoudre.

### 1. Le choix du modèle LLM 

Constat initial : Le choix du modèle s'est révélé déterminant pour la fiabilité et la testabilité du système.

**Phase exploratoire** : **Gemma 2 (2B)** : Les premiers tests avec ce modèle se sont avérés peu concluants. Les réponses étaient incohérentes, le suivi des instructions en français très limité, et surtout, il était impossible de valider le fonctionnement du système : les modifications apportées aux prompts ou au code ne produisaient pas d'effets prévisibles, rendant le développement particulièrement complexe.

**Phase intermédiaire** : **Llama 3.2 (3B)** : Ce modèle a apporté une amélioration significative de la compréhension et du respect des consignes. Cependant, après une période d'utilisation, un phénomène d'hallucinations récurrentes est apparu : l'agent inventait des appels d'outils inexistants, générait des réponses hors contexte, ou produisait des informations factuellement erronées, compromettant la fiabilité de l'assistant.

**Phase finale** - **Qwen 2.5 (7B)** : La migration vers ce modèle a résolu la majorité des problèmes identifiés. Qwen 2.5 7B démontre une meilleure stabilité dans le suivi des instructions, une réduction significative des hallucinations, et une fiabilité accrue dans l'utilisation des outils.


### 2. Confusion rôle agent / rôle tool

**Problème :** Le `CorrectionAgent` disposait d'un tool `analyze_english_answer` qui appelait l'API LanguageTool pour détecter les erreurs grammaticales — puis retournait une liste structurée que l'agent devait reformuler. En pratique, l'agent faisait un double travail inutile : le LLM recevait une liste d'erreurs déjà formatée et devait la "présenter", ce qui créait de la redondance et des incohérences.

De même, certains tools "généraient du texte" (explications, formulations) alors que c'est précisément le rôle du LLM. Les tools doivent être réservés à ce que le LLM ne peut pas faire seul : écrire dans le state, appeler des APIs, faire des calculs déterministes.

**Solution :** Suppression de `analyze_english_answer`. Le `CorrectionAgent` corrige directement lui-même, et peut appeler `get_word_definition` uniquement pour enrichir une explication avec une définition précise. Séparation claire : **le LLM raisonne et génère**, **les tools agissent sur le monde extérieur**.


### 3. Gestion du state : clarification du mécanisme

**Problème rencontré** : Les tentatives de manipulation directe du state via les instructions des agents se sont révélées infructueuses. Lorsque le prompt demandait à l'agent "d'écrire la valeur X dans le state", ou que l'agent tentait d'accéder à une valeur du state, rien ne se produisait ou les résultats étaient incohérents.

**Solution apportée** : Création d'outils dédiés pour toutes les interactions avec le state

### 4. Séparation des responsabilités entre agents

**Séparation des responsabilités** : Initialement, `LevelAgent` cumulait les fonctions d'évaluation et de correction, ce qui dupliquait la logique de `CorrectionAgent`. La solution a consisté à déléguer systématiquement la correction à `CorrectionAgent` via `correction_agent_tool` (AgentTool), conformément au principe de responsabilité unique.

**Rôle des outils vs rôle du LLM**: Certains outils avaient été conçus pour générer du texte explicatif, empiétant sur le rôle du LLM. Une clarification stricte des périmètres a été opérée : le LLM est responsable du raisonnement et de la génération textuelle, les outils sont réservés aux actions externes (appels API, calculs, persistance).




---

## 🔮 Ce que j'améliorerais

- **Mémoire persistante** : utiliser `DatabaseSessionService` à la place de `InMemorySessionService` pour que la progression survive entre les sessions.
- **Tests automatisés** : Faute de temps, les tests n'ont pas été implémentés. Une version future intégrerait :
    - Trajectoire : Vérification que l'agent appelle les bons outils dans le bon ordre 
    - Réponse finale : Évaluation sémantique de la pertinence 
- **Génération d'exercice** : Remplacement de la banque statique par une API adaptative
- **Communication orale** : Permettre à l'utilisateur de communiquer à l'orale avec l'assisatnt

---


## 🚀 Industrialisation — Comment passer en production ?

Pour déployer LinguaCoach en environnement de production, plusieurs stratégies sont envisageables. La solution retenue privilégie une exposition sous forme d'API REST pour faciliter l'intégration dans des applications tierces

Donc si je voulais industrialiser ce projet, voici les étapes que je suivrais :

1. **Étape 1 : Conteneuriser l'application avec Docker**
2. **Étape 2 : Exposer l'agent via une API REST** avec FastAPI par exemple
3. **Étape 3 : Remplacer la mémoire temporaire par une base de données persistante**
4. **Étape 4 : Déployer sur un cloud (AWS, Google Cloud, Azure) avec un service de conteneurs**
5. **Étape 5 : Configurer le monitoring et les logs**
6. **Étape 6 : Automatiser le déploiement avec une pipeline CI/CD**

