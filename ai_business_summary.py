import streamlit as st


def build_summary_prompt(summary_df):

    summary_text = summary_df.to_string(index=False)

    prompt = f"""
You are a business analyst.

Below is the aspect sentiment summary.

{summary_text}

Generate:

1. Executive Summary
2. Biggest Strength
3. Biggest Weakness
4. Top 3 Recommendations
5. Immediate Action Items

Maximum 200 words.
"""
    
    return prompt

def generate_ai_summary(client, summary_df):

    if client is None:
        return None

    prompt = build_summary_prompt(summary_df)

    try:

        response = client.chat.completions.create(

            model="gpt-4o-mini",

            messages=[
                {
                    "role":"system",
                    "content":"You are an expert business analyst."
                },
                {
                    "role":"user",
                    "content":prompt
                }
            ],

            temperature=0.2,

            max_tokens=350
        )

        return response.choices[0].message.content

    except Exception as e:

        return f"AI Summary unavailable.\n\n{e}"