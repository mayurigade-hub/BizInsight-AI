import os
import uuid
import re
import requests
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()

import streamlit as st
st.set_page_config(page_title="BizInsight AI", layout="wide")

from sklearn.feature_extraction.text import CountVectorizer
from alerts import compute_alerts
from database import insert_feedback, fetch_feedback, clear_data
from openai import OpenAI
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ---------- API Key ----------
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    st.warning("OPENROUTER_API_KEY not found. AI features will be disabled.")
    client = None
else:
    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

vader_analyzer = SentimentIntensityAnalyzer()

st.title("📊 BizInsight AI")
st.caption("AI-powered customer intelligence platform for business growth")

tabs = st.tabs([
    "📊 Dashboard",
    "🤖 AI Assistant",
    "📂 Data Upload",
    "⚠️ Alerts",
    "⚙ Controls",
    "🧠 Chatbot",
])

# ---------- Helper functions ----------
def get_sentiment(text):
    """VADER sentiment compound score."""
    return vader_analyzer.polarity_scores(text)['compound']

def clean_text_for_sentiment(text):
    """Minimal cleaning for sentiment (lowercase, remove digits, #, extra spaces)."""
    text = text.lower()
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'#', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def ask_ai(question, reviews):
    """Legacy AI Assistant – uses first 40 reviews."""
    if client is None:
        return "API key missing."

    context = "\n".join(reviews[:40])
    prompt = f"""You are a business intelligence assistant.

Customer reviews:
{context}

    Question:
    {question}
    """

    try:
        response = client.chat.completions.create(
            model="tngtech/deepseek-r1t2-chimera:free",
            messages=[
                {
                    "role": "system",
                    "content": "You provide business intelligence insights."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.4
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating AI response: {str(e)}"

# ================= DATA UPLOAD =================
with tabs[2]:
    st.subheader("📂 Upload Customer Reviews")
    uploaded_file = st.file_uploader(
        "Upload CSV with review column",
        type="csv",
        key="csv_uploader",
    )

    if uploaded_file:
        if st.button("Process and Upload Data"):
            clear_data()
            # Read CSV (try UTF-8, fallback to latin1)
            try:
                df = pd.read_csv(uploaded_file)
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding='latin1')

            df = df.dropna(subset=['review'])
            df['review'] = df['review'].astype(str)

            st.dataframe(df, use_container_width=True)

            original_reviews = df["review"].tolist()
            cleaned_reviews = [clean_text_for_sentiment(t) for t in original_reviews]
            sentiments = [get_sentiment(t) for t in cleaned_reviews]

            # Insert into SQLite
            for orig, clean, sent in zip(original_reviews, cleaned_reviews, sentiments):
                insert_feedback(orig, clean, sent)

            st.success(f"✅ Added {len(original_reviews)} reviews to SQLite.")

            # Sync ChromaDB (send original reviews)
            with st.spinner("Syncing to vector database..."):
                try:
                    docs = [{"page_content": orig, "metadata": {"sentiment": sent}}
                            for orig, sent in zip(original_reviews, sentiments)]
                    resp = requests.post("http://localhost:8001/sync", json={"documents": docs})
                    if resp.status_code == 200:
                        st.success("Vector database updated! RAG chatbot ready.")
                    else:
                        st.error(f"Sync failed: {resp.text}")
                except Exception as e:
                    st.error(f"Cannot connect to RAG API: {e}")
                    st.info("Start FastAPI server: python run_chatbot_api.py")

# ================= FETCH DATA =================
data = fetch_feedback()

if data:
    # DataFrame columns: original_review, cleaned_review, sentiment, date
    df = pd.DataFrame(data, columns=["original_review", "cleaned_review", "sentiment", "date"])
    df["date"] = pd.to_datetime(df["date"])

    positive = (df["sentiment"] > 0).sum()
    negative = (df["sentiment"] < 0).sum()
    neutral = (df["sentiment"] == 0).sum()
    total = len(df)

    pos_pct = round(positive / total * 100, 2)
    neg_pct = round(negative / total * 100, 2)
    neu_pct = round(neutral / total * 100, 2)

    trend = df.groupby(df["date"].dt.date)["sentiment"].mean()

    # Keyword extraction on cleaned reviews
    reviews_clean = df["cleaned_review"].dropna()
    if reviews_clean.empty:
        keywords = []
        freq = []
    else:
        vectorizer = CountVectorizer(stop_words="english", max_features=10)
        X = vectorizer.fit_transform(reviews_clean)
        keywords = vectorizer.get_feature_names_out()
        freq = X.toarray().sum(axis=0)

    keyword_df = pd.DataFrame({"Keyword": keywords, "Frequency": freq})

    # ================= DASHBOARD =================
    with tabs[0]:
        st.subheader("📈 Business Health Overview")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Reviews", total)
        c2.metric("Positive %", f"{pos_pct}%")
        c3.metric("Negative %", f"{neg_pct}%")
        c4.metric("Neutral %", f"{neu_pct}%")

        st.markdown("---")
        st.subheader("🔍 Smart Complaint Clustering")

        if st.button("Find Complaint Clusters"):
            negative_reviews = df[df["sentiment"] < 0]["cleaned_review"].tolist()
            if len(negative_reviews) < 10:
                st.warning(f"Only {len(negative_reviews)} negative reviews. Need at least 10.")
            else:
                try:
                    from clustering.run_clustering import run_pipeline
                    from clustering.vectorize import load_model

                    embedding_model = load_model()
                except ModuleNotFoundError as e:
                    st.error(f"Clustering dependency missing: {e.name}")
                    st.info(
                        "Install the clustering dependencies with: "
                        "pip install -r requirements.txt"
                    )
                    st.stop()

                with st.spinner("Clustering negative reviews..."):
                    result = run_pipeline(
                        negative_reviews,
                        embedding_model,
                        min_topic_size=25,
                        similarity_threshold=0.4,
                        verbose=True
                    )
                    if result["success"]:
                        st.success(
                            f"✅ Found {result['n_clusters']} clusters from "
                            f"{result['total_negative_reviews']} reviews"
                        )
                        for cluster in result["clusters"]:
                            title = (
                                f"📌 {cluster['name']} "
                                f"({cluster['percentage']:.1f}%) - "
                                f"{cluster['count']} reviews"
                            )
                            with st.expander(title):
                                st.write("**Example reviews:**")
                                for ex in cluster.get('example_reviews', [])[:3]:
                                    st.write(f"- \"{ex}\"")
                    else:
                        st.error(result["message"])

        st.markdown("---")
        col1, col2 = st.columns([2,1])
        with col1:
            st.subheader("Customer Satisfaction Trend")
            st.area_chart(trend)
        with col2:
            fig, ax = plt.subplots()
            ax.pie(
                [positive, negative, neutral],
                labels=["Positive", "Negative", "Neutral"],
                autopct="%1.1f%%",
            )
            st.pyplot(fig)
            plt.close(fig)

        st.subheader("📊 Sentiment Distribution")
        fig2, ax2 = plt.subplots()
        ax2.hist(df["sentiment"], bins=20)
        ax2.set_xlabel("Sentiment Score")
        ax2.set_ylabel("Frequency")
        st.pyplot(fig2)
        plt.close(fig2)

        st.markdown("---")
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Feedback CSV",
            data=csv,
            file_name="feedback.csv",
            mime="text/csv",
        )

        st.subheader("Top Keywords")
        st.dataframe(keyword_df, use_container_width=True)

    # ================= AI ASSISTANT =================
    with tabs[1]:
        st.subheader("🤖 AI Business Consultant")
        user_q = st.text_input("Ask a business question", key="ai_q")
        if user_q and st.button("Get Insight"):
            if client:
                with st.spinner("Analyzing..."):
                    answer = ask_ai(user_q, df["original_review"].tolist())
                    st.success(answer)
            else:
                st.warning("API key missing.")

    # ================= ALERTS =================
    with tabs[3]:
        st.subheader("⚠️ Trend Alert & Risk Detection")
        st.caption("Computed over the last 7 days vs the prior 7-day baseline.")

        alert = compute_alerts()

        if alert["insufficient_data"]:
            st.warning(
                f"⚠️ Only **{alert['recent_count']}** review(s) in the last 7 days. "
                "Need at least 5 for reliable alerts. Results may be misleading."
            )

        if alert["risk_level"] == 2:
            st.error(
                f"🔴 **HIGH RISK** — {alert['recent_negative_pct']}% of recent "
                "reviews are negative. "
                "Immediate attention required."
            )
        elif alert["risk_level"] == 1:
            st.warning(
                f"🟡 **MEDIUM RISK** — {alert['recent_negative_pct']}% of recent "
                "reviews are negative."
            )
        else:
            st.success(
                f"🟢 **LOW RISK** — Sentiment is stable. "
                f"{alert['recent_negative_pct']}% negative in the last 7 days."
            )

        st.markdown("---")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Risk Score", alert["risk_score"])
        m2.metric(
            "Recent Negative %",
            f"{alert['recent_negative_pct']}%",
            delta=f"{alert['spike_delta']:+.1f}% vs prior week",
            delta_color="inverse",
        )
        m3.metric("Reviews (last 7d)", alert["recent_count"])
        m4.metric("Spike Detected", "Yes" if alert["spike_detected"] else "No")

        st.markdown("---")

        st.subheader("🔑 Top Risk Keywords (from negative reviews)")
        if alert["top_risk_keywords"]:
            keyword_cols = st.columns(4)
            for i, kw in enumerate(alert["top_risk_keywords"]):
                keyword_cols[i % 4].markdown(
                    f"<span style='background:#ff4b4b22;padding:4px 10px;"
                    f"border-radius:6px;color:#ff4b4b;font-weight:600'>{kw}</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("No recurring negative keywords found in the last 7 days.")

        st.markdown("---")

        with st.expander("📊 How is this calculated?"):
            st.markdown(f"""
| Metric | Value |
|---|---|
| Recent window | Last 7 days |
| Baseline window | Prior 7 days |
| Recent negative % | `{alert['recent_negative_pct']}%` |
| Baseline negative % | `{alert['baseline_negative_pct']}%` |
| Delta (spike) | `{alert['spike_delta']:+.1f}%` |
| Spike threshold | `+15%` change triggers spike flag |
| High risk threshold | `>= 60%` negative OR `+30%` delta |
| Medium risk threshold | `>= 40%` negative OR `+15%` delta |
            """)

    # ================= CONTROLS =================
    with tabs[4]:
        st.subheader("⚙ System Controls")
        if st.button("🗑 Clear all data"):
            clear_data()
            st.success("All data cleared. Refresh the page.")
            st.rerun()
        st.warning("This action is permanent.")

    # ================= RAG CHATBOT =================
    with tabs[5]:
        st.subheader("🧠 RAG Chatbot – Ask your reviews")
        if "session_id" not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        if "rag_messages" not in st.session_state:
            st.session_state.rag_messages = []

        if st.button("🗑️ New Conversation"):
            st.session_state.rag_messages = []
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()

        for msg in st.session_state.rag_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if "sources" in msg:
                    with st.expander("See source reviews"):
                        for src in msg["sources"]:
                            st.write(f"- {src[:200]}...")

        user_q = st.chat_input("Ask a question about your reviews...")
        if user_q:
            st.session_state.rag_messages.append({"role": "user", "content": user_q})
            with st.chat_message("user"):
                st.write(user_q)

            with st.chat_message("assistant"):
                with st.spinner("Searching and generating..."):
                    try:
                        resp = requests.post(
                            "http://localhost:8001/chat",
                            json={
                                "question": user_q,
                                "use_memory": True,
                                "session_id": st.session_state.session_id,
                            },
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            answer = data["answer"]
                            sources = data["sources"]
                            st.write(answer)
                            with st.expander("📚 Source reviews"):
                                for src in sources:
                                    st.write(f"- {src}")
                            st.session_state.rag_messages.append({
                                "role": "assistant",
                                "content": answer,
                                "sources": sources,
                            })
                        else:
                            st.error(f"API error: {resp.status_code}")
                    except Exception as e:
                        st.error(f"Cannot connect to RAG API: {e}")
                        st.info("Start FastAPI server: python run_chatbot_api.py")

else:
    st.info("Upload a CSV to start.")
