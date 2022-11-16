from datetime import datetime, timedelta, timezone
from os import path
import scrapy


class Item(scrapy.Item):
    title = scrapy.Field()
    timestamp = scrapy.Field()
    surface = scrapy.Field()
    player1_name = scrapy.Field()
    player1_odds = scrapy.Field()
    player2_name = scrapy.Field()
    player2_odds = scrapy.Field()


class PredictionsExplorer(scrapy.Spider):
    name = "prediction"
    HOME_PAGE = "https://www.tennisprediction.com/"
    jst = timezone(timedelta(hours=9), 'JST')
    date = datetime.now(jst)
    next_day_search_condition = f"?year={date.year}&month={date.month:02}&day={date.day:02}"
    custom_settings = {
        "ITEM_PIPELINES": {
            'tennis_explorer.pipelines.PredictionsPipeline': 300,
        }
    }
    balance = 0
    total_count = 0

    def start_requests(self):
        yield scrapy.Request(url=self.HOME_PAGE, callback=self.parse)

    # get main tournament names
    def parse(self, response):
        count = 0
        matches = response.css("tr[class*='match']")
        for i in range(0, len(matches), 2):
            winner = matches[i]
            winner_predict = winner.css("td.main_perc::text").get()

            if winner_predict:
                winner_predict = float(winner_predict.strip('%'))
            else:
                continue

            # winner_name = winner.css("td.main_player ::text").get()
            winner_rank = winner.css("td.main_player::text").get().split(
                "(")[-1].split(")")[0]
            winner_odds = float(winner.css("td.main_odds_m a::text").get())
            loser = matches[i+1]
            loser_predict = float(
                loser.css("td.main_perc::text").get().strip("%"))
            loser_odds = float(loser.css("td.main_odds_m a::text").get())
            # loser_name = loser.css("td.main_player ::text").get()
            loser_rank = loser.css("td.main_player::text").get().split(
                "(")[-1].split(")")[0]

            threshold_predict = 60
            threshold_odds = 1.5

            try:
                int(winner_rank)
            except:
                continue

            if(winner_predict > threshold_predict and winner_odds > threshold_odds and winner_rank > loser_rank):
                self.balance += winner_odds - 1
                count += 1
                self.total_count += 1
                print(response.url, winner_odds, self.balance,  winner_rank,
                      loser_rank, count, self.total_count)
            if(loser_predict > threshold_predict and loser_odds > threshold_odds and loser_rank > winner_rank):
                self.balance -= 1
                count += 1
                self.total_count += 1
                print(response.url, "-1", self.balance,
                      winner_rank, loser_rank, count, self.total_count)

        previos_day = response.css("td.calendarNext a::attr(href)").get()
        yield scrapy.Request(url=response.urljoin(previos_day), callback=self.parse, meta={"dont_filter": True})
