<!-- 2026-04-06 09:08:47 [DEBUG]
 Received request: POST to /v1/chat/completions with body  {
  "model": "qwen3.5-9b-uncensored-hauhaucs-aggressive",
  "temperature": 0.7,
  "stream": true,
  "messages": [
    {
      "role": "system",
      "content": "You are ARIA — Advanced Runtime Intelligence Assis... <Truncated in logs> ... or external APIs — you are local-first by design."
    },
    {
      "role": "assistant",
      "content": "Hello! I'm **ARIA** — your local AI assistant.\n\nI ... <Truncated in logs> ... common actions, or type `/help` for all commands."
    },
    {
      "role": "user",
      "content": "Explain quantum computing like I'm five"
    }
  ]
}
2026-04-06 09:08:47  [INFO]
 [qwen3.5-9b-uncensored-hauhaucs-aggressive] Running chat completion on conversation with 3 messages.
2026-04-06 09:08:47  [INFO]
 [qwen3.5-9b-uncensored-hauhaucs-aggressive] Streaming response...
2026-04-06 09:08:47 [ERROR]
 [qwen3.5-9b-uncensored-hauhaucs-aggressive] Error rendering prompt with jinja template: "No user query found in messages.".

This is usually an issue with the model's prompt template. If you are using a popular model, you can try to search the model under lmstudio-community, which will have fixed prompt templates. If you cannot find one, you are welcome to post this issue to our discord or issue tracker on GitHub. Alternatively, if you know how to write jinja templates, you can override the prompt template in My Models > model settings > Prompt Template.. Error Data: n/a, Additional Data: n/a
2026-04-06 09:08:53 [DEBUG]
 Received request: POST to /v1/chat/completions with body  {
  "model": "qwen3.5-9b-uncensored-hauhaucs-aggressive",
  "temperature": 0.7,
  "stream": true,
  "messages": [
    {
      "role": "system",
      "content": "You are ARIA — Advanced Runtime Intelligence Assis... <Truncated in logs> ... or external APIs — you are local-first by design."
    },
    {
      "role": "assistant",
      "content": "Hello! I'm **ARIA** — your local AI assistant.\n\nI ... <Truncated in logs> ... common actions, or type `/help` for all commands."
    },
    {
      "role": "user",
      "content": "Explain quantum computing like I'm five"
    },
    {
      "role": "assistant",
      "content": "\n\n[LLM Error: 'choices']"
    },
    {
      "role": "user",
      "content": "Explain quantum computing like I'm five"
    }
  ]
}
2026-04-06 09:08:53  [INFO]
 [qwen3.5-9b-uncensored-hauhaucs-aggressive] Running chat completion on conversation with 5 messages.
2026-04-06 09:08:53  [INFO]
 [qwen3.5-9b-uncensored-hauhaucs-aggressive] Streaming response...
2026-04-06 09:08:53 [ERROR]
 [qwen3.5-9b-uncensored-hauhaucs-aggressive] Error rendering prompt with jinja template: "No user query found in messages.".

This is usually an issue with the model's prompt template. If you are using a popular model, you can try to search the model under lmstudio-community, which will have fixed prompt templates. If you cannot find one, you are welcome to post this issue to our discord or issue tracker on GitHub. Alternatively, if you know how to write jinja templates, you can override the prompt template in My Models > model settings > Prompt Template.. Error Data: n/a, Additional Data: n/a
2026-04-06 09:08:56 [DEBUG]
 Received request: POST to /v1/chat/completions with body  {
  "model": "qwen3.5-9b-uncensored-hauhaucs-aggressive",
  "temperature": 0.7,
  "stream": true,
  "messages": [
    {
      "role": "system",
      "content": "You are ARIA — Advanced Runtime Intelligence Assis... <Truncated in logs> ... or external APIs — you are local-first by design."
    },
    {
      "role": "assistant",
      "content": "Hello! I'm **ARIA** — your local AI assistant.\n\nI ... <Truncated in logs> ... common actions, or type `/help` for all commands."
    },
    {
      "role": "user",
      "content": "Explain quantum computing like I'm five"
    },
    {
      "role": "assistant",
      "content": "\n\n[LLM Error: 'choices']"
    },
    {
      "role": "user",
      "content": "Explain quantum computing like I'm five"
    },
    {
      "role": "assistant",
      "content": "\n\n[LLM Error: 'choices']"
    },
    {
      "role": "user",
      "content": "Tell me something interesting"
    }
  ]
}
2026-04-06 09:08:56  [INFO]
 [qwen3.5-9b-uncensored-hauhaucs-aggressive] Running chat completion on conversation with 7 messages.
2026-04-06 09:08:56  [INFO]
 [qwen3.5-9b-uncensored-hauhaucs-aggressive] Streaming response...
