import streamlit as st
import pandas as pd
import sqlite3
import tempfile
import os
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import base64
from ingestion import ingest_contract
from analysis import analyze_clauses
from suggestions import generate_suggestions
from save_to_sheets import process_contract_data, save_to_google_sheets
from modifier import render_download_buttons
from io import BytesIO
# --- NEW IMPORTS FOR EMAIL & ENV ---
import yagmail
import json
from dotenv import load_dotenv # Used to load API key from .env

# Load environment variables FIRST (Crucial for GROQ_API_KEY to work)
load_dotenv()

# ------------------------------
# Email Configuration
# ------------------------------
SENDER_EMAIL = "sushma.shukla3011@gmail.com"
SENDER_PASSWORD = "ouiktzvxjzzcqbli" # Your App Password


# ------------------------------
# Page Config
# ------------------------------
st.set_page_config(
    page_title="AI Contract Compliance Checker",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ------------------------------
# Custom CSS for Styling
# ------------------------------
def load_css():
    st.markdown("""
    <style>
    /* ========= Global Background ========= */
    .stApp {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        color: #f5f5f5 !important;
    }

    /* ========= Center all main headings & content ========= */
    .center-page {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 75vh;
        width: 100%;
        text-align: center;
    }
    .center-page h1, .center-page h2, .center-page h3, .center-page h4, .center-page h5, .center-page h6 {
        margin: 0.5em 0;
        font-weight: bold;
        letter-spacing: 1px;
        text-align: center;
    }

    /* ========= Hero Section / Home Page Heading ========= */
    .hero-section {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        padding: 4rem 2rem;
        border-radius: 15px;
        color: #ffffff;
        text-align: center;
        margin-bottom: 2rem;
    }

    /* ========= Cards ========= */
    .metric-card, .chart-container {
        background: rgba(255, 255, 255, 0.08);
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        text-align: center;
        margin: 1rem 0;
        color: #f5f5f5 !important;
    }

    .risk-high { border-left: 5px solid #ff4757; }
    .risk-medium { border-left: 5px solid #ffa726; }
    .risk-low { border-left: 5px solid #26a69a; }

    /* ========= Upload Section ========= */
    .upload-section {
        background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
        box-shadow: 0 6px 24px rgba(20, 60, 180, 0.11);
        padding: 3rem 2rem 2rem 2rem;
        border-radius: 20px;
        text-align: center;
        margin: 2rem auto;
        max-width: 700px;
        border: 1.5px solid #e3f0ff;
    }
    .upload-section h2 {
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: 1px;
        color: #fff !important;
        text-shadow: 0 2px 6px #30548942;
        margin-bottom: 0.6rem;
    }
    .upload-section p {
        font-size: 1.1rem;
        color: #e3f0ff !important;
    }

    /* ========= Upload Section Progress Texts ========= */
    .upload-section span,
    .upload-section div[data-testid="stText"] {
        color: #ffffff !important;
        font-weight: 500;
    }

    /* ========= Tabs ========= */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
        background-color: #1e2a38;
        color: #f5f5f5 !important;
        border-radius: 10px 10px 0 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4cafef !important;
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    /* ========= Alerts (Success & Info) ========= */
    .stAlert {
        color: #ffffff !important;
        font-weight: 600;
    }
    .stAlert.stAlert-success {
        background-color: #1f7a2e !important;
        border-left: 4px solid #28a745 !important;
        padding: 12px !important;
        border-radius: 8px !important;
    }
    .stAlert.stAlert-info {
        background-color: #116c7b !important;
        border-left: 4px solid #17a2b8 !important;
        padding: 12px !important;
        border-radius: 8px !important;
    }
    .stAlert p {
        color: #ffffff !important;
        font-size: 16px !important;
    }

    /* ========= Detailed Sheets / Expander Headings ========= */
    .stExpander h2,
    .stExpander h3,
    .stExpander h4,
    .stExpander h5,
    .stExpander h6 {
        color: #ffffff !important;
        font-weight: 600;
    }
    .stExpander .css-1v0mbdj {
        color: #ffffff !important; /* section headings inside expanders */
    }

    /* ========= Processing Animation ========= */
    .processing-animation {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        border-radius: 15px;
        margin: 2rem 0;
        color: #333 !important;
    }

    /* ========= Inputs & Buttons ========= */
    [data-testid="stFileUploader"] *,
    input, textarea, select {
        color: #222 !important;
        background: #fff !important;
        border-radius: 5px;
        border: 1px solid #ddd !important;
    }
    [data-testid="stFileUploader"] input:focus,
    input:focus,
    textarea:focus,
    select:focus {
        border-color: #267afe !important;
        box-shadow: 0 0 3px #267afe44 !important;
        outline: none !important;
    }

    .stButton>button, .stDownloadButton>button {
        background: #4cafef !important;
        color: #fff !important;
        border: none;
        padding: 0.8rem 2.2rem;
        border-radius: 8px;
        box-shadow: 0 2px 6px rgba(76, 175, 239, 0.09);
        font-weight: 600;
        transition: background 0.2s, box-shadow 0.2s;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        background: #267afe !important;
        box-shadow: 0 6px 18px rgba(38, 122, 254, 0.15);
    }

    /* ========= Selectbox & Text Input on Dark Background ========= */
    /* Labels */
    .stForm label, 
    [data-testid="stTextInput"] label,
    [data-testid="stSelectbox"] label {
        color: #ffffff !important;
        font-weight: 600;
    }

    /* Text input typed text and placeholder */
    [data-testid="stTextInput"] input {
        color: #ffffff !important;
        background-color: #1e2a38 !important;
        border: 1px solid #444 !important;
    }

    /* Selectbox text and dropdown */
    [data-testid="stSelectbox"] div[role="combobox"] {
        color: #ffffff !important;
        background-color: #1e2a38 !important;
        border: 1px solid #444 !important;
    }
    div[role="listbox"] {
        color: #ffffff !important;
        background-color: #1e2a38 !important;
    }

    /* ========= Force all dynamic status/progress text (st.text, st.write) to white ========= */
    div[data-testid="stText"] *,
    div[data-testid="stText"] p,
    div[data-testid="stText"] span {
        color: #ffffff !important;
        font-weight: 500 !important;
    }

    </style>
    """, unsafe_allow_html=True)


# ------------------------------
# Database Functions
# ------------------------------
DB_PATH = "contract_history.db"
# email sending function 
def send_report_email(recipient_email, filename, num_clauses, num_high, num_medium, num_low):
    """Sends the contract summary report via email."""
    
    subject = f"AI Contract Analysis Summary: {filename}"
    
    # 1. Create the email body (HTML)
    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <div style="background-color: #f4f4f4; padding: 20px; border-radius: 10px;">
            <h2 style="color: #0984e3;">📑 AI Contract Compliance Analysis Summary</h2>
            <p>Dear User,</p>
            <p>The AI analysis for your contract <strong>{filename}</strong> is complete. Below is the risk summary:</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                <tr><td style="padding: 8px; border: 1px solid #ddd; background-color: #e3f0ff;"><strong>Total Clauses Analyzed:</strong></td><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{num_clauses}</td></tr>
                <tr style="color: #ff4757;"><td style="padding: 8px; border: 1px solid #ddd; background-color: #ffe3e6;"><strong>High Risk Clauses:</strong></td><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{num_high}</td></tr>
                <tr style="color: #ffa726;"><td style="padding: 8px; border: 1px solid #ddd; background-color: #fff4e6;"><strong>Medium Risk Clauses:</strong></td><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{num_medium}</td></tr>
                <tr style="color: #26a69a;"><td style="padding: 8px; border: 1px solid #ddd; background-color: #e6fff7;"><strong>Low Risk Clauses:</strong></td><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{num_low}</td></tr>
            </table>

            <p><strong>Next Steps:</strong></p>
            <p>The *modified contract report* is ready and can be downloaded from the *'Upload & Analyze'* tab on the web app. Full details are in the *'Detailed Results'* tab.</p>
            
            <p>Thank you for using the AI Contract Compliance Checker.</p>
        </div>
    </body>
    </html>
    """
    
    # 2. Send the email using yagmail
    try:
        yag = yagmail.SMTP(user=SENDER_EMAIL, password=SENDER_PASSWORD)
        
        # Sending summary only (no PDF attachment in this current version)
        yag.send(
            to=recipient_email,
            subject=subject,
            contents=[body_html],
        )
        return True
    except Exception as e:
        print(f"Yagmail Send Error: {e}")
        return False

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            timestamp TEXT,
            num_clauses INTEGER,
            num_high INTEGER,
            num_medium INTEGER,
            num_low INTEGER,
            sheet_name TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_history(filename, num_clauses, num_high, num_medium, num_low, sheet_name=""):
    """Save analysis results to database with validation and logging."""
    # Input validation
    try:
        # Ensure all numbers are non-negative integers
        num_clauses = max(0, int(num_clauses))
        num_high = max(0, int(num_high))
        num_medium = max(0, int(num_medium))
        num_low = max(0, int(num_low))
        
        # Basic validation
        if num_high + num_medium + num_low > num_clauses:
            print(f"Warning: Risk counts ({num_high}+{num_medium}+{num_low}) exceed total clauses ({num_clauses})")
            # Adjust risk numbers if they exceed total clauses
            factor = num_clauses / (num_high + num_medium + num_low)
            num_high = int(num_high * factor)
            num_medium = int(num_medium * factor)
            num_low = int(num_low * factor)
            print(f"Adjusted to: High={num_high}, Medium={num_medium}, Low={num_low}")
    except (ValueError, TypeError) as e:
        print(f"Error converting numbers: {str(e)}")
        # If conversion fails, set to 0
        num_clauses = num_high = num_medium = num_low = 0
    
    # Ensure filename is valid
    if not filename or not isinstance(filename, str):
        filename = f"unnamed_contract_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # First check if this exact entry exists
        c.execute("""
            SELECT id FROM history 
            WHERE filename = ? AND timestamp = ? AND num_clauses = ? 
            AND num_high = ? AND num_medium = ? AND num_low = ?
        """, (filename, ts, num_clauses, num_high, num_medium, num_low))
        
        if c.fetchone() is None:
            # Only insert if no duplicate exists
            c.execute("""
                INSERT INTO history 
                (filename, timestamp, num_clauses, num_high, num_medium, num_low, sheet_name) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (filename, ts, num_clauses, num_high, num_medium, num_low, sheet_name))
            print(f"Saved to database: {filename} with {num_clauses} clauses")
        else:
            print(f"Skipped duplicate entry for {filename}")
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")
        raise
    finally:
        conn.close()

