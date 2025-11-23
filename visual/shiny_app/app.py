from shiny import App, reactive, render, ui
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
from datetime import datetime

# Sample data as provided; in a real app, load from CSV
data_path = "../../final dataset/dataset_with_sentiment2.csv"

# Load data into DataFrame
df = pd.read_csv(data_path)

# Parse Date column assuming format DD.MM.YYYY HH:MM
def parse_date(date_str):
    try:
        return pd.to_datetime(date_str, format="%d.%m.%Y %H:%M")
    except:
        return pd.NaT

df['Parsed_Date'] = df['Date'].apply(parse_date)

# Helper to produce default datetime-local string (YYYY-MM-DDTHH:MM)
def to_dt_local_string(dt):
    if pd.isna(dt):
        return ""
    return dt.strftime("%Y-%m-%dT%H:%M")

app_ui = ui.page_fluid(
    ui.h2("Bank Reviews Dashboard"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("bank_filter", "Filter by Bank:", choices=["All"] + sorted(df["Bank"].unique().tolist())),
            ui.input_select("product_filter", "Filter by Product:", choices=["All"] + sorted(df["Product"].unique().tolist())),
            ui.input_select("city_filter", "Filter by City:", choices=["All"] + sorted(df["City"].unique().tolist())),
            ui.input_select("sentiment_filter", "Filter by Sentiment:", choices=["All", "NEUTRAL", "POSITIVE", "NEGATIVE"]),
            # Replaced date-only range with two datetime-local inputs (start + end)
            ui.tags.div(
                ui.tags.label("Start (date & time):", **{"for":"start_dt"}),
                ui.tags.input(type="datetime-local", id="start_dt",
                              value=to_dt_local_string(df['Parsed_Date'].min())),
                ui.tags.br(),
                ui.tags.label("End (date & time):", **{"for":"end_dt"}),
                ui.tags.input(type="datetime-local", id="end_dt",
                              value=to_dt_local_string(df['Parsed_Date'].max())),
                style="margin-top:8px;"
            ),
        ),
        ui.navset_tab(
            ui.nav_panel("Overview",
                ui.row(
                    # reviews_by_bank wrapped into scrollable div with fixed max height
                    ui.column(6, ui.tags.div(ui.output_plot("reviews_by_bank"), style="max-height:480px; overflow-y:auto; padding-right:10px;")),
                    ui.column(6, ui.output_plot("grade_distribution")),
                ),
                ui.row(
                    ui.column(12, ui.output_plot("reviews_over_time")),
                ),
            ),
            ui.nav_panel("Sentiments",
                ui.row(
                    ui.column(12, ui.output_plot("sentiment_grade_relation")),

                    ui.column(6, ui.output_plot("sentiment_pie")),
                ),
            ),
        ),
    ),
    ui.output_table("reviews_table"),
)

