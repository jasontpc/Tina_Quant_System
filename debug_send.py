d = open('streamlit_tw_stock.py', encoding='utf-8').read()

# The TW was replaced successfully. US pattern failed because file changed.
# Let's try to find US block with a shorter pattern.

# Find the US DEBUG line and get surrounding context
idx = d.find('DEBUG: US Send button rendering now')
if idx >= 0:
    print(f"US DEBUG at {idx}")
    print(repr(d[idx-100:idx+400]))
    print()

# Try replacing with just the button block (shorter pattern)
old_us = 'col1, _ = st.columns([1, 4])\n            if col1.button("Send Telegram", use_container_width=True):\n                st.info("US send clicked")\n                st.info(f"DEBUG chat_id={TELEGRAM_CHAT_ID} token_len={len(TELEGRAM_BOT_TOKEN)}")\n                try:\n                    ok, err = push_telegram(msg)\n                    st.info(f"ok={ok} err={err}")\n                except Exception as ex:\n                    st.error(f"ex={ex}")\n                else:\n                    if ok:\n                        st.success("Telegram sent!")\n                    else:\n                        st.error(f"Failed: {err}")'

new_us = 'col1, _ = st.columns([1, 4])\n            with st.form(key="us_single_tg_form", clear_on_submit=False):\n                submitted = st.form_submit_button("Send Telegram", use_container_width=True)\n                st.write(f"DEBUG: submitted={submitted}")\n                if submitted:\n                    st.info("US form submitted!")\n                    st.info(f"DEBUG chat_id={TELEGRAM_CHAT_ID} token_len={len(TELEGRAM_BOT_TOKEN)}")\n                    try:\n                        ok, err = push_telegram(msg)\n                        st.info(f"ok={ok} err={err}")\n                    except Exception as ex:\n                        st.error(f"ex={ex}")\n                    else:\n                        if ok:\n                            st.success("Telegram sent!")\n                        else:\n                            st.error(f"Failed: {err}")'

if old_us in d:
    d = d.replace(old_us, new_us, 1)
    print("US replaced")
else:
    print("US old pattern not found")
    # Let's find what's actually there
    idx2 = d.find('if col1.button("Send Telegram", use_container_width=True)')
    print(f"Button found at: {idx2}")
    print(repr(d[idx2:idx2+500]))

open('streamlit_tw_stock.py', 'w', encoding='utf-8').write(d)
print("Done")