def load_history():
    """Load and validate history data from database."""
    try:
        if not os.path.exists(DB_PATH):
            print("Database file does not exist yet")
            return pd.DataFrame()
            
        conn = sqlite3.connect(DB_PATH)
        
        # First verify table structure
        c = conn.cursor()
        c.execute("SELECT * FROM history LIMIT 0")
        columns = [description[0] for description in c.description]
        expected_columns = ['id', 'filename', 'timestamp', 'num_clauses', 'num_high', 
                          'num_medium', 'num_low', 'sheet_name']
        
        if not all(col in columns for col in expected_columns):
            print("Warning: Database schema mismatch")
            return pd.DataFrame()
        
        # Load data with explicit column types
        df = pd.read_sql("""
            SELECT 
                id,
                filename,
                timestamp,
                CAST(num_clauses AS INTEGER) as num_clauses,
                CAST(num_high AS INTEGER) as num_high,
                CAST(num_medium AS INTEGER) as num_medium,
                CAST(num_low AS INTEGER) as num_low,
                sheet_name
            FROM history 
            ORDER BY id DESC
        """, conn)
        
        # Additional validation and cleaning
        # Convert timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['timestamp'])  # Remove rows with invalid timestamps
        
        # Ensure numeric columns are non-negative integers
        numeric_cols = ["num_clauses", "num_high", "num_medium", "num_low"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                df[col] = df[col].apply(lambda x: max(0, int(x)))  # Ensure non-negative integers
        
        # Validate risk counts don't exceed clause counts
        mask = df[['num_high', 'num_medium', 'num_low']].sum(axis=1) > df['num_clauses']
        if mask.any():
            print(f"Warning: Found {mask.sum()} entries where risk counts exceed clause counts")
            # Adjust the problematic entries
            for idx in df[mask].index:
                total_risks = df.loc[idx, ['num_high', 'num_medium', 'num_low']].sum()
                if total_risks > 0:
                    factor = df.loc[idx, 'num_clauses'] / total_risks
                    for risk_col in ['num_high', 'num_medium', 'num_low']:
                        df.loc[idx, risk_col] = int(df.loc[idx, risk_col] * factor)
        
        print(f"Loaded {len(df)} history entries")
        return df
        
    except Exception as e:
        print(f"Error loading history: {str(e)}")
        return pd.DataFrame()
        
    finally:
        if 'conn' in locals():
            conn.close()


# ------------------------------
# Initialize Session State
# ------------------------------
if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False
if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None
if "df_results" not in st.session_state:
    st.session_state.df_results = None

# ------------------------------
# Load CSS
# ------------------------------
load_css()

# ------------------------------
# Navigation Tabs
# ------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 Home", 
    "📤 Upload & Analyze", 
    "📊 Charts & Insights", 
    "📋 Detailed Results", 
    "📈 Company Dashboard"
])

