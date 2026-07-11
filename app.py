import os
from dotenv import load_dotenv
load_dotenv()
import logging
import hashlib
import uuid
import re
import requests
import pandas as pd
import matplotlib.pyplot as plt
from forecasting import forecast_sentiment
from email_alerts import send_negative_alert
from aspect_extractor import extract_aspects
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

from pdf_generator import generate_report_pdf

import streamlit as st
st.set_page_config(page_title="BizInsight AI", layout="wide")
from sklearn.feature_extraction.text import CountVectorizer
from textblob import TextBlob
from openai import (
    OpenAI,
    AuthenticationError,
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    APIError,
)
from sentiment import analyze
# ---------- Chimera AI Client ----------
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime


from database import (
    initialize_database,
    insert_feedback_bulk,
    fetch_feedback,
    fetch_all_feedback,
    fetch_all_users,
    get_workspace_feedback,
    insert_feedback_bulk_with_aspects, #new
    fetch_aspect_sentiment,  #new
    clear_data,
    delete_user,
    no_users_exist
)
from auth import is_logged_in, get_current_user, logout, show_auth_page, show_setup_wizard
from dashboard_aspects import render_aspect_dashboard
from model_manager import aspect_model
from ai_dashboard import render_ai_dashboard

# ---------- Chimera AI Client ----------

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    st.warning("OPENROUTER_API_KEY not found. AI Assistant features will be disabled.")
    client = None
else:
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )

st.title("📊 BizInsight AI")
st.caption("AI-powered customer intelligence platform for business growth")
st.sidebar.header("🤖 AI Settings")

engine = st.sidebar.radio(
    "Aspect Analysis Engine",
    [
        "Rule-Based",
        "AI"
    ]
)

aspect_model.set_engine(engine)

if "data_cleared" in st.session_state:
    st.success("All data removed successfully.")
    del st.session_state.data_cleared
if "messages" not in st.session_state:
    st.session_state.messages=[]

tabs = st.tabs(["📊 Dashboard", "🤖 AI Assistant", "📂 Data Upload", "⚙ Controls"])


# ================= FUNCTIONS =================

if no_users_exist():
    show_setup_wizard()
    st.stop()

if not is_logged_in():
    show_auth_page()
    st.stop()
# --- Email Alert State ---
current_user = get_current_user()

if "alert_email" not in st.session_state:
    st.session_state.alert_email = (
        current_user.get("email", "") if current_user else ""
    )


# ─── OpenAI Client ───────────────────────────────────────────────────────────


def get_sentiment(text):
    return TextBlob(text).sentiment.polarity


def _extract_message_content(message):
    """
    Safely extract the text content from a chat completion message,
    regardless of whether the SDK returns an object (e.g. the modern
    OpenAI SDK's ChatCompletionMessage, which has no .get()) or a
    plain dict (older/alternate SDK responses).
    """
    # Preferred path: attribute access, as used by current OpenAI SDKs.
    content = getattr(message, "content", None)

    # Fallback for dict-like responses (e.g. some proxy/gateway APIs
    # that return raw JSON instead of typed objects).
    if content is None and isinstance(message, dict):
        content = message.get("content")

    return content or ""


def ask_ai(question, reviews:list):
    if client is None:
        return "AI features are disabled because API key is missing."

    # Build a concise prompt focusing on the reviews
    reviews_text = "\n".join(map(str, reviews[:200]))  # limit size
    messages = [
        {"role": "system", "content": "You are a concise business insights assistant. Answer only using the provided reviews."},
        {"role": "user", "content": f"Customer Reviews:\n{reviews_text}\n\nQuestion:\n{question}\n\nProvide concise, actionable insights."}
    ]

    try:
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            max_tokens=512,
            temperature=0.2
        )

        # response structure may vary; try to extract content safely
        if hasattr(resp, "choices") and len(resp.choices) > 0:
            content = _extract_message_content(resp.choices[0].message)
            return content if content else "The assistant did not return a response."
        # fallback
        return str(resp)

    except Exception as e:
        logger.error("AI request failed: %s", e)
        return f"AI request failed: {e}"

# ================= AI ASSISTANT =================

