# v75 · Test 5 retest only — Guest access and invitations

Start `python3 start.py` in this extracted folder. Visit `http://127.0.0.1:8765/`, switch to Integration and open a sample flight such as EK232 in Live. The **Test failure scenario** dropdown is outside the phone. These tests are entirely local and use `[TEST DATA]`, not Wordly.

1. **Healthy fixture:** confirm a guest joins with **no login** and one `[TEST DATA]` caption appears. Account-free discovery need not require an invitation.
2. **Revoke guest:** select `Revoke guest` and click **Run test**. Live must visibly say `ACCESS BLOCKED`; the old caption must disappear. You may still change flight or navigate public pages, but **you must not receive a test caption** or a connected guest state. Try another flight while the scenario remains revoked: still no guest caption.
3. **Invalid invitation:** select `Invalid invitation` and click **Run test**. Old captions clear and no new guest join is allowed even on the no-invite fixture path. The translated-content panel must not present a connected state. Ordinary flight search remains accessible.
4. **Restore Healthy fixture:** select Healthy and click **Run test**. Select a flight again as needed. A new test guest may join and show a new `[TEST DATA]` caption. Old denied grants must not be reused.
5. **Matching invitation:** open `http://127.0.0.1:8765/?lx_invite=DEMO-EK232` in a fresh tab/session. Choose EK232, then enter Live in Integration mode. A matching test session may join without requiring an account.
6. **Cross-flight invitation:** with the EK232 invitation still in the URL, choose a **different** flight (such as DL206). Live must say `ACCESS BLOCKED · Invitation belongs to a different flight`; no fixture caption or connected guest state may appear. Public navigation may still work.

**What counts as a failure:** any protected fixture caption or a genuinely connected translation guest session under revoke, invalid invite, or mismatched flight. Simply reaching the Live *screen* is not unauthorized translation access.

Reply with each step's pass/fail and any notes. Your previously passed Tests 1–4 and 6 do not need repetition.
