"""
Rendement des adductions d'eau potable — Direction Régionale (DR).

Formule (validée sur les données réelles de la DR) :

    Rendement = (Ventes + Cession + Pertes techniques)
                / (Production + Achat adduction + Achat externe) × 100

Les pertes techniques sont au NUMÉRATEUR : le rendement ne pénalise que les
pertes NON techniques (commerciales / non comptabilisées).

Agrégations (par catégorie et DR globale) :
    Les transferts internes (cessions/achats entre centres) sont éliminés :
      - au niveau CATÉGORIE : on retire les transferts INTRA-catégorie ;
      - au niveau DR : on retire TOUS les transferts internes.
    Ce qui reste : achats externes (entrée) et cessions hors périmètre (sortie).
    L'élimination est calculée à partir de la table des flux internes.
"""

import io

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Rendement Adductions DR", page_icon="💧", layout="wide")

# --------------------------------------------------------------------------- #
# Données réelles pré-chargées (m³)   —  Catégorie 2 = grandes, 1 = petites/moyennes
# Colonnes : Production, Achat, Achat externe, Cession, Ventes, Pertes techniques
# --------------------------------------------------------------------------- #
CENTRES_DATA = [
    # --- Grandes adductions (catégorie 2) ---
    ("TRANSPORT CHARF EL AKAB", 2, 0, 42606302, 0, 0, 41426012, 1800),
    ("PRODUCTION CHARF EL AKAB (CEA)", 2, 1680216, 44549509, 0, 44588805, 1490727, 1800),
    ("CENTRE TRANSPORT TAMOUDA-O.MARTIL-Nakhla", 2, 190375, 7500991, 0, 7322567, 186034, 6697),
    ("CENTRE TRANSPORT SMIR TORETA", 2, 0, 16144959, 0, 0, 15999943, 1800),
    ("TRANSPORT BARRAGE MBAK-RESERVOIR AL HOCEIMA", 2, 0, 3498941, 0, 941482, 2436333, 2493),
    ("TRANSPORT RM AJDIR-TRANSFERT TARGUIST-ADDUCTION REGIONALE", 2, 5729, 5640466, 0, 784710, 4501714, 18480),
    # --- Moyennes et petites adductions (catégorie 1) ---
    ("ST HACHEF", 1, 37343429, 0, 0, 37335960, 0, 0),
    ("ST M'HARHAR", 1, 11842871, 0, 0, 11520269, 0, 0),
    ("ST TANGER MED & PRODUCTION TAGHRAMT", 1, 1395479, 121720, 0, 698591, 818264, 0),
    ("CENTRE PRODUCTION RAOUZ (ST RAOUZ)", 1, 3631918, 153290, 0, 3769456, 0, 0),
    ("ST TORRETA", 1, 3059875, 0, 0, 3052620, 7255, 0),
    ("ST SMIR", 1, 4440023, 0, 0, 4440023, 0, 0),
    ("CENTRE DE PRODUCTION OUED MARTIL (ST O.MARTIL)", 1, 7491736, 0, 0, 7491736, 526, 0),
    ("CENTRE DE PRODUCTION MOULAY BOUCHETA (ST)", 1, 402328, 0, 0, 397808, 0, 0),
    ("ST AL HOCEIMA", 1, 1696018, 0, 0, 1590082, 102711, 0),
    ("STATION DESSALEMENT AL HOCEIMA", 1, 3465151, 0, 0, 3465151, 0, 0),
    ("ST TARGUIST", 1, 453963, 388468, 0, 0, 815335, 273),
    ("PRODUCTION ST LOUKKOS", 1, 7669298, 0, 0, 7664444, 0, 4854),
    ("TRANSPORT EAUX TRAITEES HACHEF", 1, 0, 3045380, 0, 0, 2924672, 0),
    ("TRANSPORT M'HARHAR-KSAR SGHIR", 1, 36315, 4104115, 0, 121720, 2709565, 175663),
    ("CENTRE TRANSPORT RAOUZ", 1, 0, 3796153, 0, 1341019, 1576353, 3769),
    ("CPT Oued Laou - Stehat", 1, 284199, 0, 0, 0, 273768, 0),
    ("CTP Bouhmed", 1, 325507, 0, 0, 0, 313742, 0),
    ("CPT Jebha-Bab Berred", 1, 424538, 0, 0, 0, 419875, 522),
    ("CPT Bab Taza - Derdara", 1, 161698, 320543, 0, 0, 457432, 0),
    ("CPT Mly Bouchta-Chefchaouen-Tetaoun", 1, 1725816, 397808, 0, 320543, 1791649, 0),
    ("CHAMPS CAPTANTS AL HOCEIMA", 1, 3414776, 0, 0, 3163361, 219127, 70),
    ("STATIONS DE TRAITEMENT SPECIFIQUES (ISSAGUEN-BNI AMMART-KETAMA)", 1, 129891, 0, 0, 0, 127562, 0),
    ("TRANSPORT LARACHE", 1, 0, 2063443, 0, 0, 1945815, 36416),
    ("PRODUCTION LARACHE", 1, 2621183, 59828, 0, 0, 2627077, 0),
    ("TRANSPORT KSAR KEBIR", 1, 0, 4942267, 0, 3082790, 1646380, 2324),
    ("PRODUCTION KSAR LEKBIR", 1, 457796, 458835, 0, 0, 861289, 11751),
    ("PRODUCTION OUEZZANE OUEST", 1, 1060243, 2420824, 0, 1126031, 2144559, 69778),
    ("PRODUCTION OUEZZANE EST", 1, 241367, 1943564, 0, 0, 1924116, 48408),
]

