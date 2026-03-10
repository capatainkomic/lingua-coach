from google.adk.agents import LlmAgent, SequentialAgent, LoopAgent
from google.adk.tools import AgentTool

from my_agent.tools import (
    extract_user_level,
    save_persona,
    save_topic,
    save_progress,
    save_conversation_turn,
    calculate_progress_score,
    generate_exercise,
    get_topic_info,
    get_word_definition,
)

from my_agent.callbacks import (
    before_model_callback,
    after_tool_callback,
    skip_if_level_known,
)

import os
from dotenv import load_dotenv

load_dotenv()
MODEL = os.getenv("ADK_MODEL_NAME", "ollama/qwen2.5:7b") # si quelqu'un oublie de configurer le .env, le projet tourne quand même avec le modele qwen2.5:7b


# ================================================================
# AGENT 2 — CorrectionAgent  (wrappé en AgentTool)
# ================================================================

correction_agent = LlmAgent(
    name="CorrectionAgent",
    model=MODEL,
    description="Corrects English errors and explains each mistake in French.",
    instruction="""
    You are a supportive English teacher for French speakers.
    The user's level is: {level}
    Read the user's last English message and correct it.
    If there are no errors, write: "✅ Parfait, aucune erreur !"
    For each error write: "❌ '{wrong}' → '{correction}' : [short explanation in French]"
    If a key word would benefit from an official definition, call `get_word_definition` once.
    End with a short encouraging sentence in French. Adapt explanation depth to level {level}.
    """,
    tools=[get_word_definition],
    after_tool_callback=after_tool_callback,
)

# agent tool car l'agent est appelé par d'autres agents
correction_agent_tool = AgentTool(agent=correction_agent)




# ================================================================
# AGENT 1 — LevelAgent
# ================================================================

level_agent = LlmAgent(
    name="LevelAgent",
    model=MODEL,
    description="Assesses the english level of a French-speaking learner through 3 diagnostic questions.",
    instruction="""
You are an English level assessor for French speakers. Always respond to the user in French.

If the user has not yet answered any English questions, introduce yourself in French
and ask these 3 questions in English:
1. What did you do last weekend?
2. Do you think social media is good or bad? Why?
3. Describe a challenge you faced and how you overcame it.

Once the user has answered, call `correction_agent_tool` with their answers
to get a grammar and vocabulary analysis.

Then write your evaluation in French using this format:
"Voici votre évaluation :
- Grammaire : [grammar observations from CorrectionAgent]
- Vocabulaire : [vocabulary observations from CorrectionAgent]
NIVEAU_DETECTE: [code only: A1, A2, B1, B2, C1 or C2]"

Then call `extract_user_level`, passing your full evaluation text as raw_text.
""",
    tools=[correction_agent_tool, extract_user_level],
    output_key="raw_evaluation_text",
    before_agent_callback=skip_if_level_known,
    before_model_callback=before_model_callback,
)




# ================================================================
# AGENT 3 — ExerciseAgent
# ================================================================

exercise_agent = LlmAgent(
    name="ExerciseAgent",
    model=MODEL,
    description="Generates an exercise adapted to level {level} and corrects the answer via CorrectionAgent.",
    instruction="""
You are an English exercise teacher for French speakers.
The user's level is: {level}. Always respond in French.

Start by asking the user which type of exercise they want:
- qcm: multiple choice question
- fill_blank: complete a sentence
- translation: translate from French to English

Once the type is chosen, call `generate_exercise` with the user's level {level} and chosen type,
then present the exercise clearly in French. Wait for the user's answer.

When the user answers, call `correction_agent_tool` with their exact answer,
reveal the correct answer, then call `save_progress` with the score (0-100) and exercise type.

Never reveal the answer before the user has responded.
""",
    tools=[generate_exercise, correction_agent_tool, save_progress],
    before_model_callback=before_model_callback,
    after_tool_callback=after_tool_callback,
)


# ================================================================
# AGENT 4 — ConversationAgent
# ================================================================

conversation_agent = LlmAgent(
    name="ConversationAgent",
    model=MODEL,
    description="Simulates a conversation as a native {persona} speaker on the topic {topic}.",
    instruction="""
    You are a native English speaker with persona {persona}, discussing the topic {topic}.

    On the first turn, call `get_topic_info` with topic {topic} to ground your responses
    in real factual context. Briefly introduce yourself in French, then ask one opening
    question in English about the theme.

    On each subsequent turn:
    - Call `correction_agent_tool` with the user's message and show the correction in French.
    - Reply naturally in English as a native {persona} speaker.
    - Call `save_conversation_turn` with the user's message and your reply.
    - Ask one follow-up question in English to keep the conversation going.

    If the user writes "stop", say goodbye in English and add one closing line in French.
""",
    tools=[get_topic_info, correction_agent_tool, save_conversation_turn],
    before_model_callback=before_model_callback,
    after_tool_callback=after_tool_callback,
)


# ================================================================
# AGENT 5 — ProgressAgent
# ================================================================

progress_agent = LlmAgent(
    name="ProgressAgent",
    model=MODEL,
    description="Generates a progress report based on the completed exercises.",
    instruction="""
    You are the progress analyst for LinguaCoach. Always write the report in French.

    Call `calculate_progress_score` to get the session statistics,
    then write a warm and encouraging report including:
    - current level ({level})
    - average score and performance label
    - number of exercises, best and worst score
    - one strength and one area to improve based on the actual data
    - one concrete tip adapted to level {level}

    If no exercises were completed, say so kindly and encourage the user to start.
""",
    tools=[calculate_progress_score],
)


# ================================================================
# WORKFLOW 1 — SessionPipeline (SequentialAgent)
# ================================================================

session_pipeline = SequentialAgent(
    name="SessionPipeline",
    description="Assesses the user's level then generates and corrects an adapted exercise.",
    sub_agents=[level_agent, exercise_agent],
)


# ================================================================
# WORKFLOW 2 — ConversationLoop (LoopAgent)
# ================================================================

conversation_loop = LoopAgent(
    name="ConversationLoop",
    description="Conversation loop with correction at each turn, until 'stop' or 10 exchanges.",
    sub_agents=[conversation_agent],
    max_iterations=10,
)

# ================================================================
# ROOT AGENT — OrchestratorAgent
# ================================================================

root_agent = LlmAgent(
    name="OrchestratorAgent",
    model=MODEL,
    description="LinguaCoach coordinator — welcomes the user and routes to the right agent.",
    instruction="""
You are LinguaCoach, an English learning assistant for French speakers.
Always respond in French. Your only role is to welcome and route.

On first contact, present the 3 options:
option 1 :  Évaluer mon niveau et faire des exercices
option 2 : Pratiquer la conversation avec un natif
option 3 : Voir mon rapport de progression

Wait for user answer

Option 1 → transfer_to_agent('SessionPipeline').

Option 2 → before transferring, ask successively:
- which persona they want (british, american, australian), then call `save_persona`
- which theme they want (travel, work, technology, environment, daily_life), then call `save_topic`
Wait for user answer 
Then transfer_to_agent('ConversationLoop').

Option 3 → transfer_to_agent('ProgressAgent').

If the user's intent is unclear, ask one clarifying question.
""",
    tools=[save_persona, save_topic],
    sub_agents=[session_pipeline, conversation_loop, progress_agent],
)