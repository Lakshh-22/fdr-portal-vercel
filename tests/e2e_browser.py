# Real-browser end-to-end test (needs: pip install playwright && playwright install chromium, and the server running on :8000)
from playwright.sync_api import sync_playwright
B = "http://localhost:8000/"; errs = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None); pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
    pg.goto(B); pg.wait_for_timeout(500)
    print("1 theme label (light):", pg.inner_text("#thl").strip())
    pg.click("#thl"); print("2 after click:", pg.inner_text("#thl").strip(), "| data-theme =", pg.evaluate("document.documentElement.dataset.theme"))
    pg.click("#thl"); pg.click("#thl")                                   # back to light then dark again
    pg.keyboard.type("") ; pg.click("#u"); pg.keyboard.type("official"); pg.click("#pw"); pg.keyboard.type("official123")
    print("3 typed password length:", len(pg.input_value("#pw")), "(must be 11)")
    pg.keyboard.press("Enter"); pg.wait_for_selector("#shell", state="visible", timeout=5000); pg.wait_for_selector(".stats")
    print("4 logged in by typing + Enter; dashboard cards:", pg.locator(".st").count(), "| top-bar theme:", pg.inner_text("#thb").strip())
    pg.screenshot(path="/tmp/dash_dark.png")
    for label in ["Institutions", "FDR Management", "Verification", "Maturity Tracking", "Notifications", "Renewals", "Release Requests", "Reports", "Audit Log", "Dashboard"]:
        pg.click(f"#nav button:has-text('{label}')"); pg.wait_for_timeout(350)
    print("5 clicked all 10 pages, h1 now:", pg.inner_text("#page h1"))
    pg.click("#lo2"); pg.wait_for_selector("#login", state="visible"); print("6 after sign-out: theme kept =", pg.evaluate("document.documentElement.dataset.theme"), "| fields cleared =", pg.input_value("#u") == "" and pg.input_value("#pw") == "")
    # registration via UI
    pg.click("a[data-a=regshow]"); pg.fill("#gn", "Maple Valley College"); pg.fill("#ge", "office@maple.example"); pg.fill("#gu", "maple"); pg.click("#gw"); pg.keyboard.type("password123")
    pg.click("button[data-a=regsub]"); pg.wait_for_timeout(600); print("7 register msg:", pg.inner_text("#rmsg"))
    pg.click("a[data-a=regback]"); pg.click("#u"); pg.keyboard.type("maple"); pg.click("#pw"); pg.keyboard.type("password123"); pg.click("#go"); pg.wait_for_timeout(500); print("8 login before approval:", pg.inner_text("#le"))
    pg.fill("#u", "official"); pg.fill("#pw", "official123"); pg.click("#go"); pg.wait_for_selector(".stats")
    print("9 Institutions nav badge:", pg.inner_text("#nav button:has-text('Institutions')").replace("\n", " "))
    pg.click("#nav button:has-text('Institutions')"); pg.wait_for_selector("text=Registration requests"); pg.click("button[data-a=rga]"); pg.wait_for_timeout(600); print("10 approved; registration card gone:", pg.locator("text=Registration requests").count() == 0)
    pg.click("#lo2"); pg.click("#u"); pg.keyboard.type("maple"); pg.click("#pw"); pg.keyboard.type("password123"); pg.keyboard.press("Enter"); pg.wait_for_selector(".stats", timeout=5000)
    print("11 new institution logged in, FDR total card:", pg.locator(".st b").first.inner_text(), "| nav items:", pg.locator("#nav .nl").count())
    # OCR UI without internet: must fail gracefully
    pg.click("#nav button:has-text('FDR Management')"); pg.click("button[data-a=addf]"); pg.set_input_files("#fl", "/mnt/user-data/outputs/ocr-samples/1_sample_fdr_indian_bank.png"); pg.wait_for_timeout(2500)
    print("12 OCR (offline here) message:", pg.inner_text("#msg")[:110])
    b.close()
print("console/page errors:", [e for e in errs if "ERR_" not in e and "Failed to load resource" not in e] or "none")
