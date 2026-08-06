"""
Rendement des adductions d'eau potable — Direction Régionale ONEE Branche Eau.

Terminologie
------------
- Achat / Cession ADDUCTION : échange au sein de l'ONEE Branche Eau
  (dans la DR ou avec une autre DR). Ex. achat depuis DR5 = achat adduction.
- Achat EXTERNE / Vente : échange avec un autre organisme (SRM, Amendis).
  Les ventes sont ventilées en Vente SRM et Vente AMENDIS.

Formule (validée sur les données réelles de la DR)
--------------------------------------------------
    Rendement = (Vente SRM + Vente AMENDIS + Cession adduction + Pertes techniques)
                / (Production + Achat adduction + Achat externe) × 100

Agrégation (secteur, catégorie, DR)
-----------------------------------
Pour un périmètre P, on élimine les transferts internes à P (flux dont la
source ET la destination sont dans P) :
    Achat net   = Σ Achat_P   − transferts internes à P
    Cession nette = Σ Cession_P − transferts internes à P
Au niveau DR, seuls restent les achats/cessions hors DR (autres DR, SRM…).
"""

import io
import json
import os

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Rendement Adductions DR", page_icon="💧", layout="wide")

DATA_FILE = "rendement_data.json"
SECTEURS = [1, 2, 3, 4]

# Centre, Secteur, Catégorie, Production, Achat add., Achat externe, Cession add.,
# Vente SRM, Vente AMENDIS, Pertes techn.   (les ventes réelles sont mises en SRM
# par défaut, à ventiler ; achat externe = 0 partout dans les données de base)
CENTRES_DATA = [
    ("TRANSPORT CHARF EL AKAB", 1, 2, 0, 42606302, 0, 0, 41426012, 0, 1800),
    ("PRODUCTION CHARF EL AKAB (CEA)", 1, 2, 1680216, 44549509, 0, 44588805, 1490727, 0, 1800),
    ("ST HACHEF", 1, 1, 37343429, 0, 0, 37335960, 0, 0, 0),
    ("TRANSPORT EAUX TRAITEES HACHEF", 1, 1, 0, 3045380, 0, 0, 2924672, 0, 0),
    ("ST M'HARHAR", 1, 1, 11842871, 0, 0, 11520269, 0, 0, 0),
    ("TRANSPORT M'HARHAR-KSAR SGHIR", 1, 1, 36315, 4104115, 0, 121720, 2709565, 0, 175663),
    ("ST TANGER MED & PRODUCTION TAGHRAMT", 1, 1, 1395479, 121720, 0, 698591, 818264, 0, 0),
    ("CENTRE PRODUCTION RAOUZ (ST RAOUZ)", 2, 1, 3631918, 153290, 0, 3769456, 0, 0, 0),
    ("CENTRE TRANSPORT RAOUZ", 2, 1, 0, 3796153, 0, 1341019, 1576353, 0, 3769),
    ("CENTRE DE PRODUCTION OUED MARTIL (ST O.MARTIL)", 2, 1, 7491736, 0, 0, 7491736, 526, 0, 0),
    ("CENTRE TRANSPORT TAMOUDA-O.MARTIL-Nakhla", 2, 2, 190375, 7500991, 0, 7322567, 186034, 0, 6697),
    ("ST SMIR", 2, 1, 4440023, 0, 0, 4440023, 0, 0, 0),
    ("ST TORRETA", 2, 1, 3059875, 0, 0, 3052620, 7255, 0, 0),
    ("CENTRE TRANSPORT SMIR TORETA", 2, 2, 0, 16144959, 0, 0, 15999943, 0, 1800),
    ("CENTRE DE PRODUCTION MOULAY BOUCHETA (ST)", 2, 1, 402328, 0, 0, 397808, 0, 0, 0),
    ("CPT Mly Bouchta-Chefchaouen-Tetaoun", 2, 1, 1725816, 397808, 0, 320543, 1791649, 0, 0),
    ("CPT Bab Taza - Derdara", 2, 1, 161698, 320543, 0, 0, 457432, 0, 0),
    ("CPT Oued Laou - Stehat", 2, 1, 284199, 0, 0, 0, 273768, 0, 0),
    ("CTP Bouhmed", 2, 1, 325507, 0, 0, 0, 313742, 0, 0),
    ("CPT Jebha-Bab Berred", 2, 1, 424538, 0, 0, 0, 419875, 0, 522),
    ("STATIONS DE TRAITEMENT SPECIFIQUES (ISSAGUEN-BNI AMMART-KETAMA)", 2, 1, 129891, 0, 0, 0, 127562, 0, 0),
    ("PRODUCTION ST LOUKKOS", 3, 1, 7669298, 0, 0, 7664444, 0, 0, 4854),
    ("PRODUCTION OUEZZANE OUEST", 3, 1, 1060243, 2420824, 0, 1126031, 2144559, 0, 69778),
    ("PRODUCTION OUEZZANE EST", 3, 1, 241367, 1943564, 0, 0, 1924116, 0, 48408),
    ("TRANSPORT KSAR KEBIR", 3, 1, 0, 4942267, 0, 3082790, 1646380, 0, 2324),
    ("PRODUCTION KSAR LEKBIR", 3, 1, 457796, 458835, 0, 0, 861289, 0, 11751),
    ("TRANSPORT LARACHE", 3, 1, 0, 2063443, 0, 0, 1945815, 0, 36416),
    ("PRODUCTION LARACHE", 3, 1, 2621183, 59828, 0, 0, 2627077, 0, 0),
    ("ST AL HOCEIMA", 4, 1, 1696018, 0, 0, 1590082, 102711, 0, 0),
    ("CHAMPS CAPTANTS AL HOCEIMA", 4, 1, 3414776, 0, 0, 3163361, 219127, 0, 70),
    ("TRANSPORT BARRAGE MBAK-RESERVOIR AL HOCEIMA", 4, 2, 0, 3498941, 0, 941482, 2436333, 0, 2493),
    ("STATION DESSALEMENT AL HOCEIMA", 4, 1, 3465151, 0, 0, 3465151, 0, 0, 0),
    ("TRANSPORT RM AJDIR-TARGUIST-ADDUCTION REGIONALE", 4, 2, 5729, 5640466, 0, 784710, 4501714, 0, 18480),
    ("ST TARGUIST", 4, 1, 453963, 388468, 0, 0, 815335, 0, 273),
]

