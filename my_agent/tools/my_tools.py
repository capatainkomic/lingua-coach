import json
import re
import os
import random
import requests
from datetime import datetime

# ================================================================
# TOOL 1 — extract_cefr_level

def extract_user_level(tool_context, raw_text: str) -> dict:
    """
    Extrais le niveau CECRL propre (ex: 'B1') depuis le texte brut
    de l'évaluation, puis sauvegarde-le dans le state sous 'user_level'.


    Args:
        raw_text: Le texte brut de l'évaluation produite par le LevelAgent.

    Returns:
        dict avec status 'success' et le niveau extrait et sauvegardé,
        ou status 'error' si aucun niveau CECRL valide n'est trouvé.
    """
    if not raw_text or not isinstance(raw_text, str):
        return {
            "status": "error",
            "message": "Texte vide. Demande à l'utilisateur son niveau (A1/A2/B1/B2/C1/C2).",
        }

    # Priorité 1 : tag explicite "NIVEAU_DETECTE: B1" placé par le LevelAgent
    match = re.search(r"NIVEAU_DETECTE:\s*(A1|A2|B1|B2|C1|C2)", raw_text)
    if match:
        level = match.group(1)
        tool_context.state["level"] = level   # enregistre le niveau dans un state 
        return {
            "status": "success",
            "level": level,
        }

    # Priorité 2 : code CECRL isolé n'importe où dans le texte
    match = re.search(r"\b(A1|A2|B1|B2|C1|C2)\b", raw_text)
    if match:
        level = match.group(1)
        tool_context.state["level"] = level  # enregistre le niveau dans un state 
        return {
            "status": "success",
            "level": level,
        }

    return {
        "status": "error",
        "message": "Aucun niveau trouvé. Demande à l'utilisateur de confirmer son niveau (A1/A2/B1/B2/C1/C2).",
    }




# ================================================================
# TOOL 2.a — save_persona
# ----------------------------------------------------------------
def save_persona(tool_context, persona: str) -> dict:
    """
    Sauvegarde le persona choisi par l'utilisateur dans le state.

    Appelle cet outil après que l'utilisateur ait choisi son persona
    (british, american, ou australian).

    Args:
        persona: Le persona choisi parmi 'british', 'american', 'australian'.

    Returns:
        dict avec status 'success' et confirmation.
    """
    valid = ["british", "american", "australian"]
    persona = persona.lower().strip()

    if persona not in valid:
        return {
            "status": "error",
            "message": f"Persona invalide. Demande à l'utilisateur de choisir parmi : {valid}",
        }

    tool_context.state["persona"] = persona
    return {
        "status": "success", 
        "persona": persona
    }

# ================================================================
# TOOL 2b — save_topic
# ----------------------------------------------------------------
def save_topic(tool_context, topic: str) -> dict:
    """
    Sauvegarde le thème de conversation choisi par l'utilisateur dans le state.

    Appelle cet outil après que l'utilisateur ait choisi son thème,
    avant de transférer vers ConversationLoop.

    Args:
        topic: Le thème choisi parmi 'travel', 'work', 'technology', 'environment', 'daily_life'.

    Returns:
        dict avec status 'success' et confirmation.
    """
    valid = ["travel", "work", "technology", "environment", "daily_life"]
    topic = topic.lower().strip()

    if topic not in valid:
        return {
            "status": "error",
            "message": f"Thème invalide. Demande à l'utilisateur de choisir parmi : {valid}",
        }

    tool_context.state["topic"] = topic
    return {
        "status": "success",
        "topic": topic
    }




def save_progress(tool_context, score: int, exercise_type: str) -> dict:
    """
    Sauvegarde le résultat d'un exercice dans le state.

    Appelle cet outil après chaque correction d'exercice,
    avec le score obtenu (0-100) et le type d'exercice.

    Args:
        score: Score obtenu entre 0 et 100.
        exercise_type: Type d'exercice ('qcm', 'fill_blank', 'translation').

    Returns:
        dict avec status 'success' et le nombre total d'exercices.
    """
    score = max(0, min(100, int(score)))

    if "progress" not in tool_context.state:
        tool_context.state["progress"] = []

    tool_context.state["progress"].append({
        "score": score,
        "type": exercise_type,
        "timestamp": datetime.now().isoformat(),
    })

    return {
        "status": "success",
        "score_saved": score,
        "total_exercises": len(tool_context.state["progress"]),
    }


