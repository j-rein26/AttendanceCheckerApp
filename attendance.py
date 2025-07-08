import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import io


def create_excel_download(results_dict):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for week_label, names in results_dict.items():
            # Extract the week number from the label (e.g., "2 weeks ago (...)")
            weeks_ago = week_label.split(" ")[0]
            sheet_name = f"Week_{weeks_ago}"

            # Write each week to its own sheet
            pd.DataFrame({'Name': names}).to_excel(writer, sheet_name=sheet_name, index=False)

    output.seek(0)
    return output


# ---------- Password Protection ----------
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["authenticated"] = True
            del st.session_state["password"]
        else:
            st.session_state["authenticated"] = False

    if "authenticated" not in st.session_state:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.stop()
    elif not st.session_state["authenticated"]:
        st.error("Incorrect password")
        st.stop()

check_password()

# ---------- Google Sheets Helper ----------
def connect_to_gsheet():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(credentials)
    return client

def load_attendance_data():
    gc = connect_to_gsheet()
    spreadsheet = gc.open("Attendance_Data")
    worksheet = spreadsheet.worksheet("TotalAttendance")
    records = worksheet.get_all_records()
    df = pd.DataFrame(records)
    return df

def save_absentee_results(results_dict):
    gc = connect_to_gsheet()
    spreadsheet = gc.open("Attendance_Data")

    # Try to open or create the "Absentee Report" worksheet
    try:
        worksheet = spreadsheet.worksheet("AbsenteeReport")
        worksheet.clear()
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="AbsenteeReport", rows="100", cols="5")

    # Flatten results into rows
    all_rows = []
    for week, names in results_dict.items():
        for name in names:
            all_rows.append([week, name])

    # Update the sheet
    worksheet.update([["Week", "Name"]] + all_rows)

# ---------- Date Helpers ----------
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

try:
    df = load_attendance_data()

    # Check required columns
    required_columns = {'First Name', 'Last Name', 'Last Attended Date'}
    if not required_columns.issubset(df.columns):
        st.error("❌ Google Sheet must contain 'First Name', 'Last Name', and 'Last Attended Date' columns.")
    else:
        # Combine first + last names
        df['Full Name'] = df['First Name'].str.strip() + ' ' + df['Last Name'].str.strip()
        df['Last Attended Date'] = pd.to_datetime(df['Last Attended Date'])

        # Select week for the report
        report_date = st.date_input("Select Monday for the Report", value=datetime.today())
        reference_sunday = get_sunday_before(pd.to_datetime(report_date))
        st.write(f"Reference Sunday (the day before): **{reference_sunday.date()}**")

        # Attendance by week
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

        # Save final results
        if st.button("Save Final Report"):
            save_absentee_results(results)
            st.success("✅ Results saved to Google Sheets.")


        # Create Excel file
            excel_data = create_excel_download(results)

        # Show download button
            st.download_button(
            label="📥 Download Excel File",
            data=excel_data,
            file_name="Absentee_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_button"
        )


except Exception as e:
    st.error(f"⚠️ Error loading data: {e}")

