import re
import io
from datetime import date
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

APP_TITLE = "FactureIA — Devis multi-métiers (Couvreur avancé)"
TVA_DEFAULT = 10

# =========================
#   CATALOGUES PAR METIER
# =========================
PRICES = {
    "couvreur": {
        # --- Nettoyage toiture ---
        "nettoyage_toiture_traitement": {"label": "Traitement toiture", "unit": "m²", "unit_price": 5.0},
        "nettoyage_toiture_hydrofuge": {"label": "Hydrofuge toiture", "unit": "m²", "unit_price": 6.0},
        "nettoyage_toiture_hydrofuge_colore": {"label": "Hydrofuge coloré toiture (coloris au choix)", "unit": "m²", "unit_price": 25.0},

        # --- Faîtage & rives ---
        "demolition_faitage_maconne_ml": {"label": "Démolition faîtage maçonné + évacuation", "unit": "ml", "unit_price": 60.0},
        "depose_faitage_sec_ml": {"label": "Dépose faîtage à sec + évacuation", "unit": "ml", "unit_price": 20.0},
        "mise_en_place_faitage_sec_ml": {"label": "Mise en place faîtage à sec", "unit": "ml", "unit_price": 80.0},
        "chassis_bois_ml": {"label": "Châssis bois sapin traité", "unit": "ml", "unit_price": 30.0},
        "pose_rives_ml": {"label": "Pose rives", "unit": "ml", "unit_price": 80.0},
        "ragreage_faitage_maconne_ml": {"label": "Ragréage faîtage maçonné", "unit": "ml", "unit_price": 60.0},
        "ragreage_rives_ml": {"label": "Ragréage rives", "unit": "ml", "unit_price": 50.0},
        "resine_hydrofuge_faitage_ml": {"label": "Résine hydrofuge faîtage", "unit": "ml", "unit_price": 90.0},
        "resine_hydrofuge_rives_ml": {"label": "Résine hydrofuge rives", "unit": "ml", "unit_price": 90.0},
        "realisation_faitage_maconne_ml": {"label": "Réalisation faîtage maçonné / à l'ancienne", "unit": "ml", "unit_price": 150.0},

        # --- Toiture complète ---
        "depose_toiture_m2": {"label": "Dépose toiture + évacuation gravats", "unit": "m²", "unit_price": 23.0},
        "pose_liteaux_m2": {"label": "Mise en place liteaux + contre-liteaux", "unit": "m²", "unit_price": 17.0},
        "pose_ecran_sous_toiture_m2": {"label": "Pose écran sous toiture", "unit": "m²", "unit_price": 17.0},

        # --- Pose tuiles (49 €/m² pour tous types pour l'instant) ---
        "pose_tuile_dc12_m2": {"label": "Pose tuiles DC12", "unit": "m²", "unit_price": 49.0},
        "pose_tuile_canal_s_m2": {"label": "Pose tuiles canal S", "unit": "m²", "unit_price": 49.0},
        "pose_tuile_canal_m2": {"label": "Pose tuiles canal", "unit": "m²", "unit_price": 49.0},
        "pose_tuile_plain_ciel_m2": {"label": "Pose tuiles Plain Ciel", "unit": "m²", "unit_price": 49.0},
        "pose_tuile_g13_m2": {"label": "Pose tuiles G13 (gothique)", "unit": "m²", "unit_price": 49.0},
        "pose_tuile_romane_m2": {"label": "Pose tuiles romane", "unit": "m²", "unit_price": 49.0},
        "pose_tuile_meridional_m2": {"label": "Pose tuiles méridional", "unit": "m²", "unit_price": 49.0},
        "pose_tuile_redland_m2": {"label": "Pose tuiles Redland", "unit": "m²", "unit_price": 49.0},

        # --- Zinguerie ---
        "gouttiere_alu_g300_ml": {"label": "Création & pose gouttière alu G300", "unit": "ml", "unit_price": 45.0},
        "gouttiere_zinc_ml": {"label": "Création & pose gouttière zinc", "unit": "ml", "unit_price": 90.0},
        "depose_gouttieres_ml": {"label": "Dépose gouttières + évacuation", "unit": "ml", "unit_price": 5.0},
        "entourage_cheminee_forfait": {"label": "Entourage de cheminée (neuf)", "unit": "forfait", "unit_price": 600.0},
        "depose_entourage_cheminee_forfait": {"label": "Dépose ancien entourage de cheminée + évacuation", "unit": "forfait", "unit_price": 100.0},
        "noue_ml": {"label": "Pose noue", "unit": "ml", "unit_price": 120.0},
        "couloir_zinc_ml": {"label": "Pose couloir zinc", "unit": "ml", "unit_price": 90.0},
        "solin_zinc_alu_ml": {"label": "Solin (zinc/alu)", "unit": "ml", "unit_price": 180.0},

        # --- Habillage & bois ---
        "avant_toit_pvc_m2": {"label": "Avant-toit PVC", "unit": "m²", "unit_price": 90.0},
        "habillage_planche_rive_pvc_ml": {"label": "Habillage planche de rive PVC", "unit": "ml", "unit_price": 45.0},
        "habillage_planche_rive_alu_ml": {"label": "Habillage planche de rive alu", "unit": "ml", "unit_price": 48.0},
        "pose_pdr_bois_ml": {"label": "Mise en place de PDR en bois", "unit": "ml", "unit_price": 40.0},
        "remplacement_chevron_u": {"label": "Remplacement chevron", "unit": "u", "unit_price": 190.0},

        # --- Ouvertures / divers ---
        "depose_cheminee_forfait": {"label": "Dépose d'une cheminée + évacuation", "unit": "forfait", "unit_price": 600.0},  # +200 si grosse cheminée
        "depose_fenetre_toit_fermeture_forfait": {"label": "Dépose fenêtre de toit (Velux) + fermeture", "unit": "forfait", "unit_price": 500.0},
        "joint_etancheite_custom": {"label": "Joint d’étanchéité (à définir)", "unit": "forfait", "unit_price": 0.0},

        # --- Isolation & charpente ---
        "isolation_laine_roche_m2": {"label": "Isolation laine de roche", "unit": "m²", "unit_price": 20.0},
        "isolation_laine_verre_m2": {"label": "Isolation laine de verre", "unit": "m²", "unit_price": 18.0},
        "isolation_ouate_m2": {"label": "Isolation ouate de cellulose", "unit": "m²", "unit_price": 15.0},
        "evacuation_ancienne_isolation_m2": {"label": "Évacuation de l’ancienne isolation", "unit": "m²", "unit_price": 15.0},
        "traitement_charpente_m2": {"label": "Traitement de charpente", "unit": "m²", "unit_price": 25.0},

        # --- Tuiles cassées ---
        "remplacement_tuiles_cassees_u": {"label": "Remplacement tuiles cassées", "unit": "u", "unit_price": 13.0},
    },

    # Structures à remplir plus tard
    "maconnerie": {},
    "placo": {},
    "elagage": {},
    "carreleur": {},
}