def save_conversation_turn(tool_context, user_message: str, ai_response: str) -> dict:
    """
    Sauvegarde un tour de conversation dans le state.

    Appelle cet outil à la fin de chaque tour de conversation,
    avec le message de l'utilisateur et ta réponse.

    Args:
        user_message: Le message de l'utilisateur.
        ai_response: Ta réponse en tant que persona.

    Returns:
        dict avec status 'success' et le nombre de tours total.
    """
    if "history" not in tool_context.state:
        tool_context.state["history"] = []

    tool_context.state["history"].append({
        "user": user_message,
        "ai": ai_response,
    })

    return {
        "status": "success",
        "turns": len(tool_context.state["history"]),
    }



def calculate_progress_score(tool_context) -> dict:
    """
    Calcule le score de progression global depuis l'historique des exercices.

    Appelle cet outil pour obtenir le score final avant de rédiger
    le rapport de progression. Lit directement le state.

    Returns:
        dict avec status 'success', score sur 100 et statistiques,
        ou status 'error' si aucun exercice n'a été fait.
    """
    progress = tool_context.state.get("progress", [])

    if not progress:
        return {
            "status": "error",
            "message": "Aucun exercice complété cette session.",
        }

    scores = [entry["score"] for entry in progress]
    average = round(sum(scores) / len(scores))
    best = max(scores)
    worst = min(scores)

    if average >= 85:
        label = "Expert"
    elif average >= 65:
        label = "Avancé"
    elif average >= 40:
        label = "Intermédiaire"
    else:
        label = "Débutant"

    return {
        "status": "success",
        "total_exercises": len(scores),
        "average_score": average,
        "best_score": best,
        "worst_score": worst,
        "performance_label": label,
    }



def get_topic_info(topic: str) -> dict:
    """
    Récupère un contexte factuel sur un thème via Wikipedia.

    Appelle cet outil au début d'une conversation pour enrichir
    tes réponses avec des informations réelles sur le thème choisi.

    Args:
        topic: Le thème de conversation (ex: 'travel', 'technology').

    Returns:
        dict avec status 'success' et un résumé Wikipedia,
        ou status 'error' si le thème est introuvable.
    """
    # Nettoyer le topic (remplacer les espaces par des underscores)
    formatted_topic = topic.replace(' ', '_')
    
    # Construire l'URL
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{formatted_topic}"
    
    # Ajouter un User-Agent 
    headers = {
        'User-Agent': 'LinguaCoachProject/1.0 (ramlat.maoulana-charif@etu.unice.fr)'  
    }
    
    try:
        # Faire la requête avec headers
        r = requests.get(url, headers=headers)
        
        # Vérifier si la requête a réussi
        r.raise_for_status()
        
        # Parser le JSON
        data = r.json()
        
        # Vérifier si la page existe
        if 'title' not in data or 'extract' not in data:
            return {
                "status": "error",
                "message": f"Page '{topic}' not found",
                "title": topic,
                "summary": None
            }
        
        # Retourner les données
        return {
            "status": "success",
            "topic" : topic, 
            "title": data["title"],
            "summary": data["extract"],
        }
        
    except requests.exceptions.RequestException as e:
        # Gérer les erreurs réseau/HTTP
        return {
            "status": "error",
            "message": str(e),
            "title": topic,
            "summary": None
        }
    except (KeyError, ValueError) as e:
        # Gérer les erreurs de parsing JSON
        return {
            "status": "error",
            "message": f"Failed to parse response: {str(e)}",
            "title": topic,
            "summary": None
        }


