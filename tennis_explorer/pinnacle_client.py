import os
import datetime
import pinnacle


class PinnacleClient():
    def __init__(self, USERNAME=os.environ.get('PINNACLE_USERNAME'), PASSWORD=os.environ.get('PINNACLE_PASSWORD'), SPORTS_ID=33):
        self.api = pinnacle.APIClient(USERNAME, PASSWORD)
        self.MATCH_LIST = self.api.market_data.get_fixtures(SPORTS_ID)
        self.SPORTS_ID = SPORTS_ID
        self.IGNORE_WORD = ["ITF", "Doubles"]
        self.PERIOD_NUMBER = 0
        self.TODAY = datetime.datetime.now()
        self.TOMORROW = self.TODAY + datetime.timedelta(1)
        self.YESTERDAY = self.TODAY - datetime.timedelta(1)

    def check_dup(self, home, away):
        bet_list = self._get_bets()
        if not bet_list:
            return False
        bet_list = bet_list["straightBets"]

        for event in bet_list:
            if home in (event["team1"] + event["team2"]) and away in (event["team1"] + event["team2"]):
                return True
        return False

    def _get_bets(self):
        return self.api.betting.get_bets(
            from_date=self.YESTERDAY, to_date=self.TOMORROW, betlist="ALL")

    def search_event(self, home, away):
        home_characters = home.replace("-", " ").split(" ")
        away_characters = away.replace("-", " ").split(" ")
        for league in self.MATCH_LIST["league"]:
            if any(word in league["name"] for word in self.IGNORE_WORD):
                continue
            for event in league["events"]:
                if any(home_name in event["home"] for home_name in home_characters) and any(away_name in event["away"] for away_name in away_characters) and True:
                    if "(" in event["home"] and "(" in event["away"]:
                        continue
                    return league["id"], event["id"]
        return None, None

    def get_line(self, league_id, event_id, team):
        return self.api.market_data.get_line(league_id=league_id,
                                             event_id=event_id,
                                             team=team,
                                             sport_id=self.SPORTS_ID,
                                             bet_type=pinnacle.enums.BetType.MoneyLine.value,
                                             period_number=self.PERIOD_NUMBER)

    def place_bet(self, line_id, event_id, team, stake):
        return self.api.betting.place_bet(
            team=team,
            event_id=event_id,
            line_id=line_id,
            stake=stake,
            bet_type=pinnacle.enums.BetType.MoneyLine.value,
            sport_id=self.SPORTS_ID,
            period_number=self.PERIOD_NUMBER,
            fill_type=pinnacle.enums.FillType.Normal.value
        )


if __name__ == "__main__":
    client = PinnacleClient()
    client.execute()
