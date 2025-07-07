import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# ---------- Helper functions ----------

def get_sunday_before(date):
    """Return the Sunday before the given date."""
    return date - timedelta(days=(date.weekday() + 1) % 7)

def get_people_last_attended_in_week(df, reference_sunday, weeks_ago):
    """Return people whose last attendance date was Sunday-Tuesday of the week."""
    week_sunday = reference_sunday - timedelta(weeks=weeks_ago)
    week_dates = [week_sunday + timedelta(days=i) for i in range(3)]  # Sunday, Monday, Tuesday

    # Filter for Last Attended Date in that range
    matches = df[df['Last Attended Date'].isin(week_dates)]
    attendees = sorted(matches['Full Name'].unique())

    return attendees, week_dates

# ---------- Streamlit App ----------

st.title("Attendance Checker: Last Attended Dates by Week")

# Upload CSV
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
                # ✅ Combine First + Last Name into Full Name
                df['Full Name'] = df['First Name'].str.strip() + ' ' + df['Last Name'].str.strip()

                # ✅ Parse dates
                df['Last Attended Date'] = pd.to_datetime(df['Last Attended Date'])

                # Get Report Date (Monday)
                report_date = st.date_input("Select Monday for the Report", value=datetime.today())
                reference_sunday = get_sunday_before(pd.to_datetime(report_date))
                st.write(f"Reference Sunday (the day before): **{reference_sunday.date()}**")

                # Loop for 2 to 8 weeks ago
                results = {}
                for weeks_ago in range(2, 9):
                    attendees, week_dates = get_people_last_attended_in_week(df, reference_sunday, weeks_ago)
                    week_label = f"{weeks_ago} weeks ago ({week_dates[0].date()} - {week_dates[-1].date()})"

                    with st.expander(week_label, expanded=True):
                        st.write(f"Last attended on: {', '.join([d.strftime('%Y-%m-%d') for d in week_dates])}")

                        # Show attendees as multi-select
                        checked_names = st.multiselect(
                            f"Uncheck names if they were actually present ({week_label}):",
                            attendees,
                            default=attendees,
                            key=week_label
                        )

                        results[week_label] = checked_names

                # Download final report
                if st.button("Download Final Report"):
                    with pd.ExcelWriter("Absentee_Report.xlsx") as writer:
                        for week, names in results.items():
                            pd.DataFrame({'Name': names}).to_excel(writer, sheet_name=week[:31], index=False)

                    with open("Absentee_Report.xlsx", "rb") as f:
                        st.download_button(
                            "Download Excel File",
                            f,
                            file_name="Absentee_Report.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

            except Exception as e:
                st.error(f"⚠️ Error processing dates: {e}")
    except Exception as e:
        st.error(f"⚠️ Could not read CSV file: {e}")


