import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Definiera användarnamn och lösenord
usernames = ["user1", "user2"]
passwords = ["password1", "password2"]

# Skapa en lista av hashade lösenord (använd hash_passwords för att förhasha lösenorden)
credentials = {
    'usernames': {
        'user1': {
            'email': 'user1@example.com',
            'first_name': 'User',
            'last_name': 'One',
            'password': 'password1',  # Detta är fortfarande det okrypterade lösenordet
        },
        'user2': {
            'email': 'user2@example.com',
            'first_name': 'User',
            'last_name': 'Two',
            'password': 'password2',  # Detta är fortfarande det okrypterade lösenordet
        }
    }
}

# För-hasha lösenord
stauth.Hasher.hash_passwords(credentials)

# Konfigurera autentisering
authenticator = stauth.Authenticate(
    credentials['usernames'],
    cookie_name="cookie_name",
    cookie_key="cookie_key",
    cookie_expiry_days=30
)

# Använd autentisering
name, authentication_status = authenticator.login("Logga in", "main")

# Om användaren inte är inloggad, visa ett felmeddelande och stoppa appen från att fortsätta
if not authentication_status:
    st.error("Felaktigt användarnamn eller lösenord")
    st.stop()  # Stoppar appen här, så den inte fortsätter köra
else:
    st.write(f"Välkommen {name}!")
    # Din app-kod här
    # Exempel på att visa något efter inloggning:
    st.write("Din app kör här!")

    # Resten av din app-kod följer här, t.ex. uppladdning av filer, datahantering, visualiseringar osv.

    # Titel och konfiguration
    st.set_page_config(page_title='Aktiekursanalys', page_icon='📈')
    st.title("📈 Aktiekalkylator")

    # Filuppladdning (multipla filer)
    uploaded_files = st.file_uploader("Ladda upp en eller flera CSV-filer (endast Millistream)", type=["csv"], accept_multiple_files=True)

    if uploaded_files:
        dataframes = {}

        # Läs in alla uppladdade filer och skapa en dataram för varje
        for uploaded_file in uploaded_files:
            # Läs CSV-filen och hantera olika skiljetecken
            try:
                df = pd.read_csv(uploaded_file, sep=None, decimal=",", engine="python")
            except Exception as e:
                st.error(f"⚠️ Kunde inte läsa filen: {uploaded_file.name}, fel: {e}")
                continue

            # Definiera kolumnnamn
            date_col = "Date"  # Kolumnen för datum
            price_col = "Price"  # Kolumnen för pris

            # Kontrollera om dessa kolumner finns
            if date_col not in df.columns or price_col not in df.columns:
                st.error(f"⚠️ Filen '{uploaded_file.name}' saknar nödvändiga kolumner!")
                continue

            # Konvertera datatyper
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")  # Omvandla datum till datetime-format
            df[price_col] = pd.to_numeric(df[price_col], errors="coerce")  # Omvandla pris till numeriska värden

            # Ta bort rader med saknade värden i datum eller pris
            df = df.dropna(subset=[date_col, price_col])

            # Sortera efter datum
            df = df.sort_values(by=[date_col])

            # Spara data från varje fil i dictionary
            dataframes[uploaded_file.name.replace(".csv", "")] = df[['Date', 'Price']]

        # Slå samman alla dataframes från de uppladdade filerna
        df_merged = None
        for name, df in dataframes.items():
            if df_merged is None:
                df_merged = df.rename(columns={price_col: name})
            else:
                df_merged = df_merged.merge(df, on=date_col, how="outer").rename(columns={price_col: name})

        # Sätt datumformat för det sammanslagna dataframe
        df_merged[date_col] = pd.to_datetime(df_merged[date_col])
        min_date = df_merged[date_col].min().date()
        max_date = df_merged[date_col].max().date()

        # Flikval för användarens val av funktioner (Indexering, Kursutveckling, Bästa/Sämsta Kursdagar)
        option = st.radio("Välj funktion", ("Indexering", "Kursutveckling", "Bästa och sämsta börsdagarna"))

        # Indexering av aktiekurser
        if option == "Indexering":
            st.subheader("📊 Indexera aktiekurser")
            col1, col2 = st.columns(2)
            with col1:
                from_year = st.date_input("Startdatum:", min_date, min_value=min_date, max_value=max_date, format="YYYY-MM-DD")
            with col2:
                to_year = st.date_input("Slutdatum:", max_date, min_value=min_date, max_value=max_date, format="YYYY-MM-DD")

            # Hämta listan med aktier
            aktier = list(dataframes.keys())
            selected_aktier = st.multiselect("Välj aktier att visa:", aktier, aktier[:min(5, len(aktier))])

            # Filtrera data baserat på användarens valda tidsintervall
            df_filtered = df_merged[(df_merged[date_col].dt.date >= from_year) & (df_merged[date_col].dt.date <= to_year)]

            # Kontrollera om det finns data för det valda intervallet
            if df_filtered.empty:
                st.warning("⚠️ Inga data finns för det valda datumintervallet.")
            else:
                # Indexera aktiekurser om checkbox är markerad
                indexera = st.checkbox("Indexera till 100 vid startdatum")
                if indexera and from_year in df_filtered[date_col].dt.date.values:
                    start_values = df_filtered.set_index(date_col).loc[pd.to_datetime(from_year)].dropna()
                    for col in start_values.index:
                        df_filtered[col] = (df_filtered[col] / start_values[col]) * 100
                elif indexera:
                    st.warning(f"⚠️ Startdatum {from_year} finns inte i datan. Indexering görs utifrån första tillgängliga datum i intervallet.")
                    first_valid_date = df_filtered[date_col].min()
                    if pd.notna(first_valid_date):
                        start_values = df_filtered.set_index(date_col).loc[first_valid_date].dropna()
                        for col in start_values.index:
                            df_filtered[col] = (df_filtered[col] / start_values[col]) * 100

                # Runda till två decimaler för att göra det mer läsbart
                for col in df_filtered.columns:
                    if col != date_col:
                        df_filtered[col] = df_filtered[col].round(2)

                st.dataframe(df_filtered[[date_col] + selected_aktier])

                # Plotta graf
                fig, ax = plt.subplots(figsize=(10, 5))
                for aktie in selected_aktier:
                    ax.plot(df_filtered[date_col], df_filtered[aktie], label=aktie)
                ax.set_xlabel("Datum")
                ax.set_ylabel("Kursvärde")
                ax.legend()
                ax.grid(True)
                st.pyplot(fig)

                # Exportera indexerad data
                csv = df_filtered.to_csv(index=False, sep=";", decimal=",").encode("utf-8")
                st.download_button("⬇️ Ladda ner Infogram-data (CSV)", data=csv, file_name="indexed_data.csv", mime="text/csv")

                # Lägga till en länk till Infogram och en förklarande text
                st.markdown(
                    """
                [Länk till Infogram-mallen (öppnas i ny flik)](https://infogram.com/app/#/edit/d93aa8ea-472b-42f5-a0f8-12e675221e71)

                Steg: 1) Duplicera Infogram-mallen. 2) Ladda upp CSV-filen under "Edit data"

                """
                )

        # Kursutveckling
        elif option == "Kursutveckling":
            st.subheader("📈 Kursutveckling")
            col1, col2 = st.columns(2)
            with col1:
                from_year = st.date_input("Startdatum:", min_date, min_value=min_date, max_value=max_date, format="YYYY-MM-DD")
            with col2:
                to_year = st.date_input("Slutdatum:", max_date, min_value=min_date, max_value=max_date, format="YYYY-MM-DD")

            selected_aktier = st.multiselect("Välj aktier att visa:", list(dataframes.keys()))
            df_filtered = df_merged[(df_merged[date_col].dt.date >= from_year) & (df_merged[date_col].dt.date <= to_year)]

            procentuell_forandring = {}
            for aktie in selected_aktier:
                start_value = df_filtered[df_filtered[date_col] == pd.to_datetime(from_year)].get(aktie)
                end_value = df_filtered[df_filtered[date_col] == pd.to_datetime(to_year)].get(aktie)
                if not start_value.empty and not end_value.empty:
                    start_value = start_value.iloc[0]
                    end_value = end_value.iloc[0]
                    procent = ((end_value - start_value) / start_value) * 100
                    procentuell_forandring[aktie] = round(procent, 2)
                else:
                    procentuell_forandring[aktie] = None

            for aktie, procent in procentuell_forandring.items():
                if procent is not None:
                    st.write(f"{aktie}: {procent}% förändring från {from_year} till {to_year}")
                else:
                    st.write(f"{aktie}: Ingen data tillgänglig för det valda tidsintervallet.")

        # Bästa och Sämsta Kursdagar
        elif option == "Bästa och sämsta börsdagarna":
            st.subheader("📅 Bästa och sämsta börsdagarna")
            col1, col2 = st.columns(2)
            with col1:
                from_year = st.date_input("Startdatum:", min_date, min_value=min_date, max_value=max_date, format="YYYY-MM-DD")
            with col2:
                to_year = st.date_input("Slutdatum:", max_date, min_value=min_date, max_value=max_date, format="YYYY-MM-DD")

            # Filtrera data baserat på valt intervall
            df_filtered = df_merged[(df_merged[date_col].dt.date >= from_year) & (df_merged[date_col].dt.date <= to_year)]
            
            # Omvandla alla aktiekurser till en lång format för att kunna sortera
            df_stacked = df_filtered.set_index(date_col).stack().reset_index(name='Price')
            df_stacked.columns = ['Date', 'Stock', 'Price']  # Döpa om kolumnerna för tydlighet
            
            # Beräkna procentuell förändring mellan dagens och föregående dags stängningskurs
            df_stacked['Prev Price'] = df_stacked.groupby('Stock')['Price'].shift(1)
            df_stacked['Percent Change'] = ((df_stacked['Price'] - df_stacked['Prev Price']) / df_stacked['Prev Price']) * 100

            # Filtrera bort de rader där vi inte kan beräkna förändring (första dagen)
            df_stacked = df_stacked.dropna(subset=['Percent Change'])

            # Hitta de bästa och sämsta kursdagarna
            best_days = df_stacked.nlargest(10, 'Percent Change')
            worst_days = df_stacked.nsmallest(10, 'Percent Change')

            # Visa tabeller med snyggare format
            st.write("De 10 bästa kursdagarna:")
            st.dataframe(best_days[['Date', 'Stock', 'Price', 'Percent Change']].style.format({'Price': '{:.2f}', 'Percent Change': '{:.2f}'}))

            st.write("De 10 sämsta kursdagarna:")
            st.dataframe(worst_days[['Date', 'Stock', 'Price', 'Percent Change']].style.format({'Price': '{:.2f}', 'Percent Change': '{:.2f}'}))
