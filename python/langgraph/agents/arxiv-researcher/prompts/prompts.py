HIGH_LEVEL_SUMMARY_PROMPT = """
You are a specialist in creating concise, high-level summaries of academic papers.

Given the following paper content, write a concise 4-5 sentence high-level summary that captures:
- The paper's core contribution and main findings
- The significance and impact of the work
- Why this research matters in the broader context

Focus on the big picture and key takeaways that would be most valuable to a general academic audience.

Paper content:
{paper_text}
"""

DETAILED_SUMMARY_PROMPT = """
You are a specialist in creating comprehensive technical summaries of academic papers.

Given the following paper content, write a detailed technical summary that includes:
- The methodology and technical approach used
- Key experiments, datasets, and evaluation metrics
- Main results and findings with specific details
- Strengths and limitations of the approach
- Comparison with related work (if mentioned)
- Significance and potential impact in the field
- Future directions suggested by the authors

Provide sufficient technical depth for researchers and practitioners in the field.

Paper content:
{paper_text}
"""

APPLICATION_PROMPT = """
You are a specialist in identifying and describing real-world applications of academic research.

Given the following paper content, describe concrete real-world applications including:
- Current industry applications or use cases where this research could be applied
- Potential future applications and emerging opportunities  
- Specific domains, sectors, or industries that could benefit
- Practical implementation considerations and challenges
- How this research could solve real problems or create value

Focus on bridging the gap between academic research and practical implementation.

Paper content:
{paper_text}
"""