with tabs[1]:

    st.subheader("🤖 AI Business Assistant")

    # Show previous messages

    for message in st.session_state.messages:

        with st.chat_message(message["role"]):
            st.write(message["content"])
    st.empty()

    # Chat input at bottom

    question = st.chat_input(
        "Ask business insights question"
    )
    st.components.v1.html(
    """
    <script>
        const input = parent.document.querySelector('textarea');
        if (input) {
            input.focus();
        }
    </script>
    """,
    height=0,
)


    if question:
        with st.chat_message("user"):
            st.write(question)

        # Save user message
        st.session_state.messages.append(
            {
                "role": "user",
                "content": question
            }
        )

        if client is None:
            st.warning("AI features unavailable because API key is missing.")

        else:

            if current_user["workspace_type"] == "corporate":
                data = get_workspace_feedback(current_user["workspace_id"])
            else:
                data = fetch_feedback(user_id=current_user["id"])
            
            if not data:
                st.warning("No feedback data available.")

            else:

                df_ai = pd.DataFrame(
                    data,
                    columns=["review", "sentiment", "date"]
                )

                answer = ask_ai(question, df_ai["review"].astype(str).tolist())

                with st.chat_message("assistant"):
                    st.write(answer)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer
                    }
                )

# ================= DATA UPLOAD =================

