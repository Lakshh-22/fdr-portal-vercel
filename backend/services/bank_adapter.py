"""Bank verification adapter. Demo: looks up the bank_registry table.
Replace `lookup` with a call to the issuing bank's verification API when formally authorised;
keep the return shape (bank, amount, maturity_date) and nothing else in the portal changes."""


def lookup(c, fdr_number): return c.execute("SELECT * FROM bank_registry WHERE fdr_number=?", (fdr_number,)).fetchone()
