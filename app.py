            usd_to_eur = st.number_input(
                "Taux de conversion dollar → euro",
                min_value=0.0,
                value=float(st.session_state.usd_to_eur),
                step=0.01,
                format="%.4f",
            )

            other_expenses = st.number_input(
                "Autres dépenses (€)",
                min_value=0.0,
                value=float(st.session_state.other_expenses),
                step=10.0,
            )

        with right:
            creator_level = st.selectbox(
                "Palier Créateurs atteint",
                [4, 7, 9, 11, 13, 15],
                index=[4, 7, 9, 11, 13, 15].index(
                    int(st.session_state.creator_level)
                ),
            )

            consultant_level = st.selectbox(
                "Palier Consultants atteint",
                [5, 7, 9, 11, 13],
                index=[5, 7, 9, 11, 13].index(
                    int(st.session_state.consultant_level)
                ),
            )

            manager_level = st.selectbox(
                "Palier Responsables performance atteint",
                [5, 7, 9, 11, 13],
                index=[5, 7, 9, 11, 13].index(
                    int(st.session_state.manager_level)
                ),
            )

            director_level = st.selectbox(
                "Palier Directeur atteint",
                [4, 5, 7, 8, 10, 11, 13],
                index=[4, 5, 7, 8, 10, 11, 13].index(
                    int(st.session_state.director_level)
                ),
            )

        st.subheader("Paramètres financiers")

        fin1, fin2, fin3 = st.columns(3)

        coin_pack_price = fin1.number_input(
            "Prix de 1 000 pièces TikTok (€)",
            min_value=0.0,
            value=float(st.session_state.coin_pack_price),
            step=0.001,
            format="%.3f",
            disabled=financial_settings_locked,
        )

        invoice_rate = fin2.number_input(
            "Valeur facture par diamant (€)",
            min_value=0.0,
            value=float(st.session_state.invoice_rate),
            step=0.0001,
            format="%.4f",
            disabled=financial_settings_locked,
        )

        charges_rate = fin3.number_input(
            "Charges sur le CA (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(st.session_state.charges_rate),
            step=0.1,
            disabled=financial_settings_locked,
        )

        save_parameters = st.form_submit_button(
            "💾 Enregistrer les paramètres",
            use_container_width=True,
        )

    if save_parameters:
        old_levels = (
            st.session_state.creator_level,
            st.session_state.consultant_level,
        )

        st.session_state.month = month
        st.session_state.revenue_usd = revenue_usd
        st.session_state.usd_to_eur = usd_to_eur
        st.session_state.other_expenses = other_expenses
        st.session_state.creator_level = creator_level
        st.session_state.consultant_level = consultant_level
        st.session_state.manager_level = manager_level
        st.session_state.director_level = director_level

        if current_user_role == "admin":
            st.session_state.coin_pack_price = coin_pack_price
            st.session_state.invoice_rate = invoice_rate
            st.session_state.charges_rate = charges_rate

        permanent_save_succeeded = False
        permanent_save_error = None

        if persistent_settings_available:
            scopes_to_save = {
                branch_settings_scope(current_user_email): {
                    key: st.session_state[key]
                    for key in BRANCH_PARAMETER_KEYS
                }
            }

            if current_user_role == "admin":
                scopes_to_save["global:financial"] = {
                    key: st.session_state[key]
                    for key in GLOBAL_FINANCIAL_KEYS
                }

            try:
                save_persistent_scopes(
                    database_url,
                    scopes_to_save,
                    current_user_email,
                )
                permanent_save_succeeded = True

            except Exception:
                permanent_save_error = (
                    "L’enregistrement permanent a échoué. Les valeurs "
                    "restent disponibles dans la session actuelle."
                )

        if old_levels != (
            creator_level,
            consultant_level,
        ):
            reset_calculations()

        if permanent_save_succeeded:
            st.success(
                "Les paramètres ont été enregistrés définitivement."
            )

        elif permanent_save_error:
            st.error(permanent_save_error)

        else:
            st.warning(
                "Les paramètres ont été enregistrés uniquement pour la "
                "session actuelle. Configurez la base permanente pour les "
                "retrouver après une déconnexion."
            )


