import asyncio


class MockAIService:
    async def generate_reply(self, user_message: str) -> str:
        await asyncio.sleep(0.2)
        return f"Mock assistant reply: you said '{user_message[:200]}'"