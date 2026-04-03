---
description: "Brainstorm project directions and feature ideas with implementation options and improvement opportunities"
name: "brainstorm-project-features"
argument-hint: "Project idea, product area, or feature concept to explore"
agent: "agent"
---
You are helping with structured brainstorming for projects or features.

Task:
Use the user input as the topic. Generate practical options for what to build, how to implement it, and what to improve.

Requirements:
1. Start with a short interpretation of the topic and list key assumptions.
2. Propose 6 to 10 feature or project directions.
3. For each direction, include:
   - Problem it solves
   - Target user or scenario
   - Why it is valuable
   - 2 or more implementation approaches (quick MVP and scalable path)
   - Risks, tradeoffs, and dependencies
   - Complexity estimate (S, M, L)
   - Impact estimate (Low, Medium, High)
4. Add an Improvement Opportunities section with:
   - UX or workflow improvements
   - Technical quality improvements
   - Cost, performance, or reliability improvements
5. End with:
   - Top 3 recommended directions with reasons
   - A phased implementation plan (Phase 1, 2, 3)
   - 5 sharp follow-up questions to refine decisions

Output format:
Use this exact section order:
1. Topic Interpretation
2. Idea Matrix
3. Improvement Opportunities
4. Recommended Top 3
5. Phased Plan
6. Follow-up Questions

In Idea Matrix, present a markdown table with columns:
Direction | User Value | MVP Approach | Scalable Approach | Risks | Complexity | Impact

Quality bar:
- Prefer concrete and testable ideas over generic suggestions.
- Make tradeoffs explicit.
- If context is missing, state assumptions clearly instead of inventing facts.
