---
name: prompt-engineering-expert
description: Use when crafting, reviewing, or improving prompts for Claude or other LLMs. Covers clarity, examples, chain of thought, XML tags, system prompts, prefilling, prompt chaining, and long context handling. Essential for building production-quality prompts.
---

# Prompt Engineering Expert

Design effective prompts for Claude using Anthropic's best practices. This skill covers the full spectrum of prompt engineering techniques from basic clarity to advanced chaining patterns.

## Before Writing Prompts

### Prerequisites

Before engineering prompts, ensure you have:
1. **Clear success criteria** - What does a good output look like?
2. **Empirical tests** - How will you measure success?
3. **First draft** - A starting point to iterate from

### The Golden Rule

> Show your prompt to a colleague with minimal context. If they're confused, Claude will be too.

## Core Techniques (Priority Order)

Apply these techniques in order of impact. Start with fundamentals before adding complexity.

### 1. Be Clear, Direct, and Detailed

Think of Claude as a brilliant new employee with no context on your norms, styles, or preferences.

**Provide Context:**
- What the results will be used for
- Who the audience is
- Where this fits in the workflow
- What success looks like

**Be Specific:**
- State exactly what you want
- Use numbered steps for sequential instructions
- Include constraints and format requirements

```markdown
# Vague (Bad)
Please remove PII from this feedback.

# Clear (Good)
Your task is to anonymize customer feedback for our quarterly review.

Instructions:
1. Replace all customer names with "CUSTOMER_[ID]" (e.g., "Jane Doe" → "CUSTOMER_001")
2. Replace email addresses with "EMAIL_[ID]@example.com"
3. Redact phone numbers as "PHONE_[ID]"
4. If a message mentions a specific product (e.g., "AcmeCloud"), leave it intact
5. If no PII is found, copy the message verbatim
6. Output only the processed messages, separated by "---"

Data to process: {{FEEDBACK_DATA}}
```

### 2. Use Examples (Multishot Prompting)

Examples are your secret weapon for consistency and accuracy.

**Best Practices:**
- Include 3-5 diverse examples
- Cover edge cases and potential challenges
- Wrap examples in `<example>` tags
- Vary examples to avoid unintended pattern matching

```markdown
Our CS team is overwhelmed with unstructured feedback. Analyze feedback and categorize issues.

Categories: UI/UX, Performance, Feature Request, Integration, Pricing, Other
Also rate: Sentiment (Positive/Neutral/Negative), Priority (High/Medium/Low)

<example>
Input: The new dashboard is a mess! It takes forever to load, and I can't find the export button. Fix this ASAP!
Category: UI/UX, Performance
Sentiment: Negative
Priority: High
</example>

Now analyze this feedback: {{FEEDBACK}}
```

### 3. Let Claude Think (Chain of Thought)

For complex tasks, structured thinking improves accuracy dramatically.

**When to Use CoT:**
- Complex math or logic
- Multi-step analysis
- Decisions with many factors
- Tasks a human would need to think through

**CoT Levels (Least to Most Complex):**

| Level | Technique | Example |
|-------|-----------|---------|
| Basic | "Think step-by-step" | Quick and minimal |
| Guided | Outline specific steps | More control over reasoning |
| Structured | Use `<thinking>` and `<answer>` tags | Easy to parse and validate |

```markdown
# Structured CoT Example
Analyze this investment scenario.

Think before answering in <thinking> tags:
1. First, calculate potential returns for each option
2. Then, assess risk factors given the timeline
3. Finally, consider the client's stated priorities

Provide your recommendation in <answer> tags.

Scenario: {{INVESTMENT_SCENARIO}}
```

### 4. Use XML Tags for Structure

XML tags prevent Claude from mixing up instructions, examples, and data.

**Benefits:**
- Clear separation of prompt components
- Consistent referencing ("Using the contract in `<contract>` tags...")
- Easy post-processing of structured outputs
- Reduced misinterpretation

**Common Tag Patterns:**

| Purpose | Tags |
|---------|------|
| Input data | `<document>`, `<data>`, `<context>` |
| Instructions | `<instructions>`, `<task>`, `<rules>` |
| Examples | `<example>`, `<examples>` |
| Output structure | `<thinking>`, `<answer>`, `<output>` |
| Formatting | `<format>`, `<formatting_example>` |

**Best Practices:**
- Be consistent with tag names throughout
- Nest tags for hierarchical content: `<outer><inner></inner></outer>`
- Reference tags explicitly in instructions

```markdown
Analyze this software licensing agreement for legal risks.

<agreement>
{{CONTRACT}}
</agreement>

<standard_contract>
{{STANDARD_CONTRACT}}
</standard_contract>

<instructions>
1. Analyze these clauses: Indemnification, Limitation of liability, IP ownership
2. Note unusual or concerning terms
3. Compare to our standard contract
4. Summarize findings in <findings> tags
5. List actionable recommendations in <recommendations> tags
</instructions>
```

### 5. Give Claude a Role (System Prompts)

Role prompting tailors Claude's expertise, tone, and focus.

**Benefits:**
- Enhanced accuracy in specialized domains
- Tailored communication style
- Improved focus on task requirements