2026-04-06 09:08:56 [ERROR]
 [qwen3.5-9b-uncensored-hauhaucs-aggressive] Error rendering prompt with jinja template: "No user query found in messages.".

This is usually an issue with the model's prompt template. If you are using a popular model, you can try to search the model under lmstudio-community, which will have fixed prompt templates. If you cannot find one, you are welcome to post this issue to our discord or issue tracker on GitHub. Alternatively, if you know how to write jinja templates, you can override the prompt template in My Models > model settings > Prompt Template.. Error Data: n/a, Additional Data: n/a
2026-04-06 09:09:14 [DEBUG]
 Received request: GET to /v1/models
2026-04-06 09:09:14  [INFO]
 Returning {
  "data": [
    {
      "id": "qwen3.5-9b-uncensored-hauhaucs-aggressive",
      "object": "model",
      "owned_by": "organization_owner"
    },
    {
      "id": "intent1",
      "object": "model",
      "owned_by": "organization_owner"
    },
    {
      "id": "intent",
      "object": "model",
      "owned_by": "organization_owner"
    },
    {
      "id": "excel-qwen3.5-2b",
      "object": "model",
      "owned_by": "organization_owner"
    },
    {
      "id": "qwen3-vl-8b-instruct",
      "object": "model",
      "owned_by": "organization_owner"
    },
    {
      "id": "text-embedding-nomic-embed-text-v1.5",
      "object": "model",
      "owned_by": "organization_owner"
    }
  ],
  "object": "list"
}
2026-04-06 09:09:18 [DEBUG]
 Received request: POST to /v1/chat/completions with body  {
  "model": "qwen3.5-9b-uncensored-hauhaucs-aggressive",
  "temperature": 0.7,
  "stream": true,
  "messages": [
    {
      "role": "system",
      "content": "You are ARIA — Advanced Runtime Intelligence Assis... <Truncated in logs> ... or external APIs — you are local-first by design."
    },
    {
      "role": "assistant",
      "content": "Hello! I'm **ARIA** — your local AI assistant.\n\nI ... <Truncated in logs> ... common actions, or type `/help` for all commands."
    },
    {
      "role": "user",
      "content": "What would happen if the internet stopped?"
    }
  ]
}
2026-04-06 09:09:18  [INFO]
 [qwen3.5-9b-uncensored-hauhaucs-aggressive] Running chat completion on conversation with 3 messages.
2026-04-06 09:09:18  [INFO]
 [qwen3.5-9b-uncensored-hauhaucs-aggressive] Streaming response...
2026-04-06 09:09:18 [ERROR]
 [qwen3.5-9b-uncensored-hauhaucs-aggressive] Error rendering prompt with jinja template: "No user query found in messages.".

This is usually an issue with the model's prompt template. If you are using a popular model, you can try to search the model under lmstudio-community, which will have fixed prompt templates. If you cannot find one, you are welcome to post this issue to our discord or issue tracker on GitHub. Alternatively, if you know how to write jinja templates, you can override the prompt template in My Models > model settings > Prompt Template.. Error Data: n/a, Additional Data: n/a
2026-04-06 09:09:28 [DEBUG]
 Received request: POST to /v1/chat/completions with body  {
  "model": "qwen3.5-9b-uncensored-hauhaucs-aggressive",
  "temperature": 0.7,
  "stream": true,
  "messages": [
    {
      "role": "system",
      "content": "You are ARIA — Advanced Runtime Intelligence Assis... <Truncated in logs> ... or external APIs — you are local-first by design."
    },
    {
      "role": "assistant",
      "content": "Hello! I'm **ARIA** — your local AI assistant.\n\nI ... <Truncated in logs> ... common actions, or type `/help` for all commands."
    },
    {
      "role": "user",
      "content": "What would happen if the internet stopped?"
    },
    {
      "role": "assistant",
      "content": "\n\n[LLM Error: 'choices']"
    },
    {
      "role": "user",
      "content": "hi"
    }
  ]
}
2026-04-06 09:09:28  [INFO]
 [qwen3.5-9b-uncensored-hauhaucs-aggressive] Running chat completion on conversation with 5 messages.
2026-04-06 09:09:28  [INFO]
 [qwen3.5-9b-uncensored-hauhaucs-aggressive] Streaming response...
2026-04-06 09:09:28 [ERROR]
 [qwen3.5-9b-uncensored-hauhaucs-aggressive] Error rendering prompt with jinja template: "No user query found in messages.".

This is usually an issue with the model's prompt template. If you are using a popular model, you can try to search the model under lmstudio-community, which will have fixed prompt templates. If you cannot find one, you are welcome to post this issue to our discord or issue tracker on GitHub. Alternatively, if you know how to write jinja templates, you can override the prompt template in My Models > model settings > Prompt Template.. Error Data: n/a, Additional Data: n/a -->