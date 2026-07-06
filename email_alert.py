"""
email_alert.py — sends a Google-style security-alert email to the logged-in
operator. The email includes a "This was a false alarm" BUTTON; clicking it hits
the /dismiss route in app.py and marks the alert false in the database directly
(just like Google's "No, it wasn't me" button). No reply, no login needed.
"""
import smtplib
from email.message import EmailMessage
from datetime import datetime

SENDER   = "surveillancesystem077@gmail.com"          # the Gmail that sends alerts
APP_PASS = "abfh myyc kugr njhk"    # Gmail App Password (no spaces)
SYSTEM_NAME = "Surveillance System"       # shows as the sender NAME (not your raw email)

# where your Flask app is reachable. Use your LAN IP (e.g. http://192.168.1.5:5000)
# if you want to click the button from a PHONE on the same wifi.
BASE_URL = "http://192.168.18.6"
DISMISS_SECRET = "kec_surveillance_2026"  # MUST match the value in app.py


def send_email_alert(to_email, message, alert_id):
    """Email the operator on a real threat, with a one-click 'false alarm' button."""
    if not to_email:
        return
    time_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    dismiss_url = f"{BASE_URL}/dismiss/{alert_id}/{DISMISS_SECRET}"
    try:
        msg = EmailMessage()
        msg["Subject"] = f"Security Alert: {message} [ID:{alert_id}]"
        msg["From"] = f"{SYSTEM_NAME} <{SENDER}>"
        msg["To"] = to_email

        # plain-text fallback (includes the link too)
        msg.set_content(
            f"SECURITY ALERT\n\n{message}\n\n"
            f"Alert ID: {alert_id}\nTime: {time_str}\n\n"
            f"If this was NOT a real threat, click to dismiss it:\n{dismiss_url}\n\n"
            f"-- Automated notification, {SYSTEM_NAME}"
        )

        # HTML version with the one-click button
        html = f"""
        <div style="font-family:Arial,Helvetica,sans-serif; max-width:480px; margin:auto;
                    border:1px solid #e0e0e0; border-radius:10px; overflow:hidden;">
          <div style="background:#d93025; color:#ffffff; padding:16px 22px;">
            <h2 style="margin:0; font-size:18px;">&#9888;&nbsp; Security Alert</h2>
          </div>
          <div style="padding:22px; color:#202124;">
            <p style="font-size:15px; margin-top:0;">
              A security event was detected on your monitored surveillance feed.
            </p>
            <table style="width:100%; border-collapse:collapse; font-size:14px; margin:14px 0;">
              <tr><td style="padding:8px 0; color:#5f6368;">Event</td>
                  <td style="padding:8px 0; font-weight:bold;">{message}</td></tr>
              <tr><td style="padding:8px 0; color:#5f6368;">Alert ID</td>
                  <td style="padding:8px 0;">#{alert_id}</td></tr>
              <tr><td style="padding:8px 0; color:#5f6368;">Time</td>
                  <td style="padding:8px 0;">{time_str}</td></tr>
            </table>
            <p style="font-size:13.5px; color:#5f6368;">Was this a real threat?</p>
            <a href="{dismiss_url}"
               style="display:inline-block; background:#ffffff; color:#d93025;
                      border:1px solid #d93025; text-decoration:none; padding:10px 20px;
                      border-radius:6px; font-size:14px; font-weight:bold;">
              No, it was a false alarm
            </a>
          </div>
          <div style="background:#f8f9fa; padding:12px 20px; font-size:12px;
                      color:#9aa0a6; text-align:center;">
            Automated notification &middot; {SYSTEM_NAME}
          </div>
        </div>
        """
        msg.add_alternative(html, subtype="html")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER, APP_PASS)
            server.send_message(msg)
        print("[EMAIL] sent to", to_email)
    except Exception as e:
        print("[EMAIL] failed:", e)