from datetime import datetime, timedelta, timezone
from os import path
from analyze import predict_player_win
from explanatory_variables import EXPLANATORY_VARIABLES
import requests  # to get image from the web
import scrapy
from bs4 import BeautifulSoup
import re
import pandas as pd
import io
import json
import csv
import os


class MatchesExplorer(scrapy.Spider):
    name = "matches"
    HOME_PAGE = "https://www.tennisexplorer.com/"
    jst = timezone(timedelta(hours=9), 'JST')
    now = datetime.now(jst)
    tomorrow = now + timedelta(days=1)
    next_day_search_condition = f"&year={tomorrow.year}&month={tomorrow.month:02}&day={tomorrow.day:02}"
    TODAYS_MATCH = [
        "https://www.tennisexplorer.com/matches/?type=atp-single&timezone=+9",
        "https://www.tennisexplorer.com/matches/?type=wta-single&timezone=+9",
        f"https://www.tennisexplorer.com/next/?type=atp-single{next_day_search_condition}&timezone=+9",
        f"https://www.tennisexplorer.com/next/?type=wta-single{next_day_search_condition}&timezone=+9",
    ]
    CRAWL_FLAG = False
    EXPLANATORY_VARIABLES.remove("winner")

    # options: multiple_regression_model, lightbgm_model
    NEXT_24_HOURS_MATCHES = "./data/next_48_hours_match.csv"

    def start_requests(self):
        os.remove(self.NEXT_24_HOURS_MATCHES) if os.path.exists(
            self.NEXT_24_HOURS_MATCHES) else None
        yield scrapy.Request(url=self.HOME_PAGE, callback=self.parse_main_tournaments, meta={"dont_cache": True})

    # get main tournament names
    def parse_main_tournaments(self, response):
        atp_competitions = self.get_main_tournaments(response.css(
            'div#idxActTour div.half-l'))
        wta_competitions = self.get_main_tournaments(
            response.css('div#idxActTour div.half-r'))
        self.main_competitions = list(dict.fromkeys(
            atp_competitions + wta_competitions))
        yield scrapy.Request(url=self.TODAYS_MATCH[0], callback=self.parse_todays_match, meta={"dont_cache": True}, priority=100)
        yield scrapy.Request(url=self.TODAYS_MATCH[1], callback=self.parse_todays_match, meta={"dont_cache": True}, priority=10)
        yield scrapy.Request(url=self.TODAYS_MATCH[2], callback=self.parse_todays_match, meta={"dont_cache": True}, priority=1)
        yield scrapy.Request(url=self.TODAYS_MATCH[3], callback=self.parse_todays_match, meta={"dont_cache": True}, priority=0)

    # get only main tournaments from list. exclude lower level tournaments
    def get_main_tournaments(self, table):
        x = table.css('td::text').getall()
        # lower_level_tournaments_index = list(
        #     filter(('\xa0').__ne__, x)).index('Lower level tournaments')
        # if(lower_level_tournaments_index == 0):
        #     return []
        match_list = list(filter(lambda name: name not in ['\xa0'], table.css(
            'td a::text').getall()))
        # match_list = list(filter(lambda name: name not in ['\xa0'], table.css(
        #     'td a::text').getall()))
        self.crawler.stats.set_value('match_list', match_list)
        return match_list
        # return list(filter(lambda name: name not in ['Davis Cup'], match_list))

    def parse_todays_match(self, response):
        tour_type = "wta" if "wta" in response.url else "atp"
        for tr in response.css('table.result tr'):
            if(tr.css('tr::attr(class)').get() == "head flags"):
                self.CRAWL_FLAG = tr.css(
                    'a::text').get() in self.main_competitions
            else:
                if(self.CRAWL_FLAG):
                    if not tr.css('td.nbr').get():
                        continue
                    detail_page = tr.css(
                        'a[title="Click for match detail"]::attr(href)').get()
                    if(detail_page):
                        yield scrapy.Request(url=response.urljoin(detail_page), callback=self.parse_detail, meta={"tour_type": tour_type, "dont_filter": True})

    def parse_detail(self, response):
        match_detail = response.xpath(
            '//*[@id="center"]/div[1]/text()[2]').get()
        # if "Qualification" in match_detail:
        #     return
        # if "qualification" in match_detail:
        #     return
        self.crawler.stats.inc_value('count_load_parse_detail')
        player_profile_urls = response.css('th.plName a::attr(href)').getall()
        title = response.css("#center > div:nth-child(2) > a ::text").get()
        time_stamp = self.parse_timestamp(response.xpath(
            '//*[@id="center"]/div[1]/span/text()').get(), response.xpath('//*[@id="center"]/div[1]/text()[1]').get())
        match_detail = response.xpath(
            "/html/body/div[1]/div[1]/div/div[3]/div[3]/div[1]/text()[2]").get()
        match_round = match_detail.split(',')[1].lstrip()
        surface = match_detail.split(',')[2].lstrip()
        if surface == "-":
            surface = "hard"
        H2H = response.xpath('//*[@id="center"]/h2[1]').get()
        odds = self.get_odds(response.css('div#oddsMenu-1-data table'))
        player1 = {}
        player1["H2H"] = get_integer(H2H.split(
            ":")[-1].split("-")[0])[0] if len(H2H.split(":")) == 2 else 0
        try:
            player1["odds"] = odds[0]
        except IndexError:
            return
        player1["latest_win"] = len(response.css('table.result.mutual')[
            0].css('td.icon-result.win'))

        player2 = {}
        player2["H2H"] = get_integer(H2H.split(
            ":")[-1].split("-")[1])[0] if len(H2H.split(":")) == 2 else 0
        player2["odds"] = odds[1]
        player2["latest_win"] = len(response.css('table.result.mutual')[
            1].css('td.icon-result.win'))
        player1_data = {f"player1_{key}": value for (
            key, value) in player1.items()}
        player2_data = {f"player2_{key}": value for (
            key, value) in player2.items()}
        data = {}
        data.update(player1_data)
        data.update(player2_data)
        base = {
            "match_id": str(response.url).split("id=")[1],
            "time_stamp": time_stamp,
            "title": title,
            "tour": response.meta['tour_type'],
            "round": match_round,
            "surface": surface,
        }
        base.update(data)

        player1_profile_url = response.urljoin(player_profile_urls[0])
        player2_profile_url = response.urljoin(player_profile_urls[1])
        yield scrapy.Request(url=player1_profile_url, callback=self.parse_profile, meta={
            "base": base,
            "index": 1,
            "next_url": player2_profile_url,
            "dont_filter": True,
        })

    def parse_profile(self, response):
        base = response.meta["base"]
        index = response.meta["index"]
        next_url = response.meta["next_url"]
        player = self.parse_player_profile(response, base["surface"])
        player_data = {f"player{index}_{key}": value for (
            key, value) in player.items()}
        base.update(player_data)
        if index == 1:
            yield scrapy.Request(url=next_url, callback=self.parse_profile, meta={
                "base": base,
                "index": 2,
                "next_url": None,
                "dont_filter": True,
            })
        if index == 2:
            strong_predict = False
            predict = self.predict_v3(base)
            if predict:
                strong_predict = True
            else:
                predict = self.predict_v2(base)

            print(base.get("title"), base.get(
                "player1_name"), base.get("player2_name"), predict, strong_predict)
            base.update({
                "predict": predict,
                "strong_predict": strong_predict,
            })

            with open(self.NEXT_24_HOURS_MATCHES, 'a+', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=base.keys())
                if csvfile.tell() == 0:
                    writer.writeheader()
                writer.writerow(base)
            self.crawler.stats.inc_value('count_write_parse_detail')

            yield base

    def parse_timestamp(self, date_string, time_string):
        time = time_string
        if date_string == "Today":
            date = f'{self.now.year:02}-{self.now.month:02}-{self.now.day:02}'
        else:
            date = get_integer(date_string)
            date = f'{date[2]}-{date[1]}-{date[0]}'

        return f'{date}-{"-".join(get_integer(time))}'

    # get elo rating from github and return them as pandas dataframe
    def get_elo_ranking(self):
        url = "https://raw.githubusercontent.com/ebijun1007/tennis_elo_scraper/main/latest/atp.csv"
        raw_csv = requests.get(url).content
        df1 = pd.read_csv(io.StringIO(raw_csv.decode('utf-8')))

        url = "https://raw.githubusercontent.com/ebijun1007/tennis_elo_scraper/main/latest/wta.csv"
        raw_csv = requests.get(url).content
        df2 = pd.read_csv(io.StringIO(raw_csv.decode('utf-8')))

        return pd.concat([df1, df2], ignore_index=True)

    def name_order(self, name):
        if(len(ordered_name := name.split(" ")) == 2):
            return ordered_name[1] + " " + ordered_name[0]
        elif(len(ordered_name) == 3):
            return ordered_name[2] + " " + ordered_name[0] + " " + ordered_name[1]
        elif(len(ordered_name) == 4):
            return ordered_name[0] + " " + ordered_name[1] + " " + ordered_name[2]

    def get_surface_elo(self, player, surface):
        df = self.get_elo_ranking()
        if surface == "indoors":
            surface = "hard"
        try:
            row = df[df['Player'].str.contains(".".join(player.split(' ')))]
            elo = float(row.iloc[0]['Elo'])
            elo_surface = float(row.iloc[0][f'{surface.lower()[0]}Elo'])
            return round((elo + elo_surface) / 2)
        except:
            with open("unmatched_name_list.json", 'r') as f:
                data = json.load(f)
            try:
                if data[player]:
                    row = df[df['Player'].str.contains(
                        ".".join(data[player].split(' ')))]
                    elo = float(row.iloc[0]['Elo'])
                    elo_surface = float(
                        row.iloc[0][f'{surface.lower()[0]}Elo'])
                    return round((elo + elo_surface) / 2)
            except:
                data[player] = ""
            with open("unmatched_name_list.json", 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=4,
                          sort_keys=True, separators=(',', ': '))
            return "-"

    def get_odds(self, table):
        odds = table.css('tr.average').css('div.odds-in::text').getall()
        for tr in table.css('tr'):
            if 'Pinnacle' in tr.css('td ::text').getall():
                odds = tr.css('div.odds-in::text').getall()
                break
        return odds

    # parse player profile page
    def parse_player_profile(self, response, surface):
        try:
            soup = BeautifulSoup(response.text, "lxml")
        except Exception as e:
            print(e)
            print(response)
        table = soup.find("table", {"class": "plDetail"})
        name = self.name_order(table.find('h3').text)
        data = table.find_all('div', {"class": "date"})
        country = [row.text for row in data if "Country" in row.text][0].split(": ")[
            1]
        try:
            height, weight = get_integer(
                [row.text for row in data if "Height / Weight" in row.text][0])
        except:
            height, weight = self.load_height_and_weight(name)
        age = get_integer(
            [row.text for row in data if "Age" in row.text][0])[0]
        try:
            current_rank, highest_rank = get_integer(
                [row.text for row in data if "Current/Highest rank" in row.text][0])
        except:
            current_rank, highest_rank = ["-", "-"]

        wl_table = soup.find("div", {"id": "balMenu-1-data"})
        heads = [x.text for x in wl_table.find('tr').find_all('th')]
        year_row = wl_table.find('tbody').find_all('tr')[0]
        year_wl = year_row.find_all(
            'td')[1].text if year_row.find_all('td')[1].text != "-" else "0/0"
        career_row = wl_table.find('tfoot').find('tr')
        career_wl = career_row.find_all('td')[1].text if career_row.find_all('td')[
            1].text != "-" else "0/0"
        try:
            surface_index = heads.index(surface.capitalize())
            year_surface_wl = year_row.find_all('td')[surface_index].text if year_row.find_all(
                'td')[surface_index].text != "-" else "0/0"
            career_surface_wl = career_row.find_all('td')[surface_index].text if career_row.find_all(
                'td')[surface_index].text != "-" else "0/0"
        except:
            year_surface_wl = "0/0"
            career_surface_wl = "0/0"

        year_total_win = year_wl.split('/')[0]
        year_total_lose = year_wl.split('/')[1]
        year_surface_win = year_surface_wl.split('/')[0]
        year_surface_lose = year_surface_wl.split('/')[1]
        career_total_win = career_wl.split('/')[0]
        career_total_lose = career_wl.split('/')[1]
        career_surface_win = career_surface_wl.split('/')[0]
        career_surface_lose = career_surface_wl.split('/')[1]

        roi = self.calc_roi(
            soup.find('div', {'id': f'matches-{self.now.year}-1-data'}))

        elo = self.get_surface_elo(name, surface)

        return{
            "name": name,
            "country": country,
            "height": height,
            "weight": weight,
            "age": age,
            "current_rank": current_rank,
            "highest_rank": highest_rank,
            "year_total_win": year_total_win,
            "year_total_lose": year_total_lose,
            "year_surface_win": year_surface_win,
            "year_surface_lose": year_surface_lose,
            "career_total_win": career_total_win,
            "career_total_lose": career_total_lose,
            "career_surface_win": career_surface_win,
            "career_surface_lose": career_surface_lose,
            "roi": roi,
            "elo": elo,
        }

    def calc_roi(self, table):
        try:
            balance = 1
            for tr in table.find_all('tr'):
                if "Result" in tr.text:
                    continue
                win = "notU" in str(tr.find('a'))
                try:
                    odds = float(tr.find('td', {"class": "course"}).text)
                except:
                    odds = 1.0
                if(win):
                    balance += float(odds - 1)
                else:
                    balance -= 1
            return round(balance, 2)
        except:
            return 0

    def predict_v1(self, match_type, data):
        if float(data["player1_roi"]) >= 10 and float(data["player2_roi"]) >= 10:
            if float(data["player1_roi"]) >= float(data["player2_roi"]):
                return 1.4
            return 1.6
        elif float(data["player1_roi"]) >= 10:
            return 1
        elif float(data["player2_roi"]) >= 10:
            return 2

        # ROIの差が10以上ある場合、ROIの高い方の選手を返す。ただしトップ10の選手は除く
        if not ((float(data["player1_current_rank"]) >= 20) or (float(data["player2_current_rank"]) >= 10)):
            if (abs(float(data["player1_roi"]) - float(data["player2_roi"])) > 10):
                if float(data["player1_roi"]) > float(data["player2_roi"]):
                    return 1
                return 2

        # オッズが4以上の場合、逆張りとして４以上の選手を返す。ただしトップ50の選手は除く
        if not ((float(data["player1_current_rank"]) >= 20) or (float(data["player2_current_rank"]) >= 50)):
            if (abs(float(data["player1_odds"]) > 4)):
                return 1.4
            if (abs(float(data["player2_odds"]) > 4)):
                return 1.6

        # オッズの差が1以上ある場合、オッズの低い選手を返す
        # if (abs(float(data["player1_odds"]) - float(data["player2_odds"])) > 1):
        #     if float(data["player1_odds"]) < float(data["player2_odds"]):
        #         return 1.2
        #     return 1.8

        if match_type == "atp":
            prediction_model = self.atp_prediction_model
        elif match_type == "wta":
            prediction_model = self.wta_prediction_model
        df = pd.DataFrame.from_dict(data, orient='index').T
        df = df.dropna()

        x = df[EXPLANATORY_VARIABLES]  # 説明変数

        try:
            predict = round(prediction_model.predict(
                x.astype(float)).array[0], 2)
        except AttributeError:
            predict = round(prediction_model.predict(
                x.astype(float))[0], 2)
        except Exception as e:
            print(e)
            return 0

        try:
            if predict != 0 and predict < 1:
                predict = 1.00
            elif predict > 2:
                predict = 2.00
            return predict
        except Exception as e:
            print(e)
            return 0

    def predict_v2(self, row):
        if (abs(float(row["player1_odds"]) - float(row["player2_odds"])) > 4) and (float(row["player1_roi"]) - float(row["player2_roi"]) < 10):
            if float(row["player1_odds"]) < float(row["player2_odds"]):
                predict = 1
            else:
                predict = 2
        else:
            if float(row["player1_roi"]) > float(row["player2_roi"]):
                predict = 1
            else:
                predict = 2
        return predict

    def predict_v3(self, row):
        tour = row["tour"]
        try:
            return predict_player_win(tour, row)
        except:
            return

    def load_height_and_weight(self, name):
        with open("physical_data.json", 'r+') as f:
            try:
                data = json.load(f)
            except:
                data = {"players": {}}
            if(name in data["players"]):
                return data["players"][name]["height"], data["players"][name]["weight"]
            else:
                data["players"][name] = {
                    "height": "-",
                    "weight": "-",
                }
                f.seek(0)
                json.dump(data, f, ensure_ascii=False, indent=4,
                          sort_keys=True, separators=(',', ': '))
                return "-", "-"


def get_integer(string):
    return re.findall(r'\d+', string)
