# NeverSoft-Agent

Autonomous, provider-agnostic task agent built around a **Build Completion Loop**.

## Completion loop

`receive → inspect → plan → implement → build → test → recover → audit → verify → ship`

The agent is designed to keep working when implementation is incomplete or a build fails. Durable task records and lightweight memory allow work to be resumed instead of starting from zero.

## Current core

- OpenAI-compatible LLM transport (Ollama/local models by default)
- Model-driven function/tool calling
- Workspace-scoped filesystem and shell tools
- Autonomous multi-step execution
- Failure feedback and recovery
- Build Completion Loop infrastructure
- Durable task state
- Lightweight persistent memory
- Resumable orchestration

## Run

```bash
export LLM_MODEL=qwen3:1.7b
python run.py
```

The default model endpoint is `http://localhost:11434/v1`. Override it with `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`.

## Philosophy

A task is not complete because code was written. It is complete when the result has been implemented, exercised, audited, and verified with evidence.