# =========================
#   HELPERS & NLP
# =========================

FRENCH_QTY_WORDS = {"quinzaine":15,"douzaine":12,"dizaine":10,"quinze":15,"douze":12,"dix":10,"vingt":20}

def num(s):
    try: return float(s.replace(",", "."))
    except: return None

def qty_from_words(w):
    return float(FRENCH_QTY_WORDS.get(w.lower().strip(), 0))

def find_qty(text, unit_kind):
    """
    unit_kind in {"ml","m2","u","forfait"}
    """
    if unit_kind == "ml":
        m = re.search(r"(\d+[,.]?\d*)\s*(?:m|ml|m(?:è|e)tre?s?\s*lin(?:é|e)aires?)", text)
        return num(m.group(1)) if m else 0.0
    if unit_kind == "m2":
        m = re.search(r"(\d+[,.]?\d*)\s*(?:m2|m²|m\^?2|m(?:è|e)tre?s?\s*carr(?:é|e)s?)", text)
        return num(m.group(1)) if m else 0.0
    if unit_kind == "u":
        m = re.search(r"(\d+)\s*(?:u|unit(?:é|e)s?|tuiles?|chevrons?)", text)
        if m: return float(m.group(1))
        m2 = re.search(r"(?:une?\s+)?([a-zéèêîïç]+)\s+(?:de\s+)?(?:tuiles?|chevrons?)", text)
        if m2: return qty_from_words(m2.group(1))
        return 0.0
    return 1.0  # forfait par défaut

