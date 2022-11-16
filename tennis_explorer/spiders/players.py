from os import path
import scrapy
from bs4 import BeautifulSoup
import re
import csv
import os


class PlayersExplorer(scrapy.Spider):
    name = "players"
    HOME_PAGE = "https://www.tennisexplorer.com/"
    urls = [
        "https://www.tennisexplorer.com/ranking/atp-men/",
        "https://www.tennisexplorer.com/ranking/atp-men/?page=2",
        "https://www.tennisexplorer.com/ranking/atp-men/?page=3",
        "https://www.tennisexplorer.com/ranking/atp-men/?page=4",
        "https://www.tennisexplorer.com/ranking/wta-women/",
        "https://www.tennisexplorer.com/ranking/wta-women/?page=2",
        "https://www.tennisexplorer.com/ranking/wta-women/?page=3",
        "https://www.tennisexplorer.com/ranking/wta-women/?page=4",
    ]
    CSV_FILE_NAME = "./data/roi.csv"

    def start_requests(self):
        try:
            os.remove(self.CSV_FILE_NAME)
        except Exception:
            pass
        for url in self.urls:
            yield scrapy.Request(url=url, callback=self.parse_list)

    def parse_list(self, response):
        pass
        table = response.css('table.result tbody.flags')
        for url in table.css('td.t-name a::attr(href)').getall():
            yield scrapy.Request(url=response.urljoin(url), callback=self.parse_player_profile)

    # parse player profile page
    def parse_player_profile(self, response):
        soup = BeautifulSoup(response.body, "lxml")
        name = response.css('h3::text').get()
        rank = response.css('h3::text').get()
        roi = self.calc_roi(
            soup.find('div', {'id': f'matches-2022-1-data'}))
        rank = response.css(
            '#center > div.box.boxBasic.lGray > table > tbody > tr > td:nth-child(2) > div:nth-child(5)::text').get()
        base = {
            rank: get_integer(rank)[0],
            name: name,
            roi: roi
        }
        with open(self.CSV_FILE_NAME, 'a+', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=base.keys())
            writer.writerow(base)

    def calc_roi(self, table):
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

    def name_order(self, name):
        if(len(ordered_name := name.split(" ")) == 2):
            return ordered_name[1] + " " + ordered_name[0]
        elif(len(ordered_name) == 3):
            return ordered_name[2] + " " + ordered_name[0] + " " + ordered_name[1]
        elif(len(ordered_name) == 4):
            return ordered_name[0] + " " + ordered_name[1] + " " + ordered_name[2]


def get_integer(string):
    return re.findall(r'\d+', string)