COLS = ["Centre", "Catégorie", "Production", "Achat", "Achat externe",
        "Cession", "Ventes", "Pertes techniques"]

# Graphe des transferts internes à la DR (source -> destination). Volumes à saisir.
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
    ("TRANSPORT BARRAGE MBAK-RESERVOIR AL HOCEIMA", "TRANSPORT RM AJDIR-TRANSFERT TARGUIST-ADDUCTION REGIONALE"),
    ("STATION DESSALEMENT AL HOCEIMA", "TRANSPORT RM AJDIR-TRANSFERT TARGUIST-ADDUCTION REGIONALE"),
    ("CHAMPS CAPTANTS AL HOCEIMA", "TRANSPORT RM AJDIR-TRANSFERT TARGUIST-ADDUCTION REGIONALE"),
    ("TRANSPORT RM AJDIR-TRANSFERT TARGUIST-ADDUCTION REGIONALE", "ST TARGUIST"),
]


def default_centres_df() -> pd.DataFrame:
    return pd.DataFrame([dict(zip(COLS, row)) for row in CENTRES_DATA])


def default_flux_df() -> pd.DataFrame:
    return pd.DataFrame(
        [{"Source": s, "Destination": d, "Volume": 0.0} for s, d in FLUX_INTERNES]
    )


def rdt(num: float, den: float) -> float:
    return (num / den * 100) if den else 0.0


