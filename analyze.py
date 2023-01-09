import pandas as pd
import os
import numpy as np
import matplotlib.pyplot as plt
import math
from datetime import datetime


def calc_history():
    plot_x = []
    plot_y = []
    plot_y2 = []
    sum = 0.0
    strong_sum = 0.0
    strong_predict_roi = 0
    for csv_data in sorted(os.listdir("data")):
        if ".csv" not in csv_data:
            continue
        if "next_48_hours_match.csv" == csv_data:
            continue
        try:
            df = pd.read_csv(f'./data/{csv_data}')
            win = len(
                df.loc[df['prediction_roi'] > 0].index)
            lose = len(
                df.loc[df['prediction_roi'] < 0].index)
            roi = round(
                df["prediction_roi"].sum(), 2)
            strong_predict_df = df[df["strong_predict"] == True]
            strong_predict_roi = round(
                strong_predict_df["prediction_roi"].sum(), 2)
            print(
                f'{csv_data}: win:{win} lose:{lose} win_rate: {round(win / (win + lose) ,2)} roi:{roi} strong_predict_roi:{strong_predict_roi}')
            print(strong_predict_roi)
            sum += float(roi)
            strong_sum += float(strong_predict_roi)
            x_label = csv_data.replace(".csv", "").split("-")
            plot_x.append(datetime(
                int(x_label[0]), int(x_label[1]), int(x_label[2])))
            plot_y.append(sum)
            plot_y2.append(strong_sum)
        except Exception as e:
            print(e)
            continue
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.set_ylabel("ROI(units)")
    ax.set_xlabel("DATE")
    ax.plot(plot_x, plot_y2)
    plt.savefig("roi")


def emurate():
    for tour_type in ["atp", "wta"]:
        balance = 30_000

        if balance < 0:
            exit()
        df = pd.read_csv(f"{tour_type}.csv").sort_values('time_stamp')
        conditional_balance = 0
        conditional_count = 0
        win_count = 0
        lose_count = 0
        win_total_odds = 0
        winner_1 = winner_2 = 0
        for _, row in df.iterrows():
            if not row[f"strong_predict"]:
                continue
            unit = balance / 25
            winner = int(row["winner"])
            if (math.isnan(row[f"player1_elo"]) or math.isnan(row[f"player2_elo"])):
                continue
            predict_winner = predict_player_win(tour_type, row)
            if(predict_winner == 1):
                winner_1 += 1
            if(predict_winner == 2):
                winner_2 += 1
            if not predict_winner:
                continue
            if math.isnan(row[f"player{winner}_odds"]):
                continue
            conditional_count += 1
            conditional_balance -= 1
            balance -= unit
            if (predict_winner == winner):
                win_count += 1
                win_total_odds += row[f"player{winner}_odds"]
                conditional_balance += row[f"player{winner}_odds"]
                balance += unit * float(row[f"player{winner}_odds"])
            else:
                lose_count += 1
        print(f"########################{tour_type}########################")
        print(f"conditional_balance: {conditional_balance}")
        print(f"conditional_count: {conditional_count}")
        print(f"total_count: {len(df)}")
        print(f"win_count: {win_count}")
        print(f"win_average_odds: {win_total_odds / win_count}")
        print(f"lose_count: {lose_count}")
        print("balance:", balance)
        print("home:", winner_1, "away:", winner_2)


def predict_player_win(tour_type, row):
    def diff(variable):
        return (float(row[f"player{home}_{variable}"]) - float(row[f"player{away}_{variable}"]))

    def get(player, variable):
        return float(row[f"player{player}_{variable}"])

    winner = None

    for i in range(1, 3):
        home = i
        away = 3 - i
        if (tour_type == "atp"):
            condition = (float(row[f"player{home}_roi"]) > 5
                         and diff("current_rank") > 0
                         and diff("elo") < 0
                         and diff("roi") > 0) \
                or (
                get(home, "elo") > 2000
                and get(home, "odds") > 1.3
            ) \
                or (
                diff("elo") > 0
                and get(home, "odds") > 2
            )
        if (tour_type == "wta"):
            condition = (diff("age") < 5
                         and (diff("height") >= 5 and diff("height") < 10)) \
                or (
                    get(home, "elo") > 1700
                    and get(home, "odds") > 1.7
            )
        if(condition):
            if not winner:
                winner = i
            if(winner and diff("odds") > 0):
                winner = i
    return winner


if __name__ == "__main__":
    calc_history()
    emurate()
