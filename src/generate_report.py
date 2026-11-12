from sqlalchemy import create_engine, text
import pandas as pd
import plotly.express as px
from bokeh.plotting import figure, output_file, save
from bokeh.layouts import column, row
from bokeh.models import Div, ColumnDataSource, HoverTool, Select, CustomJS, DataTable, TableColumn, DateFormatter
from bokeh.transform import factor_cmap
from bokeh.palettes import Spectral6
# import configparser

# config = configparser.ConfigParser()
# config.read("config.ini")

# USER = config["MYSQL"]["USER"]
# PASSWORD = config["MYSQL"]["PASSWORD"]
# HOST = config["MYSQL"]["HOST"]
# DATABASE = config["MYSQL"]["DATABASE"]

# from project_config import DAILY_STATION_SUMMARY_TABLE, REPORT_DIR

# from store_data_mysql import create_database_engine

# engine = create_database_engine(USER, PASSWORD, HOST, DATABASE)

def create_report_plotly(sql_engine, summary_table, output_report_path):
    # Read historical aggregates from our intermediate summary layer
    query_str = f"""
                SELECT * 
                FROM {summary_table}
                WHERE date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) 
                     and station_name in ("London", "Edinburgh", "Manchester", "Glasgow", 
                     "Birmingham", "Bristol")
                ORDER BY date ASC, station_name ASC;
                """
    df = pd.read_sql(query_str, con = sql_engine)

    # Build Time Series Plot
    fig_time = px.line(
        df, x = 'date', y = 'avg_temp_c', color = 'station_name',
        title = "Daily Mean Temperature Timeline",
        template = "plotly_dark", markers = True,
        labels = {"avg_temp_c": "Avg Temp (°C)", "date": "Date", "station_name": "Station"})
    fig_time.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=400)

    # Build Bar Chart
    fig_bar = px.bar(
        df, x = "date", y="max_wind_speed_mph", color = "station_name",
        title = "Daily Peak Wind Velocity Profiles",
        template="plotly_dark", barmode="group",
        labels={"max_wind_speed_mph": "Max Wind (mph)", "date": "Date"}
    )
    fig_bar.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=400)

    # Compile plots to htmls
    chart1_html = fig_time.to_html(full_html=False, include_plotlyjs='cdn')
    chart2_html = fig_bar.to_html(full_html=False, include_plotlyjs='cdn')

    # Build Table
    table_rows_html = ""
    for _, row in df.tail(15).iterrows():  # Expose the latest 15 records as an audit example
        table_rows_html += f"""
        <tr class="border-b border-gray-800 hover:bg-gray-800 text-sm">
            <td class="px-6 py-3 font-mono text-gray-300">{row['date']}</td>
            <td class="px-6 py-3 font-semibold text-white">{row['station_name']}</td>
            <td class="px-6 py-3 text-orange-400 font-medium">{row['avg_temp_c']} °C</td>
            <td class="px-6 py-3 text-blue-400">{row['max_wind_speed_mph']} mph</td>
            <td class="px-6 py-3 text-emerald-400">{row['avg_pressure_mb']} mb</td>
        </tr>
        """

    # Assemble the Unified Tailwind CSS Dashboard Template
    html_report = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>UK Executive Climate Report (Plotly-Engine)</title>
        <script src="https://jsdelivr.net"></script>
        <script src="https://tailwindcss.com"></script>
    </head>
    <body class="bg-gray-900 text-gray-100 p-8 font-sans">
        <div class="max-w-7xl mx-auto">
            
            <!-- Header -->
            <header class="border-b border-gray-800 pb-4 mb-8 flex justify-between items-center">
                <div>
                    <h1 class="text-3xl font-extrabold text-white tracking-tight">🛰️ UK Climate Analytics Warehouse Report</h1>
                    <p class="text-sm text-gray-400 mt-1">Compiled Automated Production Asset • Summary Layer</p>
                </div>
                <div class="bg-gray-800 px-4 py-2 rounded-lg font-mono text-sm border border-gray-700">
                    Engine: <span class="text-orange-400 font-bold">Plotly Core</span>
                </div>
            </header>

            <!-- MAIN METRICS SECTION -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div class="bg-gray-800 border border-gray-700 p-6 rounded-xl">
                    <span class="text-xs text-gray-400 font-bold uppercase tracking-wider">Absolute Max Temp</span>
                    <h2 class="text-3xl font-black text-amber-500 mt-2">{df['max_temp_c'].max()} °C</h2>
                </div>
                <div class="bg-gray-800 border border-gray-700 p-6 rounded-xl">
                    <span class="text-xs text-gray-400 font-bold uppercase tracking-wider">Peak Recorded Wind Speed</span>
                    <h2 class="text-3xl font-black text-blue-400 mt-2">{df['max_wind_speed_mph'].max()} mph</h2>
                </div>
                <div class="bg-gray-800 border border-gray-700 p-6 rounded-xl">
                    <span class="text-xs text-gray-400 font-bold uppercase tracking-wider">Total Accumulated Freezing Hours</span>
                    <h2 class="text-3xl font-black text-emerald-400 mt-2">{int(df['freezing_hours_count'].sum())} Hours</h2>
                </div>
            </div>

            <!-- CHARTS SECTION -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                <div class="bg-gray-800 border border-gray-700 p-4 rounded-xl shadow-lg">{chart1_html}</div>
                <div class="bg-gray-800 border border-gray-700 p-4 rounded-xl shadow-lg">{chart2_html}</div>
            </div>

            <!-- AUDIT TABLES SECTION -->
            <div class="bg-gray-800 border border-gray-700 rounded-xl shadow-lg p-6">
                <h2 class="text-lg font-bold mb-4 text-white">🔍 Data Warehouse Audit Layer (Latest Summary Records)</h2>
                <div class="overflow-x-auto">
                    <table class="w-full text-left table-auto min-w-max">
                        <thead>
                            <tr class="bg-gray-700 text-gray-300 text-xs uppercase tracking-wider">
                                <th class="px-6 py-3 rounded-l-lg">Date</th>
                                <th class="px-6 py-3">Station Name</th>
                                <th class="px-6 py-3">Mean Temp</th>
                                <th class="px-6 py-3">Peak Wind</th>
                                <th class="px-6 py-3 rounded-r-lg">Mean Pressure</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows_html}
                        </tbody>
                    </table>
                </div>
            </div>

        </div>
    </body>
    </html>
    """

    with open(output_report_path, "w", encoding="utf-8") as f:
        f.write(html_report)

def create_report_bokeh(sql_engine, summary_table, output_report_path):
        # Read historical aggregates from our intermediate summary layer
    query_str = f"""
                SELECT * 
                FROM {summary_table}
                WHERE date >= DATE_SUB(CURDATE(), INTERVAL 14 DAY) 
                     and station_name in ("London", "Edinburgh", "Manchester", "Glasgow", 
                     "Birmingham", "Bristol")
                ORDER BY date ASC, station_name ASC;
                """
    df = pd.read_sql(query_str, con = sql_engine)

    # Format dates to string to avoid serialization bugs inside browser JavaScript engines
    df['date_str'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    stations = sorted(list(df["station_name"].unique()))

    # 2. Setup Data Sources for the JavaScript Dropdown Callback Engine
    # 'source_visible' holds what is currently showing on screen.
    # 'source_master' retains the entire database snapshot for reference filtering.
    initial_station = stations[0]
    df_filtered = df[df["station_name"] == initial_station]

    source_visible = ColumnDataSource(df_filtered)
    source_master = ColumnDataSource(df)

    # 3. Main Metrics Header Component (KPI Cards)
    max_temp = df['avg_temp_c'].max()
    peak_wind = df['max_wind_speed_mph'].max()
    kpi_div = Div(text=f"""
        <div style="display: flex; gap: 20px; font-family: sans-serif; margin-bottom: 25px;">
            <div style="background: #1f2937; border: 1px solid #374151; padding: 15px; border-radius: 8px; flex: 1;">
                <span style="color: #9ca3af; font-size: 11px; text-transform: uppercase; font-weight: bold;">System Peak Temperature</span>
                <h2 style="color: #f59e0b; margin: 5px 0 0 0; font-size: 24px;">{max_temp} °C</h2>
            </div>
            <div style="background: #1f2937; border: 1px solid #374151; padding: 15px; border-radius: 8px; flex: 1;">
                <span style="color: #9ca3af; font-size: 11px; text-transform: uppercase; font-weight: bold;">Maximum Wind Velocity</span>
                <h2 style="color: #3b82f6; margin: 5px 0 0 0; font-size: 24px;">{peak_wind} mph</h2>
            </div>
        </div>
    """, width=1120)

    # 4. Create Component A: Interactive Time-Series Plot
    p_time = figure(x_range=sorted(list(df['date_str'].unique())), title=f"Temperature Timeline Tracker", 
                    x_axis_label="Date", y_axis_label="Mean Temp (°C)", height=350, width=550,
                    background_fill_color="#1f2937", border_fill_color="#111827")
    # 2. Set the title properties directly on the .title object
    p_time.title.text_color = "white"
    p_time.title.text_font_size = "13pt"

    p_time.line(x="date_str", y="avg_temp_c", source=source_visible, line_width=3, color="#f59e0b")
    p_time.scatter(x="date_str", y="avg_temp_c", source=source_visible, size=8, color="#ffffff")
    p_time.add_tools(HoverTool(tooltips=[("Date", "@date_str"), ("Temp", "@avg_temp_c°C")]))

    # 5. Create Component B: Bar Chart Plot (Station Means Comparison)
    station_means = df.groupby("station_name")["max_wind_speed_mph"].mean().reset_index()
    bar_source = ColumnDataSource(station_means)
    p_bar = figure(x_range=stations, title="Aggregated Average Wind Profiles by Station Location", height=350, width=550,
                background_fill_color="#1f2937", border_fill_color="#111827")
    p_bar.title.text_color = "white"
    p_bar.title.text_font_size = "13pt"
    p_bar.vbar(x="station_name", top="max_wind_speed_mph", width=0.4, source=bar_source,
            fill_color=factor_cmap('station_name', palette=Spectral6, factors=stations))
    p_bar.xaxis.major_label_orientation = 0.3

    # 6. Develop the Client-Side JavaScript Dropdown Filter Utility
    select_widget = Select(title="📍 Select Meteorological Station to Isolate:", value=initial_station, options=stations, width=300)

    callback = CustomJS(args=dict(source_visible=source_visible, source_master=source_master, select_widget=select_widget), code="""
        const selected_station = select_widget.value;
        const data_visible = source_visible.data;
        const data_master = source_master.data;
        
        // Clear out current visible arrays completely
        for (let key in data_visible) {
            data_visible[key] = [];
        }
        
        // Loop through master dictionary logs and append records matching selection parameters
        for (let i = 0; i < data_master['station_name'].length; i++) {
            if (data_master['station_name'][i] === selected_station) {
                for (let key in data_visible) {
                    data_visible[key].push(data_master[key][i]);
                }
            }
        }
        
        // Signal update triggers down to canvas rendering view layers
        source_visible.change.emit();
    """)
    select_widget.js_on_change('value', callback)

    # 7. Create Component C: Interactive Data Table Audit Layer
    columns = [
        TableColumn(field="date_str", title="Date", formatter=DateFormatter()),
        TableColumn(field="station_name", title="Station Name"),
        TableColumn(field="avg_temp_c", title="Mean Temp (°C)"),
        TableColumn(field="max_wind_speed_mph", title="Peak Wind (mph)"),
        TableColumn(field="avg_pressure_mb", title="Pressure (mb)")
    ]
    data_table = DataTable(source=source_master, columns=columns, width=1120, height=250,  styles={"background-color": "#1f2937", "color": "white"} )

    # 8. Assemble Layout and Export
    report_layout = column(
        Div(text="<h1 style='color:white; font-family:sans-serif;'>🇬🇧 UK Weather Intelligence Grid (Bokeh)</h1>", width=1120),
        kpi_div,
        select_widget,
        row(p_time, p_bar),
        Div(text="<h3 style='color:white; font-family:sans-serif; margin-top:20px;'>📋 Data Audit Matrix</h3>", width=1120),
        data_table
    )

    output_file(output_report_path, title="UK Weather Executive Report")
    save(report_layout)


if __name__ == "__main__":
    report_plotly_html = REPORT_DIR / "report_plotly_test.html"
    create_report_plotly(engine, DAILY_STATION_SUMMARY_TABLE, report_plotly_html)
    report_bokeh_html = REPORT_DIR / f"report_bokeh_test.html" 
    create_report_bokeh(engine, DAILY_STATION_SUMMARY_TABLE, report_bokeh_html)