with tabs[2]:

    st.subheader("📂 Upload Customer Reviews")

    uploaded_file = st.file_uploader(
        "Upload CSV with review column",
        type="csv"
    )

    if uploaded_file:

        file_hash = hashlib.md5(uploaded_file.read()).hexdigest()
        uploaded_file.seek(0)

        df = None
        encodings_to_try = ['utf-8', 'utf-16', 'latin1', 'cp1252']

        for encoding in encodings_to_try:
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding=encoding)
                break
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue

        if df is None:
            st.error("Unable to read CSV file. Please ensure it is not corrupted and uses a standard encoding such as UTF-8 or Latin-1.")
        else:
            st.dataframe(df, use_container_width=True)

            missing_columns = []
            if "review" not in df.columns:
                missing_columns.append("review")
            if "date" not in df.columns:
                missing_columns.append("date")

            if missing_columns:
                for col in missing_columns:
                    st.error(f"CSV must contain a '{col}' column.")
                st.stop()

            df["date"] = pd.to_datetime(
                df["date"],
                dayfirst=True
            )
            st.dataframe(df, width='stretch')

            df = df.dropna(subset=["review"])
            df["review"] = df["review"].astype(str).str.strip()
            df = df[df["review"] != ""]

            if df.empty:
                st.warning("No valid reviews found after cleaning. Nothing to process.")
            else:
                with st.spinner("Analyzing reviews, please wait..."):
                    total = len(df)
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    sentiments = []
                    update_interval = max(1, total // 100)
                    for i, review in enumerate(df["review"]):
                        sentiments.append(get_sentiment(review))
                        if (i + 1) % update_interval == 0 or (i + 1) == total:
                            progress_bar.progress((i + 1) / total)
                            status_text.text(f"Processing review {i + 1} of {total}...")
#updated
                    df["sentiment"] = sentiments

                    # Compute per-aspect sentiment BEFORE saving, so it can be persisted
                    # alongside the review instead of being thrown away after this run.
                    df["aspects"] = df["review"].apply(extract_aspects)
                    from aspect_sentiment import analyze_aspect_sentiment
                    df["aspect_sentiment"] = df["review"].apply(
                        aspect_model.analyze
                    )

                    reviews_data = list(
                        zip(df["review"], df["sentiment"], df["aspect_sentiment"])
                    )

                    if st.session_state.get("last_upload_hash") != file_hash:
                        insert_feedback_bulk_with_aspects(
                            reviews_data, user_id=current_user["id"]
                        )
                        st.session_state["last_upload_hash"] = file_hash
                        st.success(f"✅ {total} reviews analyzed and saved successfully!")
                    else:
                        st.success(f"✅ {total} reviews analyzed successfully!")

                progress_bar.empty()
                status_text.empty()

                with st.expander("Aspect-wise Sentiment"):

                    preview_df = df[
                        ["review", "aspect_sentiment"]
                    ].copy()

                    st.dataframe(
                        preview_df,
                        use_container_width=True
                )
                with st.expander("Detected Aspects"):
                    preview_df = df[["review", "aspects"]].copy()
                    st.dataframe(preview_df, use_container_width=True)

                new_negative_percent = round((df[df["sentiment"] < 0].shape[0] / df.shape[0]) * 100, 2)
                if new_negative_percent > 30:
                    subject = "BizInsight AI Alert: Negative Sentiment Spike Detected"
                    body = (
                        f"Hello,\n\nA recent data upload has shown a significant spike in negative sentiment.\n\n"
                        f"Negative Sentiment in new batch: {new_negative_percent}%\n\n"
                        f"Please log in to the BizInsight AI dashboard to analyze the feedback and take appropriate action.\n\n"
                        f"Regards,\nThe BizInsight AI Team"
                    )
                    send_negative_alert(st.session_state.alert_email, subject, body)

if current_user["workspace_type"] == "corporate":

    data = get_workspace_feedback(
        current_user["workspace_id"]
    )

else:

    data = fetch_feedback(
        user_id=current_user["id"]
    )

df = pd.DataFrame(data, columns=["review", "sentiment", "date"])

from aspect_extractor import extract_aspects
from aspect_sentiment import analyze_aspect_sentiment

df["aspects"] = df["review"].apply(extract_aspects)
df["aspect_sentiment"] = df["review"].apply(
    aspect_model.analyze
)

if not df.empty:

    df["date"] = pd.to_datetime(
        df["date"],
        dayfirst=True
    )

    positive = (df["sentiment"] > 0.1).sum()
    neutral = ((df["sentiment"] >= -0.1) & (df["sentiment"] <= 0.1)).sum()
    negative = (df["sentiment"] < -0.1).sum()
    total_reviews = len(df)

    # Percentages


    # These are now safe from ZeroDivisionError because total_reviews > 0

    positive_percent = round((positive / total_reviews) * 100, 2)
    negative_percent = round((negative / total_reviews) * 100, 2)
    neutral_percent = round((neutral / total_reviews) * 100, 2)

    # Trend

    # Existing sentiment trend
    trend = df.groupby(df["date"].dt.date)["sentiment"].mean()

    # Keyword Extraction

    # Keywords

    # =========================================
    # NEGATIVE REVIEW SPIKE DETECTION
    # =========================================

    # Only negative reviews
    negative_df = df[df["sentiment"] < 0]

    # Daily negative review counts
    negative_trend = (
        negative_df
        .groupby(negative_df["date"].dt.date)
        .size()
    )

    # Rolling statistics
    rolling_mean = negative_trend.rolling(window=3).mean()

    rolling_std = negative_trend.rolling(window=3).std()

    # Threshold-based anomaly detection
    
    anomalies = negative_trend[
        negative_trend > (rolling_mean + rolling_std)
    ]

    # =========================================


    reviews = df["review"].dropna()

    if reviews.empty or (
        reviews.apply(lambda x: isinstance(x, str)).all()
        and reviews.str.strip().eq("").all()
    ):
        keywords = []
        keyword_counts = []

    else:




        vectorizer = CountVectorizer(
            stop_words="english",
            max_features=10
        )

        try:

            X = vectorizer.fit_transform(reviews)

            keywords = vectorizer.get_feature_names_out()

            keyword_counts = X.toarray().sum(axis=0)


        except ValueError as e:

            if "empty vocabulary" in str(e).lower():
                keywords = []
                keyword_counts = []

            else:
                raise

    # ================= DASHBOARD =================

    with tabs[0]:

        st.subheader("📈 Business Health Overview")



        if not anomalies.empty:
            st.error(
                f"⚠️ {len(anomalies)} negative sentiment spike(s) detected!"
            )

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Reviews", len(df))
        c2.metric("Positive", positive)
        c3.metric("Negative", negative)

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Total Reviews", total_reviews)
        c2.metric("Positive %", f"{positive_percent}%")
        c3.metric("Negative %", f"{negative_percent}%")
        c4.metric("Neutral %", f"{neutral_percent}%")

        st.markdown("---")

        # ASPECT-BASED SENTIMENT 
        st.subheader("🔍 Sentiment by Aspect")

        aspect_rows = fetch_aspect_sentiment(current_user["id"])

        if not aspect_rows:
            st.info("No aspect-level data yet. Upload reviews to see this breakdown.")
        else:
            aspect_df = pd.DataFrame(
                aspect_rows, columns=["aspect", "sentiment", "count"]
            )
            pivot = (
                aspect_df
                .pivot(index="aspect", columns="sentiment", values="count")
                .fillna(0)
            )
            for col in ["Positive", "Neutral", "Negative"]:
                if col not in pivot.columns:
                    pivot[col] = 0
            pivot = pivot[["Positive", "Neutral", "Negative"]]

            fig, ax = plt.subplots()
            pivot.plot(
                kind="bar",
                stacked=True,
                ax=ax,
                color={"Positive": "#2ecc71", "Neutral": "#95a5a6", "Negative": "#e74c3c"},
            )
            ax.set_ylabel("Number of Reviews")
            ax.set_xlabel("Aspect")
            ax.legend(title="Sentiment")
            st.pyplot(fig)

            st.dataframe(pivot, use_container_width=True)

        st.markdown("---")

        # Trend Chart


        col1, col2 = st.columns([2,1])

        with col1:

            st.subheader("Customer Satisfaction Trend")
            st.area_chart(trend)

        with col2:



            fig3, ax3 = plt.subplots(figsize=(3.2, 3.2))

            ax3.pie(
                [positive, negative, neutral],
                labels=["Positive", "Negative", "Neutral"],
                autopct="%1.1f%%"
            )

            st.pyplot(fig3)
            plt.close(fig3)

            st.markdown("---")

        # Histogram

        st.subheader("📊 Sentiment Score Distribution")

        col_small, _ = st.columns([1.5, 4])

        with col_small:
            fig2, ax2 = plt.subplots(figsize=(2.8, 2.1))
            try:
                ax2.hist(df["sentiment"], bins=10)
                
                ax2.set_xlabel("Score", fontsize=8)
                
                ax2.set_ylabel("Freq", fontsize=8)
                
                ax2.tick_params(axis='both', labelsize=7)
                
                st.pyplot(fig2)
            finally:
                # Ensure matplotlib resources are always released
                plt.close(fig2)

        st.subheader("📊 Sentiment Distribution")
        fig2, ax2 = plt.subplots()
        ax2.hist(df["sentiment"], bins=20)
        ax2.set_xlabel("Sentiment Score")
        ax2.set_ylabel("Frequency")
        st.pyplot(fig2)
        plt.close(fig2)

        with col1:
            st.subheader("Negative Review Spike Detection")
            
            fig2, ax2 = plt.subplots(figsize=(10,4))
            
            # Main negative trend line
            ax2.plot(
                negative_trend.index,
                negative_trend.values,
                marker="o"
            )
            
            # Highlight anomalies
            ax2.scatter(
                anomalies.index,
                anomalies.values,
                color="red",
                s=220,
                marker="X",
                label="Anomaly"
            )
            
            ax2.legend()
            
            ax2.set_xlabel("Date")
            ax2.set_ylabel("Negative Reviews")
            ax2.set_title("Anomaly Detection in Negative Reviews")
            
            st.pyplot(fig2)

        col_small, _ = st.columns([1.5, 4])

        with col_small:

            fig2, ax2 = plt.subplots(figsize=(2.8, 2.1))

            ax2.hist(df["sentiment"], bins=10)

            ax2.set_xlabel("Score", fontsize=8)
            ax2.set_ylabel("Freq", fontsize=8)

            ax2.tick_params(axis='both', labelsize=7)

            st.pyplot(fig2)
            plt.close(fig2)

        # ==========================================
        # Aspect Dashboard
        # ==========================================

        from aspect_extractor import extract_aspects
        from aspect_sentiment import analyze_aspect_sentiment

        df["aspects"] = df["review"].apply(extract_aspects)
        df["aspect_sentiment"] = df["review"].apply(
            aspect_model.analyze
        )

        render_aspect_dashboard(df, client)
        if aspect_model.engine == "AI":
            st.markdown("---")

            render_ai_dashboard(df)

        st.markdown("---")
        st.markdown("---")
        st.subheader("📈 Future Sentiment Forecast")

        forecast_days = st.selectbox(
            "Select Forecast Horizon",
            [7, 14, 30]
        )

        try:

            forecast_df, synthetic_history = forecast_sentiment(
                df,
                forecast_days
            )

            st.line_chart(
                forecast_df.set_index("date")
            )

            if synthetic_history:
                st.warning(
                    "All reviews share the same date. The forecast history was generated synthetically "
                    "to support the model, so results may not reflect actual time-series behavior."
                )

            current_sentiment = round(
                df["sentiment"].mean(),
                3
            )

            future_sentiment = round(
                forecast_df["predicted_sentiment"].mean(),
                3
            )

            col1, col2 = st.columns(2)

            col1.metric(
                "Current Avg Sentiment",
                current_sentiment
            )

            col2.metric(
                f"{forecast_days}-Day Forecast",
                future_sentiment,
                round(
                    future_sentiment - current_sentiment,
                    3
                )
            )

            if future_sentiment < -0.2:
                st.error(
                    "⚠️ Forecast suggests future customer dissatisfaction."
                )

            elif future_sentiment > 0.2:
                st.success(
                    "✅ Forecast suggests improving customer sentiment."
                )

            else:
                st.info(
                    "ℹ️ Forecast suggests stable customer sentiment."
                )

        except ValueError as e:
            st.warning(str(e))
        
        pdf_file = generate_report_pdf(
            df,
            trend,
            list(keywords)
        )
        st.download_button("Download PDF Report", pdf_file, file_name="report.pdf", mime="application/pdf")

        col_small, _ = st.columns([1.5, 4])

        with col_small:

            fig2, ax2 = plt.subplots(figsize=(2.8, 2.1))

            ax2.hist(df["sentiment"], bins=10)

            ax2.set_xlabel("Score", fontsize=8)
            ax2.set_ylabel("Freq", fontsize=8)

            ax2.tick_params(axis='both', labelsize=7)

            st.pyplot(fig2)

        # Keywords

        st.markdown("---")

        # Keywords

        st.subheader("Top Customer Issues / Keywords")



    # ================= DYNAMIC KEYWORD EXTRACTION & FILTERING =================
        col_filter, _ = st.columns([1, 3])
        with col_filter:
            sentiment_filter = st.selectbox(
                "Select Sentiment Category for Keywords",
                ["All Reviews", "Positive Reviews", "Neutral Reviews", "Negative Reviews"]
            )

        # Filter the dataframe dynamically based on selection
        if sentiment_filter == "Positive Reviews":
            filtered_df = df[df["sentiment"] > 0.1]
        elif sentiment_filter == "Negative Reviews":
            filtered_df = df[df["sentiment"] < -0.1]
        elif sentiment_filter == "Neutral Reviews":
            filtered_df = df[(df["sentiment"] >= -0.1) & (df["sentiment"] <= 0.1)]
        else:
            filtered_df = df.copy()

        reviews = filtered_df["review"].dropna()

        if reviews.empty or reviews.str.strip().eq("").all():
            keywords = []
            keyword_counts = []

        else:
            vectorizer = CountVectorizer(stop_words="english", max_features=10)

            try:
                X = vectorizer.fit_transform(reviews)
                keywords = vectorizer.get_feature_names_out()
                keyword_counts = X.toarray().sum(axis=0)
            except ValueError as e:
                if "empty vocabulary" in str(e).lower():
                    keywords = []
                    keyword_counts = []
                else:
                    raise

        keyword_df = pd.DataFrame({"Keyword": keywords, "Frequency": keyword_counts}).sort_values(by="Frequency", ascending=False).reset_index(drop=True)
        # Sort by frequency, but keep the numbering intact regardless of its position in the dataframe
    
        st.dataframe(keyword_df, use_container_width=True)


    # ================= CONTROLS =================

    with tabs[3]:


        st.subheader("⚙ System Controls")
        
        st.markdown("---")
        st.subheader("📧 Email Alerts")
        st.session_state.alert_email = st.text_input(
            "Recipient email for alerts",
            value=st.session_state.alert_email,
            placeholder="Enter your email to receive alerts"
        )
        st.info("Alerts for negative sentiment spikes will be sent to this email.")
        st.markdown("---")

        st.warning("⚠️ Clearing data permanently deletes all your stored reviews. This cannot be undone.")

        if "confirm_clear" not in st.session_state:
            st.session_state["confirm_clear"] = False

        if not st.session_state["confirm_clear"]:
            if st.button("🗑️ Clear my feedback data"):
                st.session_state["confirm_clear"] = True
                st.rerun()
        else:
            st.error("Are you sure? All your reviews will be permanently deleted.")
            col1, col2 = st.columns(2)
            if col1.button("✅ Yes, delete everything"):
                clear_data(user_id=current_user["id"])
                st.session_state["confirm_clear"] = False
                st.session_state.pop("last_upload_hash", None)
                st.success("All your data has been removed.")
                st.rerun()
            if col2.button("❌ Cancel"):
                st.session_state["confirm_clear"] = False
                st.rerun()