COLS = ["Centre", "Secteur", "Catégorie", "Production", "Achat adduction",
        "Achat externe", "Cession adduction", "Vente SRM", "Vente AMENDIS",
        "Pertes techniques"]
NUM_COLS = COLS[3:]

FLUX_INTERNES = [
    ("ST HACHEF", "PRODUCTION CHARF EL AKAB (CEA)"),
    ("ST HACHEF", "TRANSPORT EAUX TRAITEES HACHEF"),
    ("PRODUCTION CHARF EL AKAB (CEA)", "TRANSPORT CHARF EL AKAB"),
    ("ST M'HARHAR", "PRODUCTION CHARF EL AKAB (CEA)"),
    ("ST M'HARHAR", "TRANSPORT M'HARHAR-KSAR SGHIR"),
    ("ST TANGER MED & PRODUCTION TAGHRAMT", "TRANSPORT M'HARHAR-KSAR SGHIR"),
    ("ST TANGER MED & PRODUCTION TAGHRAMT", "CENTRE PRODUCTION RAOUZ (ST RAOUZ)"),
    ("CENTRE PRODUCTION RAOUZ (ST RAOUZ)", "CENTRE TRANSPORT RAOUZ"),
    ("CENTRE DE PRODUCTION OUED MARTIL (ST O.MARTIL)", "CENTRE TRANSPORT TAMOUDA-O.MARTIL-Nakhla"),
    ("ST SMIR", "CENTRE TRANSPORT SMIR TORETA"),
    ("ST TORRETA", "CENTRE TRANSPORT SMIR TORETA"),
    ("CENTRE TRANSPORT RAOUZ", "CENTRE TRANSPORT SMIR TORETA"),
    ("CENTRE TRANSPORT TAMOUDA-O.MARTIL-Nakhla", "CENTRE TRANSPORT SMIR TORETA"),
    ("CENTRE DE PRODUCTION MOULAY BOUCHETA (ST)", "CPT Mly Bouchta-Chefchaouen-Tetaoun"),
    ("CPT Mly Bouchta-Chefchaouen-Tetaoun", "CPT Bab Taza - Derdara"),
    ("PRODUCTION ST LOUKKOS", "PRODUCTION OUEZZANE OUEST"),
    ("PRODUCTION ST LOUKKOS", "TRANSPORT KSAR KEBIR"),
    ("TRANSPORT KSAR KEBIR", "PRODUCTION KSAR LEKBIR"),
    ("TRANSPORT KSAR KEBIR", "TRANSPORT LARACHE"),
    ("ST AL HOCEIMA", "TRANSPORT BARRAGE MBAK-RESERVOIR AL HOCEIMA"),
    ("CHAMPS CAPTANTS AL HOCEIMA", "TRANSPORT BARRAGE MBAK-RESERVOIR AL HOCEIMA"),
    ("TRANSPORT BARRAGE MBAK-RESERVOIR AL HOCEIMA", "TRANSPORT RM AJDIR-TARGUIST-ADDUCTION REGIONALE"),
    ("STATION DESSALEMENT AL HOCEIMA", "TRANSPORT RM AJDIR-TARGUIST-ADDUCTION REGIONALE"),
    ("CHAMPS CAPTANTS AL HOCEIMA", "TRANSPORT RM AJDIR-TARGUIST-ADDUCTION REGIONALE"),
    ("TRANSPORT RM AJDIR-TARGUIST-ADDUCTION REGIONALE", "ST TARGUIST"),
]


