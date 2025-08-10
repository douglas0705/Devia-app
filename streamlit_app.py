\
import re
import io
from datetime import date
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

# ---------- BARÈME PAR DÉFAUT (prix moyens HT) ----------
PRICES = {
    "mise_en_place": {"label": "Mise en place du chantier", "unit": "forfait", "unit_price": 0.0},

    # Faîtage à sec (décomposition typique)
    "faitage_sec_ml": {"label": "Dépose faîtage + évacuation (à sec)", "unit": "ml", "unit_price": 50.0},
    "chassis_bois_ml": {"label": "Création châssis bois sapin traité", "unit": "ml", "unit_price": 19.0},
    "pose_closoir_ml": {"label": "Pose closoir ventilé (alu/butyl)", "unit": "ml", "unit_price": 18.0},
    "pose_faitieres_ml": {"label": "Repose faîtières (système à sec)", "unit": "ml", "unit_price": 22.0},

    # Divers
    "tuile_unite": {"label": "Remplacement de tuiles", "unit": "u", "unit_price": 14.0},
    "deplacement_forfait": {"label": "Déplacement / approvisionnement", "unit": "forfait", "unit_price": 30.0},
    "fournitures_forfait": {"label": "Petites fournitures", "unit": "forfait", "unit_price": 25.0},
}

FRENCH_QTY = {
    "quinzaine": 15, "douzaine": 12, "dizaine": 10,
    "quinze": 15, "douze": 12, "dix": 10, "vingt": 20
}

def parse_quantity(token: str) -> float:
    import re
    token = token.strip().lower()
    m = re.match(r"(\d+[,.]?\d*)", token)
    if m:
        return float(m.group(1).replace(",", "."))
    return float(FRENCH_QTY.get(token, 0))

def extract_faitage_ml(txt: str) -> float:
    import re
    m = re.search(r"(\d+[,.]?\d*)\s*(?:m|ml|m(?:è|e)tre?s?)\s+.*fa[iî]tage", txt)
    return float(m.group(1).replace(",", ".")) if m else 0.0

def extract_tiles_qty(txt: str) -> int:
    import re
    m_num = re.search(r"(?:changer|remplacer)\s+(\d+)\s*tuil", txt)
    if m_num:
        return int(m_num.group(1))
    m_word = re.search(r"(?:changer|remplacer)\s+une?\s+([a-zéèêîïç]+)\s+de\s+tuil", txt)
    if m_word:
        return int(parse_quantity(m_word.group(1)))
    return 0

def detect_faitage_a_sec(txt: str) -> bool:
    import re
    return bool(re.search(r"fa[iî]tage\s*(?:a|à)?\s*sec|closoir|fa[iî]ti[eè]res?\s*(?:a|à)?\s*sec", txt))

def extract_items_from_text(text: str, auto_faitage_kit: True):
    txt = text.lower()
    lines = []
    for k in ("mise_en_place", "deplacement_forfait", "fournitures_forfait"):
        lines.append({
            "key": k, "label": PRICES[k]["label"], "qty": 1,
            "unit": PRICES[k]["unit"], "unit_price": PRICES[k]["unit_price"],
        })
    qty_ml = extract_faitage_ml(txt)
    if qty_ml > 0:
        lines.append({"key": "faitage_sec_ml", "label": PRICES["faitage_sec_ml"]["label"],
                      "qty": qty_ml, "unit": PRICES["faitage_sec_ml"]["unit"],
                      "unit_price": PRICES["faitage_sec_ml"]["unit_price"]})
        lines.append({"key": "chassis_bois_ml", "label": PRICES["chassis_bois_ml"]["label"],
                      "qty": qty_ml, "unit": PRICES["chassis_bois_ml"]["unit"],
                      "unit_price": PRICES["chassis_bois_ml"]["unit_price"]})
        if auto_faitage_kit and detect_faitage_a_sec(txt):
            lines.append({"key": "pose_closoir_ml", "label": PRICES["pose_closoir_ml"]["label"],
                          "qty": qty_ml, "unit": PRICES["pose_closoir_ml"]["unit"],
                          "unit_price": PRICES["pose_closoir_ml"]["unit_price"]})
            lines.append({"key": "pose_faitieres_ml", "label": PRICES["pose_faitieres_ml"]["label"],
                          "qty": qty_ml, "unit": PRICES["pose_faitieres_ml"]["unit"],
                          "unit_price": PRICES["pose_faitieres_ml"]["unit_price"]})
    qty_tiles = extract_tiles_qty(txt)
    if qty_tiles > 0:
        lines.append({"key": "tuile_unite", "label": PRICES["tuile_unite"]["label"],
                      "qty": qty_tiles, "unit": PRICES["tuile_unite"]["unit"],
                      "unit_price": PRICES["tuile_unite"]["unit_price"]})
    for ln in lines:
        ln["total"] = round(ln["qty"] * ln["unit_price"], 2)
    return lines

