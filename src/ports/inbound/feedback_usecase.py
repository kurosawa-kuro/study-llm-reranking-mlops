from __future__ import annotations

from typing import Protocol

from src.application.dtos.feedback_dto import FeedbackAction, FeedbackCommandDTO

FeedbackCommand = FeedbackCommandDTO


class FeedbackUseCase(Protocol):
    def execute(self, command: FeedbackCommand) -> dict[str, object]:
        ...