def compute(centres: pd.DataFrame, flux: pd.DataFrame):
    df = centres.copy()
    for c in COLS[2:]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    df["Catégorie"] = pd.to_numeric(df["Catégorie"], errors="coerce").fillna(1).astype(int)

    df["Entrée"] = df["Production"] + df["Achat"] + df["Achat externe"]
    df["Sortie comptée"] = df["Ventes"] + df["Cession"] + df["Pertes techniques"]
    df["Pertes non tech."] = df["Entrée"] - df["Sortie comptée"]
    df["Rendement %"] = df.apply(lambda r: rdt(r["Sortie comptée"], r["Entrée"]), axis=1)

    cat = dict(zip(df["Centre"], df["Catégorie"]))
    fx = flux.copy()
    fx["Volume"] = pd.to_numeric(fx["Volume"], errors="coerce").fillna(0.0)

    # élimination intra-catégorie et intra-DR à partir des flux internes
    elim_cat = {1: 0.0, 2: 0.0}
    elim_dr = 0.0
    unknown = set()
    cess_flux, ach_flux = {}, {}  # somme des flux par centre (source / destination)
    for _, r in fx.iterrows():
        s, d, v = r["Source"], r["Destination"], float(r["Volume"])
        cess_flux[s] = cess_flux.get(s, 0.0) + v
        ach_flux[d] = ach_flux.get(d, 0.0) + v
        if s in cat and d in cat:
            elim_dr += v
            if cat[s] == cat[d]:
                elim_cat[cat[s]] += v
        else:
            unknown.update({x for x in (s, d) if x not in cat})

    # réconciliation : cumuls saisis (table Centres) vs somme des flux
    recon_rows = []
    for _, r in df.iterrows():
        c = r["Centre"]
        cf, af = cess_flux.get(c, 0.0), ach_flux.get(c, 0.0)
        recon_rows.append({
            "Centre": c,
            "Cession (cumul)": r["Cession"], "Cession (flux)": cf,
            "Écart cession": r["Cession"] - cf,
            "Achat (cumul)": r["Achat"], "Achat (flux)": af,
            "Écart achat": r["Achat"] - af,
        })
    recon = pd.DataFrame(recon_rows)

    def agg(sub, elim):
        prod, ach, ext = sub["Production"].sum(), sub["Achat"].sum(), sub["Achat externe"].sum()
        cess, vte, pt = sub["Cession"].sum(), sub["Ventes"].sum(), sub["Pertes techniques"].sum()
        net_ach = ach - elim
        net_cess = cess - elim
        entree = prod + net_ach + ext
        sortie = vte + net_cess + pt
        return {
            "Production": prod, "Achat net": net_ach, "Achat externe": ext,
            "Entrée": entree, "Ventes": vte, "Cession nette": net_cess,
            "Pertes techniques": pt, "Sortie comptée": sortie,
            "Pertes non tech.": entree - sortie, "Rendement %": rdt(sortie, entree),
        }

    cat_rows = []
    for c in (1, 2):
        sub = df[df["Catégorie"] == c]
        if len(sub):
            row = {"Périmètre": f"Catégorie {c} ({'grandes' if c == 2 else 'petites/moyennes'})",
                   "Nb centres": len(sub)}
            row.update(agg(sub, elim_cat[c]))
            cat_rows.append(row)
    dr_row = {"Périmètre": "DR globale", "Nb centres": len(df)}
    dr_row.update(agg(df, elim_dr))
    synthese = pd.DataFrame(cat_rows + [dr_row])

    return df, synthese, sorted(unknown), elim_cat, elim_dr, recon


# --------------------------------------------------------------------------- #
# État
# --------------------------------------------------------------------------- #
if "centres" not in st.session_state:
    st.session_state.centres = default_centres_df()
    st.session_state.flux = default_flux_df()

st.title("💧 Rendement des adductions — Direction Régionale")
st.caption("Rendement = (Ventes + Cession + Pertes techniques) / "
           "(Production + Achat + Achat externe) × 100")

with st.sidebar:
    st.header("Options")
    periode = st.text_input("Période (libellé)", value="")
    st.markdown("**Élimination des transferts internes**")
    netting = st.checkbox(
        "Nette les cessions/achats internes (via table des flux)", value=True,
        help="Décoché : totaux bruts (simple somme). Coché : on retire les "
             "transferts intra-catégorie / intra-DR saisis dans l'onglet Flux.",
    )
    if st.button("↺ Réinitialiser les données"):
        st.session_state.centres = default_centres_df()
        st.session_state.flux = default_flux_df()
        st.rerun()

tab_c, tab_f, tab_r = st.tabs(["🏭 Centres", "🔁 Flux internes", "📊 Résultats"])

