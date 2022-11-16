from datetime import datetime, timedelta, timezone
import os
import traceback
import re
import scrapy
from scrapy_splash import SplashRequest


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
    set1 = scrapy.Field()
    set2 = scrapy.Field()
    set3 = scrapy.Field()
    score = scrapy.Field()
    winner = scrapy.Field()
    prize = scrapy.Field()


class OddsHistoryAllExplorer(scrapy.Spider):
    name = "odds_history_all"
    HOME_PAGE = "https://www.oddsportal.com/tennis/results/"
    jst = timezone(timedelta(hours=9), 'JST')
    now = datetime.now(jst)
    yesterday = now - timedelta(days=1)
    EXCLUDE_WORDS = ["Challenger", "Doubles",
                     "ITF", "Exhibition", "Cup", "Olympic", "Mix"]
    # EXCLUDE_WORDS = ["Doubles", "Exhibition", "Mix"]
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
        "HTTPCACHE_ENABLED": True,
        "HTTPCACHE_EXPIRATION_SECS": 0,
        "HTTPCACHE_DIR": 'httpcache',
        "HTTPCACHE_IGNORE_HTTP_CODES": [],
        "HTTPCACHE_STORAGE": 'scrapy_splash.SplashAwareFSCacheStorage',
        "CONCURRENT_REQUESTS": 8,
        "DOWNLOAD_DELAY": 2,
    }
    WAIT_TIME = 3

    def start_requests(self):
        yield scrapy.Request(url=self.HOME_PAGE, callback=self.parse)

    def parse(self, response):
        table = response.css("table.table-main.sport")

        for td in table.css('td'):
            title = td.css("a::text").get()
            if not title:
                continue
            if any([w in title for w in self.EXCLUDE_WORDS]):
                continue
            href = td.css("a::attr('href')").get()
            yield SplashRequest(url=response.urljoin(href), callback=self.parse_detail, meta={'dont_cache': True}, args={
                'wait': self.WAIT_TIME,
            },)

    def parse_detail(self, response):
        pagination = len(response.css("#pagination a"))
        table = response.css("#tournamentTable > tbody")
        latest_date = self.convert_date(table.css(
            "tr").css("span.datet::text").get())
        if not latest_date:
            return
        week_ago = self.now - timedelta(days=7)

        do_cache = latest_date < week_ago.isoformat().split("T")[0]

        for i in range(1, pagination - 2):
            yield SplashRequest(url=f"{response.url}/#/page/{i}/", callback=self.parse_match, meta={'dont_cache': do_cache}, args={
                'wait': self.WAIT_TIME,
            },)
        year_list = response.css(
            "#col-content > div.main-menu2.main-menu-gray > ul > li > span > strong > a::attr('href')")

        for year in year_list:
            yield SplashRequest(url=response.urljoin(year.get()), callback=self.parse_detail, args={
                'wait': self.WAIT_TIME,
            },)

    def parse_match(self, response):
        h1 = response.css("h1::text").get()
        title = h1.split(" (")[0]
        surface = self.get_surface(h1)
        table = response.css("#tournamentTable > tbody")
        date = None
        for tr in table.css("tr"):
            try:
                item = MatchInfo()
                if new_date := tr.css("span.datet::text").get():
                    if "Today" in new_date:
                        continue
                    date = new_date

                if not date:
                    continue

                if "deactivate" not in tr.get():
                    continue
                category = ""
                if "WTA" in title:
                    category = "WTA"
                if "ATP" in title:
                    category = "ATP"
                if "Men" in title:
                    category = "ATP"
                if "Women" in title:
                    category = "WTA"
                time = tr.css("td.table-time::text").get()
                timestamp = " ".join([self.convert_date(date), time])
                names = "".join(tr.css("td.name  ::text").getall())
                match_url = tr.css("td.name > a::attr('href')").get()
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
                item["prize"] = "".join(get_integer(prize))
                item["winner"] = int(winner)
                yield SplashRequest(url=response.urljoin(match_url), callback=self.parse_score, args={
                    'wait': self.WAIT_TIME,
                }, meta={
                    "item": item
                })

            except Exception:
                print(traceback.format_exc())
                continue

    def parse_score(self, response):
        item = response.meta["item"]
        set = response.css("p.result::text").get().replace(
            "(", "").replace(")", "").split(",")
        try:
            item["set1"] = set[0].strip()
            item["set2"] = set[1].strip()
            item["set3"] = set[2].strip() if len(set) == 3 else None
            yield item
        except:
            return

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
