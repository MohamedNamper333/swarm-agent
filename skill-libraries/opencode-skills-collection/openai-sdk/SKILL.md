---
name: openai-sdk
description: Use when integrating with OpenAI APIs for chat completions, embeddings, assistants, fine-tuning, and image generation. Invoke for SDK setup, streaming responses, function/tool calling, RAG with embeddings, assistant thread management, and model fine-tuning pipelines.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: ai
  triggers: OpenAI, GPT, chat completion, embeddings, assistants API, fine-tuning, DALL-E, Whisper, function calling, tool use, streaming, Azure OpenAI, vector store, RAG, prompt engineering, moderation
  role: specialist
  scope: implementation
  output-format: code
  related-skills: rag-architect, prompt-engineer, fine-tuning-expert, python-pro, typescript-pro
---

# OpenAI SDK

The OpenAI SDK provides programmatic access to OpenAI's models including GPT-4 for chat completions, text-embedding-3 for embeddings, the Assistants API for agent-like workflows, and fine-tuning endpoints for custom model training. It supports streaming, tool/function calling, structured outputs, and multimodal inputs.

## When to Use This Skill

- Building chat interfaces with GPT-4o with streaming, tool calling, and structured JSON output
- Generating embeddings for semantic search, clustering, and RAG pipeline integration
- Creating AI assistants with custom instructions, knowledge retrieval, code interpreter, and function tools
- Fine-tuning models on custom datasets for improved domain-specific performance

## Key Capabilities

- Configure the OpenAI client with API key, organization ID, timeout, and retry settings for production reliability
- Implement streaming chat completions with `stream: true` and iterating over chunks for real-time UX
- Use tool/function calling to let models invoke external APIs, query databases, or perform actions
- Manage the Assistants run lifecycle — create thread, add messages, run assistant, poll status, handle required actions

## Best Practices

- Always stream responses (`stream: true`) for chat interfaces to reduce perceived latency
- Use structured outputs with `response_format: { type: 'json_schema', json_schema: {...} }` instead of parsing plain text
- Set reasonable `max_tokens` and `temperature` defaults (temperature 0-0.7 for factual, higher for creative)
- Implement exponential backoff with jitter for retry handling on rate limits (429 status)

## Core Workflow

1. **Initialize** — Create an OpenAI client with your API key and base URL (supports Azure and third-party proxies)
2. **Request** — Call `client.chat.completions.create` with messages, model, and parameters
3. **Stream** — Iterate over the response stream for real-time token delivery to the user
4. **Tool Call** — When the model requests a tool, execute the function and submit the result back
5. **Assistants** — For complex multi-step tasks, use the Assistants API with thread/message/run management

## Key Patterns

```typescript
// Streaming chat completion with tool calling
import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  timeout: 30000,
  maxRetries: 3,
});

async function chatStream(messages: OpenAI.Chat.ChatCompletionMessageParam[]) {
  const stream = await openai.chat.completions.create({
    model: 'gpt-4o',
    messages,
    stream: true,
    tools: [
      {
        type: 'function',
        function: {
          name: 'get_weather',
          description: 'Get the weather for a location',
          parameters: {
            type: 'object',
            properties: {
              location: { type: 'string' },
              unit: { type: 'string', enum: ['celsius', 'fahrenheit'] },
            },
            required: ['location'],
          },
        },
      },
    ],
  });

  for await (const chunk of stream) {
    const delta = chunk.choices[0]?.delta;
    if (delta?.content) process.stdout.write(delta.content);
  }
}
```

```typescript
// Embeddings for RAG
async function getEmbedding(text: string): Promise<number[]> {
  const response = await openai.embeddings.create({
    model: 'text-embedding-3-small',
    input: text,
  });
  return response.data[0].embedding;
}
```

## Constraints

### MUST DO
- Handle API errors gracefully — catch `OpenAI.APIError` for rate limits, auth failures, and server errors
- Set `max_tokens` on all completions to bound response length and cost
- Use `user` parameter to associate requests with end users for monitoring and abuse detection

### MUST NOT DO
- Hard-code API keys — always use environment variables or a secrets manager
- Log full request/response bodies containing user messages in production (PII risk)
- Use `gpt-3.5-turbo` for tasks requiring complex reasoning, tool calling, or structured output — prefer `gpt-4o` or `gpt-4o-mini`