def server(input, output, session):
    @reactive.calc
    def filtered_df():
        df_filtered = df.copy()
        if input.bank_filter() != "All":
            df_filtered = df_filtered[df_filtered["Bank"] == input.bank_filter()]
        if input.product_filter() != "All":
            df_filtered = df_filtered[df_filtered["Product"] == input.product_filter()]
        if input.city_filter() != "All":
            df_filtered = df_filtered[df_filtered["City"] == input.city_filter()]
        if input.sentiment_filter() != "All":
            df_filtered = df_filtered[df_filtered["sentiment"] == input.sentiment_filter()]

        # Read datetime-local inputs created in UI.
        # Use input[...]() to be robust for custom html inputs.
        start_dt_str = input["start_dt"]() if "start_dt" in input else None
        end_dt_str = input["end_dt"]() if "end_dt" in input else None

        if start_dt_str:
            try:
                start_date = pd.to_datetime(start_dt_str)
            except:
                start_date = None
        else:
            start_date = None

        if end_dt_str:
            try:
                end_date = pd.to_datetime(end_dt_str)
            except:
                end_date = None
        else:
            end_date = None

        if start_date is not None and end_date is not None:
            # ensure timezone-naive comparisons work (both are naive)
            df_filtered = df_filtered[(df_filtered['Parsed_Date'] >= start_date) & (df_filtered['Parsed_Date'] <= end_date)]

        return df_filtered

    @output
    @render.table
    def reviews_table():
        return filtered_df()[["Bank", "Product", "City", "Review", "Grade", "sentiment"]]

    @output
    @render.plot
    def reviews_by_bank():
        # сколько топ-банков показываем
        top_n = 15

        if "Bank" not in filtered_df().columns:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "Column 'Bank' not found", ha="center", va="center")
            ax.axis("off")
            return fig

        counts = filtered_df()["Bank"].value_counts()
        if counts.empty:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "No data for selected filters", ha="center", va="center")
            ax.axis("off")
            return fig

        # агрегируем мелкие банки в "Other"
        if len(counts) > top_n:
            top = counts.iloc[:top_n]
            other_sum = counts.iloc[top_n:].sum()
            other_series = pd.Series({"Other": other_sum})
            plot_counts = pd.concat([top, other_series])
            plot_counts = plot_counts[::-1]  # инвертируем порядок
        else:
            plot_counts = counts[::-1]

        df_plot = plot_counts.reset_index()
        df_plot.columns = ["Bank", "Count"]

        total = df_plot["Count"].sum()
        df_plot["Pct"] = df_plot["Count"] / total * 100

        # высота фигуры зависит от числа строк
        n = len(df_plot)
        fig_height = max(3, n * 0.35)
        fig, ax = plt.subplots(figsize=(8, fig_height))

        sns.barplot(data=df_plot, y="Bank", x="Count", ax=ax)
        ax.set_title(f"Top {top_n} banks (+Other) — reviews count")
        ax.set_xlabel("Count")
        ax.set_ylabel("")

        # подписи справа от баров
        for i, (count, pct) in enumerate(zip(df_plot["Count"], df_plot["Pct"])):
            ax.text(count + max(1, total * 0.005), i, f"{int(count)} ({pct:.1f}%)", va="center")

        plt.tight_layout()
        return fig

    @output
    @render.plot
    def grade_distribution():
        fig, ax = plt.subplots()
        sns.histplot(data=filtered_df(), x="Grade", bins=5, kde=True, ax=ax)
        ax.set_title("Distribution of Grades")
        return fig

    @output
    @render.plot
    def reviews_over_time():
        df_time = filtered_df().copy()
        # if Parsed_Date contains NaT, drop them for time-series
        df_time = df_time.dropna(subset=['Parsed_Date'])
        if df_time.empty:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "No data in selected datetime range", ha="center", va="center")
            ax.axis("off")
            return fig

        # group by finer-grained time (e.g. hourly if span small, otherwise by day/month)
        # Here: we'll count per day+hour if range <= 7 days, else per day
        min_dt = df_time['Parsed_Date'].min()
        max_dt = df_time['Parsed_Date'].max()
        span_days = (max_dt - min_dt).days

        if span_days <= 7:
            # group by hourly
            df_time['Period'] = df_time['Parsed_Date'].dt.to_period('H')
        else:
            # group by day
            df_time['Period'] = df_time['Parsed_Date'].dt.to_period('D')

        counts = df_time.groupby('Period').size()
        # convert PeriodIndex to datetime for plotting
        x = counts.index.to_timestamp()
        y = counts.values

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(x, y, marker='o')
        ax.set_title("Reviews Over Time")
        ax.set_xlabel("Time")
        ax.set_ylabel("Number of reviews")
        fig.autofmt_xdate()
        plt.tight_layout()
        return fig

    @output
    @render.plot

    def sentiment_grade_relation():
        df_f = filtered_df().copy()

        # используем вероятности тональностей
        prob_cols = [c for c in ["NEUTRAL", "POSITIVE", "NEGATIVE"] if c in df_f.columns]
        if not prob_cols or "Grade" not in df_f.columns:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "Нет данных по оценкам или вероятностям", ha="center", va="center")
            ax.axis("off")
            return fig

        # числа
        df_f = df_f.dropna(subset=["Grade"] + prob_cols)

        # группируем по оценке, считаем средние вероятности
        grouped = df_f.groupby("Grade")[prob_cols].mean()

        fig, ax = plt.subplots(figsize=(8, 5))

        # рисуем линию для каждого класса
        for col in prob_cols:
            ax.plot(grouped.index, grouped[col], marker="o", label=col)

        ax.set_title("Зависимость оценок от вероятностей тональности")
        ax.set_xlabel("Оценка (Grade)")
        ax.set_ylabel("Средняя вероятность")
        ax.legend(title="Sentiment Class")

        ax.set_xticks(sorted(df_f["Grade"].unique()))

        return fig

    @output
    @render.plot
    def sentiment_pie():
        sentiment_counts = filtered_df()["sentiment"].value_counts()
        fig, ax = plt.subplots()
        sentiment_counts.plot(kind="pie", autopct='%1.1f%%', ax=ax)
        ax.set_title("Sentiment Breakdown")
        return fig

    @output
    @render.plot
    def ratings_box():
        ratings = filtered_df()[["Clear Conditions", "Polite Employee", "Availability", "Convenience"]].melt()
        fig, ax = plt.subplots()
        sns.boxplot(data=ratings, x="variable", y="value", ax=ax)
        ax.set_title("Box Plot of Ratings")
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45)
        return fig

app = App(app_ui, server)

if __name__ == "__main__":
    app.run()
