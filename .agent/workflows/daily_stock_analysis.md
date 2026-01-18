---
description: Daily stock analysis using Agent AI capabilities
---

# Daily Stock Analysis Workflow

This workflow automates the complete stock analysis pipeline using local Agent capabilities instead of external API calls.

## Prerequisites
- Python script must have completed stock selection and saved task files
- Task files location: `results/YYYYMMDD/agent_tasks/`

## Steps

### 1. Read Analysis Task
Read the stock analysis task file and generate response:
```
📂 Task File: results/YYYYMMDD/agent_tasks/task_analysis.txt
```

After reading the task file, **generate a comprehensive stock analysis response** following the exact requirements in the task prompt.

Save your response to:
```
📝 Output: results/YYYYMMDD/agent_outputs/result_analysis.txt
```

### 2. Read Xiaohongshu Task
Read the social media content task file:
```
📂 Task File: results/YYYYMMDD/agent_tasks/task_xiaohongshu.txt
```

After reading the task file, **generate social media content** following all formatting requirements specified in the task prompt (emoji usage, 2-line format per stock, desensitization rules, etc.).

Save your response to:
```
📝 Output: results/YYYYMMDD/agent_outputs/result_xiaohongshu.txt
```

### 3. Read Image Prompt Task
Read the image generation prompt task file:
```
📂 Task File: results/YYYYMMDD/agent_tasks/task_image_prompt.txt
```

After reading the task file, **generate an English image generation prompt** following all specifications in the task (vertical 10:16 layout, desensitization, dynamic mascot, hand-drawn sketch style, tomorrow's trading strategy in footer, etc.).

Save your response to:
```
📝 Output: results/YYYYMMDD/agent_outputs/result_image_prompt.txt
```

### 4. Generate and Save Stock Analysis Poster
After completing step 3, **generate the actual image** using the prompt from `result_image_prompt.txt`.

Read the prompt:
```bash
cat results/YYYYMMDD/agent_outputs/result_image_prompt.txt
```

Generate the image using the `generate_image` tool with the exact prompt content.

Save the generated image to:
```
📁 Output: results/YYYYMMDD/agent_outputs/stock_poster.png
```

**Important Notes:**
- Use 10:16 aspect ratio (vertical)
- Ensure hand-drawn sketch style
- Include all desensitized stock names and codes
- Add tomorrow's trading strategy in footer if available

### 4. Completion
After all three tasks are completed, the Python script will automatically detect the output files and continue execution to generate the final reports.

## Important Notes
- Replace `YYYYMMDD` with today's date (e.g., `20260118`)
- Each task file contains the complete prompt with all requirements
- Follow the prompts **exactly** as specified - they contain detailed formatting rules
- The Agent's responses should maintain the same quality and structure as the original Gemini API outputs