with tab_c:
    st.subheader("Centres — catégorie et volumes (m³)")
    st.session_state.centres = st.data_editor(
        st.session_state.centres, num_rows="dynamic", use_container_width=True,
        key="ed_c", height=560,
        column_config={
            "Catégorie": st.column_config.SelectboxColumn(options=[1, 2], required=True,
                help="1 = petites/moyennes · 2 = grandes"),
            **{c: st.column_config.NumberColumn(min_value=0.0, format="%.0f")
               for c in COLS[2:]},
        },
    )

with tab_f:
    st.subheader("Transferts internes à la DR (pour l'élimination)")
    st.caption("Saisissez le volume de chaque cession interne. Un flux entre deux "
               "centres de la même catégorie est retiré du total de la catégorie ; "
               "tous les flux internes sont retirés du total DR.")
    st.session_state.flux = st.data_editor(
        st.session_state.flux, num_rows="dynamic", use_container_width=True,
        key="ed_f", height=520,
        column_config={"Volume": st.column_config.NumberColumn(min_value=0.0, format="%.0f")},
    )

    _, _, _, _, _, recon = compute(st.session_state.centres, st.session_state.flux)
    st.markdown("**Réconciliation** — cumuls saisis (onglet Centres) vs somme des flux")
    ecart = recon[(recon["Écart cession"].abs() > 0.5) | (recon["Écart achat"].abs() > 0.5)]
    if ecart.empty:
        st.success("Cohérent : chaque cumul achat/cession = somme des flux correspondants.")
    else:
        st.caption("Lignes avec écart (à vérifier) :")
        st.dataframe(
            ecart.style.format({c: "{:,.0f}" for c in ecart.columns if c != "Centre"}),
            use_container_width=True,
        )

with tab_r:
    flux_used = st.session_state.flux if netting else default_flux_df().assign(Volume=0.0)
    detail, synthese, unknown, elim_cat, elim_dr, _ = compute(st.session_state.centres, flux_used)

    if unknown:
        st.warning("Centres cités dans les flux mais absents de la liste : "
                   + ", ".join(unknown))

    dr = synthese[synthese["Périmètre"] == "DR globale"].iloc[0]
    titre = "Rendement global DR" + (f" — {periode}" if periode else "")
    st.subheader(titre)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rendement DR", f"{dr['Rendement %']:.2f} %")
    c2.metric("Entrée (m³)", f"{dr['Entrée']:,.0f}")
    c3.metric("Sortie comptée (m³)", f"{dr['Sortie comptée']:,.0f}")
    c4.metric("Pertes non tech. (m³)", f"{dr['Pertes non tech.']:,.0f}")

    if netting:
        st.caption(f"Élimination intra-catégorie — cat.1 : {elim_cat[1]:,.0f} m³ · "
                   f"cat.2 : {elim_cat[2]:,.0f} m³ · intra-DR : {elim_dr:,.0f} m³")
    else:
        st.info("Netting désactivé : les totaux sont bruts (transferts internes non éliminés).")

    st.subheader("Synthèse par périmètre")
    num_fmt = {c: "{:,.0f}" for c in synthese.columns
               if c not in ("Périmètre", "Nb centres", "Rendement %")}
    st.dataframe(synthese.style.format({**num_fmt, "Rendement %": "{:.2f}"}),
                 use_container_width=True)
    st.bar_chart(synthese.set_index("Périmètre")["Rendement %"])

    st.subheader("Détail par centre")
    show = detail[["Centre", "Catégorie", "Entrée", "Ventes", "Cession",
                   "Pertes techniques", "Sortie comptée", "Pertes non tech.", "Rendement %"]]
    st.dataframe(show.style.format({**{c: "{:,.0f}" for c in show.columns
                 if c not in ("Centre", "Catégorie", "Rendement %")},
                 "Rendement %": "{:.2f}"}), use_container_width=True, height=560)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as xls:
        detail.to_excel(xls, sheet_name="Par centre", index=False)
        synthese.to_excel(xls, sheet_name="Synthese", index=False)
        st.session_state.flux.to_excel(xls, sheet_name="Flux internes", index=False)
    st.download_button("⬇️ Exporter (Excel)", buffer.getvalue(),
                       file_name="rendement_adductions.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
