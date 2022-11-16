import csv
import io
import os
import datetime
import requests
import pinnacle
import slackweb
import traceback


class PinnacleClient():
    USERNAME = os.environ.get('PINNACLE_USERNAME')
    PASSWORD = os.environ.get('PINNACLE_PASSWORD')
    SLACK = slackweb.Slack(url=os.environ.get('SLACK_WEBHOOK_URL'))
    TENNIS_ID = 33
    PERIOD_NUMBER = 0
    MAX_BET_PRICE = 200
    MINIMUM_ODDS = 1.7
    IGNORE_WORD = ["ITF", "Doubles"]
    TODAY = datetime.datetime.now()
    TOMORROW = TODAY + datetime.timedelta(1)
    YESTERDAY = TODAY - datetime.timedelta(1)
    MATCH_FILE = "https://raw.githubusercontent.com/ebijun1007/tennis_major_tour_scraper/main/data/next_48_hours_match.csv"
    api = pinnacle.APIClient(USERNAME, PASSWORD)
    count = 0
    error_count = 0

    def execute(self):
        self.tennis_events = self.load_matches()
        bet_list = self.get_bets()
        event_id_list = [bet["eventId"] for bet in bet_list["straightBets"]]

        for match in self.matches:
            try:
                tour = match["tour"]
                if tour != "wta":
                    continue
                home = match["player1_name"]
                away = match["player2_name"]
                predict = int(match["predict"])
                print(tour, home, away, predict)
                league_id, event_id = self.search_event(home, away)
                line = self.get_line(league_id, event_id, f"Team{predict}")
                if(line["price"] < self.MINIMUM_ODDS):
                    continue
                if not (event_id in event_id_list):
                    print(event_id)
                    print(event_id_list)
                    # bet = self.place_bet(
                    #     line, event_id, f"TEAM{predict}")
                    # print(bet)
                    self.count += 1
                    # self.SLACK.notify(text=str(bet))
            except Exception as e:
                print(e)
                self.error_count += 1
                self.SLACK.notify(text=f"{home} vs {away}: {str(e)}")
                self.SLACK.notify(text=str(traceback.format_exc()))

                continue
        # self.SLACK.notify(
        #     text=f"count: {self.count}, error: {self.error_count}")

    def get_bets(self):
        return self.api.betting.get_bets(
            from_date=self.YESTERDAY, to_date=self.TODAY, betlist="ALL")

    def load_matches(self):
        raw_csv = requests.get(self.MATCH_FILE).content
        reader = csv.reader(io.StringIO(
            raw_csv.decode('utf-8')), skipinitialspace=True)
        header = next(reader)
        self.matches = [dict(zip(header, row)) for row in reader]
        return self.api.market_data.get_fixtures(self.TENNIS_ID)

    def search_event(self, home, away):
        for league in self.tennis_events["league"]:
            if any(word in league["name"] for word in self.IGNORE_WORD):
                continue
            for event in league["events"]:
                list1 = [home, away]
                list2 = [event["home"], event["away"]]
                if any(name in list1 for name in list2):
                    return league["id"], event["id"]

    def get_line(self, league_id, event_id, team):
        return self.api.market_data.get_line(league_id=league_id,
                                             event_id=event_id,
                                             team=team,
                                             sport_id=self.TENNIS_ID,
                                             bet_type=pinnacle.enums.BetType.MoneyLine.value,
                                             period_number=self.PERIOD_NUMBER)

    def place_bet(self, line, event_id, team):
        return self.api.betting.place_bet(
            team=team,
            event_id=event_id,
            line_id=line["lineId"],
            # stake=self.MAX_BET_PRICE,
            stake=line["minRiskStake"],
            bet_type=pinnacle.enums.BetType.MoneyLine.value,
            sport_id=self.TENNIS_ID,
            period_number=self.PERIOD_NUMBER,
            fill_type=pinnacle.enums.FillType.Normal.value
        )


if __name__ == "__main__":
    client = PinnacleClient()
    client.execute()
