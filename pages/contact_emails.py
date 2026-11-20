"""The emails sent by the contact form, both built on one layout that follows the website's design.

The visitor's confirmation never repeats the message itself: anyone can type someone else's address
in the form, and a copy of free text would let the form be used to send spam to strangers.
"""
import re
from html import escape
from urllib.parse import quote

SITE_URL = "https://andreafrancin.com"
# Sent inside each email as an inline attachment (see contact_mail.HEADER_CONTENT_ID).
HEADER_IMAGE = "cid:andrea-francin-header"
INSTAGRAM_URL = "https://www.instagram.com/andreafrancin.art"

FONT = "'Inter',-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
TEXT = "#141516"
TEXT_2 = "#4b4650"
TEXT_3 = "#6d6673"
LINE = "#eee5ec"
SURFACE_2 = "#f8f3f7"
ACCENT = "#bc0e4d"
PAGE = "#fbf6fa"

CONFIRMATION = {
    "es": {
        "subject": "He recibido tu mensaje",
        "greeting": "¡Gracias, {name}!",
        "greeting_anonymous": "¡Gracias por escribir!",
        "lead": "He recibido tu mensaje y te responderé lo antes posible, normalmente en uno o dos días laborables.",
        "service": "Servicio que te interesa",
        "next": "Mientras tanto, puedes ver más proyectos en el portfolio. Si quieres añadir algo, solo tienes que responder a este correo.",
        "button": "Ver el portfolio",
        "signature": "Un abrazo,",
        "footer": "Recibes este correo porque se ha enviado el formulario de contacto de andreafrancin.com con esta dirección. No recibirás publicidad. Si no has sido tú, puedes ignorarlo.",
        "privacy": "Política de privacidad",
        "privacy_anchor": "privacidad",
    },
    "ca": {
        "subject": "He rebut el teu missatge",
        "greeting": "Gràcies, {name}!",
        "greeting_anonymous": "Gràcies per escriure!",
        "lead": "He rebut el teu missatge i et respondré tan aviat com pugui, normalment en un o dos dies feiners.",
        "service": "Servei que t’interessa",
        "next": "Mentrestant, pots veure més projectes al portfoli. Si vols afegir alguna cosa, només has de respondre aquest correu.",
        "button": "Veure el portfoli",
        "signature": "Una abraçada,",
        "footer": "Reps aquest correu perquè s’ha enviat el formulari de contacte d’andreafrancin.com amb aquesta adreça. No rebràs publicitat. Si no has estat tu, pots ignorar-lo.",
        "privacy": "Política de privacitat",
        "privacy_anchor": "privacitat",
    },
    "en": {
        "subject": "I’ve received your message",
        "greeting": "Thank you, {name}!",
        "greeting_anonymous": "Thank you for writing!",
        "lead": "I’ve received your message and I’ll get back to you as soon as I can, usually within one or two working days.",
        "service": "Service you’re interested in",
        "next": "In the meantime, you can see more projects in the portfolio. If you’d like to add anything, just reply to this email.",
        "button": "See the portfolio",
        "signature": "Best wishes,",
        "footer": "You’re receiving this email because the contact form on andreafrancin.com was sent with this address. You won’t receive any advertising. If it wasn’t you, you can ignore it.",
        "privacy": "Privacy policy",
        "privacy_anchor": "privacy",
    },
}

LANGUAGE_NAMES = {"es": "Español", "ca": "Català", "en": "English"}

# Only a plain first name is greeted; anything that looks like a link or an address is left out.
NAME_PATTERN = re.compile(r"^[^\W\d_][\w'’\- ]{0,39}$", re.UNICODE)


def greeting_name(name: str) -> str | None:
    first = name.strip().split(" ")[0] if name.strip() else ""
    return first if NAME_PATTERN.match(first) else None


# ---------- Building blocks ----------

# Gmail's apps recolour emails in dark mode whatever the email asks for. Backgrounds and text are
# plain colours so that, when it does, both change together and the text stays readable.
def _bg(color: str) -> str:
    return f"background-color:{color};"


def _row(content: str, padding: str = "0 40px 28px") -> str:
    return f'<tr><td class="pad" style="padding:{padding};">{content}</td></tr>'


def _paragraph(text: str, color: str = TEXT_2) -> str:
    return f'<p style="margin:0;font-size:16px;line-height:26px;color:{color};">{text}</p>'


def _eyebrow(text: str) -> str:
    return (
        f'<p style="margin:0 0 6px;font-size:11px;line-height:16px;font-weight:700;letter-spacing:0.12em;'
        f'text-transform:uppercase;color:{TEXT_3};">{escape(text)}</p>'
    )


def _panel(inner: str) -> str:
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="{_bg(SURFACE_2)}border-radius:16px;"><tr><td style="padding:18px 20px;">{inner}</td></tr></table>'
    )