elif page == "🛡️ Administration":
    if current_user_role not in {"admin", "director"}:
        st.error("Vous n’avez pas accès à cette page.")
        st.stop()

    st.title("🛡️ Administration des exclusions")

    st.write(
        "Ajoutez, modifiez ou supprimez une adresse à tout moment. "
        "Une ligne supprimée est automatiquement réintégrée aux calculs."
    )

    st.info(
        f"Les exclusions enregistrées ici concernent uniquement "
        f"**{current_user_direction}**. Elles n’affectent aucune autre "
        "direction."
    )

    exclusions_save_notice = st.session_state.pop(
        "exclusions_save_notice",
        None,
    )

    if exclusions_save_notice:
        notice_type, notice_message = exclusions_save_notice
        getattr(st, notice_type)(notice_message)

    if persistent_settings_available:
        st.caption(
            "☁️ Sauvegarde permanente active : les exclusions seront "
            "retrouvées après une déconnexion ou un redémarrage."
        )

    elif persistent_settings_error:
        st.warning(persistent_settings_error)

    else:
        st.warning(
            "La sauvegarde permanente n’est pas configurée. Les exclusions "
            "seront conservées uniquement pendant cette session."
        )

    if st.session_state.backstage_data is not None:
        backstage = st.session_state.backstage_data
        detected_rows = []

        if "Agent" in backstage.columns:
            for value in backstage["Agent"].dropna().unique():
                email = normalize_email(value)

                if email and email != "nan":
                    detected_rows.append(
                        {
                            "Adresse détectée": email,
                            "Emplacement": "Agent",
                        }
                    )

        if "Groupe" in backstage.columns:
            for value in backstage["Groupe"].dropna().unique():
                email = normalize_email(value)

                if email and email != "nan":
                    detected_rows.append(
                        {
                            "Adresse détectée": email,
                            "Emplacement": "Groupe",
                        }
                    )

        if detected_rows:
            detected_dataframe = (
                pd.DataFrame(detected_rows).drop_duplicates()
            )

            with st.expander(
                "🔎 Voir toutes les adresses détectées dans l’export"
            ):
                st.dataframe(
                    detected_dataframe.sort_values(
                        [
                            "Emplacement",
                            "Adresse détectée",
                        ]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

    exclusions_dataframe = pd.DataFrame(
        st.session_state.exclusions,
        columns=[
            "Adresse e-mail",
            "Exclure consultants",
            "Exclure responsables performance",
        ],
    )

    edited_exclusions = st.data_editor(
        exclusions_dataframe,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Adresse e-mail": st.column_config.TextColumn(
                "E-mail ou nom du groupe",
                help=(
                    "Saisissez l’adresse exacte de la colonne Agent ou le "
                    "nom exact présent dans la colonne Groupe."
                ),
            ),
            "Exclure consultants": (
                st.column_config.CheckboxColumn(
                    "Exclure consultants",
                    default=True,
                )
            ),
            "Exclure responsables performance": (
                st.column_config.CheckboxColumn(
                    "Exclure responsables performance",
                    default=True,
                )
            ),
        },
        key="exclusions_editor",
    )

    if st.button(
        "💾 Enregistrer les exclusions",
        type="primary",
        use_container_width=True,
    ):
        cleaned_exclusions = clean_exclusions(
            edited_exclusions.to_dict("records")
        )

        st.session_state.exclusions = cleaned_exclusions
        st.session_state.pop("consultant_results", None)
        st.session_state.pop("consultant_signature", None)
        st.session_state.pop("consultant_payment_editor", None)
        st.session_state.pop("responsable_results", None)
        st.session_state.pop("responsable_signature", None)
        st.session_state.pop("responsable_payment_editor", None)

        if persistent_settings_available:
            try:
                save_persistent_scopes(
                    database_url,
                    {
                        exclusions_scope(current_user_email): {
                            "rows": cleaned_exclusions,
                        }
                    },
                    current_user_email,
                )

                st.session_state.exclusions_save_notice = (
                    "success",
                    f"{len(cleaned_exclusions)} exclusion(s) "
                    "enregistrée(s) définitivement pour votre direction.",
                )

            except Exception:
                st.session_state.exclusions_save_notice = (
                    "error",
                    "L’enregistrement permanent a échoué. Les exclusions "
                    "restent actives uniquement dans la session actuelle.",
                )

        else:
            st.session_state.exclusions_save_notice = (
                "warning",
                f"{len(cleaned_exclusions)} exclusion(s) enregistrée(s) "
                "uniquement pour cette session.",
            )

        st.rerun()

    if st.session_state.exclusions:
        st.caption(
            "Les exclusions sont actives dans les calculs Consultants et "
            "Responsables performance."
        )

    else:
        st.info("Aucune adresse n’est actuellement exclue.")


