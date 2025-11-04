import pandas as pd
import os

def generate_insights(summary_file):
    print(f"🔍 Reading summary file: {summary_file}")

    if not os.path.exists(summary_file):
        print("❌ Summary file not found.")
        return

    # Read file safely
    try:
        df = pd.read_csv(summary_file)
    except Exception as e:
        print(f"⚠️ Could not read CSV: {e}")
        return

    if df.empty:
        print("⚠️ No data found in summary file.")
        return

    # Ensure expected columns exist
    required_cols = {"ip.src", "category", "count"}
    if not required_cols.issubset(df.columns):
        print(f"⚠️ Missing columns in CSV. Found: {list(df.columns)}")
        return

    # --- Generate insights ---
    total_records = len(df)
    unique_devices = df["ip.src"].nunique()
    unique_categories = df["category"].nunique()

    top_devices = df.groupby("ip.src")["count"].sum().sort_values(ascending=False).head(5)
    top_categories = df.groupby("category")["count"].sum().sort_values(ascending=False).head(5)

    print("\n📊 --- Traffic Insights ---")
    print(f"Total Records: {total_records}")
    print(f"Unique Devices: {unique_devices}")
    print(f"Unique Categories: {unique_categories}")

    print("\n👤 Top 5 Devices by Activity:")
    print(top_devices)

    print("\n🏆 Top Categories:")
    print(top_categories)

    # --- Save as a structured insights file ---
    insight_path = summary_file.replace("summary_", "insights_")

    with open(insight_path, "w", encoding="utf-8") as f:
        f.write("=== Traffic Insights Summary ===\n")
        f.write(f"Total Records: {total_records}\n")
        f.write(f"Unique Devices: {unique_devices}\n")
        f.write(f"Unique Categories: {unique_categories}\n\n")

        f.write("Top 5 Devices by Activity:\n")
        f.write(top_devices.to_string())
        f.write("\n\nTop Categories:\n")
        f.write(top_categories.to_string())

    print(f"\n💾 Insights saved -> {insight_path}")
    return insight_path

# Allow standalone execution
if __name__ == "__main__":
    files = [f for f in os.listdir() if f.startswith("summary_") and f.endswith(".csv")]
    if not files:
        print("⚠️ No summary_ file found in directory.")
    else:
        latest_summary = max(files, key=os.path.getctime)
        generate_insights(latest_summary)
