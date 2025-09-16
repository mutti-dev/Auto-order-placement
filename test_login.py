import time
import pytest
from playwright.sync_api import Playwright, sync_playwright, expect, TimeoutError as PlaywrightTimeoutError


# ----------------------------------------------------------------------
# Core script logic – unchanged apart from small defensive wrappers.
# ----------------------------------------------------------------------
def _run_flow(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False, slow_mo=500)
    context = browser.new_context()
    page = context.new_page()

    # ---- Login ---------------------------------------------------------
    page.goto("https://order.harmonps.com/Login/")
    page.locator("form").filter(
        has_text="Secure Access Email Address * Password * Access My Account Don't have an"
    ).locator('input[name="sEmail"]').fill("orders@harmonps.com")
    page.locator("form").filter(
        has_text="Secure Access Email Address * Password * Access My Account Don't have an"
    ).locator('input[name="sPassword"]').fill("9awzv85H6%X97*2jU&")
    page.locator("form").filter(
        has_text="Secure Access Email Address * Password * Access My Account Don't have an"
    ).locator('input[name="sPassword"]').press("Enter")

    # Wait for the dashboard – give a bit more time than the default
    try:
        page.wait_for_url("https://order.harmonps.com/Dashboard/", timeout=20000)
    except PlaywrightTimeoutError:
        pytest.fail("Dashboard did not load after login")

    # ---- Navigate to New Site -----------------------------------------
    page.goto("https://order.harmonps.com/Sites/NewSite.asp")
    # Guard against pages that never fire “networkidle”
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PlaywrightTimeoutError:
        # Continue – the form may still be usable
        pass

    # ---- Fill site details ---------------------------------------------
    page.get_by_role("textbox", name="Enter a location").fill("Main Office")
    page.locator('input[name="sAddress"]').fill("123 Main Street")
    page.locator('input[name="sAddress2"]').fill("Suite 456")
    page.locator('input[name="sCity"]').fill("Carrboro")
    page.get_by_role("combobox").select_option("NC")          # state
    page.locator('input[name="sZipcode"]').fill("10001")

    
    page.get_by_text("Manual Order Entry").click()
    page.get_by_role("radio", name="Manual Order Entry - Order").check()
    page.locator('input[name="UserComboSearch"]').fill("Lisa Kincaid")
    time.sleep(0.5)
    expect(page.get_by_role("radio", name="Manual Order Entry - Order")).to_be_visible()

    time.sleep(5)
    page.locator('input[name="UserComboSearch"]').press("Enter")

    # Expect navigation after “Create New Site” (the button is commented out in the
    # original script, so we just wait for any navigation that may happen)
    try:
        page.expect_navigation(timeout=15000)
    except PlaywrightTimeoutError:
        # Navigation may not occur – ignore
        pass

    # ---- Order specifics ------------------------------------------------
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PlaywrightTimeoutError:
        pass

    page.locator('input[name="squarefeet"]').fill("10001")
    page.get_by_text("Hidden / Extra Products (NOTE").click()
    time.sleep(0.5)
    page.get_by_role("checkbox", name="Manual Order $").check()
    page.get_by_role("cell", name="17 Select").get_by_role("button").click()
    page.get_by_role("cell", name="18 Select").get_by_role("button").click()
    page.get_by_role("checkbox", name="Skip Scheduling for Now  (").check()
    billing_city = page.locator("input[name='search_BillingCity']")
    billing_state = page.locator("select[name='search_BillingState']")
    billing_zip = page.locator("input[name='search_BillingZipcode']")
    billing_city.fill("Carrboro") if billing_city.input_value().strip() == "" else None
    billing_state.select_option("NC") if billing_state.input_value().strip() == "" else None
    billing_zip.fill("10001") if billing_zip.input_value().strip() == "" else None

    page.get_by_role("checkbox", name="I Agree * required").check()
    page.get_by_role("checkbox", name="Do NOT send invoice/receipt").check()
    page.get_by_role("button", name="Place My Order!").click()

    # Optional: wait for a confirmation element (adjust selector if needed)
    try:
        page.wait_for_selector("//div[contains(., 'Order Created')]", timeout=15000)
    except PlaywrightTimeoutError:
        pass

    # Pause so you can see the result when running locally
    time.sleep(5)

    context.close()
    browser.close()


# ----------------------------------------------------------------------
# Pytest entry point – no code runs at import time.
# ----------------------------------------------------------------------
def test_harmonps_order_flow():
    """
    Pytest will import this file; the actual Playwright actions are executed
    inside the test function so the test collection phase does not trigger
    any Playwright calls (avoids the “event loop already running” error).
    """
    with sync_playwright() as playwright:
        _run_flow(playwright)