elif page == "💎 Créateurs":
    st.title("💎 Calcul des créateurs")
    show_estimation_notice()

    if st.session_state.backstage_data is None:
        st.warning("Importez d’abord un export Backstage.")
        st.stop()

    creator_signature = (
        st.session_state.backstage_filename,
        st.session_state.creator_level,
    )

    if (
        "creator_results" not in st.session_state
        or st.session_state.get("creator_signature")
        != creator_signature
    ):
        creator_results = calculate_creator_rewards(
            st.session_state.backstage_data,
            int(st.session_state.creator_level),
        )

        creator_results["Rémunération calculée 💎"] = (
            creator_results["Rémunération 💎"]
        )
        creator_results["Inclure rémunération créateur"] = "Oui"
        creator_results["Mode paiement"] = "Diamants"

        st.session_state.creator_results = creator_results
        st.session_state.creator_signature = creator_signature

    creator_results = st.session_state.creator_results.copy()

    if "Rémunération calculée 💎" not in creator_results.columns:
        creator_results["Rémunération calculée 💎"] = (
            creator_results["Rémunération 💎"]
        )

    if "Inclure rémunération créateur" not in creator_results.columns:
        creator_results["Inclure rémunération créateur"] = "Oui"

    st.divider()

    payment_table = creator_results[
        [
            "Pseudo",
            "Groupe",
            "Agent",
            "Diamants",
            "Inclure rémunération créateur",
            "Rémunération 💎",
            "Mode paiement",
        ]
    ].copy()

    edited_payment_table = st.data_editor(
        payment_table,
        use_container_width=True,
        hide_index=True,
        disabled=[
            "Pseudo",
            "Groupe",
            "Agent",
            "Diamants",
            "Rémunération 💎",
        ],
        column_config={
            "Inclure rémunération créateur": (
                st.column_config.SelectboxColumn(
                    "Rémunérer le créateur",
                    options=["Oui", "Non"],
                    required=True,
                    help=(
                        "Choisissez Non pour un créateur parti. Cela annule "
                        "uniquement sa rémunération personnelle, sans "
                        "modifier les calculs du consultant ou du responsable."
                    ),
                )
            ),
            "Mode paiement": st.column_config.SelectboxColumn(
                "Mode paiement",
                options=[
                    "Diamants",
                    "Facture €",
                ],
                required=True,
            ),
        },
        key="creator_payment_editor",
    )

    creator_results["Mode paiement"] = (
        edited_payment_table["Mode paiement"].values
    )

    creator_results["Inclure rémunération créateur"] = (
        edited_payment_table[
            "Inclure rémunération créateur"
        ].values
    )

    creator_results["Rémunération 💎"] = creator_results[
        "Rémunération calculée 💎"
    ].where(
        creator_results["Inclure rémunération créateur"] == "Oui",
        0,
    )

    creator_results = financial_columns(creator_results)
    st.session_state.creator_results = creator_results

    diamond_total = creator_results.loc[
        creator_results["Mode paiement"] == "Diamants",
        "Rémunération 💎",
    ].sum()

    metric1, metric2, metric3, metric4, metric5 = st.columns(5)

    metric1.metric(
        "Créateurs importés",
        len(creator_results),
    )

    metric2.metric(
        "Créateurs rémunérés",
        int(
            (
                creator_results["Rémunération 💎"] > 0
            ).sum()
        ),
    )

    metric3.metric(
        "Paiements diamants",
        f"{diamond_total:,.0f} 💎",
    )

    metric4.metric(
        "Paiements factures",
        f"{creator_results['Facture €'].sum():,.0f} €",
    )

    metric5.metric(
        "Comptés pour la hiérarchie",
        int(
            (
                creator_results["Compté hiérarchie"] == "Oui"
            ).sum()
        ),
    )

    show_financial_summary(creator_results)

    with st.expander(
        "Afficher le détail complet des calculs"
    ):
        st.dataframe(
            creator_results,
            use_container_width=True,
            hide_index=True,
        )