# ------------------------------
# HOME PAGE
# ------------------------------
with tab1:
    st.markdown("""
    <div class="hero-section">
        <h1 style="font-size: 3rem; margin-bottom: 1rem;">📑 AI Contract Compliance Checker</h1>
        <p style="font-size: 1.2rem; margin-bottom: 2rem;">
            Transform your contract analysis with AI-powered risk detection and compliance checking
        </p>
        <p style="font-size: 1rem; opacity: 0.9;">
            Upload your contracts • Get instant risk analysis • Receive actionable suggestions
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>🔍 Smart Analysis</h3>
            <p>Advanced AI models analyze your contracts for potential risks and compliance issues</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>📊 Visual Insights</h3>
            <p>Comprehensive charts and dashboards to understand your contract portfolio</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>💡 Actionable Suggestions</h3>
            <p>Get specific recommendations to improve contract terms and reduce risks</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🚀 Getting Started")
    st.markdown("""
    1. Navigate to Upload & Analyze - Upload your contract PDF
    2. View Results - Get instant risk assessment and analysis
    3. Explore Charts - Visualize risk distribution and patterns
    4. Review Details - Examine clause-by-clause analysis
    5. Track Progress - Monitor your contract portfolio in the dashboard
    """)

# ------------------------------
# UPLOAD & ANALYZE PAGE
# ------------------------------
with tab2:
    st.markdown("""
    <div class="upload-section">
        <h2>📤 Upload Your Contract</h2>
        <p>Select a PDF contract file to begin the AI-powered analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Upload your contract in PDF format for analysis"
    )
    # --- FEATURE ADDED: Email Input Field ---
    recipient_email = st.text_input(
        "Enter Recipient Email for Summary Report:",
        placeholder="user@example.com",
        help="The analysis summary (High, Medium, Low risks) will be sent to this email address."
    )
    # ----------------------------------------
    
    
    
    if uploaded_file:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            st.info(f"📄 File size: {uploaded_file.size / 1024:.1f} KB")
        
        with col2:
            if st.button("🚀 Start Analysis", type="primary", use_container_width=True):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    tmp_path = tmp_file.name
                
                # Processing Animation
                st.markdown("""
                <div class="processing-animation">
                    <h3>🔄 Processing Your Contract</h3>
                    <p>Please wait while we analyze your document...</p>
                </div>
                """, unsafe_allow_html=True)
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Step 1: Extract clauses
                status_text.text("🔍 Extracting clauses...")
                progress_bar.progress(25)
                clauses = ingest_contract(tmp_path)
                
                # Step 2: Analyze clauses
                status_text.text("🧠 Analyzing risks...")
                progress_bar.progress(50)
                analysis_results = analyze_clauses(clauses)
                
                # Step 3: Generate suggestions
                status_text.text("💡 Generating suggestions...")
                progress_bar.progress(75)
                suggestions = generate_suggestions(analysis_results)
                
                # Step 4: Process data
                status_text.text("📊 Preparing results...")
                progress_bar.progress(100)
                combined_data = process_contract_data(clauses, analysis_results, suggestions)

                # Step 5: Provide download button for safe contract
                status_text.text("✅ Preparing modified contract report...")
                try:
                    render_download_buttons(analysis_results)
                except Exception as e:
                    st.error(f"❌ Failed to generate modified contract: {e}")
                
                # Save to session state
                st.session_state.analysis_data = combined_data
                st.session_state.df_results = pd.DataFrame(combined_data)
                st.session_state.analysis_complete = True
                
                # Clean up
                os.unlink(tmp_path)
                progress_bar.empty()
                status_text.empty()

                # --- Validation for Email (Add this check before processing starts) ---
                if not recipient_email or "@" not in recipient_email:
                    st.error("❌ Please enter a valid email address to receive the report.")
                    st.stop()
                # --------------------------
                
                # ... (Your existing Steps 1 through 5 and cleanup code) ...
                
                # --- FEATURE ADDED: SEND EMAIL SUMMARY REPORT (Step 6) ---
                status_text.text("📧 Sending email summary...")
                
                df = st.session_state.df_results
                num_clauses = len(df)
                num_high = (df["Risk_Severity"] == "High").sum()
                num_medium = (df["Risk_Severity"] == "Medium").sum()
                num_low = (df["Risk_Severity"] == "Low").sum()

                email_sent = send_report_email(
                    recipient_email, 
                    uploaded_file.name, 
                    num_clauses, 
                    num_high, 
                    num_medium, 
                    num_low
                )
                if email_sent:
                    st.success(f"✅ Analysis Complete and *Summary Emailed* to *{recipient_email}*! Full reports available below.")
                else:
                    st.error(f"❌ Analysis Complete, but *Email Failed* to send to *{recipient_email}*. Please check App Password/SMTP settings.")
                # ----------------------------------------------------
                
                progress_bar.empty()
                status_text.empty()
                
                st.balloons()
                
                st.success("✅ Analysis Complete!")
                st.balloons()
    
    # Display results if analysis is complete
    if st.session_state.analysis_complete and st.session_state.df_results is not None:
        df = st.session_state.df_results
        
        st.markdown("### 📊 Analysis Summary")
        
        # Summary metrics
        num_clauses = len(df)
        num_high = (df["Risk_Severity"] == "High").sum()
        num_medium = (df["Risk_Severity"] == "Medium").sum()
        num_low = (df["Risk_Severity"] == "Low").sum()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{num_clauses}</h3>
                <p>Total Clauses</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card risk-high">
                <h3>{num_high}</h3>
                <p>High Risk</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card risk-medium">
                <h3>{num_medium}</h3>
                <p>Medium Risk</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card risk-low">
                <h3>{num_low}</h3>
                <p>Low Risk</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Quick actions
        st.markdown("### 🎯 Quick Actions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 View Charts", use_container_width=True):
                st.info("Navigate to the 'Charts & Insights' tab to view visualizations")
        
        with col2:
            if st.button("📋 View Details", use_container_width=True):
                st.info("Navigate to the 'Detailed Results' tab for full analysis")
        
        with col3:
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇ Download CSV",
                csv,
                file_name=f"contract_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        # Save to history
        if uploaded_file:
            save_history(uploaded_file.name, num_clauses, num_high, num_medium, num_low)

