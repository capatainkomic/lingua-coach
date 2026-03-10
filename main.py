import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from my_agent.agent import root_agent


async def run_linguacoach():
    session_service = InMemorySessionService()

    await session_service.create_session(
        app_name="lingua_coach",
        user_id="user_001",
        session_id="session_001",
    )

    runner = Runner(
        agent=root_agent,
        app_name="lingua_coach",
        session_service=session_service,
    )

    print("=" * 60)
    print("   🎓 LinguaCoach — Assistant d'apprentissage de l'anglais")
    print("=" * 60)
    print("Tapez 'quit' pour quitter.\n")

    while True:
        user_input = input("Vous : ").strip()
        if not user_input:
            continue
        if user_input.lower() in ["quit", "quitter", "exit"]:
            print("\nLinguaCoach : Au revoir ! 🎓")
            break

        async for event in runner.run_async(
            user_id="user_001",
            session_id="session_001",
            new_message=genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=user_input)],
            ),
        ):
            if event.is_final_response():
                response_text = event.content.parts[0].text if event.content.parts else ""
                print(f"\nLinguaCoach : {response_text}\n")


if __name__ == "__main__":
    asyncio.run(run_linguacoach())

