import sqlite3
import xml.etree.ElementTree as ET
import os



def local_name(tag):
    """
    Helper function that strips a namespace from an element tag.
    For example, '{http://example.com}TrackStatsExtension' becomes 'TrackStatsExtension'.
    """
    return tag.split('}')[-1] if '}' in tag else tag


def add_data_to_db():
    xml_dir = "parsed_xmls"
    db_path = "gpx_data.db"



    # Connect to (or create) the SQLite database
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Drop existing tables (if they exist)
    cur.execute("DROP TABLE IF EXISTS track_stats")
    cur.execute("DROP TABLE IF EXISTS track_points")

    # Create the table for overall track stats from TrackStatsExtension
    cur.execute('''
        CREATE TABLE IF NOT EXISTS track_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            distance REAL,
            timer_time INTEGER,
            total_elapsed_time INTEGER,
            moving_time INTEGER,
            ascent REAL,
            descent REAL,
            calories INTEGER,
            avg_heart_rate INTEGER,
            avg_cadence INTEGER
        )
    ''')

    # Create the table for each track point from trkpt elements
    cur.execute('''
        CREATE TABLE IF NOT EXISTS track_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ele REAL,
            time TEXT,
            temperature REAL,
            hr INTEGER,
            cad INTEGER
        )
    ''')

    # Iterate over all XML files in the directory
    for filename in os.listdir(xml_dir):
        if filename.endswith(".xml"):
            file_path = os.path.join(xml_dir, filename)
            print(f"Processing: {file_path}")

            try:
                tree = ET.parse(file_path)
                root = tree.getroot()

                # ---------------------------
                # 1. Extract overall track stats
                # ---------------------------
                track_stats_ext = None
                for elem in root.iter():
                    if local_name(elem.tag) == "TrackStatsExtension":
                        track_stats_ext = elem
                        break

                if track_stats_ext is not None:
                    data = {local_name(child.tag): child.text for child in track_stats_ext}

                    try:
                        cur.execute('''
                            INSERT INTO track_stats (
                                distance, timer_time, total_elapsed_time, moving_time,
                                ascent, descent, calories, avg_heart_rate, avg_cadence
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            float(data.get("Distance", 0)),
                            int(data.get("TimerTime", 0)),
                            int(data.get("TotalElapsedTime", 0)),
                            int(data.get("MovingTime", 0)),
                            float(data.get("Ascent", 0)),
                            float(data.get("Descent", 0)),
                            int(data.get("Calories", 0)),
                            int(data.get("AvgHeartRate", 0)),
                            int(data.get("AvgCadence", 0))
                        ))
                        conn.commit()
                        print(f"Inserted track stats for {filename}")
                    except Exception as e:
                        print(f"Error inserting track stats for {filename}: {e}")

                # ---------------------------
                # 2. Extract each track point from trkpt elements
                # ---------------------------
                track_point_count = 0
                for trkpt in root.iter():
                    if local_name(trkpt.tag) == "trkpt":
                        ele_val, time_val, temperature_val, hr_val, cad_val = None, None, None, None, None

                        for child in trkpt:
                            tag = local_name(child.tag)
                            if tag == "ele":
                                ele_val = float(child.text) if child.text else None
                            elif tag == "time":
                                time_val = child.text
                            elif tag == "extensions":
                                for ext in child:
                                    if local_name(ext.tag) == "TrackPointExtension":
                                        for sub in ext:
                                            sub_tag = local_name(sub.tag)
                                            if sub_tag in ["atemp", "Temperature"]:
                                                temperature_val = float(sub.text) if sub.text else None
                                            elif sub_tag == "hr":
                                                hr_val = int(sub.text) if sub.text else None
                                            elif sub_tag == "cad":
                                                cad_val = int(sub.text) if sub.text else None

                        try:
                            cur.execute('''
                                INSERT INTO track_points (ele, time, temperature, hr, cad)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (ele_val, time_val, temperature_val, hr_val, cad_val))
                            track_point_count += 1
                        except Exception as e:
                            print(f"Error inserting track point for {filename}: {e}")

                conn.commit()
                print(f"Inserted {track_point_count} track points for {filename}")

            except ET.ParseError as e:
                print(f"Error parsing {filename}: {e}")
            except Exception as e:
                print(f"Unexpected error with {filename}: {e}")

    conn.close()
    print("All XML files processed.")