def compute_totals(lines, tva_rate):
    subtotal = round(sum(ln["total"] for ln in lines), 2)
    tva = round(subtotal * (tva_rate / 100.0), 2)
    total = round(subtotal + tva, 2)
    return subtotal, tva, total

def make_pdf_devis(company, client, devis_num, date_str, lines, tva_rate, subtotal, tva, total, conditions):
    buf = io.BytesIO()
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    x_margin = 2 * cm; y = height - 2 * cm
    c.setFont("Helvetica-Bold", 14); c.drawString(x_margin, y, company.get("name", "DEV’IA – Couvreur"))
    c.setFont("Helvetica", 10); y -= 14; c.drawString(x_margin, y, company.get("addr", "Adresse"))
    y -= 12; c.drawString(x_margin, y, company.get("siret", "SIRET: ")); y -= 20
    c.setFont("Helvetica-Bold", 12); c.drawString(x_margin, y, f"DEVIS n° {devis_num}"); y -= 14
    c.setFont("Helvetica", 10); c.drawString(x_margin, y, f"Date : {date_str}"); y -= 12
    c.drawString(x_margin, y, f"Client : {client.get('name','')}"); y -= 12
    if client.get("addr"): c.drawString(x_margin, y, f"Adresse : {client['addr']}"); y -= 12
    y -= 8; c.setFont("Helvetica-Bold", 10)
    c.drawString(x_margin, y, "Désignation"); c.drawString(x_margin + 9*cm, y, "Qté"); c.drawString(x_margin + 11*cm, y, "PU"); c.drawString(x_margin + 14*cm, y, "Total")
    y -= 12; c.setFont("Helvetica", 10); c.line(x_margin, y, width - x_margin, y); y -= 6
    for ln in lines:
        c.drawString(x_margin, y, ln["label"])
        c.drawRightString(x_margin + 10*cm, y, f"{ln['qty']:.2f} {ln['unit']}")
        c.drawRightString(x_margin + 13*cm, y, f"{ln['unit_price']:.2f} €")
        c.drawRightString(width - x_margin, y, f"{ln['total']:.2f} €")
        y -= 12
        if y < 5*cm:
            c.showPage(); y = height - 2*cm
    y -= 10; c.line(x_margin, y, width - x_margin, y); y -= 14; c.setFont("Helvetica-Bold", 10)
    c.drawRightString(x_margin + 13*cm, y, "Sous-total :"); c.drawRightString(width - x_margin, y, f"{subtotal:.2f} €")
    y -= 12; c.drawRightString(x_margin + 13*cm, y, f"TVA ({tva_rate:.0f}%) :"); c.drawRightString(width - x_margin, y, f"{tva:.2f} €")
    y -= 12; c.drawRightString(x_margin + 13*cm, y, "Total TTC :"); c.drawRightString(width - x_margin, y, f"{total:.2f} €")
    y -= 24; c.setFont("Helvetica", 9)
    for i in range(0, len(conditions), 90):
        c.drawString(x_margin, y, conditions[i:i+90]); y -= 12
    c.save(); buf.seek(0); return buf