elif page == "👥 Consultants":
    st.title("👥 Calcul des consultants")
    show_estimation_notice()

    if st.session_state.backstage_data is None:
        st.warning("Importez d’abord un export Backstage.")
        st.stop()

    creator_signature = (
        st.session_state.backstage_filename,
        st.session_state.creator_level,
    )

    if (
        "creator_results" not in st.session_state
        or st.session_state.get("creator_signature")
        != creator_signature
    ):
        creator_results = calculate_creator_rewards(
            st.session_state.backstage_data,
            int(st.session_state.creator_level),
        )

        creator_results["Mode paiement"] = "Diamants"
        st.session_state.creator_results = creator_results
        st.session_state.creator_signature = creator_signature

    exclusion_signature = tuple(
        sorted(excluded_emails("consultants"))
    )

    consultant_signature = (
        st.session_state.backstage_filename,
        st.session_state.creator_level,
        st.session_state.consultant_level,
        exclusion_signature,
    )

    if (
        "consultant_results" not in st.session_state
        or st.session_state.get("consultant_signature")
        != consultant_signature
    ):
        consultant_results = calculate_consultant_rewards(
            creator_results=st.session_state.creator_results,
            consultant_level=int(
                st.session_state.consultant_level
            ),
            minimum_team_diamonds=200_000,
        )

        consultant_results["Mode paiement"] = "Diamants"
        st.session_state.consultant_results = consultant_results
        st.session_state.consultant_signature = consultant_signature

    consultant_results = (
        st.session_state.consultant_results.copy()
    )

    if consultant_results.empty:
        st.warning(
            "Aucun consultant n’a été détecté dans la colonne Agent."
        )
        st.stop()

    excluded = excluded_emails("consultants")

    consultant_results["Inclure dans le calcul"] = (
        consultant_results["Consultant"].map(
            lambda value: (
                "Non"
                if normalize_email(value) in excluded
                else "Oui"
            )
        )
    )

    excluded_mask = (
        consultant_results["Inclure dans le calcul"] == "Non"
    )

    consultant_results.loc[
        excluded_mask,
        [
            "Taux",
            "Rémunération 💎",
        ],
    ] = 0

    st.divider()

    payment_table = consultant_results[
        [
            "Consultant",
            "Inclure dans le calcul",
            "Créateurs rattachés",
            "Créateurs comptés",
            "Diamants éligibles",
            "Seuil atteint",
            "Taux",
            "Rémunération 💎",
            "Mode paiement",
        ]
    ].copy()

    edited_payment_table = st.data_editor(
        payment_table,
        use_container_width=True,
        hide_index=True,
        disabled=[
            "Consultant",
            "Inclure dans le calcul",
            "Créateurs rattachés",
            "Créateurs comptés",
            "Diamants éligibles",
            "Seuil atteint",
            "Taux",
            "Rémunération 💎",
        ],
        column_config={
            "Mode paiement": st.column_config.SelectboxColumn(
                "Mode paiement",
                options=[
                    "Diamants",
                    "Facture €",
                ],
                required=True,
            ),
        },
        key="consultant_payment_editor",
    )

    consultant_results["Mode paiement"] = (
        edited_payment_table["Mode paiement"].values
    )

    consultant_results = financial_columns(
        consultant_results
    )

    st.session_state.consultant_results = consultant_results

    diamond_total = consultant_results.loc[
        consultant_results["Mode paiement"] == "Diamants",
        "Rémunération 💎",
    ].sum()

    metric1, metric2, metric3, metric4, metric5 = (
        st.columns(5)
    )

    metric1.metric(
        "Consultants détectés",
        len(consultant_results),
    )

    metric2.metric(
        "Consultants rémunérés",
        int(
            (
                consultant_results["Rémunération 💎"] > 0
            ).sum()
        ),
    )

    metric3.metric(
        "Diamants éligibles",
        f"{consultant_results.loc[~excluded_mask, 'Diamants éligibles'].sum():,.0f} 💎",
    )

    metric4.metric(
        "Paiements diamants",
        f"{diamond_total:,.0f} 💎",
    )

    metric5.metric(
        "Paiements factures",
        f"{consultant_results['Facture €'].sum():,.0f} €",
    )

    show_financial_summary(consultant_results)

    with st.expander("Afficher le détail complet"):
        st.dataframe(
            consultant_results,
            use_container_width=True,
            hide_index=True,
        )


