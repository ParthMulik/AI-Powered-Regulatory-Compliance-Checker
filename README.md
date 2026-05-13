# AI-Powered Regulatory Compliance Contract Checker

An intelligent contract analysis platform that automates regulatory compliance review by identifying risky contract clauses, explaining risks in plain language, and generating safer compliant alternatives.

Built to reduce manual legal review effort, improve consistency in compliance checks, and provide actionable contract modifications instantly.

---

## Overview

Manual contract review is time-consuming, error-prone, and difficult to scale—especially when handling complex legal agreements with multiple compliance requirements.

This project solves that challenge through AI-powered contract intelligence.

The application can:

✅ Scan contracts automatically  
✅ Extract and classify clauses  
✅ Detect high-risk or non-compliant clauses  
✅ Explain risks in plain language  
✅ Suggest safer compliant alternatives  
✅ Generate downloadable compliance reports (Word/PDF)  
✅ Export analysis to Excel and Google Sheets  
✅ Send automated notifications via Gmail  

The platform also integrates with enterprise productivity tools like Word, Excel, and Google Sheets while keeping security and scalability in mind.

---

## Key Features

### 1. Clause Identification & Risk Analysis
The system parses uploaded contracts and identifies individual legal clauses for analysis.

**Capabilities:**
- Clause extraction
- Clause categorization
- Risk scoring
- Compliance validation
- Transparent reasoning for flagged clauses

---

### 2. Contract Modification Engine
For clauses marked as risky, the platform generates legally safer alternatives.

**Capabilities:**
- AI-generated compliant clause suggestions
- Automatic contract modification recommendations
- Downloadable modification reports
- Word and PDF export support

---

### 3. Data Export & Reporting
Users can export contract analysis data in multiple formats.

Supported exports:
- Excel (.xlsx)
- Google Sheets
- Word (.docx)
- PDF (.pdf)

---

### 4. Notification Automation
Users receive automated compliance risk alerts directly through email.

Features:
- Gmail notifications
- Analysis completion alerts
- Risk summary emails

---

## Tech Stack

### Backend
- Python

### Frontend / UI
- Streamlit

### AI / LLM Integration
- Groq API
- Google Gemini API

### Database
- SQLite

### Data Processing & Visualization
- Pandas
- Matplotlib

### Document Processing
- python-docx
- docx2pdf

### Notifications
- yagmail

### Spreadsheet Integration
- gsheets
- openpyxl

---

## System Architecture

```text
User Uploads Contract
        ↓
Clause Extraction Module
        ↓
Risk Detection Engine
        ↓
Compliance Analysis
        ↓
AI Safer Clause Generation
        ↓
Report Generation
   ├── Word Export
   ├── PDF Export
   ├── Excel Export
   └── Google Sheets Export
        ↓
Email Notification to User
```

---

## Project Modules

### Clause Identification and Risk Analysis Module
Responsible for:
- Parsing contracts
- Identifying clauses
- Detecting risky clauses
- Assigning risk levels
- Providing compliance explanations

---

### Contract Modification Module
Responsible for:
- Generating compliant alternatives
- Suggesting safer rewrites
- Creating downloadable modification reports

---

## Performance Highlights

The developed system demonstrated:

- Faster review compared to manual contract analysis
- Consistent risk detection performance
- Effective handling of both short and complex contracts
- Transparent AI-generated explanations
- Reliable safer clause recommendations

---

## Use Cases

This platform can be used by:

- Legal teams
- Compliance officers
- Startups reviewing vendor contracts
- Enterprises managing procurement agreements
- HR teams reviewing employment contracts
- Contract management teams

---

## Installation

### Clone Repository
```bash
git clone https://github.com/your-username/contract-compliance-checker.git
cd contract-compliance-checker
```

### Create Virtual Environment
```bash
python -m venv venv
```

Activate environment:

**Windows**
```bash
venv\Scripts\activate
```

**Mac/Linux**
```bash
source venv/bin/activate
```

---

### Install Dependencies
```bash
pip install -r requirements.txt
```

---

### Configure Environment Variables
Create a `.env` file:

```env
GROQ_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
```

---

## Run Application

```bash
streamlit run app.py
```

---

## Future Improvements

Planned enhancements:

- Support for DOCX/PDF contract uploads
- Multi-language contract analysis
- Role-based enterprise authentication
- Contract version comparison
- Audit logs
- Advanced compliance framework support
- Cloud deployment
- Real-time collaboration

---

## Sample Workflow

1. Upload contract
2. System extracts clauses
3. Risk analysis runs
4. High-risk clauses are flagged
5. AI generates safer alternatives
6. Export compliance report
7. Receive email notification

---

## Security Considerations

This system is designed with enterprise-grade workflow considerations including:

- Controlled API access
- Secure document handling
- Restricted email authentication
- Protected export workflows

---

## Contributors

Developed by **[Parth Mulik]**

---

## License

This project is for academic / educational / demonstration purposes unless otherwise specified.
