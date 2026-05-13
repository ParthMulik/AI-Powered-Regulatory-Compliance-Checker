# save_to_sheets.py (updated - process + save)
import os
import sys
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from ingestion import ingest_contract
from analysis import analyze_clauses
from suggestions import generate_suggestions
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv()

def generate_sheet_name(pdf_path):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = os.path.splitext(os.path.basename(pdf_path))[0]
    clean_filename = "".join(c for c in pdf_filename if c.isalnum() or c in ('-', '_'))[:20]
    sheet_name = f"{clean_filename}_{timestamp}"
    return sheet_name

def save_to_google_sheets(data, sheet_name=None):
    SHEET_ID = os.getenv("SHEET_ID")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not SHEET_ID or not creds_path:
        raise ValueError("Missing SHEET_ID or GOOGLE_APPLICATION_CREDENTIALS in .env")
    if not data:
        print("⚠️ No data to save")
        return None
    if not sheet_name:
        sheet_name = f"Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        creds = Credentials.from_service_account_file(
            creds_path, 
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        service = build("sheets", "v4", credentials=creds)
        df = pd.DataFrame(data)
        if df.empty:
            print("⚠️ DataFrame is empty")
            return None
        values = [df.columns.tolist()] + df.values.tolist()
        spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        existing_sheets = [s['properties']['title'] for s in spreadsheet['sheets']]
        original_sheet_name = sheet_name
        counter = 1
        while sheet_name in existing_sheets:
            sheet_name = f"{original_sheet_name}_{counter}"
            counter += 1
        print(f"📝 Creating new sheet: {sheet_name}")
        request_body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': sheet_name,
                        'gridProperties': {
                            'rowCount': len(values) + 10,
                            'columnCount': len(values[0]) if values else 12
                        }
                    }
                }
            }]
        }
        batch_response = service.spreadsheets().batchUpdate(
            spreadsheetId=SHEET_ID,
            body=request_body
        ).execute()
        result = service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"{sheet_name}!A1",
            valueInputOption="RAW",
            body={"values": values}
        ).execute()
        # Optional header formatting: ignore errors
        try:
            format_request = {
                'requests': [{
                    'repeatCell': {
                        'range': {
                            'sheetId': batch_response['replies'][0]['addSheet']['properties']['sheetId'],
                            'startRowIndex': 0,
                            'endRowIndex': 1,
                            'startColumnIndex': 0,
                            'endColumnIndex': len(values[0]) if values else 12
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'textFormat': {'bold': True},
                                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
                            }
                        },
                        'fields': 'userEnteredFormat(textFormat,backgroundColor)'
                    }
                }]
            }
            service.spreadsheets().batchUpdate(
                spreadsheetId=SHEET_ID,
                body=format_request
            ).execute()
        except Exception as format_error:
            print(f"⚠️ Could not format header: {format_error}")
        print(f"✅ Data saved to Google Sheets: {sheet_name}")
        sheet_id = batch_response['replies'][0]['addSheet']['properties']['sheetId']
        print(f"🔗 Sheet URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid={sheet_id}")
        return sheet_name
    except Exception as e:
        print(f"❌ Error saving to Google Sheets: {e}")
        raise

def process_contract_data(clauses, analysis_results, suggestions):
    """
    Combine data for sheet with only required columns:
    Clause_ID | Clause_Text | Clause_Type | Regulatory_Relevance | Regulation | Risk_Description | Risk_Severity | Suggestion
    """
    combined = []
    # build maps from clause_id -> analysis & suggestion
    analysis_map = {int(r['clause_id']): r for r in analysis_results if r.get('clause_id') is not None}
    suggestion_map = {int(s['clause_id']): s for s in suggestions if s.get('clause_id') is not None}

    for i, clause in enumerate(clauses):
        # clause can be dict or str
        if isinstance(clause, dict):
            clause_text_full = clause.get('content') or clause.get('clause') or ''
            clause_id = int(clause.get('chunk_id', i + 1))
            clause_type = clause.get('primary_type', 'unknown')
            regulatory_relevance = clause.get('regulatory_relevance', 'minimal')
        else:
            clause_text_full = str(clause)
            clause_id = i + 1
            clause_type = 'unknown'
            regulatory_relevance = 'minimal'

        analysis = analysis_map.get(clause_id, {})
        suggestion = suggestion_map.get(clause_id, {})

        combined_row = {
            "Clause_ID": clause_id,
            "Clause_Text": clause_text_full[:1000] + ('...' if len(clause_text_full) > 1000 else ''),
            "Clause_Type": clause_type,
            "Regulatory_Relevance": regulatory_relevance,
            "Regulation": analysis.get("regulation", "Not analyzed"),
            "Risk_Description": analysis.get("risk", "Not analyzed"),
            "Risk_Severity": analysis.get("severity", "Unknown"),
            "Suggestion": suggestion.get("suggestion", "No suggestion generated")
        }
        combined.append(combined_row)

    return combined

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python save_to_sheets.py <contract.pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    try:
        print("🔎 Extracting clauses...")
        clauses = ingest_contract(pdf_path)

        if not clauses:
            print("❌ No clauses extracted from PDF")
            sys.exit(1)

        print(f"✅ Extracted {len(clauses)} clauses")

        print("📊 Analyzing clauses...")
        analysis_results = analyze_clauses(clauses)

        print(f"✅ Analysis complete: {len(analysis_results)} results")

        print("💡 Generating suggestions...")
        suggestions = generate_suggestions(analysis_results)

        print(f"✅ Suggestions complete: {len(suggestions)} suggestions")

        print("🔄 Processing data for Google Sheets...")
        combined_data = process_contract_data(clauses, analysis_results, suggestions)

        print("📝 Saving results to Google Sheets...")
        sheet_name = generate_sheet_name(pdf_path)
        print(f"🏷️ Generated sheet name: {sheet_name}")
        final_sheet_name = save_to_google_sheets(combined_data, sheet_name)

        print("🎉 Process completed successfully!")
        print(f"\n📋 Summary:")
        print(f"   📄 Contract processed: {os.path.basename(pdf_path)}")
        print(f"   📊 Sheet created: {final_sheet_name}")
        print(f"   📄 Clauses extracted: {len(clauses)}")
        print(f"   📊 Analysis results: {len(analysis_results)}")
        print(f"   💡 Suggestions generated: {len(suggestions)}")
        print(f"   📝 Rows saved to sheets: {len(combined_data)}")

    except Exception as e:
        print(f"❌ Process failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