elif page == "📈 Responsables performance":
    st.title("📈 Calcul des responsables performance")
    show_estimation_notice()

    if st.session_state.backstage_data is None:
        st.warning("Importez d’abord un export Backstage.")
        st.stop()

    creator_signature = (
        st.session_state.backstage_filename,
        st.session_state.creator_level,
    )

    if (
        "creator_results" not in st.session_state
        or st.session_state.get("creator_signature")
        != creator_signature
    ):
        creator_results = calculate_creator_rewards(
            st.session_state.backstage_data,
            int(st.session_state.creator_level),
        )

        creator_results["Mode paiement"] = "Diamants"
        st.session_state.creator_results = creator_results
        st.session_state.creator_signature = creator_signature

    exclusion_signature = tuple(
        sorted(excluded_emails("responsables"))
    )

    responsable_signature = (
        st.session_state.backstage_filename,
        st.session_state.creator_level,
        st.session_state.manager_level,
        exclusion_signature,
    )

    if (
        "responsable_results" not in st.session_state
        or st.session_state.get("responsable_signature")
        != responsable_signature
    ):
        responsable_results = calculate_responsable_rewards(
            creator_results=st.session_state.creator_results,
            responsable_level=int(
                st.session_state.manager_level
            ),
            minimum_group_diamonds=600_000,
        )

        responsable_results["Mode paiement"] = "Diamants"
        st.session_state.responsable_results = responsable_results
        st.session_state.responsable_signature = (
            responsable_signature
        )

    responsable_results = (
        st.session_state.responsable_results.copy()
    )

    if responsable_results.empty:
        st.warning(
            "Aucun responsable performance n’a été détecté dans la "
            "colonne Groupe."
        )
        st.stop()

    excluded = excluded_emails("responsables")

    responsable_results["Inclure dans le calcul"] = (
        responsable_results["Responsable performance"].map(
            lambda value: (
                "Non"
                if normalize_email(value) in excluded
                else "Oui"
            )
        )
    )

    excluded_mask = (
        responsable_results["Inclure dans le calcul"] == "Non"
    )

    responsable_results.loc[
        excluded_mask,
        [
            "Taux",
            "Rémunération 💎",
        ],
    ] = 0

    st.divider()

    payment_table = responsable_results[
        [
            "Responsable performance",
            "Inclure dans le calcul",
            "Créateurs rattachés",
            "Créateurs comptés",
            "Diamants éligibles",
            "Seuil atteint",
            "Taux",
            "Rémunération 💎",
            "Mode paiement",
        ]
    ].copy()

    edited_payment_table = st.data_editor(
        payment_table,
        use_container_width=True,
        hide_index=True,
        disabled=[
            "Responsable performance",
            "Inclure dans le calcul",
            "Créateurs rattachés",
            "Créateurs comptés",
            "Diamants éligibles",
            "Seuil atteint",
            "Taux",
            "Rémunération 💎",
        ],
        column_config={
            "Mode paiement": st.column_config.SelectboxColumn(
                "Mode paiement",
                options=[
                    "Diamants",
                    "Facture €",
                ],
                required=True,
            ),
        },
        key="responsable_payment_editor",
    )

    responsable_results["Mode paiement"] = (
        edited_payment_table["Mode paiement"].values
    )

    responsable_results = financial_columns(
        responsable_results
    )

    st.session_state.responsable_results = responsable_results

    diamond_total = responsable_results.loc[
        responsable_results["Mode paiement"] == "Diamants",
        "Rémunération 💎",
    ].sum()

    metric1, metric2, metric3, metric4, metric5 = (
        st.columns(5)
    )

    metric1.metric(
        "Responsables détectés",
        len(responsable_results),
    )

    metric2.metric(
        "Responsables rémunérés",
        int(
            (
                responsable_results["Rémunération 💎"] > 0
            ).sum()
        ),
    )

    metric3.metric(
        "Diamants éligibles",
        f"{responsable_results.loc[~excluded_mask, 'Diamants éligibles'].sum():,.0f} 💎",
    )

    metric4.metric(
        "Paiements diamants",
        f"{diamond_total:,.0f} 💎",
    )

    metric5.metric(
        "Paiements factures",
        f"{responsable_results['Facture €'].sum():,.0f} €",
    )

    show_financial_summary(responsable_results)

    with st.expander("Afficher le détail complet"):
        st.dataframe(
            responsable_results,
            use_container_width=True,
            hide_index=True,
        )


