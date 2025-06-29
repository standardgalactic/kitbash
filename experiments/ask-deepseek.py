#!/usr/bin/python3

from openai import OpenAI

client = OpenAI(
    base_url="https://router.huggingface.co/fireworks-ai/inference/v1",
    api_key="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",
)

stream = client.chat.completions.create(
    model="accounts/fireworks/models/deepseek-r1-0528",
    messages=[
        {
            "role": "user",
            "content": "What is the purpose of a null-wavefront in Null Convention Logic?"
        }
    ],
    stream=True,
)

for chunk in stream:
    print(chunk.choices[0].delta.content, end="")
