from datetime import datetime, timedelta, timezone
import os
import traceback
import re
import scrapy
from scrapy_splash import SplashRequest


script = """
function main(splash)
    splash:wait(1)
    local element = splash:select('div#user-header-r1 > div > ul > li:nth-child(1) > a')
    element:click()
    splash:wait(5)
    return {
        html = splash:html(),
    }
end
"""


class MatchInfo(scrapy.Item):
    id = scrapy.Field()
    timestamp = scrapy.Field()
    category = scrapy.Field()
    title = scrapy.Field()
    surface = scrapy.Field()
    player1_name = scrapy.Field()
    player1_odds = scrapy.Field()
    player2_name = scrapy.Field()
    player2_odds = scrapy.Field()
    score = scrapy.Field()
    winner = scrapy.Field()


class OddsHistoryExplorer(scrapy.Spider):
    name = "odds_history"
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    path = yesterday.isoformat().replace('-', '').split("T")[0]
    HOME_PAGE = f"https://www.oddsportal.com/matches/tennis/{path}/"
    EXCLUDE_WORDS = ["Challenger", "Doubles",
                     "ITF", "Exhibition", "Cup", "Olympic", "Boys", "Girls"]
    custom_settings = {
        "SPLASH_URL": os.environ.get("SPLASH_URL"),
        "DOWNLOADER_MIDDLEWARES": {
            'scrapy_splash.SplashCookiesMiddleware': 723,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        "SPIDER_MIDDLEWARES": {
            'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
        },
        "ITEM_PIPELINES": {
            'tennis_explorer.pipelines.OddsHistoryPipeline': 300,
        },
        "CONCURRENT_REQUESTS": 64,
    }
    WAIT_TIME = 3

    def start_requests(self):
        yield SplashRequest(url=self.HOME_PAGE, callback=self.parse, args={
            'wait': self.WAIT_TIME,
            'lua_source': script,
            'timeout': 10
        },)

    def parse(self, response):
        date = response.css("h1::text").get().split(",")[1].strip()
        table = response.css("#table-matches")
        title = ""
        surface = ""
        for tr in table.css("tr"):
            try:
                if "dark center" in tr.get():
                    full_title = tr.css("a:nth-child(3) ::text").get()
                    title = full_title.replace(
                        "\xa0", "").split(" (")[0]
                    surface = self.get_surface(full_title)
                    continue
                if not any([w in title for w in self.EXCLUDE_WORDS]):
                    item = MatchInfo()
                    category = ""
                    if "WTA" in title:
                        category = "WTA"
                    if "ATP" in title:
                        category = "ATP"
                    time = tr.css("td.table-time::text").get()
                    timestamp = " ".join([self.convert_date(date), time])
                    names = "".join(tr.css("td.name  ::text").getall())
                    player1_name = self.name_format(names.split(" - ")[0])
                    player2_name = self.name_format(names.split(" - ")[1])
                    score = tr.css("td.table-score::text").get()
                    odds = tr.css("td.odds-nowrp")
                    player1_odds = odds[0].css("a::text").get()
                    player2_odds = odds[1].css("a::text").get()
                    prize = response.css("div.prizemoney::text").get()
                    winner = None
                    if "result-ok" in odds[0].get():
                        winner = 1
                    if "result-ok" in odds[1].get():
                        winner = 2
                    id = "-".join([timestamp.split(" ")[0], player1_name.split(".")[
                        0], player2_name.split(".")[0]])

                    item["id"] = id
                    item["timestamp"] = timestamp
                    item["title"] = title
                    item["category"] = category
                    item["surface"] = surface
                    item["player1_name"] = player1_name
                    item["player1_odds"] = round(float(player1_odds), 2)
                    item["player2_name"] = player2_name
                    item["player2_odds"] = round(float(player2_odds), 2)
                    item["score"] = score
                    item["prize"] = get_integer(prize)
                    item["winner"] = int(winner)
                    yield item

            except Exception:
                print(traceback.format_exc())
                continue

    def convert_date(self, date):
        if not date:
            return None
        if "Today" in date:
            return self.now.isoformat().split("T")[0]
        if "Yesterday" in date:
            return self.yesterday.isoformat().split("T")[0]
        months = {
            "Jan": "01",
            "Feb": "02",
            "Mar": "03",
            "Apr": "04",
            "May": "05",
            "Jun": "06",
            "Jul": "07",
            "Aug": "08",
            "Sep": "09",
            "Oct": "10",
            "Nov": "11",
            "Dec": "12",
        }
        try:
            d, m, y = date.split(" ")
            m = months[m]
            return "-".join([y, m, d])
        except Exception:
            print(traceback.format_exc())
            print(f"date: {date}")
            return

    def get_surface(self, text):
        if("clay" in text):
            return "clay"
        if("hard" in text):
            return "hard"
        if("grass" in text):
            return "grass"

    def name_format(self, name):
        return name.replace("\xa0", "")


def get_integer(string):
    return re.findall(r'\d+', string)