elif page == "🏢 Directeur de branche":
    st.title("🏢 Calcul du directeur de branche")
    show_estimation_notice()

    if st.session_state.backstage_data is None:
        st.warning("Importez d’abord un export Backstage.")
        st.stop()

    creator_signature = (
        st.session_state.backstage_filename,
        st.session_state.creator_level,
    )

    if (
        "creator_results" not in st.session_state
        or st.session_state.get("creator_signature")
        != creator_signature
    ):
        creator_results = calculate_creator_rewards(
            st.session_state.backstage_data,
            int(st.session_state.creator_level),
        )

        creator_results["Mode paiement"] = "Diamants"
        st.session_state.creator_results = creator_results
        st.session_state.creator_signature = creator_signature

    all_creator_results = (
        st.session_state.creator_results.copy()
    )

    available_groups = sorted(
        value
        for value in all_creator_results["Groupe"]
        .fillna("")
        .astype(str)
        .str.strip()
        .unique()
        if value and value.lower() != "nan"
    )

    st.subheader("Composition de la branche")

    selected_groups = st.multiselect(
        "Cochez les responsables performance appartenant à cette branche",
        options=available_groups,
        default=available_groups,
        help=(
            "Si l’export contient uniquement la branche du directeur, "
            "laissez tous les responsables cochés."
        ),
        key="director_selected_groups",
    )

    if not selected_groups:
        st.warning(
            "Sélectionnez au moins un responsable performance."
        )
        st.stop()

    st.subheader("Taux de conversion dollar → euro")

    rate_col1, rate_col2 = st.columns([3, 1])

    use_ecb_rate = rate_col1.checkbox(
        "Utiliser automatiquement le dernier taux officiel BCE disponible",
        value=bool(st.session_state.use_ecb_rate),
        key="director_use_ecb_rate",
    )

    st.session_state.use_ecb_rate = use_ecb_rate

    if rate_col2.button(
        "🔄 Actualiser le taux",
        use_container_width=True,
        disabled=not use_ecb_rate,
    ):
        fetch_ecb_usd_to_eur_rate.clear()
        st.rerun()

    active_usd_to_eur = float(
        st.session_state.usd_to_eur
    )
    rate_source = "Taux manuel de secours"
    rate_date = datetime.now().strftime("%Y-%m-%d")

    if use_ecb_rate:
        try:
            active_usd_to_eur, rate_date = (
                fetch_ecb_usd_to_eur_rate()
            )

            st.session_state.last_ecb_usd_to_eur = (
                active_usd_to_eur
            )
            st.session_state.last_ecb_rate_date = rate_date
            rate_source = "Banque centrale européenne"

            st.success(
                f"Taux BCE du {rate_date} : "
                f"1 $ = {active_usd_to_eur:.6f} €"
            )

        except Exception:
            if (
                st.session_state.last_ecb_usd_to_eur
                is not None
            ):
                active_usd_to_eur = float(
                    st.session_state.last_ecb_usd_to_eur
                )
                rate_date = (
                    st.session_state.last_ecb_rate_date
                )
                rate_source = "Dernier taux BCE mémorisé"

                st.warning(
                    "La BCE est momentanément inaccessible. Le dernier "
                    f"taux mémorisé du {rate_date} est utilisé."
                )

            else:
                st.warning(
                    "La BCE est momentanément inaccessible. Le taux manuel "
                    "enregistré dans Paramètres est utilisé."
                )

    else:
        active_usd_to_eur = st.number_input(
            "Taux manuel : valeur de 1 dollar en euros",
            min_value=0.0,
            value=float(st.session_state.usd_to_eur),
            step=0.0001,
            format="%.6f",
            key="director_manual_rate",
        )

    st.caption(
        f"Source utilisée : {rate_source}. Le taux BCE est un taux de "
        "référence quotidien et peut différer du taux réellement appliqué "
        "par la banque."
    )

    input1, input2 = st.columns(2)

    revenue_usd = input1.number_input(
        "Chiffre d’affaires Backstage de la branche ($)",
        min_value=0.0,
        value=float(
            st.session_state.director_branch_revenue_usd
        ),
        step=100.0,
        key="director_revenue_input",
    )

    branch_other_expenses = input2.number_input(
        "Autres dépenses propres à la branche (€)",
        min_value=0.0,
        value=float(
            st.session_state.director_branch_other_expenses
        ),
        step=10.0,
        key="director_expenses_input",
    )

    st.session_state.director_branch_revenue_usd = (
        revenue_usd
    )
    st.session_state.director_branch_other_expenses = (
        branch_other_expenses
    )

    branch_creators = all_creator_results[
        all_creator_results["Groupe"].isin(
            selected_groups
        )
    ].copy()

    if "Mode paiement" not in branch_creators.columns:
        branch_creators["Mode paiement"] = "Diamants"

    branch_creators = financial_columns(
        branch_creators
    )

    branch_consultants = calculate_consultant_rewards(
        creator_results=branch_creators,
        consultant_level=int(
            st.session_state.consultant_level
        ),
        minimum_team_diamonds=200_000,
    )

    if not branch_consultants.empty:
        branch_consultants["Mode paiement"] = "Diamants"

        if "consultant_results" in st.session_state:
            saved_consultant_modes = (
                st.session_state.consultant_results
                .drop_duplicates("Consultant")
                .set_index("Consultant")["Mode paiement"]
                .to_dict()
            )

            branch_consultants["Mode paiement"] = (
                branch_consultants["Consultant"]
                .map(saved_consultant_modes)
                .fillna("Diamants")
            )

        consultant_exclusions = excluded_emails(
            "consultants"
        )

        consultant_excluded_mask = (
            branch_consultants["Consultant"].map(
                lambda value: (
                    normalize_email(value)
                    in consultant_exclusions
                )
            )
        )

        branch_consultants.loc[
            consultant_excluded_mask,
            [
                "Taux",
                "Rémunération 💎",
            ],
        ] = 0

        branch_consultants = financial_columns(
            branch_consultants
        )

    branch_responsables = calculate_responsable_rewards(
        creator_results=branch_creators,
        responsable_level=int(
            st.session_state.manager_level
        ),
        minimum_group_diamonds=600_000,
    )

    if not branch_responsables.empty:
        branch_responsables["Mode paiement"] = "Diamants"

        if "responsable_results" in st.session_state:
            saved_responsable_modes = (
                st.session_state.responsable_results
                .drop_duplicates("Responsable performance")
                .set_index(
                    "Responsable performance"
                )["Mode paiement"]
                .to_dict()
            )

            branch_responsables["Mode paiement"] = (
                branch_responsables[
                    "Responsable performance"
                ]
                .map(saved_responsable_modes)
                .fillna("Diamants")
            )

        responsable_exclusions = excluded_emails(
            "responsables"
        )

        responsable_excluded_mask = (
            branch_responsables[
                "Responsable performance"
            ].map(
                lambda value: (
                    normalize_email(value)
                    in responsable_exclusions
                )
            )
        )

        branch_responsables.loc[
            responsable_excluded_mask,
            [
                "Taux",
                "Rémunération 💎",
            ],
        ] = 0

        branch_responsables = financial_columns(
            branch_responsables
        )

    revenue_eur = revenue_usd * active_usd_to_eur

    charges_eur = (
        revenue_eur
        * float(st.session_state.charges_rate)
        / 100
    )

    creator_cost = float(
        branch_creators["Total déduction €"].sum()
    )

    consultant_cost = (
        float(
            branch_consultants[
                "Total déduction €"
            ].sum()
        )
        if not branch_consultants.empty
        else 0.0
    )

    responsable_cost = (
        float(
            branch_responsables[
                "Total déduction €"
            ].sum()
        )
        if not branch_responsables.empty
        else 0.0
    )

    net_profit_before_director = max(
        0.0,
        revenue_eur
        - charges_eur
        - creator_cost
        - consultant_cost
        - responsable_cost
        - branch_other_expenses,
    )

    director_rate = DIRECTOR_RATES.get(
        int(st.session_state.director_level),
        0.0,
    )

    director_reward = (
        net_profit_before_director * director_rate
    )

    remaining_after_director = (
        net_profit_before_director
        - director_reward
    )

    st.divider()
    st.subheader("Résultat de la branche")

    result1, result2, result3, result4 = (
        st.columns(4)
    )

    result1.metric(
        "CA converti",
        f"{revenue_eur:,.2f} €",
    )

    result2.metric(
        f"Charges ({st.session_state.charges_rate:.1f} %)",
        f"− {charges_eur:,.2f} €",
    )

    result3.metric(
        "Bénéfice avant directeur",
        f"{net_profit_before_director:,.2f} €",
    )

    result4.metric(
        f"Rémunération directeur "
        f"({director_rate * 100:.0f} %)",
        f"{director_reward:,.2f} €",
    )

    summary = pd.DataFrame(
        [
            (
                "Chiffre d’affaires converti",
                revenue_eur,
            ),
            (
                "Charges sur le CA",
                -charges_eur,
            ),
            (
                "Rémunérations créateurs",
                -creator_cost,
            ),
            (
                "Rémunérations consultants",
                -consultant_cost,
            ),
            (
                "Rémunérations responsables performance",
                -responsable_cost,
            ),
            (
                "Autres dépenses de la branche",
                -branch_other_expenses,
            ),
            (
                "Bénéfice avant directeur",
                net_profit_before_director,
            ),
            (
                "Rémunération du directeur",
                -director_reward,
            ),
            (
                "Bénéfice restant",
                remaining_after_director,
            ),
        ],
        columns=[
            "Élément",
            "Montant €",
        ],
    )

    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Montant €": st.column_config.NumberColumn(
                format="%.2f €"
            )
        },
    )

    with st.expander(
        "Voir les groupes sélectionnés"
    ):
        st.write(selected_groups)

        st.caption(
            f"{len(branch_creators)} créateur(s), "
            f"{len(branch_consultants)} consultant(s) et "
            f"{len(branch_responsables)} responsable(s) pris en compte."
        )
