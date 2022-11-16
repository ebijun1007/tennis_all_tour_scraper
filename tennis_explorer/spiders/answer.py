from datetime import datetime, timedelta, timezone
from os import path
import scrapy
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np


class AnswerExplorer(scrapy.Spider):
    name = "answer"
    home_page = "https://www.tennisexplorer.com/match-detail/"
    jst = timezone(timedelta(hours=9), 'JST')
    now = datetime.now(jst) - timedelta(days=1)
    ANSWER_FILE = f'./data/{now.strftime("%Y-%m-%d")}.csv'
    MATCH_FILE = "./data/next_48_hours_match.csv"

    def start_requests(self):
        self.df_org = pd.read_csv(
            self.MATCH_FILE, index_col=0)
        self.df = self.df_org.copy()
        self.df.insert(5, 'winner', np.nan)
        self.df.insert(7, 'prediction_roi', np.nan)
        self.df_org.to_csv(self.MATCH_FILE)
        for id in self.df.index.array:
            yield scrapy.Request(url=f"{self.home_page}?id={id}", callback=self.parse_detail)

    # get match details

    def parse_detail(self, response):
        # when score is empty, do not parse
        if (response.css('td.gScore::text').get() == "\xa0"):
            return

        match_id = int(response.url.split('id=')[1])
        data = self.df.loc[[match_id]]

        winner_name = self.name_order(response.css('th.plName ::text').get())

        if(data.iloc[0]['player1_name'] == winner_name):
            winner = 1
        else:
            winner = 2
        data = data.assign(winner=winner)
        predicted_winner = round(data.iloc[0]['predict'], 0)
        if(predicted_winner == 0.0):
            data = data.assign(prediction_roi=0)
        elif(predicted_winner == winner):
            roi = float(data.iloc[0][f"player{winner}_odds"]) - 1
            data = data.assign(prediction_roi=round(roi, 2))
        else:
            data = data.assign(prediction_roi=-1)

        print(data)

        with open(self.ANSWER_FILE, 'a', newline='') as csvfile:
            if csvfile.tell() == 0:
                data.to_csv(self.ANSWER_FILE, mode='w',
                            header=True, index=True)
            else:
                data.to_csv(self.ANSWER_FILE, mode='a',
                            header=False, index=True)

    def name_order(self, name):
        if(len(ordered_name := name.split(" ")) == 2):
            return ordered_name[1] + " " + ordered_name[0]
        elif(len(ordered_name) == 3):
            return ordered_name[2] + " " + ordered_name[0] + " " + ordered_name[1]
        elif(len(ordered_name) == 4):
            return ordered_name[1] + " " + ordered_name[0]
