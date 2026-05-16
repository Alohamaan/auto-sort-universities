from admissions_agent.classifier import ThreadClassifier
from admissions_agent.decision_engine import DecisionEngine
from admissions_agent.gmail import GmailClient


class PollMailboxJob:
    def __init__(self) -> None:
        self.gmail = GmailClient()
        self.classifier = ThreadClassifier()
        self.engine = DecisionEngine()

    def run_once(self) -> list[dict]:
        outputs = []
        for thread in self.gmail.fetch_new_threads():
            classification = self.classifier.classify(thread)
            decision = self.engine.decide(classification)
            outputs.append(decision.model_dump())
        return outputs
