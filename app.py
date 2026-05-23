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
from database import insert_feedback, fetch_feedback, clear_data

from openai import OpenAI
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from clustering.run_clustering import run_pipeline
from clustering.vectorize import load_model

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise ValueError("OPENROUTER_API_KEY environment variable not set. Please create a .env file with your API key.")

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    st.warning("OPENROUTER_API_KEY not found. AI Assistant features will be disabled.")
    client = None
else:
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )

vader_analyzer = SentimentIntensityAnalyzer()

st.title("📊 BizInsight AI")
st.caption("AI-powered customer intelligence platform for business growth")

tabs = st.tabs(["📊 Dashboard", "🤖 AI Assistant", "📂 Data Upload", "⚙ Controls", "🧠 Chatbot"])

# ---------- Core Functions ----------
def get_sentiment(text):
    """Improved sentiment using VADER"""
    scores = vader_analyzer.polarity_scores(text)
    return scores['compound']

def clean_text_for_sentiment(text):
    text = text.lower()
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'#', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ================= AI ASSISTANT =================

    prompt = f"""
    You are a professional business analyst.

    Customer feedback:
    {context}

    Analyze patterns, root problems and give improvement suggestions.

    Question:
    {question}
    """

    response = client.chat.completions.create(
        model="google/gemma-2-9b-it:free", # Updated to a fast, reliable model
        messages=[
            {"role": "system", "content": "You provide business intelligence insights."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4
    )
    return response.choices[0].message.content

# ================= DATA UPLOAD =================
with tabs[2]:

    st.subheader("📂 Upload Customer Reviews")

    uploaded_file = st.file_uploader(
        "Upload CSV with review column",
        type="csv"
    )

    if uploaded_file:
        # CRITICAL FIX: We need to send the original reviews to the RAG API for vectorization, not the cleaned reviews, to preserve important details like ticket numbers or specific product mentions that might be lost in cleaning. 
        if st.button("Process and Upload Data"):
            clear_data()

            # We attempt to read the uploaded CSV file using UTF-8 encoding first, which is standard. However, if the file contains special characters or was saved with a different encoding (like Excel's default on Windows), it may fail to read. In that case, we catch the UnicodeDecodeError, reset the file pointer to the beginning of the file, and try reading it again using 'latin1' encoding.
            try:
                # Try standard UTF-8 first
                df = pd.read_csv(uploaded_file)
            except UnicodeDecodeError:
                # If it fails, reset the file pointer and try Excel/Windows encoding
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding='latin1')

            df = df.dropna(subset=['review'])  # Remove rows where the review is completely blank
            df['review'] = df['review'].astype(str)  # Force all remaining reviews to be text strings


            st.dataframe(df, width="stretch")

            # Prepare columns
            original_reviews = df["review"].tolist()
            cleaned_reviews = [clean_text_for_sentiment(text) for text in original_reviews]
            sentiments = [get_sentiment(cleaned) for cleaned in cleaned_reviews]

            # Insert into SQLite
            for orig, cleaned, sent in zip(original_reviews, cleaned_reviews, sentiments):
                insert_feedback(orig, cleaned, sent)

            st.success("Feedback successfully added to SQLite!")

            # Auto-sync vector DB via API
            with st.spinner("Syncing reviews to vector database..."):
                try:
                    # CRITICAL FIX: Send original_reviews to RAG so it doesn't lose numbers!
                    docs_to_sync = [
                        {"page_content": orig, "metadata": {"sentiment": sent}}
                        for orig, sent in zip(original_reviews, sentiments)
                    ]
                    
                    # We send a POST request to the /sync endpoint of our RAG API, passing the list of documents (original reviews with sentiment metadata) in the required format. The API will then add these documents to the ChromaDB vector store, making them available for retrieval during chat interactions. We also handle the API response to confirm that the syncing was successful or to display an error message if it failed.
                    response = requests.post(
                        "http://localhost:8001/sync",
                        json={"documents": docs_to_sync}
                    )
                    
                    if response.status_code == 200:
                        st.success("Vector database updated! RAG chatbot is ready.")
                    else:
                        st.error(f"API Error: {response.text}")
                        
                except Exception as e:
                    st.error(f"Failed to connect to RAG API: {e}")
                    st.info("Make sure your FastAPI server is running!")

# ================= LOAD STORED DATA =================

data = fetch_feedback()

if data:
    df = pd.DataFrame(data, columns=["original_review", "cleaned_review", "sentiment", "date"])
    df["date"] = pd.to_datetime(df["date"])

    # Sentiment Counts

    positive = (df["sentiment"] > 0).sum()
    negative = (df["sentiment"] < 0).sum()
    neutral = (df["sentiment"] == 0).sum()

    total_reviews = len(df)

    # Percentages

    positive_percent = round((positive / total_reviews) * 100, 2)
    negative_percent = round((negative / total_reviews) * 100, 2)
    neutral_percent = round((neutral / total_reviews) * 100, 2)

    # Trend

    trend = df.groupby(df["date"].dt.date)["sentiment"].mean()

    vectorizer = CountVectorizer(stop_words="english", max_features=10)
    X = vectorizer.fit_transform(df["cleaned_review"])
    keywords = vectorizer.get_feature_names_out()

    keyword_df = pd.DataFrame({
        "Keyword": keywords,
        "Frequency": keyword_counts
    })

    # ================= DASHBOARD =================

    with tabs[0]:

        st.markdown("---")
        
        st.subheader("🔍 Smart Complaint Clustering")

        embedding_model = load_model()
        
        if st.button("Find Complaint Clusters"):
            with st.spinner("Analyzing negative reviews..."):
                negative_reviews = df[df["sentiment"] < 0]["cleaned_review"].tolist()
                
                if len(negative_reviews) < 10:
                    st.warning(f"Only {len(negative_reviews)} negative reviews found. Need at least 10 for meaningful clustering.")
                else:
                    result = run_pipeline(
                        negative_reviews, 
                        embedding_model, 
                        min_topic_size=25, # Adjusted for better cluster quality with small datasets 
                        similarity_threshold=0.4, # Tuned for better merging of similar clusters, can be adjusted based on dataset size and diversity
                        verbose=True # Keep verbose on to show progress
                    ) 
                    
                    if result["success"]:
                        st.success(f"✅ Found {result['n_clusters']} complaint clusters from {result['total_negative_reviews']} negative reviews")
                        
                        for cluster in result["clusters"]:
                            with st.expander(f"📌 {cluster['name']} ({cluster['percentage']:.1f}%) - {cluster['count']} reviews"):
                                st.write("**Some Reviews:**")
                                for i, review in enumerate(cluster.get('example_reviews', [cluster['sample_review']])[:3]):
                                    st.write(f"  {i+1}. \"{review}\"")
                    else:
                        st.error(result["message"])

        st.markdown("---")
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

    # ================= AI ASSISTANT =================

        with col_small:

            fig2, ax2 = plt.subplots(figsize=(2.8, 2.1))

        if user_q:
            with st.spinner("Analyzing feedback..."):
                st.success(ask_ai(user_q, df["original_review"].tolist()))

    # ================= CONTROLS =================

    with tabs[3]:

        st.subheader("⚙ System Controls")

        if st.button("🗑 Clear all stored feedback"):

            clear_data()
            st.success("All data removed successfully.")
            st.rerun()

        st.warning("This action cannot be undone.")

    # ================= RAG CHATBOT =================

    with tabs[4]:
        st.subheader("🧠 Chatbot – Ask your customer reviews")
        st.markdown("Ask any question about the customer feedback. The AI will answer based on the actual reviews.")
        
        # We use Streamlit's session state to maintain a unique session ID for each user, which allows the RAG API to keep track of conversation history and provide more contextually relevant answers.
        if "session_id" not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())

        # We also maintain a list of chat messages in the session state to display the conversation history in the UI. 
        if "rag_messages" not in st.session_state:
            st.session_state.rag_messages = []
            
        # The "Start New Conversation" button allows users to reset the chat history and generate a new session ID, effectively starting a fresh conversation with the RAG chatbot. 
        if st.button("🗑️ Start New Conversation"):
            st.session_state.rag_messages = []
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()
        
        # We loop through the stored messages in the session state and display them in the chat interface. User messages are shown as they are, while assistant messages also include an expander to show the source reviews that the AI used to generate its answer, providing transparency and context to the user.
        for msg in st.session_state.rag_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if "sources" in msg and msg["sources"]:
                    with st.expander("See source reviews"):
                        for src in msg["sources"]:
                            st.write(f"- {src[:200]}...")
        
        # The user input is captured through a chat input box. When the user submits a question, it is sent to the RAG API along with the session ID and a flag indicating that we want to use memory (conversation history). 
        user_q = st.chat_input("Type your question here...")
        if user_q:
            st.session_state.rag_messages.append({"role": "user", "content": user_q})
            with st.chat_message("user"):
                st.write(user_q)
            
            # When the user submits a question, we send a POST request to the /chat endpoint of our RAG API, passing the question, session ID, and use_memory flag.
            with st.chat_message("assistant"):
                with st.spinner("Searching and generating answer..."):
                    try:
                        response = requests.post(
                            "http://localhost:8001/chat",
                            json={
                                "question": user_q, 
                                "use_memory": True, 
                                "session_id": st.session_state.session_id
                            }
                        )
                        # We handle the API response to extract the AI's answer and the sources it used. The answer is displayed in the chat interface, and the sources are shown in an expander for transparency. 
                        if response.status_code == 200:
                            data = response.json()
                            answer = data["answer"]
                            sources = data["sources"]
                            st.write(answer)
                            with st.expander("📚 Source reviews"):
                                for src in sources:
                                    st.write(f"- {src}")
                            
                            # We also append the assistant's response and sources to the session state messages so that they are displayed in the chat history.
                            st.session_state.rag_messages.append({
                                "role": "assistant",
                                "content": answer,
                                "sources": sources
                            })
                        else:
                            st.error(f"API error: {response.status_code}")
                    except Exception as e:
                        st.error(f"Failed to connect to RAG API: {e}")

else:
    st.info("Upload feedback to start building insights.")