def add_line(lines, key, qty, meta=None):
    cfg = PRICES["couvreur"][key]
    ln = {"key": key, "label": cfg["label"], "unit": cfg["unit"], "unit_price": cfg["unit_price"], "qty": float(qty)}
    if meta:
        ln.update(meta)
    lines.append(ln)

def extract_couvreur_from_text_advanced(text: str):
    """
    Détecte les prestations couvreur sur un texte libre (français).
    Couvre tout le catalogue défini plus haut.
    """
    txt = text.lower()

    lines = []

    # --- Nettoyage ---
    if re.search(r"\btraitement\b.*toiture|\btraiter\b.*toiture", txt):
        add_line(lines, "nettoyage_toiture_traitement", find_qty(txt, "m2") or 0)
    if re.search(r"\bhydrofuge\b(?!.*color)", txt) or re.search(r"imperm(?:é|e)abilis", txt):
        add_line(lines, "nettoyage_toiture_hydrofuge", find_qty(txt, "m2") or 0)
    if re.search(r"\bhydrofuge\s+color(é|e)", txt):
        add_line(lines, "nettoyage_toiture_hydrofuge_colore", find_qty(txt, "m2") or 0)

    # --- Faîtage & rives ---
    if re.search(r"d(é|e)molition.*fa[iî]tage.*ma(ç|c)onn", txt):
        add_line(lines, "demolition_faitage_maconne_ml", find_qty(txt, "ml") or 0)
    if re.search(r"d(é|e)pose.*fa[iî]tage.*(sec|syst(è|e)me\s+sec)", txt):
        add_line(lines, "depose_faitage_sec_ml", find_qty(txt, "ml") or 0)
    if re.search(r"(mise\s+en\s+place|pose).*(fa[iî]tage).*(sec|syst(è|e)me\s+sec)", txt):
        add_line(lines, "mise_en_place_faitage_sec_ml", find_qty(txt, "ml") or 0)
    if re.search(r"ch(a|â)ssis.*(sapin|bois)", txt):
        add_line(lines, "chassis_bois_ml", find_qty(txt, "ml") or 0)

    if re.search(r"\bragr(é|e)age\b.*fa[iî]tage", txt):
        add_line(lines, "ragreage_faitage_maconne_ml", find_qty(txt, "ml") or 0)
    if re.search(r"\bragr(é|e)age\b.*rives?", txt):
        add_line(lines, "ragreage_rives_ml", find_qty(txt, "ml") or 0)

    if re.search(r"(rives?|rive)\b.*(poser|pose|mise\s+en\s+place)", txt) or re.search(r"\bpose\s+de\s+rives?", txt):
        add_line(lines, "pose_rives_ml", find_qty(txt, "ml") or 0)

    if re.search(r"r(é|e)sine.*hydrofuge.*fa[iî]tage", txt):
        add_line(lines, "resine_hydrofuge_faitage_ml", find_qty(txt, "ml") or 0)
    if re.search(r"r(é|e)sine.*hydrofuge.*rives?", txt):
        add_line(lines, "resine_hydrofuge_rives_ml", find_qty(txt, "ml") or 0)

    if re.search(r"fa[iî]tage.*(ma(ç|c)onn(é|e)|ancien|ancienne)", txt):
        add_line(lines, "realisation_faitage_maconne_ml", find_qty(txt, "ml") or 0)

    # --- Toiture complète ---
    if re.search(r"d(é|e)pose.*toiture", txt):
        add_line(lines, "depose_toiture_m2", find_qty(txt, "m2") or 0)
    if re.search(r"(liteau|liteaux).*(contre[-\s]?liteau|contre[-\s]?liteaux)|mise\s+en\s+place\s+des?\s+liteaux", txt):
        add_line(lines, "pose_liteaux_m2", find_qty(txt, "m2") or 0)
    if re.search(r"(é|e)cran\s+sous\s+toiture|hpv|sous[-\s]?toiture", txt):
        add_line(lines, "pose_ecran_sous_toiture_m2", find_qty(txt, "m2") or 0)

    # --- Pose tuiles (types) ---
    m2_qty = find_qty(txt, "m2") or 0
    if re.search(r"pose.*tuiles?.*dc\s*12|dc12", txt): add_line(lines, "pose_tuile_dc12_m2", m2_qty)
    if re.search(r"pose.*tuiles?.*canal\s*s", txt): add_line(lines, "pose_tuile_canal_s_m2", m2_qty)
    if re.search(r"pose.*tuiles?.*canal(?!\s*s)", txt): add_line(lines, "pose_tuile_canal_m2", m2_qty)
    if re.search(r"pose.*tuiles?.*plain\s*ciel", txt): add_line(lines, "pose_tuile_plain_ciel_m2", m2_qty)
    if re.search(r"pose.*tuiles?.*g13|gothique", txt): add_line(lines, "pose_tuile_g13_m2", m2_qty)
    if re.search(r"pose.*tuiles?.*roman(e|es?)", txt): add_line(lines, "pose_tuile_romane_m2", m2_qty)
    if re.search(r"pose.*tuiles?.*m(é|e)ridion(al|aux|ale|ales)", txt): add_line(lines, "pose_tuile_meridional_m2", m2_qty)
    if re.search(r"pose.*tuiles?.*redland", txt): add_line(lines, "pose_tuile_redland_m2", m2_qty)

    # --- Tuiles cassées ---
    if re.search(r"(changer|remplacer)\s+(\d+|\w+)\s+tuil", txt):
        qty = find_qty(txt, "u")
        add_line(lines, "remplacement_tuiles_cassees_u", qty or 0)

    # --- Zinguerie ---
    if re.search(r"goutti(è|e)res?.*alu.*g\s*300|g300", txt):
        add_line(lines, "gouttiere_alu_g300_ml", find_qty(txt, "ml") or 0)
    if re.search(r"goutti(è|e)res?.*zinc", txt):
        add_line(lines, "gouttiere_zinc_ml", find_qty(txt, "ml") or 0)
    if re.search(r"d(é|e)pose.*goutti(è|e)res?", txt):
        add_line(lines, "depose_gouttieres_ml", find_qty(txt, "ml") or 0)

    if re.search(r"entourage.*chemin(é|e)e", txt) and not re.search(r"d(é|e)pose.*entourage", txt):
        add_line(lines, "entourage_cheminee_forfait", 1)
    if re.search(r"d(é|e)pose.*entourage.*chemin(é|e)e", txt):
        add_line(lines, "depose_entourage_cheminee_forfait", 1)

    if re.search(r"\bnoues?\b", txt):
        add_line(lines, "noue_ml", find_qty(txt, "ml") or 0)
    if re.search(r"couloirs?.*zinc", txt):
        add_line(lines, "couloir_zinc_ml", find_qty(txt, "ml") or 0)
    if re.search(r"\bsolins?\b", txt):
        add_line(lines, "solin_zinc_alu_ml", find_qty(txt, "ml") or 0)

    # --- Habillage & bois ---
    if re.search(r"avant[-\s]?toit.*pvc|sous[-\s]?face.*pvc|cache[-\s]?moineaux.*pvc", txt):
        add_line(lines, "avant_toit_pvc_m2", find_qty(txt, "m2") or 0)
    if re.search(r"habillage.*planche.*rive.*pvc", txt):
        add_line(lines, "habillage_planche_rive_pvc_ml", find_qty(txt, "ml") or 0)
    if re.search(r"habillage.*planche.*rive.*alu|minium", txt):
        add_line(lines, "habillage_planche_rive_alu_ml", find_qty(txt, "ml") or 0)
    if re.search(r"\bpdr\b.*bois|pi(è|e)ce.*bois.*rive", txt):
        add_line(lines, "pose_pdr_bois_ml", find_qty(txt, "ml") or 0)

    if re.search(r"(changer|remplacer)\s+(\d+|\w+)\s+chevrons?", txt):
        qty = find_qty(txt, "u")
        add_line(lines, "remplacement_chevron_u", qty or 0)

    # --- Ouvertures / divers ---
    if re.search(r"d(é|e)pose.*(chemin(é|e)e)", txt):
        # prix ajusté ensuite par switch "grosse cheminée"
        add_line(lines, "depose_cheminee_forfait", 1)
    if re.search(r"d(é|e)pose.*(fen(ê|e)tre\s+de\s+toit|velux).*(fermeture|rebouchage)?", txt):
        add_line(lines, "depose_fenetre_toit_fermeture_forfait", 1)

    if re.search(r"joint.*(étanch|etanch)", txt):
        add_line(lines, "joint_etancheite_custom", 1)

    # --- Isolation & charpente ---
    if re.search(r"isolation.*laine.*roche", txt):
        add_line(lines, "isolation_laine_roche_m2", find_qty(txt, "m2") or 0)
    if re.search(r"isolation.*laine.*verre", txt):
        add_line(lines, "isolation_laine_verre_m2", find_qty(txt, "m2") or 0)
    if re.search(r"isolation.*ouate", txt):
        add_line(lines, "isolation_ouate_m2", find_qty(txt, "m2") or 0)
    if re.search(r"(é|e)vacuation.*ancienne.*isolation", txt):
        add_line(lines, "evacuation_ancienne_isolation_m2", find_qty(txt, "m2") or 0)
    if re.search(r"traitement.*charpente", txt):
        add_line(lines, "traitement_charpente_m2", find_qty(txt, "m2") or 0)

    # --- Cas générique faîtage à sec (phrase courte) ---
    # "15 ml de faîtage à refaire à sec" → kit dépose + mise en place + châssis
    m = re.search(r"(\d+[,.]?\d*)\s*(?:m|ml|m(?:è|e)tre?s?)\s+.*fa[iî]tage.*(sec|syst(è|e)me\s+sec)", txt)
    if m and not any(ln["key"] in {"depose_faitage_sec_ml","mise_en_place_faitage_sec_ml","chassis_bois_ml"} for ln in lines):
        qty_ml = float(m.group(1).replace(",", "."))
        add_line(lines, "depose_faitage_sec_ml", qty_ml)
        add_line(lines, "mise_en_place_faitage_sec_ml", qty_ml)
        add_line(lines, "chassis_bois_ml", qty_ml)

    # Nettoyage → si aucune ligne m² n'a été trouvée mais on mentionne "nettoyage/hydrofuge"
    if not any(l["unit"]=="m²" and l["qty"]>0 for l in lines):
        if re.search(r"nettoyage|hydrofuge|traitement\s+toiture", txt):
            # si l'utilisateur n'a pas mis la surface, on laisse 0 (il ajustera)
            pass

    # Tuiles → si "changer tuiles" sans nombre, laisse 0 pour que l'artisan ajuste
    return lines

