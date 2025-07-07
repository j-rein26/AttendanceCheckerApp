import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io

# ---------- Simple Password Protection ----------
def check_password():
    """Simple password check."""
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["authenticated"] = True
            del st.session_state["password"]  # remove password from memory
        else:
            st.session_state["authenticated"] = False

    if "authenticated" not in st.session_state:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.stop()
    elif not st.session_state["authenticated"]:
        st.error("Incorrect password")
        st.stop()

check_password()  # Require password before running the rest of the app

# ---------- Helper functions ----------

def get_sunday_before(date):
    return date - timedelta(days=(date.weekday() + 1) % 7)

def get_people_last_attended_in_week(df, reference_sunday, weeks_ago):
    week_sunday = reference_sunday - timedelta(weeks=weeks_ago)
    week_dates = [week_sunday + timedelta(days=i) for i in range(3)]  # Sunday, Monday, Tuesday

    matches = df[df['Last Attended Date'].isin(week_dates)]
    attendees = sorted(matches['Full Name'].unique())

    return attendees, week_dates

# ---------- Streamlit App ----------

st.title("Attendance Checker: Last Attended Dates by Week")

uploaded_file = st.file_uploader("Upload Attendance CSV", type=['csv'])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)

        # ✅ Check required columns
        required_columns = {'First Name', 'Last Name', 'Last Attended Date'}
        if not required_columns.issubset(df.columns):
            st.error("❌ CSV must contain 'First Name', 'Last Name', and 'Last Attended Date' columns.")
        else:
            try:
                # ✅ Combine First + Last Name
                df['Full Name'] = df['First Name'].str.strip() + ' ' + df['Last Name'].str.strip()
                df['Last Attended Date'] = pd.to_datetime(df['Last Attended Date'])

                report_date = st.date_input("Select Monday for the Report", value=datetime.today())
                reference_sunday = get_sunday_before(pd.to_datetime(report_date))
                st.write(f"Reference Sunday (the day before): **{reference_sunday.date()}**")

                # Process 2 to 8 weeks ago
                results = {}
                for weeks_ago in range(2, 9):
                    attendees, week_dates = get_people_last_attended_in_week(df, reference_sunday, weeks_ago)
                    week_label = f"{weeks_ago} weeks ago ({week_dates[0].date()} - {week_dates[-1].date()})"

                    with st.expander(week_label, expanded=True):
                        st.write(f"Last attended on: {', '.join([d.strftime('%Y-%m-%d') for d in week_dates])}")

                        checked_names = st.multiselect(
                            f"Uncheck names if they were actually present ({week_label}):",
                            attendees,
                            default=attendees,
                            key=week_label
                        )

                        results[week_label] = checked_names

                # Download final report (in-memory Excel file)
                if st.button("Download Final Report"):
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        for week, names in results.items():
                            pd.DataFrame({'Name': names}).to_excel(writer, sheet_name=week[:31], index=False)

                    output.seek(0)
                    st.download_button(
                        label="Download Excel File",
                        data=output,
                        file_name="Absentee_Report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            except Exception as e:
                st.error(f"⚠️ Error processing dates: {e}")
    except Exception as e:
        st.error(f"⚠️ Could not read CSV file: {e}")

