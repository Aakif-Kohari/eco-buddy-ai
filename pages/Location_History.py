import streamlit as st
import hashlib
import pandas as pd
import folium
from streamlit_folium import st_folium
from location_parser import parse_and_segment_file_bytes
from emissions import calculate_footprint
from database import save_assessment
from background_tasks import submit_background_task, render_task_progress, clear_background_task
import gamification as gf

st.set_page_config(page_title="Location History", page_icon="🗺️", layout="wide")

st.title("Location History & Emissions Tracking")
st.write("Upload your GPX or Google Takeout JSON files to automatically parse trips and calculate your footprint.")

uploaded_file = st.file_uploader("Upload Location File (.gpx, .json)", type=["gpx", "json"])

if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    file_key = hashlib.md5(file_bytes).hexdigest()
    task_key = f"location_parse_{file_key}"

    submit_background_task(
        task_key,
        parse_and_segment_file_bytes,
        file_bytes,
        uploaded_file.name,
        task_name="Parsing & Segmenting Location File"
    )

    is_done, parse_res = render_task_progress(task_key, success_msg="Location parsing complete!")

    if is_done and parse_res is not None:
        err = parse_res.get("error")
        waypoints = parse_res.get("waypoints", [])
        segments = parse_res.get("segments", [])

        if err:
            st.error(err)
        elif not waypoints:
            st.error("No valid waypoints found in the file. Ensure it's a valid GPX or Google Takeout JSON.")
        else:
            min_time = min(wp["timestamp"] for wp in waypoints).date()
            max_time = max(wp["timestamp"] for wp in waypoints).date()
            
            st.subheader("Filter Location History")
            col1, col2 = st.columns(2)
            start_date = col1.date_input("Start Date", min_time)
            end_date = col2.date_input("End Date", max_time)
            
            filtered_waypoints = [
                wp for wp in waypoints 
                if start_date <= wp["timestamp"].date() <= end_date
            ]
            
            filtered_segments = [
                seg for seg in segments
                if start_date <= seg["start_time"].date() <= end_date
            ]
            
            st.success(f"Showing {len(filtered_waypoints)} waypoints and {len(filtered_segments)} distinct trips.")

            if filtered_waypoints:
                total_locs = len(filtered_waypoints)
                unique_locs = len(set((wp["lat"], wp["lon"]) for wp in filtered_waypoints))
                latest_loc = max(wp["timestamp"] for wp in filtered_waypoints)

                st.subheader("Location History Summary")
                sum_col1, sum_col2, sum_col3 = st.columns(3)
                sum_col1.metric("Total Recorded Locations", total_locs)
                sum_col2.metric("Unique Locations", unique_locs)
                sum_col3.metric("Latest Record", latest_loc.strftime("%Y-%m-%d %H:%M"))

                st.subheader("Trip Map")
                first_wp = filtered_waypoints[0]
                m = folium.Map(
                    location=[first_wp["lat"], first_wp["lon"]],
                    zoom_start=12,
                    tiles="CartoDB positron"
                )

                try:
                    from folium.plugins import MarkerCluster
                    mc = MarkerCluster()
                    # Limit markers to 1000 to prevent browser freeze
                    step = max(1, len(filtered_waypoints) // 1000)
                    for wp in filtered_waypoints[::step]:
                        folium.Marker(
                            location=[wp["lat"], wp["lon"]],
                            popup=f"Time: {wp['timestamp'].strftime('%Y-%m-%d %H:%M')}<br>Lat: {wp['lat']:.4f}, Lon: {wp['lon']:.4f}",
                            tooltip="Recorded Location"
                        ).add_to(mc)
                    mc.add_to(m)
                except ImportError:
                    pass

                colors = {
                    "Walking": "green",
                    "Bike": "blue",
                    "Public Transport": "orange",
                    "Car": "red",
                    "Flying": "purple"
                }

                legend_html = """
            <div style="position: fixed; bottom: 30px; left: 30px; z-index: 9999;
                        background-color: white; padding: 10px 14px; border-radius: 6px;
                        border: 1px solid #ccc; font-size: 13px; box-shadow: 0 1px 4px rgba(0,0,0,0.2);">
              <b>Transport Mode</b><br>
              <span style="color:green;">&#9679;</span> Walking<br>
              <span style="color:blue;">&#9679;</span> Bike<br>
              <span style="color:orange;">&#9679;</span> Public Transport<br>
              <span style="color:red;">&#9679;</span> Car<br>
              <span style="color:purple;">&#9679;</span> Flying
            </div>
            """
                m.get_root().html.add_child(folium.Element(legend_html))

                segment_data = []

                for i, seg in enumerate(filtered_segments):
                    path = [(wp["lat"], wp["lon"]) for wp in seg["waypoints"]]
                    color = colors.get(seg["mode"], "gray")

                    folium.PolyLine(
                        locations=path,
                        color=color,
                        weight=4,
                        opacity=0.8,
                        tooltip=(
                            f"Trip {i + 1}: {seg['mode']} "
                            f"({seg['distance_km']:.2f} km)"
                        )
                    ).add_to(m)

                    folium.CircleMarker(
                        location=path[0],
                        radius=6,
                        color=color,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.9,
                        tooltip=f"Start: Trip {i + 1} ({seg['mode']})"
                    ).add_to(m)

                    folium.CircleMarker(
                        location=path[-1],
                        radius=6,
                        color=color,
                        fill=True,
                        fill_color="white",
                        fill_opacity=0.9,
                        tooltip=f"End: Trip {i + 1} ({seg['mode']})"
                    ).add_to(m)

                    if seg["mode"] in ["Car", "Bike", "Public Transport", "Walking"]:
                        _, contributors = calculate_footprint(
                            seg["mode"],
                            seg["distance_km"] / 365.0,
                            0,
                            "Vegetarian",
                            0
                        )
                        emissions_kg = contributors["Transport"]
                    elif seg["mode"] == "Flying":
                        _, contributors = calculate_footprint(
                            "Walking",
                            0,
                            0,
                            "Vegetarian",
                            1
                        )
                        emissions_kg = contributors["Flights"]
                    else:
                        emissions_kg = 0.0

                    segment_data.append({
                        "Start Time": seg["start_time"].strftime("%Y-%m-%d %H:%M"),
                        "End Time": seg["end_time"].strftime("%Y-%m-%d %H:%M"),
                        "Mode": seg["mode"],
                        "Distance (km)": round(seg["distance_km"], 2),
                        "Avg Speed (km/h)": round(seg["avg_speed_kmh"], 2),
                        "Emissions (kg CO2)": emissions_kg,
                        "segment": seg
                    })

                st_folium(m, width=1000, height=500)
                
                df_waypoints = pd.DataFrame(filtered_waypoints)
                if not df_waypoints.empty:
                    df_waypoints['timestamp'] = df_waypoints['timestamp'].astype(str)
                    csv_data = df_waypoints.to_csv(index=False).encode('utf-8')
                    col_dl, col_clr = st.columns(2)
                    col_dl.download_button(
                        label="Download Filtered Location History as CSV",
                        data=csv_data,
                        file_name='filtered_location_history.csv',
                        mime='text/csv',
                    )
                    
                    if col_clr.button("Clear Location History"):
                        clear_background_task(task_key)
                        st.rerun()

                total_distance = sum(s["distance_km"] for s in filtered_segments)
                total_emissions = sum(d["Emissions (kg CO2)"] for d in segment_data)
                mode_counts = pd.Series([s["mode"] for s in filtered_segments]).value_counts()

                st.subheader("Trip Summary")
                sum_col1, sum_col2, sum_col3 = st.columns(3)
                sum_col1.metric("Total Distance", f"{total_distance:.2f} km")
                sum_col2.metric("Total Emissions", f"{total_emissions:.2f} kg CO2")
                sum_col3.metric("Most Used Mode", mode_counts.idxmax() if not mode_counts.empty else "N/A")

                st.subheader("Trip Details")
                df = pd.DataFrame(segment_data).drop(columns=["segment"])
                st.dataframe(df)

                if st.button("Commit to Permanent Emissions Log"):
                    success_count = 0
                    failed_count = 0

                    for item in segment_data:
                        if item["Mode"] in ["Car", "Bike", "Public Transport", "Walking", "Flying"]:
                            transport = item["Mode"]
                            dist = item["Distance (km)"]
                            footprint = item["Emissions (kg CO2)"]
                            eco_score = 50

                            if save_assessment(
                                transport,
                                dist,
                                0,
                                "Vegetarian",
                                0,
                                footprint,
                                eco_score
                            ):
                                success_count += 1
                                gf.check_badge_eligibility(1)
                            else:
                                failed_count += 1

                    if success_count > 0 and failed_count == 0:
                        st.success(f"Successfully committed all {success_count} trips to the emissions log!")
                    elif success_count > 0 and failed_count > 0:
                        st.warning(f"Partially committed trips: {success_count} succeeded and {failed_count} failed.")
                    elif failed_count > 0:
                        st.error(f"Failed to commit {failed_count} trips to the emissions log.")
                    else:
                        st.warning("No trips were committed.")