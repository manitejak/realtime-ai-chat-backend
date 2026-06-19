from typing import Literal

from pydantic import BaseModel, Field


class WSChatMessageIn(BaseModel):
    type: Literal['message.send']
    content: str = Field(min_length=1, max_length=5000)