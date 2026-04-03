---
description: "Produce implementation plan based on requirements with actionable engineering steps, risks, dependencies, testing strategy, and done criteria"
name: "create-implementation-plan"
argument-hint: "Ticket, requirement, or feature request to plan"
agent: "agent"
---
You are generating an implementation plan that can be directly executed by a software engineer.

Primary objective:
Create a concrete HOW-to plan from the provided requirement or ticket, grounded in the current repository.

Execution workflow:
1. Analyze repository context before planning:
   - Project structure and module boundaries
   - Existing code patterns, naming conventions, and architecture decisions
   - Existing docs and design artifacts, especially: README and architecture related docs.
2. Synthesize findings into an implementation plan tailored to the ticket goals.
3. Break work into clear, actionable engineering steps.
4. Include dependencies, risks, unit-testing strategy, and done criteria.

Mandatory planning rules:
1. Focus on implementation details (HOW), not generic summaries.
2. Each step must be actionable and clear to a software engineer, what and how to complete it.
3. Explicitly define for each action what needs to be done: create endpoint in <module/file>, run command, etc.
4. Infer and propose technology stack and conventions only when not explicitly defined by:
   - repository instructions or configuration
   - project documentation
   - user input
5. Do NOT include integration tests.
6. Include unit-test actions for each relevant implementation area.
7. Maintain professional, concise language.
8. Use clear section headers.

Output format (use exactly these sections and order):

## 1) Goal and Scope
- Restate implementation target and in-scope/out-of-scope boundaries.

## 2) Repository Findings
- Summarize relevant structure, existing patterns, and constraints discovered in the repo.

## 3) Assumptions and Clarifications
- List explicit assumptions.
- Add "Clarifications Needed" only for blocking or high-risk unknowns.

## 4) Implementation Plan
- Provide numbered phases and steps.
- For each step include:
  - Objective
  - Concrete changes (files/modules/endpoints/classes/functions)
  - Execution details (commands, migrations, config updates)
  - Unit tests to add/update (no integration tests)
  - Verification checks
  - Documentation updates if needed

## 5) Dependencies and Sequencing
- Identify technical and team dependencies.
- Explain ordering constraints and parallelizable work.

## 6) Risks and Mitigations
- List key implementation risks and specific mitigation actions.

## 7) Validation Strategy
- Define how to validate functional correctness and non-functional requirements with:
  - Unit tests
  - Static checks/lint/type checks
  - Manual verification where needed

## 8) Definition of Done
- Provide measurable completion criteria tied to scope and requirements.

Quality bar:
- Prefer repository-specific instructions over generic best practices.
- Avoid vague items like "implement feature"; replace with concrete actions.
- If repository details are missing, state that clearly and proceed with explicit assumptions.