def compute_totals(lines, tva_rate):
    subtotal = round(sum(ln["qty"] * ln["unit_price"] for ln in lines), 2)
    tva = round(subtotal * (tva_rate / 100.0), 2)
    total = round(subtotal + tva, 2)
    return subtotal, tva, total

def make_pdf_devis(company, client, devis_num, date_str, lines, tva_rate, subtotal, tva, total, conditions):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    x_margin = 2 * cm
    y = height - 2 * cm

    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x_margin, y, company.get("name", "FactureIA"))
    c.setFont("Helvetica", 10); y -= 14
    c.drawString(x_margin, y, company.get("addr", "Adresse"))
    y -= 12; c.drawString(x_margin, y, company.get("siret", "SIRET: "))
    y -= 20

    # Client / devis
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x_margin, y, f"DEVIS n° {devis_num}")
    y -= 14; c.setFont("Helvetica", 10)
    c.drawString(x_margin, y, f"Date : {date_str}")
    y -= 12; c.drawString(x_margin, y, f"Client : {client.get('name','')}")
    y -= 12
    if client.get("addr"):
        c.drawString(x_margin, y, f"Adresse : {client['addr']}"); y -= 12
    y -= 8

    # Table header
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x_margin, y, "Désignation")
    c.drawString(x_margin + 9*cm, y, "Qté")
    c.drawString(x_margin + 11*cm, y, "PU")
    c.drawString(x_margin + 14*cm, y, "Total")
    y -= 12; c.setFont("Helvetica", 10)
    c.line(x_margin, y, width - x_margin, y); y -= 6

    # Lines
    for ln in lines:
        line_total = ln["qty"] * ln["unit_price"]
        c.drawString(x_margin, y, ln["label"])
        c.drawRightString(x_margin + 10*cm, y, f"{ln['qty']:.2f} {ln['unit']}")
        c.drawRightString(x_margin + 13*cm, y, f"{ln['unit_price']:.2f} €")
        c.drawRightString(width - x_margin, y, f"{line_total:.2f} €")
        y -= 12
        if y < 5*cm:
            c.showPage(); y = height - 2*cm

    # Totals
    y -= 10; c.line(x_margin, y, width - x_margin, y); y -= 14
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(x_margin + 13*cm, y, "Sous-total :")
    c.drawRightString(width - x_margin, y, f"{subtotal:.2f} €")
    y -= 12
    c.drawRightString(x_margin + 13*cm, y, f"TVA ({tva_rate:.0f}%) :")
    c.drawRightString(width - x_margin, y, f"{tva:.2f} €")
    y -= 12
    c.drawRightString(x_margin + 13*cm, y, "Total TTC :")
    c.drawRightString(width - x_margin, y, f"{total:.2f} €")

    # Footer
    y -= 24; c.setFont("Helvetica", 9)
    for i in range(0, len(conditions), 90):
        c.drawString(x_margin, y, conditions[i:i+90]); y -= 12

    c.save(); buf.seek(0)
    return buf

