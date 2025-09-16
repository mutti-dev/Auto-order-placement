import os
import asyncio
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError          # <-- new import
from playwright.async_api import async_playwright

# ---------- CONFIG ----------
SPREADSHEET_ID = '1mAYW47RZaAHRThY35N7uh6K9J_59SO0t3hpXlg7dn5s'
SHEET_NAME = 'Orders'
SERVICE_ACCOUNT_FILE = 'service-account.json'
HARMON_URL = 'https://order.harmonps.com/Login/'

# Added Drive scope (full access) in addition to Sheets scope
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'   # <-- new: allows read/write on shared sheets
]

# Column indices (1-based)
COL_STATUS = 11        
COL_RESULT = 12        
COL_PROCESSED_AT = 14 

# ---------- Google Sheets helpers ----------
print("[DEBUG] Loading credentials...")
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
sheets_service = build('sheets', 'v4', credentials=creds)
sheet = sheets_service.spreadsheets()
print(f"[DEBUG] Connected to Google Sheets API with service account: {creds.service_account_email}")

def col_letter(col: int) -> str:
    letters = ''
    while col:
        col, rem = divmod(col-1, 26)
        letters = chr(65+rem) + letters
    return letters

def read_orders():
    """Read rows from the Orders sheet. Raises a clear error if the service-account
    lacks permission on the spreadsheet."""
    range_name = f"{SHEET_NAME}!A2:Z"
    print(f"[DEBUG] Reading rows from range: {range_name} in sheet {SPREADSHEET_ID}")
    try:
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                   range=range_name).execute()
    except HttpError as err:
        print(f"[DEBUG] HttpError while reading rows: {err}")
        if err.resp.status == 403:
            raise PermissionError(
                f"The service account does not have access to spreadsheet "
                f"{SPREADSHEET_ID}. Share the sheet with "
                f"{creds.service_account_email} or use a sheet the account can read."
            )
        raise
    values = result.get('values', [])
    print(f"[DEBUG] Retrieved {len(values)} rows from sheet.")
    return values

def update_row(row_idx, col_idx, value):
    range_name = f"{SHEET_NAME}!{col_letter(col_idx)}{row_idx}"
    print(f"[DEBUG] Updating row {row_idx}, col {col_idx} ({range_name}) with value: {value}")
    body = {'values': [[value]]}
    sheet.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=range_name,
        valueInputOption='RAW',
        body=body
    ).execute()

# ---------- Playwright order filler ----------
async def fill_order(page, order):
    """
    order is a list of values from the sheet row.
    Adjust indexes according to your sheet columns.
    """
    client_name = order[1] if len(order) > 1 else ''
    address = order[2] if len(order) > 2 else ''
    city = order[3] if len(order) > 3 else ''
    state = order[4] if len(order) > 4 else ''
    zip_code = order[5] if len(order) > 5 else ''
    sqft = order[6] if len(order) > 6 else ''
    package_name = order[7] if len(order) > 7 else ''

    print(f"[DEBUG] Starting order fill: {client_name}, {address}, {city}, {state}, {zip_code}, sqft={sqft}, package={package_name}")

    await page.goto(HARMON_URL)
    print(f"[DEBUG] Navigated to {HARMON_URL}")

    # Fill form fields (adjust selectors based on inspection)
    await page.fill('input[name="ClientName"]', client_name)
    await page.fill('input[name="Address"]', address)
    await page.fill('input[name="City"]', city)
    await page.select_option('select[name="State"]', label=state)
    await page.fill('input[name="Zip"]', zip_code)
    await page.fill('input[name="SquareFeet"]', sqft)

    # Select service package
    if package_name:
        try:
            await page.click(f'//label[contains(text(), "{package_name}")]')
            print(f"[DEBUG] Selected package: {package_name}")
        except:
            print(f"[DEBUG] Package not found: {package_name}")

    # Confirm address if button exists
    try:
        await page.click('//button[contains(., "Confirm Address")]')
        print("[DEBUG] Clicked confirm address button")
    except:
        print("[DEBUG] No confirm address button found")

    # Submit the form
    await page.click('button[type="submit"]')
    print("[DEBUG] Submitted form, waiting for response...")

    # Wait for success or error
    try:
        await page.wait_for_selector('//div[contains(., "Order Created")]', timeout=10000)
        print("[DEBUG] Order created successfully")
        return "ORDER_SUCCESS"
    except:
        try:
            err_text = await page.inner_text('.error')
            print(f"[DEBUG] Error detected after submit: {err_text}")
            return f"ERROR: {err_text}"
        except:
            print("[DEBUG] Unknown error after submit")
            return "ERROR: unknown after submit"

# ---------- Main runner ----------
async def main(override_sheet_id: str = None):
    # Allow the webhook to override the spreadsheet ID
    global SPREADSHEET_ID
    if override_sheet_id:
        SPREADSHEET_ID = override_sheet_id
        print(f"[DEBUG] Overriding SPREADSHEET_ID with: {SPREADSHEET_ID}")

    print("[DEBUG] Reading orders...")
    rows = read_orders()
    row_number = 2

    async with async_playwright() as p:
        print("[DEBUG] Launching Chromium browser...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        for r in rows:
            status = r[10] if len(r) > 10 else ''
            print(f"[DEBUG] Processing row {row_number}, current status: {status} and rows data: {r}")

            
            if status.strip().upper() != 'PENDING':
                print(f"[DEBUG] Skipping row {row_number} (status not PENDING)")
                row_number += 1
                continue

            update_row(row_number, COL_STATUS, 'IN_PROGRESS')

            try:
                result = await fill_order(page, r)
                update_row(row_number, COL_RESULT, result)
                update_row(row_number, COL_STATUS,
                           'DONE' if 'ORDER_SUCCESS' in result else 'FAILED')
                update_row(row_number, COL_PROCESSED_AT,
                           datetime.utcnow().isoformat())
                print(f"[DEBUG] Row {row_number} processed: {result}")
            except Exception as e:
                update_row(row_number, COL_RESULT, f"EXCEPTION: {str(e)}")
                update_row(row_number, COL_STATUS, 'FAILED')
                print(f"[DEBUG] Exception processing row {row_number}: {e}")
            row_number += 1

        await browser.close()
        print("[DEBUG] Browser closed, all done!")

if __name__ == '__main__':
    print("[DEBUG] Starting main()")
    asyncio.run(main())
