# order_processor.py

import os
import time
import asyncio
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime, timedelta

# ---------- CONFIG ----------
SPREADSHEET_ID = '1mAYW47RZaAHRThY35N7uh6K9J_59SO0t3hpXlg7dn5s'  # update with your ID
RANGE_NAME = 'Orders!A2:M'

HARMON_URL = "https://order.harmonps.com/Login/"

# Column mappings (1-based like Sheets)
COL_CLIENT_NAME = 1
COL_ADDRESS = 2
COL_CITY = 3
COL_STATE = 4
COL_ZIP = 5
COL_SQFT = 6
COL_BILL_CITY = 7
COL_BILL_STATE = 8
COL_BILL_ZIP = 9
COL_STATUS = 10

# ---------- GOOGLE SHEETS ----------
def get_service():
    creds = Credentials.from_service_account_file(
        "service-account.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return build("sheets", "v4", credentials=creds)

def get_orders():
    try:
        service = get_service()
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME)
            .execute()
        )
        return result.get("values", [])
    except HttpError as err:
        print(f"Google Sheets API error: {err}")
        return []

def mark_order_processed(row_index, status):
    """Mark the row as processed with timestamp."""
    try:
        service = get_service()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body = {"values": [[status, now]]}
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"Orders!M{row_index+2}:N{row_index+2}",  # M=status, N=timestamp
            valueInputOption="RAW",
            body=body,
        ).execute()
    except HttpError as err:
        print(f"Failed to update sheet: {err}")

# ---------- HARMON LOGIN ----------
async def login(page):
    email = os.getenv("HARMON_USER", "orders@harmonps.com")
    password = os.getenv("HARMON_PASS", "9awzv85H6%X97*2jU&")

    await page.goto(HARMON_URL)

    form = page.locator("form").filter(
        has_text="Secure Access Email Address * Password * Access My Account Don't have an"
    )
    await form.locator('input[name="sEmail"]').fill(email)
    await form.locator('input[name="sPassword"]').fill(password)
    await form.locator('input[name="sPassword"]').press("Enter")

    # wait for dashboard
    await page.wait_for_url("https://order.harmonps.com/Dashboard/", timeout=60000)

# ---------- ORDER FILLING ----------
async def fill_order(page, order):
    """Fill the order form with row data from Sheets."""

    # extract fields safely
    client_name   = order[COL_CLIENT_NAME]
    address       = order[COL_ADDRESS]
    city          = order[COL_CITY]
    state         = order[COL_STATE]
    zip_code      = order[COL_ZIP]
    sqft          = order[COL_SQFT]
    billing_city  = order[COL_BILL_CITY]
    billing_state = order[COL_BILL_STATE]
    billing_zip   = order[COL_BILL_ZIP]


    print(f"Filling order for {client_name} and index {COL_CLIENT_NAME}")

    # ---- Navigate to New Site -----------------------------------------
    await page.goto("https://order.harmonps.com/Sites/NewSite.asp",
                    timeout=60000, wait_until="networkidle")

    try:
        await page.wait_for_load_state("networkidle")
    except:
        pass

    # ---- Fill site details ---------------------------------------------
    # await page.get_by_role("textbox", name="Enter a location").fill("Main Office")
    await page.locator('input[name="sAddress"]').fill(address or "123 Main Street")
    await page.locator('input[name="sAddress2"]').fill("Suite 456")
    await page.locator('input[name="sCity"]').fill(city or "Carrboro")
    await page.get_by_role("combobox").select_option(state or "NC")
    await page.locator('input[name="sZipcode"]').fill(zip_code or "10001")

    # ---- Manual Order Entry --------------------------------------------
    await page.get_by_text("Manual Order Entry").click()
    await page.get_by_role("radio", name="Manual Order Entry - Order").check()

    if client_name:
        
        await page.locator('input[name="UserComboSearch"]').fill(client_name)
        time.sleep(0.5)
        await page.get_by_role("listitem").first.click()


    await page.get_by_role("button", name="Create New Site").click()

    # await page.wait_for_load_state("networkidle", timeout=60000)
       

    # ---- Order specifics -----------------------------------------------
    await page.locator('input[name="squarefeet"]').fill(sqft or "10001")
    await page.get_by_text("Hidden / Extra Products (NOTE").click()
    await page.wait_for_timeout(500)
    await page.get_by_role("checkbox", name="Manual Order $").check()

    today_day = datetime.today().day
    for offset in [1, 2]:
        day_to_select = today_day + offset
        locator = page.get_by_role("cell", name=f"{day_to_select} Select").get_by_role("button")
        await locator.click()
    # await page.get_by_role("cell", name="17 Select").get_by_role("button").click()
    # await page.get_by_role("cell", name="18 Select").get_by_role("button").click()
    await page.get_by_role("checkbox", name="Skip Scheduling for Now  (").check()

  
    await page.locator("input[name='search_BillingCity']").fill(city or "123 Main Street")

   

    await page.locator("select[name='search_BillingState']").select_option(state or "NC")

  
    await page.locator("input[name='search_BillingZipcode']").fill(zip_code or "10001")

    # ---- Final confirmations -------------------------------------------
    await page.get_by_role("checkbox", name="I Agree * required").check()
    await page.get_by_role("checkbox", name="Do NOT send invoice/receipt").check()

    # ---- Place order ---------------------------------------------------
    await page.get_by_role("button", name="Place My Order!").click()

    # ---- Confirm -------------------------------------------------------
    try:
        await page.get_by_text("Your order has been placed.").wait_for(timeout=30000)
        return "ORDER_SUCCESS"
    except:
        return "ERROR: No confirmation"

# ---------- MAIN RUNNER ----------
async def main():
    orders = get_orders()
    if not orders:
        print("No orders found.")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await login(page)

        for i, order in enumerate(orders):
            try:
                status = await fill_order(page, order)
                mark_order_processed(i, status)
                print(f"Row {i+2}: {status}")
            except Exception as e:
                print(f"Row {i+2}: ERROR {e}")
                mark_order_processed(i, f"ERROR: {e}")

        await browser.close()

async def main(*args, **kwargs):
    orders = get_orders()
    if not orders:
        print("No orders found.")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await login(page)

        for i, order in enumerate(orders):
            try:
                status = await fill_order(page, order)
                if status == "ORDER_SUCCESS":
                    mark_order_processed(i, "COMPLETED")
                else:
                    mark_order_processed(i, status)
                print(f"Row {i+2}: {status}")
            except Exception as e:
                print(f"Row {i+2}: ERROR {e}")
                mark_order_processed(i, f"ERROR: {e}")

        await browser.close()

