def organization_invite_template(
    inviter_name: str,
    inviter_email: str,
    organization_name: str,
    invite_link: str,
    expires_at: str,
) -> str:
    expires_at_str = expires_at.strftime("%B %d, %Y, %I:%M %p (UTC)")

    return f"""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html dir="ltr" lang="en">
  <head>
    <meta content="text/html; charset=UTF-8" http-equiv="Content-Type" />
    <meta name="x-apple-disable-message-reformatting" />
  </head>
  <body>
    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="width:100% !important;">
      <tr><td align="center">
        <table style="border:1px solid #eaeaea; border-radius:5px; margin:40px 0;" width="600" border="0" cellspacing="0" cellpadding="40">
          <tr>
            <td align="center">
              <div style="font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif; text-align:left; width:465px;">
                
                <!-- Logo Section -->
                <table width="100%" border="0" cellspacing="0" cellpadding="0" style="width:100% !important;">
                  <tr><td align="center">
                    <img src="https://textfully.dev/icon.png" width="40" height="40" alt="Textfully Logo" />
                    <h2 style="color:#000000; font-size:24px; font-weight:normal; margin:30px 0; padding:0;">Join <b>{organization_name}</b> on <b>Textfully</b></h2>
                  </td></tr>
                </table>

                <!-- Message Section -->
                <p style="color:#000000; font-size:14px; line-height:24px;">
                  Hello!
                </p>
                <p style="color:#000000; font-size:14px; line-height:24px;">
                  <b>{inviter_name}</b> ({inviter_email}) has invited you to join <b>{organization_name}</b> on <b>Textfully</b>. Click the button below to accept the invitation:
                </p>

                <!-- Button Section -->
                <table width="100%" border="0" cellspacing="0" cellpadding="0" style="width:100% !important;">
                  <tr>
                    <td align="center" bgcolor="#0A93F6" valign="middle" height="40" style="font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif; font-size:16px; font-weight:bold;">
                      <a href="{invite_link}" style="color:#FFFFFF; text-decoration:none; display:inline-block; padding:10px 0px; width:100%; background-color:#0A93F6; border-radius:5px;">Join Organization</a>
                    </td>
                  </tr>
                </table>

                <!-- Display Full URL -->
                <p style="color:#0A93F6; font-size:14px; line-height:24px; word-break:break-word; margin-top:20px;">
                  <a href="{invite_link}" style="color:#0A93F6; text-decoration:none;">{invite_link}</a>
                </p>

                <!-- Footer Section -->
                <hr style="border:none; border-top:1px solid #eaeaea; margin:26px 0; width:100%;" />
                <p style="color:#666666; font-size:12px; line-height:24px;">
                  This invitation was sent on {expires_at_str} and will expire in 72 hours. This invitation should not be shared. If you didn't expect this invitation, please ignore this email. For help, please reach out to
                  <a href="mailto:textfully@gtfol.dev" style="color:#0A93F6; text-decoration:none;">textfully@gtfol.dev</a>.
                </p>
              </div>
            </td>
          </tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>
""".format(
        inviter_name=inviter_name,
        inviter_email=inviter_email,
        organization_name=organization_name,
        invite_link=invite_link,
    )