# =========================
#   BUSINESS RULES
# =========================
def apply_business_rules(metier, lines, grosse_cheminee=False):
    out = []

    # 0) Ajout auto: Vérification (pour couvreur)
    if metier == "couvreur":
        out.append({
            "label": "Vérification toiture avant travaux",
            "qty": 1, "unit": "forfait", "unit_price": 0.0
        })

    # 1) Copier les lignes saisies/détectées
    out.extend(lines)

    if metier == "couvreur":
        # 2) Si nettoyage présent → tuiles cassées = 0 €
        has_cleaning = any(ln.get("key","").startswith("nettoyage_toiture_") for ln in lines)
        for ln in out:
            if ln.get("key") == "remplacement_tuiles_cassees_u" and has_cleaning:
                ln["unit_price"] = 0.0

        # 3) Switch grosse cheminée (+200€)
        if grosse_cheminee:
            for ln in out:
                if ln.get("key") == "depose_cheminee_forfait":
                    ln["unit_price"] = 800.0  # sinon 600 par défaut

    return out

# =========================
#   APP UI
# =========================
st.set_page_config(page_title=APP_TITLE, page_icon="🧾")
st.title(APP_TITLE)
st.caption("Écris tes travaux en français : l’app détecte toutes les prestations Couvreur, applique les règles, et génère le PDF. Multi-métiers prêt pour la suite.")

