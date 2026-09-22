from __future__ import annotations

import json

from app.config import settings
from app.providers.base import LLMProvider


class BedrockProvider(LLMProvider):
    """Calls AWS Bedrock's Messages API (Anthropic Claude models by default).

    Requires standard AWS credential resolution (env vars, profile, or IAM
    role) -- this class does not manage credentials itself. Not exercised in
    Phase 0 (no Bedrock access provisioned yet); LLM_PROVIDER=mock is the
    default until it is.
    """

    def __init__(self) -> None:
        import boto3  # local import so 'mock' mode never requires boto3/creds

        self._client = boto3.client("bedrock-runtime", region_name=settings.aws_region)

    def complete(self, prompt: str, *, skill_id: str) -> str:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        response = self._client.invoke_model(
            modelId=settings.bedrock_model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(response["body"].read())
        # Anthropic Messages API on Bedrock returns content as a list of blocks.
        return "".join(block.get("text", "") for block in payload.get("content", []))
