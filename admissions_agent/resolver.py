from admissions_agent.models import EmailThread, InstitutionCandidate


class InstitutionResolver:
    def resolve(self, thread: EmailThread) -> InstitutionCandidate:
        return InstitutionCandidate(
            canonical_name="Unknown Institution",
            source_value=thread.snippet,
            confidence=0.2,
            is_known=False,
        )