# ------------------------------
# CHARTS & INSIGHTS PAGE (FIXED)
# ------------------------------
with tab3:
    st.markdown("# 📊 Charts & Insights")
    
    if not st.session_state.analysis_complete or st.session_state.df_results is None:
        st.warning("⚠ No analysis data available. Please upload and analyze a contract first.")
    else:
        df = st.session_state.df_results.copy()
        
        # Ensure we have risk severity data
        if "Risk_Severity" not in df.columns or df.empty:
            st.error("⚠ No risk analysis data available in the current contract.")
        else:
            # Clean and validate risk severity data
            df = df.dropna(subset=['Risk_Severity'])
            df['Risk_Severity'] = df['Risk_Severity'].astype(str).str.strip()
            
            if df.empty or df['Risk_Severity'].value_counts().sum() == 0:
                st.info("ℹ No risk classifications found in the analyzed contract.")
            else:
                # Set up matplotlib style
                plt.style.use('default')
                sns.set_palette("husl")
                
                col1, col2 = st.columns(2)
                
                # --- Risk Distribution Bar ---
                with col1:
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    st.subheader("🎯 Risk Distribution")
                    
                    fig, ax = plt.subplots(figsize=(8, 5))
                    risk_counts = df["Risk_Severity"].value_counts()
                    
                    color_map = {'High': '#ff4757', 'Medium': '#ffa726', 'Low': '#26a69a'}
                    colors = [color_map.get(risk, '#74b9ff') for risk in risk_counts.index]
                    
                    bars = ax.bar(risk_counts.index, risk_counts.values, color=colors, alpha=0.8)
                    
                    for bar in bars:
                        height = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                               f'{int(height)}', ha='center', va='bottom', fontsize=12, fontweight='bold')
                    
                    ax.set_xlabel("Risk Severity", fontsize=12)
                    ax.set_ylabel("Number of Clauses", fontsize=12)
                    ax.set_title("Risk Distribution by Severity", fontsize=14, fontweight='bold', pad=20)
                    ax.set_ylim(0, risk_counts.max() * 1.3)
                    
                    ax.grid(True, axis='y', linestyle='--', alpha=0.3)
                    ax.spines['top'].set_visible(False)
                    ax.spines['right'].set_visible(False)
                    
                    plt.tight_layout()
                    st.pyplot(fig, use_container_width=True)
                    plt.close(fig)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # --- Risk Distribution Pie ---
                with col2:
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    st.subheader("📈 Risk Percentage")
                    
                    fig2, ax2 = plt.subplots(figsize=(8, 5))
                    risk_counts = df["Risk_Severity"].value_counts()
                    
                    color_map = {'High': '#ff4757', 'Medium': '#ffa726', 'Low': '#26a69a'}
                    colors = [color_map.get(risk, '#74b9ff') for risk in risk_counts.index]
                    
                    wedges, texts, autotexts = ax2.pie(
                        risk_counts.values,
                        labels=risk_counts.index,
                        autopct=lambda pct: f'{pct:.1f}%\n({int(pct*sum(risk_counts.values)/100)})',
                        colors=colors,
                        startangle=90,
                        explode=[0.05] * len(risk_counts)
                    )
                    
                    plt.setp(autotexts, size=10, weight="bold", color='white')
                    plt.setp(texts, size=11, weight='bold')
                    
                    ax2.set_title("Risk Distribution Percentage", fontsize=14, fontweight='bold', pad=20)
                    
                    plt.tight_layout()
                    st.pyplot(fig2, use_container_width=True)
                    plt.close(fig2)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # --- Risk Trends ---
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                st.subheader("📅 Risk Analysis Trends")
                
                init_db()
                history_df = load_history()
                
                if not history_df.empty and len(history_df) > 1:
                    fig3, ax3 = plt.subplots(figsize=(14, 6))
                    history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])
                    history_df = history_df.sort_values('timestamp')
                    
                    ax3.plot(history_df['timestamp'], history_df['num_high'], 'o-', 
                            color='#ff4757', label='High Risk', linewidth=3, markersize=8)
                    ax3.plot(history_df['timestamp'], history_df['num_medium'], 's-', 
                            color='#ffa726', label='Medium Risk', linewidth=3, markersize=8)
                    ax3.plot(history_df['timestamp'], history_df['num_low'], '^-', 
                            color='#26a69a', label='Low Risk', linewidth=3, markersize=8)
                    
                    ax3.set_xlabel("Date", fontsize=12)
                    ax3.set_ylabel("Number of Clauses", fontsize=12)
                    ax3.set_title("Risk Trends Over Time", fontsize=14, fontweight='bold', pad=20)
                    ax3.legend(fontsize=11, loc='upper left')
                    ax3.grid(True, alpha=0.3)
                    
                    plt.xticks(rotation=45)
                    ax3.spines['top'].set_visible(False)
                    ax3.spines['right'].set_visible(False)
                    
                    plt.tight_layout()
                    st.pyplot(fig3, use_container_width=True)
                    plt.close(fig3)
                else:
                    st.info("📊 Need at least 2 analyses for trend visualization")
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # --- Clause Length Analysis (Full Width) ---
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                st.subheader("📏 Clause Length Analysis")
                
                if "Clause_Text" in df.columns and not df["Clause_Text"].isnull().all():
                    df['clause_length'] = df['Clause_Text'].astype(str).str.len()
                    
                    fig5, ax5 = plt.subplots(figsize=(10, 6))
                    ax5.hist(df['clause_length'], bins=15, color='skyblue', alpha=0.7, edgecolor='black', linewidth=1.2)
                    ax5.set_xlabel("Clause Length (characters)", fontsize=12)
                    ax5.set_ylabel("Frequency", fontsize=12)
                    ax5.set_title("Distribution of Clause Lengths", fontsize=14, fontweight='bold', pad=20)
                    
                    mean_length = df['clause_length'].mean()
                    ax5.axvline(mean_length, color='red', linestyle='--', linewidth=2, 
                               label=f'Mean: {mean_length:.0f}')
                    ax5.legend()
                    
                    ax5.grid(True, alpha=0.3)
                    ax5.spines['top'].set_visible(False)
                    ax5.spines['right'].set_visible(False)
                    
                    plt.tight_layout()
                    st.pyplot(fig5, use_container_width=True)
                    plt.close(fig5)
                else:
                    st.info("📄 Clause text data not available")
                
                st.markdown('</div>', unsafe_allow_html=True)
