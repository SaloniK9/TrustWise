class TrustEngine:
    def verify(self, agent_results):
        trusted = []

        for result in agent_results:
            if (
                result.get("confidence", 0) >= 0.8
                and result.get("status") == "trusted"
            ):
                trusted.append(result)

        if not trusted:
            raise Exception(
                "No trusted verified sources. LLM execution aborted."
            )

        return trusted