st.set_page_config(page_title="DEV’IA – Devis & Factures IA", page_icon="🧾")
st.title("DEV’IA – Devis & Factures IA")
st.caption("Version cloud : écris une phrase et génère un devis PDF.")

colA, colB = st.columns(2)
with colA:
    company_name = st.text_input("Nom entreprise", value="DEV’IA – Couvreur")
    company_addr = st.text_input("Adresse entreprise", value="12 Rue des Toits, 69000 Lyon")
    company_siret = st.text_input("SIRET", value="SIRET: 123 456 789 00012")
with colB:
    client_name = st.text_input("Nom du client", value="Mme BLANC")
    client_addr = st.text_input("Adresse client", value="")

st.subheader("Demande (texte)")
default_text = "Fais un devis pour Mme BLANC : 15 ml de faîtage à refaire à sec et changer une quinzaine de tuiles."
user_text = st.text_area("Décris les travaux :", value=default_text, height=120)

st.subheader("Options d'analyse")
auto_faitage_kit = st.checkbox("Ajouter automatiquement closoir + faîtières si 'faîtage à sec' détecté", value=True)

st.subheader("Barème (modifiable)")
with st.expander("Voir / Modifier le barème"):
    for key, cfg in PRICES.items():
        label = cfg['label']
        if cfg["unit"] == "forfait":
            PRICES[key]["unit_price"] = st.number_input(f"{label} (forfait €)", value=float(cfg["unit_price"]), step=1.0)
        elif cfg["unit"] == "ml":
            PRICES[key]["unit_price"] = st.number_input(f"{label} (€ / ml)", value=float(cfg["unit_price"]), step=1.0)
        elif cfg["unit"] == "u":
            PRICES[key]["unit_price"] = st.number_input(f"{label} (€ / u)", value=float(cfg["unit_price"]), step=1.0)

st.subheader("TVA & Numéro de devis")
tva_rate = st.slider("TVA (%)", min_value=0, max_value=20, value=10, step=1)
devis_num = st.text_input("N° de devis", value=f"D{date.today().strftime('%Y%m%d')}-001")
conditions = st.text_area("Conditions (affichées en bas du PDF)", value=(
    "Prix indicatifs basés sur constat sur place. TVA et barème ajustables selon nature du chantier. "
    "Validité du devis: 30 jours. Paiement: 30% à la commande, solde à la réception. "
    "Assurance décennale. Délais selon météo et approvisionnement."
), height=80)

if st.button("Générer le devis"):
    lines = extract_items_from_text(user_text, auto_faitage_kit=auto_faitage_kit)
    subtotal, tva, total = compute_totals(lines, tva_rate)
    st.success("Devis généré")
    st.write("### Lignes")
    st.dataframe(
        [{"Désignation": l["label"], "Qté": l["qty"], "Unité": l["unit"], "PU €": l["unit_price"], "Total €": l["total"]} for l in lines]
    )
    st.write(f"**Sous-total**: {subtotal:.2f} €  •  **TVA ({tva_rate}%)**: {tva:.2f} €  •  **Total TTC**: {total:.2f} €")
    pdf = make_pdf_devis(
        company={"name": company_name, "addr": company_addr, "siret": company_siret},
        client={"name": client_name, "addr": client_addr},
        devis_num=devis_num,
        date_str=date.today().strftime("%d/%m/%Y"),
        lines=lines,
        tva_rate=tva_rate,
        subtotal=subtotal,
        tva=tva,
        total=total,
        conditions=conditions
    )
    st.download_button(label="⬇️ Télécharger le devis (PDF)", data=pdf, file_name=f"{devis_num}.pdf", mime="application/pdf")

st.caption("Cloud-ready. Si besoin: logo, base clients et facturation peuvent être ajoutés.")