def default_centres_df() -> pd.DataFrame:
    return pd.DataFrame([dict(zip(COLS, r)) for r in CENTRES_DATA])


def default_flux_df() -> pd.DataFrame:
    return pd.DataFrame([{"Source": s, "Destination": d, "Volume": 0.0}
                         for s, d in FLUX_INTERNES])


def rdt(num, den):
    return (num / den * 100) if den else 0.0


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, encoding="utf-8") as f:
                d = json.load(f)
            return pd.DataFrame(d["centres"]), pd.DataFrame(d["flux"])
        except Exception:
            pass
    return default_centres_df(), default_flux_df()


def save_data(centres, flux):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"centres": centres.to_dict("records"),
                   "flux": flux.to_dict("records")}, f, ensure_ascii=False, indent=2)


def compute(centres, flux):
    df = centres.copy()
    for c in NUM_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    for c in ("Secteur", "Catégorie"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    df["Ventes"] = df["Vente SRM"] + df["Vente AMENDIS"]
    df["Entrée"] = df["Production"] + df["Achat adduction"] + df["Achat externe"]
    df["Sortie comptée"] = df["Ventes"] + df["Cession adduction"] + df["Pertes techniques"]
    df["Pertes non tech."] = df["Entrée"] - df["Sortie comptée"]
    df["Rendement %"] = df.apply(lambda r: rdt(r["Sortie comptée"], r["Entrée"]), axis=1)

    cat = dict(zip(df["Centre"], df["Catégorie"]))
    fx = flux.copy()
    fx["Volume"] = pd.to_numeric(fx["Volume"], errors="coerce").fillna(0.0)

    def elim_interne(members):
        members = set(members)
        return sum(float(r["Volume"]) for _, r in fx.iterrows()
                   if r["Source"] in members and r["Destination"] in members)

    def agg(sub):
        elim = elim_interne(sub["Centre"])
        prod = sub["Production"].sum(); ach = sub["Achat adduction"].sum()
        ext = sub["Achat externe"].sum(); cess = sub["Cession adduction"].sum()
        vte = sub["Ventes"].sum(); pt = sub["Pertes techniques"].sum()
        entree = prod + (ach - elim) + ext
        sortie = vte + (cess - elim) + pt
        return {"Nb centres": len(sub), "Production": prod, "Achat net": ach - elim,
                "Achat externe": ext, "Entrée": entree, "Ventes": vte,
                "Cession nette": cess - elim, "Pertes techniques": pt,
                "Sortie comptée": sortie, "Pertes non tech.": entree - sortie,
                "Rendement %": rdt(sortie, entree)}

    rows = []
    for s in SECTEURS:
        sub = df[df["Secteur"] == s]
        if len(sub):
            rows.append({"Périmètre": f"SP{s}", **agg(sub)})
    for c in (1, 2):
        sub = df[df["Catégorie"] == c]
        if len(sub):
            lib = "grandes" if c == 2 else "petites/moyennes"
            rows.append({"Périmètre": f"Catégorie {c} ({lib})", **agg(sub)})
    rows.append({"Périmètre": "DR GLOBALE", **agg(df)})
    synthese = pd.DataFrame(rows)

    # réconciliation cumuls vs flux
    cess_f, ach_f = {}, {}
    for _, r in fx.iterrows():
        cess_f[r["Source"]] = cess_f.get(r["Source"], 0.0) + float(r["Volume"])
        ach_f[r["Destination"]] = ach_f.get(r["Destination"], 0.0) + float(r["Volume"])
    recon = pd.DataFrame([{
        "Centre": r["Centre"],
        "Cession (cumul)": r["Cession adduction"], "Cession (flux)": cess_f.get(r["Centre"], 0.0),
        "Écart cession": r["Cession adduction"] - cess_f.get(r["Centre"], 0.0),
        "Achat (cumul)": r["Achat adduction"], "Achat (flux)": ach_f.get(r["Centre"], 0.0),
        "Écart achat": r["Achat adduction"] - ach_f.get(r["Centre"], 0.0),
    } for _, r in df.iterrows()])

    return df, synthese, recon


def build_html_report(synthese, detail, periode):
    dr = synthese[synthese["Périmètre"] == "DR GLOBALE"].iloc[0]
    secteurs = synthese[synthese["Périmètre"].str.startswith("SP")]
    faibles = detail[detail["Rendement %"] < 90].sort_values("Rendement %")
    best_sec = secteurs.loc[secteurs["Rendement %"].idxmax()] if len(secteurs) else None
    worst_sec = secteurs.loc[secteurs["Rendement %"].idxmin()] if len(secteurs) else None

    def tbl(dfr, cols):
        h = "".join(f"<th>{c}</th>" for c in cols)
        rws = ""
        for _, r in dfr.iterrows():
            tds = ""
            for c in cols:
                v = r[c]
                v = f"{v:,.2f} %" if c == "Rendement %" else (f"{v:,.0f}" if isinstance(v, (int, float)) else v)
                tds += f"<td>{v}</td>"
            rws += f"<tr>{tds}</tr>"
        return f"<table><thead><tr>{h}</tr></thead><tbody>{rws}</tbody></table>"

    obs = []
    if worst_sec is not None:
        obs.append(f"Le secteur de production au rendement le plus faible est <b>{worst_sec['Périmètre']}</b> "
                   f"({worst_sec['Rendement %']:.2f} %), le plus élevé <b>{best_sec['Périmètre']}</b> "
                   f"({best_sec['Rendement %']:.2f} %).")
    if len(faibles):
        noms = ", ".join(faibles["Centre"].head(6))
        obs.append(f"{len(faibles)} centre(s) sous 90 % de rendement : {noms}.")
    obs.append(f"Pertes non techniques (non comptabilisées) au niveau DR : "
               f"{dr['Pertes non tech.']:,.0f} m³.")

    syn_cols = ["Périmètre", "Entrée", "Ventes", "Cession nette", "Pertes techniques",
                "Sortie comptée", "Rendement %"]
    det_cols = ["Centre", "Secteur", "Catégorie", "Entrée", "Sortie comptée", "Rendement %"]
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>Rapport rendement adductions</title><style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:32px;color:#173}}
h1{{color:#0a6}}h2{{color:#085;border-bottom:2px solid #0a6;padding-bottom:4px;margin-top:28px}}
.kpi{{font-size:34px;font-weight:700;color:#0a6}}
table{{border-collapse:collapse;width:100%;margin:10px 0;font-size:13px}}
th,td{{border:1px solid #cfe;padding:6px 8px;text-align:right}}th{{background:#e6f7f0}}
td:first-child,th:first-child{{text-align:left}}
li{{margin:4px 0}}.foot{{margin-top:30px;color:#789;font-size:12px}}
</style></head><body>
<h1>Rapport de rendement des adductions — DR</h1>
<p>Période : <b>{periode or "(non précisée)"}</b> · Éditable par le responsable régional.</p>
<p>Rendement global DR : <span class="kpi">{dr['Rendement %']:.2f} %</span></p>
<h2>Synthèse par périmètre</h2>{tbl(synthese[syn_cols], syn_cols)}
<h2>Observations</h2><ul>{''.join(f'<li>{o}</li>' for o in obs)}</ul>
<h2>Détail par centre</h2>{tbl(detail[det_cols], det_cols)}
<p class="foot">Formule : Rendement = (Ventes + Cession adduction + Pertes techniques) /
(Production + Achat adduction + Achat externe) × 100.
Généré automatiquement — à valider par le responsable DR.</p>
</body></html>"""


# --------------------------------------------------------------------------- #
# État + rôle
# --------------------------------------------------------------------------- #
if "centres" not in st.session_state:
    st.session_state.centres, st.session_state.flux = load_data()

st.sidebar.title("💧 Rendement adductions")
profil = st.sidebar.radio(
    "Profil / accès",
    ["Responsable DR"] + [f"Agent SP{s}" for s in SECTEURS],
    help="Un agent de secteur de production ne saisit que son périmètre ; le responsable DR "
         "voit tout et édite les rapports.",
)
periode = st.sidebar.text_input("Période", value="")
if st.sidebar.button("💾 Enregistrer les données"):
    save_data(st.session_state.centres, st.session_state.flux)
    st.sidebar.success("Données enregistrées.")
if st.sidebar.button("↺ Réinitialiser"):
    st.session_state.centres, st.session_state.flux = default_centres_df(), default_flux_df()
    st.rerun()

centres = st.session_state.centres.copy()
centres["Secteur"] = pd.to_numeric(centres["Secteur"], errors="coerce").fillna(0).astype(int)
sec_of = dict(zip(centres["Centre"], centres["Secteur"]))

is_dr = profil == "Responsable DR"
mon_secteur = None if is_dr else int(profil.replace("Agent SP", ""))

# --------------------------------------------------------------------------- #
# Interface
# --------------------------------------------------------------------------- #
if is_dr:
    st.title("Tableau de bord — Responsable DR")
else:
    st.title(f"Saisie — Secteur de production {mon_secteur} (SP{mon_secteur})")
    st.caption("Vous ne modifiez que les centres et les flux de votre secteur de production.")

col_cfg = {
    "Secteur": st.column_config.SelectboxColumn("Secteur prod.", options=SECTEURS, required=True,
        help="Secteur de production (SP1 à SP4)"),
    "Catégorie": st.column_config.SelectboxColumn(options=[1, 2], required=True,
        help="1 = petites/moyennes · 2 = grandes"),
    **{c: st.column_config.NumberColumn(min_value=0.0, format="%.0f") for c in NUM_COLS},
}

tabs = st.tabs(["🏭 Centres", "🔁 Flux internes", "📊 Résultats"]
               + (["📄 Rapports"] if is_dr else []))

# --- Centres ---
with tabs[0]:
    if is_dr:
        st.subheader("Tous les centres")
        edited = st.data_editor(st.session_state.centres, num_rows="dynamic",
                                use_container_width=True, key="ed_c", height=560,
                                column_config=col_cfg)
        st.session_state.centres = edited
    else:
        st.subheader(f"Centres de la secteur de production {mon_secteur} (SP{mon_secteur})")
        mine = st.session_state.centres[st.session_state.centres["Secteur"] == mon_secteur]
        others = st.session_state.centres[st.session_state.centres["Secteur"] != mon_secteur]
        edited = st.data_editor(mine, num_rows="dynamic", use_container_width=True,
                                key="ed_c", height=520, column_config=col_cfg)
        st.session_state.centres = pd.concat([others, edited], ignore_index=True)

# --- Flux ---
with tabs[1]:
    st.subheader("Transferts internes à la DR (source → destination)")
    st.caption("Volume de chaque cession interne. Élimination automatique : "
               "intra-secteur, intra-catégorie et intra-DR.")
    flux = st.session_state.flux
    if is_dr:
        edited_f = st.data_editor(flux, num_rows="dynamic", use_container_width=True,
                                  key="ed_f", height=460,
                                  column_config={"Volume": st.column_config.NumberColumn(
                                      min_value=0.0, format="%.0f")})
        st.session_state.flux = edited_f
    else:
        mask = flux["Source"].map(sec_of).fillna(0).astype(int) == mon_secteur
        mine_f, others_f = flux[mask], flux[~mask]
        edited_f = st.data_editor(mine_f, num_rows="dynamic", use_container_width=True,
                                  key="ed_f", height=420,
                                  column_config={"Volume": st.column_config.NumberColumn(
                                      min_value=0.0, format="%.0f")})
        st.session_state.flux = pd.concat([others_f, edited_f], ignore_index=True)

    _, _, recon = compute(st.session_state.centres, st.session_state.flux)
    if not is_dr:
        recon = recon[recon["Centre"].map(sec_of).fillna(0).astype(int) == mon_secteur]
    ecart = recon[(recon["Écart cession"].abs() > 0.5) | (recon["Écart achat"].abs() > 0.5)]
    st.markdown("**Réconciliation** — cumuls (onglet Centres) vs somme des flux")
    if ecart.empty:
        st.success("Cohérent : cumuls achat/cession = somme des flux.")
    else:
        st.dataframe(ecart.style.format({c: "{:,.0f}" for c in ecart.columns if c != "Centre"}),
                     use_container_width=True)

# --- Résultats ---
with tabs[2]:
    detail, synthese, recon = compute(st.session_state.centres, st.session_state.flux)
    if not is_dr:
        detail = detail[detail["Secteur"] == mon_secteur]
        synthese = synthese[synthese["Périmètre"] == f"SP{mon_secteur}"]

    if is_dr:
        dr = synthese[synthese["Périmètre"] == "DR GLOBALE"].iloc[0]
        st.subheader("Rendement global DR" + (f" — {periode}" if periode else ""))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rendement DR", f"{dr['Rendement %']:.2f} %")
        c2.metric("Entrée (m³)", f"{dr['Entrée']:,.0f}")
        c3.metric("Sortie comptée (m³)", f"{dr['Sortie comptée']:,.0f}")
        c4.metric("Pertes non tech. (m³)", f"{dr['Pertes non tech.']:,.0f}")

    st.subheader("Synthèse par périmètre")
    fmt = {c: "{:,.0f}" for c in synthese.columns
           if c not in ("Périmètre", "Nb centres", "Rendement %")}
    st.dataframe(synthese.style.format({**fmt, "Rendement %": "{:.2f}"}),
                 use_container_width=True)
    if len(synthese) > 1:
        st.bar_chart(synthese.set_index("Périmètre")["Rendement %"])

    st.subheader("Détail par centre")
    show = detail[["Centre", "Secteur", "Catégorie", "Entrée", "Ventes",
                   "Cession adduction", "Pertes techniques", "Sortie comptée",
                   "Pertes non tech.", "Rendement %"]]
    st.dataframe(show.style.format({**{c: "{:,.0f}" for c in show.columns
                 if c not in ("Centre", "Secteur", "Catégorie", "Rendement %")},
                 "Rendement %": "{:.2f}"}), use_container_width=True, height=520)

# --- Rapports (responsable DR) ---
if is_dr:
    with tabs[3]:
        detail, synthese, _ = compute(st.session_state.centres, st.session_state.flux)
        st.subheader("Génération des rapports")

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as xls:
            detail.to_excel(xls, sheet_name="Par centre", index=False)
            synthese.to_excel(xls, sheet_name="Synthese", index=False)
            st.session_state.flux.to_excel(xls, sheet_name="Flux internes", index=False)
        st.download_button("⬇️ Rapport Excel (données)", buf.getvalue(),
                           file_name="rendement_adductions.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        html = build_html_report(synthese, detail, periode)
        st.download_button("⬇️ Rapport analytique (HTML, imprimable en PDF)", html,
                           file_name="rapport_rendement.html", mime="text/html")
        with st.expander("Aperçu du rapport analytique"):
            st.components.v1.html(html, height=600, scrolling=True)