def _button(label: str, href: str) -> str:
    return (
        f'<a href="{escape(href)}" style="display:inline-block;padding:14px 26px;border-radius:999px;'
        f'{_bg(ACCENT)}color:#ffffff;font-size:15px;line-height:20px;font-weight:600;'
        f'text-decoration:none;">{escape(label)} &rarr;</a>'
    )


def _layout(language: str, title: str, preheader: str, rows: str, footer: str, home_url: str) -> str:
    return f"""<!doctype html>
<html lang="{escape(language)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light only">
<meta name="supported-color-schemes" content="light only">
<title>{escape(title)}</title>
<style>
  :root {{ color-scheme: light only; supported-color-schemes: light only; }}
  @media (max-width: 480px) {{
    .pad {{ padding-left: 24px !important; padding-right: 24px !important; }}
    .card {{ border-radius: 20px !important; }}
  }}
</style>
</head>
<body class="body" style="margin:0;padding:0;{_bg(PAGE)}">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">{escape(preheader)}</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="{_bg(PAGE)}font-family:{FONT};">
    <tr>
      <td align="center" style="padding:32px 12px;">
        <table role="presentation" class="card" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;{_bg("#ffffff")}border:1px solid {LINE};border-radius:24px;">
          <tr>
            <td align="center" style="padding:36px 32px 4px;">
              <a href="{escape(home_url)}" style="text-decoration:none;">
                <img src="{HEADER_IMAGE}" width="235" height="120" alt="Andrea Francín" style="display:block;width:235px;height:auto;border:0;">
              </a>
            </td>
          </tr>
          <tr><td align="center" style="padding:18px 0 26px;"><div style="width:40px;height:3px;border-radius:3px;{_bg(ACCENT)}"></div></td></tr>
{rows}
          <tr>
            <td class="pad" style="padding:20px 40px 28px;border-top:1px solid {LINE};">{footer}</td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _footer_links(home_url: str, extra: str = "") -> str:
    dot = '<span style="color:#dccfd9;">&nbsp;·&nbsp;</span>'
    links = [
        f'<a href="{escape(home_url)}" style="color:{ACCENT};text-decoration:none;font-weight:600;">andreafrancin.com</a>',
        f'<a href="{INSTAGRAM_URL}" style="color:{ACCENT};text-decoration:none;font-weight:600;">Instagram</a>',
    ]
    if extra:
        links.append(extra)
    return f'<p style="margin:0;font-size:12px;line-height:18px;">{dot.join(links)}</p>'


# ---------- The visitor's confirmation ----------

# The texts Andrea can change in the back office (AutoReply), per language.
AUTO_REPLY_FIELDS = ("subject", "greeting", "greeting_anonymous", "body", "button", "signature")


def default_auto_reply(language: str) -> dict:
    copy = CONFIRMATION.get(language, CONFIRMATION["es"])
    return {
        "subject": f"{copy['subject']} · Andrea Francín",
        "greeting": copy["greeting"],
        "greeting_anonymous": copy["greeting_anonymous"],
        "body": f"{copy['lead']}\n\n{copy['next']}",
        "button": copy["button"],
        "signature": copy["signature"],
    }


def auto_reply_texts(saved: dict | None, language: str) -> dict:
    """Saved texts for one language, with the built-in wording wherever a text is empty."""
    texts = default_auto_reply(language)
    for field in AUTO_REPLY_FIELDS:
        value = ((saved or {}).get(field) or {}).get(language, "")
        if isinstance(value, str) and value.strip():
            texts[field] = value.strip()
    return texts


def _paragraphs(body: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", body.replace("\r\n", "\n")) if p.strip()]


def render_confirmation(
    language: str, name: str, service: str | None, texts: dict | None = None
) -> tuple[str, str, str]:
    """Return the subject, the plain text and the HTML of the confirmation sent to the visitor."""
    if language not in CONFIRMATION:
        language = "es"
    copy = CONFIRMATION[language]
    texts = texts or default_auto_reply(language)
    first = greeting_name(name)
    if first and "{name}" in texts["greeting"]:
        greeting = texts["greeting"].replace("{name}", first)
    else:
        greeting = texts["greeting_anonymous"]
    lang_query = "" if language == "es" else f"?lang={language}"
    work_url = f"{SITE_URL}/work{lang_query}"
    privacy_url = f"{SITE_URL}/legal{lang_query}#{copy['privacy_anchor']}"
    paragraphs = _paragraphs(texts["body"]) or [""]

    def paragraph_html(text: str) -> str:
        return _paragraph(escape(text).replace("\n", "<br>"))

    rows = [
        _row(
            f'<h1 style="margin:0;font-size:26px;line-height:32px;font-weight:600;letter-spacing:-0.01em;color:{TEXT};">{escape(greeting)}</h1>',
            "0 40px 10px",
        ),
        _row(paragraph_html(paragraphs[0])),
    ]
    if service:
        rows.append(_row(_panel(
            _eyebrow(copy["service"])
            + f'<p style="margin:0;font-size:16px;line-height:24px;font-weight:600;color:{TEXT};">{escape(service)}</p>'
        )))
    rows += [_row(paragraph_html(p)) for p in paragraphs[1:]]
    if texts["button"]:
        rows.append(_row(_button(texts["button"], work_url), "0 40px 32px"))
    signature = escape(texts["signature"]).replace("\n", "<br>")
    rows.append(_row(_paragraph(
        f'{signature}<br><span style="font-weight:600;color:{TEXT};">Andrea Francín</span>'
    ), "0 40px 36px"))
    footer = (
        f'<p style="margin:0 0 8px;font-size:12px;line-height:18px;color:{TEXT_3};">{escape(copy["footer"])}</p>'
        + _footer_links(
            work_url,
            f'<a href="{escape(privacy_url)}" style="color:{TEXT_3};text-decoration:underline;">{escape(copy["privacy"])}</a>',
        )
    )
    preheader = paragraphs[0][:110]
    html = _layout(language, texts["subject"], preheader, "\n".join(rows), footer, work_url)

    text_lines = [greeting, "", paragraphs[0]]
    if service:
        text_lines += ["", f"{copy['service']}: {service}"]
    for p in paragraphs[1:]:
        text_lines += ["", p]
    text_lines += [
        "", work_url, "", texts["signature"], "Andrea Francín", "", "—",
        copy["footer"], f"{copy['privacy']}: {privacy_url}",
    ]
    return texts["subject"], "\n".join(text_lines), html


# ---------- The message Andrea receives ----------

def render_notification(data: dict, sent_at: str) -> tuple[str, str, str]:
    """Return the subject, the plain text and the HTML of the message delivered to the site owner."""
    name = data["name"]
    email = data["email"]
    service = data.get("service") or ""
    language = LANGUAGE_NAMES.get(data.get("language", "es"), data.get("language", "es"))
    message = data["message"]

    subject = f"Nuevo mensaje de {name}" + (f" · {service}" if service else "")
    subject = subject[:150]
    reply_href = f"mailto:{email}?subject={quote('Re: ' + subject)}"

    details = [("Nombre", escape(name)),
               ("Correo", f'<a href="mailto:{escape(email)}" style="color:{ACCENT};text-decoration:none;font-weight:600;">{escape(email)}</a>')]
    if service:
        details.append(("Servicio", escape(service)))
    details += [("Idioma de la web", escape(language)), ("Enviado", escape(sent_at))]

    detail_rows = "".join(
        f'<tr><td style="padding:7px 16px 7px 0;font-size:13px;line-height:20px;color:{TEXT_3};white-space:nowrap;vertical-align:top;">{label}</td>'
        f'<td style="padding:7px 0;font-size:15px;line-height:20px;color:{TEXT};font-weight:500;word-break:break-word;">{value}</td></tr>'
        for label, value in details
    )
    message_html = escape(message).replace("\n", "<br>")

    rows = "\n".join([
        _row(_eyebrow("Formulario de contacto")
             + f'<h1 style="margin:0;font-size:26px;line-height:32px;font-weight:600;letter-spacing:-0.01em;color:{TEXT};">Nuevo mensaje de {escape(name)}</h1>',
             "0 40px 24px"),
        _row(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid {LINE};border-bottom:1px solid {LINE};">'
             f'<tr><td style="padding:10px 0;"><table role="presentation" cellpadding="0" cellspacing="0">{detail_rows}</table></td></tr></table>'),
        _row(_panel(_eyebrow("Mensaje")
                    + f'<p style="margin:0;font-size:16px;line-height:26px;color:{TEXT};">{message_html}</p>')),
        _row(_button(f"Responder a {name.split(' ')[0]}", reply_href), "0 40px 36px"),
    ])
    footer = (
        f'<p style="margin:0 0 8px;font-size:12px;line-height:18px;color:{TEXT_3};">Enviado desde el formulario de contacto de andreafrancin.com. '
        'La persona aceptó la política de privacidad. También puedes contestar con «Responder»: la respuesta le llegará directamente.</p>'
        + _footer_links(SITE_URL + "/work")
    )
    html = _layout("es", subject, f"{service or 'Mensaje'} · {message[:90]}", rows, footer, SITE_URL + "/work")

    text_lines = [f"Nombre: {name}", f"Correo: {email}"]
    if service:
        text_lines.append(f"Servicio: {service}")
    text_lines += [
        f"Idioma de la web: {language}", f"Enviado: {sent_at}", "", message, "", "—",
        "Mensaje enviado desde el formulario de contacto de andreafrancin.com.",
        "La persona aceptó la política de privacidad. Responde a este correo para contestarle.",
    ]
    return subject, "\n".join(text_lines), html