def get_word_definition(word: str) -> dict:
    """
    Retrieve word definition from the Free Dictionary API.
    """
    # 1. Nettoyer le mot (enlever les espaces avant/après)
    formatted_word = word.strip().lower()
    
    # 2. Construire l'URL
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{formatted_word}"
    
    # 3. Ajouter un User-Agent (c'est une bonne pratique pour toutes les API)
    headers = {
        'User-Agent': 'MonProjetDictionnaire/1.0 (contact@example.com)'  # À personnaliser
    }
    
    try:
        # 4. Faire la requête
        r = requests.get(url, headers=headers, timeout=5)  # timeout pour éviter d'attendre trop longtemps
        
        # 5. Gérer les codes d'erreur HTTP spécifiques
        if r.status_code == 404:
            return {
                "error": f"Le mot '{word}' n'a pas été trouvé.",
                "word": word,
                "definition": None
            }
        
        # 6. Vérifier les autres erreurs HTTP
        r.raise_for_status()
        
        # 7. Parser le JSON
        data = r.json()
        
        # 8. Naviguer dans la structure de données (qui peut varier)
        if data and len(data) > 0:
            meanings = data[0].get("meanings", [])
            if meanings and len(meanings) > 0:
                definitions = meanings[0].get("definitions", [])
                if definitions and len(definitions) > 0:
                    definition = definitions[0].get("definition", "Définition non disponible")
                    
                    # Optionnel : récupérer plus d'infos
                    phonetic = data[0].get("phonetic", "")
                    
                    return {
                        "word": word,
                        "definition": definition,
                        "phonetic": phonetic,
                        "example": definitions[0].get("example", "")
                    }
        
        # Si la structure n'est pas celle attendue
        return {
            "error": "Format de réponse inattendu de l'API",
            "word": word,
            "definition": None
        }
        
    except requests.exceptions.Timeout:
        return {
            "error": "La requête a expiré. Veuillez réessayer.",
            "word": word,
            "definition": None
        }
    except requests.exceptions.RequestException as e:
        # Erreur réseau ou HTTP
        return {
            "error": f"Erreur de connexion : {str(e)}",
            "word": word,
            "definition": None
        }
    except (KeyError, IndexError, ValueError) as e:
        # Erreur de parsing JSON ou structure inattendue
        return {
            "error": f"Erreur lors de l'analyse des données : {str(e)}",
            "word": word,
            "definition": None
        }