# ------------------------------
# DETAILED RESULTS PAGE
# ------------------------------
with tab4:
    st.markdown("# 📋 Detailed Analysis Results")
    
    if not st.session_state.analysis_complete or st.session_state.df_results is None:
        st.warning("⚠ No analysis data available. Please upload and analyze a contract first.")
    else:
        df = st.session_state.df_results
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            risk_filter = st.selectbox("Filter by Risk Level:", ["All"] + list(df["Risk_Severity"].unique()))
        
        with col2:
            if "Risk_Category" in df.columns:
                category_filter = st.selectbox("Filter by Category:", ["All"] + list(df["Risk_Category"].unique()))
            else:
                category_filter = "All"
        
        with col3:
            search_term = st.text_input("Search in clauses:", placeholder="Enter search term...")
        
        # Apply filters
        filtered_df = df.copy()
        
        if risk_filter != "All":
            filtered_df = filtered_df[filtered_df["Risk_Severity"] == risk_filter]
        
        if category_filter != "All" and "Risk_Category" in df.columns:
            filtered_df = filtered_df[filtered_df["Risk_Category"] == category_filter]
        
        if search_term:
            if "Clause_Text" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["Clause_Text"].str.contains(search_term, case=False, na=False)]
        
        st.markdown(f"### Showing {len(filtered_df)} of {len(df)} clauses")
        
        # Results table with styling
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Export options
        st.markdown("### 📤 Export Options")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇ Download Filtered CSV",
                csv,
                file_name=f"filtered_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            if st.button("📊 Export to Excel", use_container_width=True):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
                    filtered_df.to_excel(tmp_file.name, index=False)
                    with open(tmp_file.name, "rb") as f:
                        st.download_button(
                            "⬇ Download Excel",
                            f.read(),
                            file_name=f"contract_analysis_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.ms-excel"
                        )
        
        with col3:
            if st.button("📄 Save to Google Sheets", use_container_width=True):
                try:
                    sheet_name = save_to_google_sheets(filtered_df.to_dict('records'))
                    st.success(f"✅ Saved to Google Sheets: {sheet_name}")
                except Exception as e:
                    st.error(f"❌ Failed to save: {str(e)}")                


