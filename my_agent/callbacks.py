from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse


# ================================================================
# CALLBACK 1 — before_model_callback
# ----------------------------------------------------------------
# WHEN : Before every LLM call.
# ROLE : Log which agent is thinking and preview the incoming message.
# ================================================================

def before_model_callback( callback_context: CallbackContext,llm_request: LlmRequest) :
    agent_name = callback_context.agent_name

    last_user_message = ""
    if llm_request.contents:
        for content in reversed(llm_request.contents):
            if content.role == "user" and content.parts:
                last_user_message = content.parts[0].text or ""
                break

    preview = last_user_message[:100] + "..." if len(last_user_message) > 100 else last_user_message
    print(f"\n[before_model] Agent '{agent_name}' is thinking...")
    if preview:
        print(f"[before_model] Message: '{preview}'")

    return None


# ================================================================
# CALLBACK 2 — after_tool_callback
# ----------------------------------------------------------------
# WHEN : After every tool call.
# ROLE : Log the tool result and surface any errors clearly.
# ================================================================

def after_tool_callback(tool, tool_response: dict) :
    tool_name = tool.name if hasattr(tool, "name") else str(tool)
    status = tool_response.get("status", "unknown")

    print(f"\n[after_tool] '{tool_name}' → status: {status}")

    if status == "error":
        print(f"[after_tool] ⚠️  {tool_response.get('message', 'unknown error')}")

    return None


# ================================================================
# CALLBACK 3 — before_agent_callback  (sur LevelAgent)
# ----------------------------------------------------------------
# WHEN : Before LevelAgent runs.
# ROLE : If state["level"] already exists, skip the entire evaluation
#        and return the known level directly — avoids re-evaluating
#        a user who already went through the diagnostic.
# ================================================================

def skip_if_level_known(callback_context: CallbackContext):
    level = callback_context.state.get("level")

    if level:
        print(f"\n[before_agent] LevelAgent skipped — level already known: {level}")
        from google.genai import types as genai_types
        return genai_types.Content(
            role="model",
            parts=[genai_types.Part(text=f"Votre niveau a déjà été évalué : **{level}**. Passons directement aux exercices !")],
        )

    return None