def generate_exercise(level: str, exercise_type: str) -> dict:
    """
    Génère un exercice d'anglais structuré depuis une banque de questions.

    Appelle cet outil après avoir demandé à l'utilisateur quel type
    d'exercice il souhaite (qcm, fill_blank, translation).

    Args:
        level: Niveau CECRL (A1, A2, B1, B2, C1, C2).
        exercise_type: Type parmi 'qcm', 'fill_blank', 'translation'.

    Returns:
        dict avec status 'success' et les données de l'exercice,
        ou status 'error' si les paramètres sont invalides.
    """
    valid_levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
    valid_types = ["qcm", "fill_blank", "translation"]

    level = level.upper().strip()
    exercise_type = exercise_type.lower().strip()

    if level not in valid_levels:
        return {"status": "error", "message": f"Niveau invalide. Valides : {valid_levels}"}

    if exercise_type not in valid_types:
        return {"status": "error", "message": f"Type invalide. Valides : {valid_types}"}

    # ── QCM ──────────────────────────────────────────────────────
    qcm_bank = {
        "A1": [
            {
                "category": "Grammaire",
                "question": "Choose the correct word: 'She ___ a teacher.'",
                "choices": {"A": "am", "B": "is", "C": "are", "D": "be"},
                "correct": "B",
                "explanation": "With He/She/It we always use IS.",
            },
            {
                "category": "Vocabulaire",
                "question": "What does 'happy' mean in French?",
                "choices": {"A": "triste", "B": "fatigué", "C": "content", "D": "en colère"},
                "correct": "C",
                "explanation": "'Happy' means 'content' in French.",
            },
        ],
        "A2": [
            {
                "category": "Grammaire",
                "question": "'Yesterday, I ___ to the cinema.'",
                "choices": {"A": "go", "B": "goes", "C": "went", "D": "going"},
                "correct": "C",
                "explanation": "Simple past of 'go' is 'went' (irregular verb).",
            },
            {
                "category": "Vocabulaire",
                "question": "Choose the word that means 'très grand'.",
                "choices": {"A": "tiny", "B": "huge", "C": "light", "D": "loud"},
                "correct": "B",
                "explanation": "'Huge' means very big.",
            },
        ],
        "B1": [
            {
                "category": "Grammaire",
                "question": "'By the time she arrived, he ___ already left.'",
                "choices": {"A": "has", "B": "had", "C": "have", "D": "was"},
                "correct": "B",
                "explanation": "Past perfect (had + pp) for an action completed before another past action.",
            },
            {
                "category": "Compréhension",
                "question": "'I wouldn't mind a coffee.' What does this mean?",
                "choices": {
                    "A": "I don't like coffee",
                    "B": "I would like a coffee",
                    "C": "Coffee bothers me",
                    "D": "I never drink coffee",
                },
                "correct": "B",
                "explanation": "'Wouldn't mind' is a polite way to say 'I would like'.",
            },
        ],
        "B2": [
            {
                "category": "Grammaire",
                "question": "'She suggested ___ to the new restaurant downtown.'",
                "choices": {"A": "to go", "B": "going", "C": "go", "D": "gone"},
                "correct": "B",
                "explanation": "After 'suggest', use the gerund (-ing form).",
            },
        ],
        "C1": [
            {
                "category": "Vocabulaire",
                "question": "Choose the most precise word: 'The politician gave an ___ speech that moved the crowd.'",
                "choices": {"A": "emotional", "B": "eloquent", "C": "loud", "D": "extended"},
                "correct": "B",
                "explanation": "'Eloquent' means well-spoken and persuasive — more precise than 'emotional'.",
            },
        ],
        "C2": [
            {
                "category": "Grammaire avancée",
                "question": "'___ he known about the risks, he would never have agreed.'",
                "choices": {"A": "If", "B": "Had", "C": "Should", "D": "Were"},
                "correct": "B",
                "explanation": "Inverted conditional (Had + subject + pp) = formal 3rd conditional.",
            },
        ],
    }

    # ── FILL BLANK ───────────────────────────────────────────────
    fill_blank_bank = {
        "A1": [
            {
                "sentence": "I ___ (to be) very tired today.",
                "answer": "am",
                "explanation": "1st person singular of 'to be' is 'am'.",
            },
        ],
        "A2": [
            {
                "sentence": "She ___ (to go) to school every day.",
                "answer": "goes",
                "explanation": "3rd person singular in present simple: add -s.",
            },
        ],
        "B1": [
            {
                "sentence": "If I ___ (to have) more time, I would travel more.",
                "answer": "had",
                "explanation": "2nd conditional: If + past simple, would + infinitive.",
            },
        ],
        "B2": [
            {
                "sentence": "The report ___ (to submit) by Friday at the latest.",
                "answer": "must be submitted",
                "explanation": "Passive voice with modal: must be + past participle.",
            },
        ],
        "C1": [
            {
                "sentence": "Scarcely ___ he sat down when the phone rang.",
                "answer": "had",
                "explanation": "Inverted structure with 'scarcely': Scarcely had + subject + pp.",
            },
        ],
        "C2": [
            {
                "sentence": "The findings ___ (to challenge) the long-held assumptions of the field.",
                "answer": "have been shown to challenge",
                "explanation": "Complex passive with perfect aspect and infinitive complement.",
            },
        ],
    }

    # ── TRANSLATION ──────────────────────────────────────────────
    translation_bank = {
        "A1": [
            {
                "french": "Je m'appelle Marie et j'ai 20 ans.",
                "english": "My name is Marie and I am 20 years old.",
                "tip": "Use 'My name is' (not 'I call myself') and 'I am' for age.",
            },
        ],
        "A2": [
            {
                "french": "Hier soir, j'ai regardé un film avec mes amis.",
                "english": "Last night, I watched a film with my friends.",
                "tip": "Simple past: watched. 'Last night' signals past tense.",
            },
        ],
        "B1": [
            {
                "french": "Si j'avais plus d'argent, j'achèterais une voiture.",
                "english": "If I had more money, I would buy a car.",
                "tip": "2nd conditional: If + past simple, would + base verb.",
            },
        ],
        "B2": [
            {
                "french": "On m'a dit que la réunion avait été annulée.",
                "english": "I was told that the meeting had been cancelled.",
                "tip": "Passive reporting verb + past perfect passive in the subordinate clause.",
            },
        ],
        "C1": [
            {
                "french": "Bien qu'il soit fatigué, il a continué à travailler.",
                "english": "Despite being tired, he continued to work.",
                "tip": "Use 'despite + gerund' to sound more sophisticated than 'although'.",
            },
        ],
        "C2": [
            {
                "french": "Il aurait fallu qu'ils prennent en compte les conséquences à long terme.",
                "english": "They ought to have taken into account the long-term consequences.",
                "tip": "'Ought to have + pp' expresses criticism of a past action.",
            },
        ],
    }

    if exercise_type == "qcm":
        bank = qcm_bank.get(level, qcm_bank["B1"])
        exercise = random.choice(bank)
        
        return {
            "status": "success", 
            "type": "qcm", 
            "level": level, 
            "exercise": exercise
        }

    elif exercise_type == "fill_blank":
        bank = fill_blank_bank.get(level, fill_blank_bank["B1"])
        exercise = random.choice(bank)
        
        return {
            "status": "success", 
            "type": "fill_blank", 
            "level": level, 
            "exercise": exercise
        }

    elif exercise_type == "translation":
        bank = translation_bank.get(level, translation_bank["B1"])
        exercise = random.choice(bank)
        
        return {
            "status": "success", 
            "type": "translation", 
            "level": level, 
            "exercise": exercise
        }



    


    