# ------------------------------
# COMPANY DASHBOARD PAGE (FIXED AND STREAMLINED)
# ------------------------------
with tab5:
    st.markdown("# 📈 Company Dashboard")
    
    init_db()
    history_df = load_history()
    
    if history_df.empty or len(history_df) == 0:
        st.info("📝 No contract analysis history available. Start by analyzing some contracts!")
    else:
        try:
            # --- Data Cleaning ---
            history_df['timestamp'] = pd.to_datetime(history_df['timestamp'], errors='coerce')
            history_df = history_df.dropna(subset=['timestamp'])
            
            # Ensure num_clauses is numeric
            if 'num_clauses' in history_df.columns:
                history_df['num_clauses'] = pd.to_numeric(history_df['num_clauses'], errors='coerce').fillna(0).astype(int)
            else:
                history_df['num_clauses'] = 0

            # Remove duplicates
            history_df = history_df.drop_duplicates(subset=['filename', 'timestamp'], keep='last')
            history_df = history_df[history_df['num_clauses'] > 0]
            
            if history_df.empty:
                st.warning("⚠ No valid contract data available. Please analyze some contracts with proper data.")
                st.stop()
                
        except Exception as e:
            st.error(f"❌ Error processing dashboard data: {str(e)}")
            st.stop()
        
        # --- 3 MAIN METRICS ---
        total_contracts = len(history_df)
        total_clauses = int(history_df['num_clauses'].sum())
        avg_clauses_per_contract = round(total_clauses / total_contracts) if total_contracts > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""<div class="metric-card"><h3>{total_contracts}</h3><p>Total Contracts</p></div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="metric-card"><h3>{total_clauses}</h3><p>Total Clauses</p></div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class="metric-card"><h3>{avg_clauses_per_contract}</h3><p>Avg Clauses</p></div>""", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # --- TABLE DISPLAY ---
        st.subheader("📑 Contract History")
        display_df = history_df[['filename', 'num_clauses', 'timestamp']].rename(
            columns={
                'filename': 'Contract Name',
                'num_clauses': 'Number of Clauses',
                'timestamp': 'Analyzed On'
            }
        )
        st.dataframe(display_df.sort_values(by='Analyzed On', ascending=False))
        
        # --- BOTTOM BUTTONS ---
        colA, colB = st.columns([1, 1])
        
        with colA:
            # Export to Excel
            towrite = BytesIO()
            with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
                display_df.to_excel(writer, index=False, sheet_name="Contract History")
                worksheet = writer.sheets["Contract History"]
                
                # Set column widths
                worksheet.set_column("A:A", 40)  # Contract Name
                worksheet.set_column("B:B", 20)  # Number of Clauses
                worksheet.set_column("C:C", 25)  # Timestamp
            
            towrite.seek(0)
            st.download_button(
                label="📥 Export History (Excel)",
                data=towrite,
                file_name=f"contract_history_{pd.Timestamp.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        with colB:
            # Initialize delete confirmation state
            if "confirm_delete" not in st.session_state:
                st.session_state.confirm_delete = False

            if not st.session_state.confirm_delete:
                if st.button("🗑 Delete History", use_container_width=True):
                    st.session_state.confirm_delete = True
                    st.rerun()
            else:
                st.warning("⚠ Are you sure you want to delete all history?")
                colC, colD = st.columns(2)
                with colC:
                    if st.button("✅ Yes, Delete"):
                        try:
                            if os.path.exists(DB_PATH):
                                conn = sqlite3.connect(DB_PATH)
                                c = conn.cursor()
                                c.execute("DELETE FROM history")
                                conn.commit()
                                conn.close()
                                
                                # Clear cache
                                for key in list(st.session_state.keys()):
                                    del st.session_state[key]
                                
                                st.success("✅ All history deleted!")
                                st.rerun()
                            else:
                                st.error("❌ Database file not found")
                        except Exception as e:
                            st.error(f"❌ Error clearing history: {str(e)}")
                with colD:
                    if st.button("❌ Cancel"):
                        st.session_state.confirm_delete = False
                        st.rerun()



# ------------------------------
# Footer
# ------------------------------
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray; padding: 2rem;">
    <p>📑 AI Contract Compliance Checker | Built with Streamlit & AI</p>
    <p>Transform your contract analysis workflow with intelligent automation</p>
</div>
""", unsafe_allow_html=True)