# Choix du métier (Couvreur actif pour l’IA, les autres arrivent)
metier = st.selectbox("Choisir le métier :", ["couvreur","maconnerie","placo","elagage","carreleur"])

# Infos société / client
colA, colB = st.columns(2)
with colA:
    company_name = st.text_input("Nom entreprise", value="FactureIA — " + metier.capitalize())
    company_addr = st.text_input("Adresse entreprise", value="12 Rue des Toits, 69000 Lyon")
    company_siret = st.text_input("SIRET", value="SIRET: 123 456 789 00012")
with colB:
    client_name = st.text_input("Nom du client", value="Mme BLANC")
    client_addr = st.text_input("Adresse client", value="")

# Saisie texte (l’IA couvreur avancée)
st.subheader("Demande (texte libre)")
placeholder = (
    "Exemples :\n"
    "- Nettoyage toiture 120 m² avec hydrofuge coloré\n"
    "- Démolition faîtage maçonné 18 ml + pose faîtage à sec 18 ml + châssis sapin\n"
    "- Gouttières alu G300 22 ml + dépose anciennes 22 ml\n"
    "- Isolation laine de roche 60 m² + évacuation ancienne isolation 60 m²\n"
    "- Dépose cheminée + fermeture, pose noue 6 ml, solin zinc 8 ml\n"
    "- Habillage planche de rive PVC 15 ml, avant-toit PVC 20 m²\n"
    "- Remplacer 12 tuiles, traitement charpente 80 m²"
)
user_text = st.text_area("Décris les travaux :", value=placeholder, height=160)