**Use the `system` parameter for roles:**

```python
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=2048,
    system="You are a seasoned data scientist at a Fortune 500 company.",
    messages=[
        {"role": "user", "content": "Analyze this dataset: {{DATASET}}"}
    ]
)
```

**Role Prompting Tips:**
- Be specific: "data scientist specializing in customer insight analysis" > "data scientist"
- Experiment with roles to see different perspectives
- Match the role to your success criteria

### 6. Prefill Claude's Response

Guide output format by starting Claude's response.

**Use Cases:**
- Force specific output format (e.g., JSON)
- Skip preambles and explanations
- Maintain character in roleplay

```python
messages=[
    {"role": "user", "content": "Extract name, price, color as JSON: {{DESCRIPTION}}"},
    {"role": "assistant", "content": "{"}  # Forces JSON output
]
```

**For Roleplay/Character Consistency:**
```python
messages=[
    {"role": "user", "content": "What do you observe?"},
    {"role": "assistant", "content": "[Sherlock Holmes]"}  # Maintains character
]
```

**Note:** Prefilling cannot end with trailing whitespace.

### 7. Chain Complex Prompts

Break complex tasks into focused subtasks for better results.

**When to Chain:**
- Multi-step analysis
- Content creation pipelines (Research → Outline → Draft → Edit)
- Data processing (Extract → Transform → Analyze)
- Decision-making (Gather → List options → Analyze → Recommend)

**Chain Structure:**
1. Identify subtasks with clear objectives
2. Use XML tags to pass outputs between prompts
3. Each prompt has a single-task goal
4. Iterate based on performance

```markdown
# Prompt 1: Analysis
Review this SaaS contract for risks. Output findings in <risks> tags.
<contract>{{CONTRACT}}</contract>

# Prompt 2: Draft Response
Draft an email to the vendor based on this analysis.
<risks>{{RISKS_FROM_PROMPT_1}}</risks>

# Prompt 3: Review
Grade this email for tone, clarity, and professionalism.
<email>{{EMAIL_FROM_PROMPT_2}}</email>
```

**Self-Correction Chains:**
Have Claude review its own work to catch errors:
1. Generate content
2. Review for accuracy/completeness
3. Refine based on feedback
4. Re-review if needed

### 8. Long Context Tips

For documents over 20K tokens:

**Document Placement:**
- Put long documents at the TOP of your prompt
- Place your query and instructions at the BOTTOM
- This can improve response quality by up to 30%

**Structure Multiple Documents:**
```xml
<documents>
  <document index="1">
    <source>annual_report_2023.pdf</source>
    <document_content>
      {{ANNUAL_REPORT}}
    </document_content>
  </document>
  <document index="2">
    <source>competitor_analysis.xlsx</source>
    <document_content>
      {{COMPETITOR_ANALYSIS}}
    </document_content>
  </document>
</documents>

Analyze the annual report and competitor analysis. Identify strategic advantages.
```

**Ground Responses in Quotes:**
Ask Claude to quote relevant passages before analyzing:
```markdown
Find quotes from the documents relevant to the diagnosis. Place in <quotes> tags.
Then, based on these quotes, provide your analysis in <analysis> tags.
```

## Prompt Engineering vs. Fine-tuning

Prefer prompt engineering over fine-tuning because:

| Advantage | Why It Matters |
|-----------|----------------|
| Resource efficiency | No GPUs needed, just text input |
| Cost-effectiveness | Uses base model pricing |
| Model updates | Prompts work across versions |
| Time-saving | Instant results vs. hours/days |
| Minimal data | Works with few-shot or zero-shot |
| Flexibility | Rapid iteration and experimentation |
| Transparency | Human-readable, easy to debug |

## Quick Reference: Prompt Template

```markdown
# System (Role)
You are a [specific role with domain expertise].

# Context
<context>
[Background information, documents, data]
</context>

# Task
<instructions>
Your task is to [specific objective].

Steps:
1. [First step]
2. [Second step]
3. [Third step]

Constraints:
- [Constraint 1]
- [Constraint 2]
</instructions>

# Examples
<examples>
<example>
Input: [Sample input]
Output: [Expected output]
</example>
</examples>

# Output Format
<format>
[Specify exact format, structure, length]
</format>

# Input
<input>
{{USER_INPUT}}
</input>
```

## Debugging Prompts

When Claude's output isn't right:

1. **Isolate the problem** - Which step or requirement is failing?
2. **Add explicit instructions** - Be more specific about what you want
3. **Add examples** - Show Claude exactly what good output looks like
4. **Try chain of thought** - Let Claude reason through the problem
5. **Chain prompts** - Break into smaller, focused tasks
6. **Check context placement** - For long docs, put data at top, query at bottom

## Resources

- [Anthropic Prompt Engineering Guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview)
- [Interactive Tutorial (GitHub)](https://github.com/anthropics/prompt-eng-interactive-tutorial)
- [Interactive Tutorial (Google Sheets)](https://docs.google.com/spreadsheets/d/19jzLgRruG9kjUQNKtCg1ZjdD6l6weA6qRXG5zLIAhC8)
- [Prompt Library](https://docs.anthropic.com/en/resources/prompt-library)
