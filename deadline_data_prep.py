import pandas as pd
import os

# Define the folder containing the CSV files
input_folder = "tables"

# List of CSV files (assuming you have 4 tables)
csv_files = [
    "fall_2024_and_spring_2025financial_aid_priority_deadline.csv",
    "fall_2025_and_spring_2026financial_aid_priority_deadline.csv",
    "summer_2025_financial_aid_prioritydeadline.csv",
    "summer_2026_financial_aid_prioritydeadline.csv"
]

# Function to read and preprocess each table
def preprocess_table(file_path):
    df = pd.read_csv(file_path)
    df["DETAILS"] = os.path.basename(file_path).replace(".csv", "")  # Remove .csv
    return df

# Read each CSV file into a separate DataFrame
df_f24_s25 = preprocess_table(os.path.join(input_folder, csv_files[0]))
df_f25_s26 = preprocess_table(os.path.join(input_folder, csv_files[1]))
df_su25 = preprocess_table(os.path.join(input_folder, csv_files[2]))
df_su26 = preprocess_table(os.path.join(input_folder, csv_files[3]))

# Print sample data
print(df_f24_s25.head(4))
print(df_f25_s26.head(4))
print(df_su25.head(3))
print(df_su26.head(3))

deadlines_df = pd.concat((df_f24_s25,df_f25_s26,df_su25,df_su26), ignore_index=True)

# Convert columns with date-like values to MM/DD/YYYY format
if "Date" in deadlines_df.columns:  # Ensure 'Date' column exists
    deadlines_df["Date"] = pd.to_datetime(deadlines_df["Date"], errors='coerce').dt.strftime('%m/%d/%Y')


print(deadlines_df.info())
print(deadlines_df[["Date", "Classification"]].head(4))
print(deadlines_df.head(4))

output_file = os.path.join("tables", "deadlines_table.csv")

# Save the DataFrame to CSV (without index)
deadlines_df.to_csv(output_file, index=False)

print(f"File saved successfully at: {output_file}")