# Lignes détectées
auto_lines = []
if metier == "couvreur" and user_text.strip():
    auto_lines = extract_couvreur_from_text_advanced(user_text)

# Catalogue manuel (si tu veux compléter)
st.subheader("Catalogue — ajouter des postes (optionnel)")
with st.expander("➕ Ajouter depuis le catalogue"):
    if PRICES.get(metier):
        key_list = list(PRICES[metier].keys())
        show = st.multiselect("Choisis des postes à ajouter :", options=key_list, format_func=lambda k: PRICES[metier][k]["label"])
        added = []
        for k in show:
            cfg = PRICES[metier][k]
            col1, col2 = st.columns(2)
            with col1:
                qty = st.number_input(f"Qté pour « {cfg['label']} » ({cfg['unit']})", min_value=0.0, step=1.0, value=0.0, key=f"qty_{k}")
            with col2:
                pu = st.number_input(f"PU € ({cfg['label']})", value=float(cfg["unit_price"]), step=1.0, key=f"pu_{k}")
            if qty > 0:
                added.append({"key": k, "label": cfg["label"], "unit": cfg["unit"], "unit_price": pu, "qty": qty})
    else:
        st.info("Catalogue à venir pour ce métier.")
        added = []

# Ligne manuelle
st.subheader("Ligne manuelle (si besoin)")
with st.form("manual_line_form", clear_on_submit=True):
    col1, col2, col3, col4 = st.columns([3,1,1,1])
    label = col1.text_input("Désignation")
    unit = col2.selectbox("Unité", ["forfait", "m²", "ml", "u"])
    qty = col3.number_input("Qté", min_value=0.0, value=0.0, step=1.0)
    pu = col4.number_input("PU €", min_value=0.0, value=0.0, step=1.0)
    manual_submit = st.form_submit_button("Ajouter la ligne")
manual_lines = []
if manual_submit and label and qty > 0:
    manual_lines.append({"key":"manual", "label": label, "unit": unit, "unit_price": pu, "qty": qty})
    st.success(f"Ligne ajoutée : {label}")

# Options
st.subheader("Options & TVA")
grosse_cheminee = st.checkbox("Grosse cheminée (avec fermeture) → 800 €", value=False) if metier=="couvreur" else False
tva_rate = st.slider("TVA (%)", min_value=0, max_value=20, value=TVA_DEFAULT, step=1)
devis_num = st.text_input("N° de devis", value=f"D{date.today().strftime('%Y%m%d')}-001")
conditions = st.text_area("Conditions (bas de page PDF)", value=(
    "Vérification préalable offerte (couvreur). Remplacement tuiles cassées offert si prestation de nettoyage incluse. "
    "Prix HT hors échafaudage spécifique. Validité 30 jours. Paiement: 30% acompte, solde à la réception. "
    "Assurance décennale. Délais selon météo et approvisionnement."
), height=80)

# Construire les lignes
lines = []
lines.extend(auto_lines)
if 'added' in locals(): lines.extend(added)
lines.extend(manual_lines)

# Appliquer règles
lines = apply_business_rules(metier, lines, grosse_cheminee=grosse_cheminee)

# Aperçu
if lines:
    st.write("### Lignes du devis")
    preview = [{"Désignation": l["label"], "Qté": l["qty"], "Unité": l["unit"], "PU €": l["unit_price"], "Total €": round(l["qty"]*l["unit_price"],2)} for l in lines]
    st.dataframe(preview)
    subtotal, tva, total = compute_totals(lines, tva_rate)
    st.write(f"**Sous-total**: {subtotal:.2f} €  •  **TVA ({tva_rate}%)**: {tva:.2f} €  •  **Total TTC**: {total:.2f} €")

# PDF
if st.button("Générer le PDF"):
    if not lines:
        st.warning("Ajoute au moins une ligne (texte, catalogue ou manuelle).")
    else:
        subtotal, tva, total = compute_totals(lines, tva_rate)
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
        st.download_button("⬇️ Télécharger le devis (PDF)", data=pdf, file_name=f"{devis_num}.pdf", mime="application/pdf")
else:
    st.caption("Astuce : écris tout en une phrase (exemples au-dessus). L’IA ajoute les bonnes lignes. Tu peux compléter avec le catalogue ou une ligne manuelle.")
