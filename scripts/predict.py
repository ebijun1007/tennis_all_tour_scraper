import os
import datetime
import traceback
from datetime import datetime, timedelta
import boto3
from boto3.dynamodb.conditions import Key, Attr
from functools import lru_cache

from get_roi import query_items_by_player_surface, query_h2h, query_items

dynamodb = boto3.resource(
    'dynamodb', endpoint_url=os.environ.get("DYNAMODB_HOST"), region_name="ap-northeast-1")
dynamo_table = dynamodb.Table("TennisPlayerROI")

LIMIT = 100000


def main(x=0, y=0):
    print(datetime.now())
    from_date = "2022-01-01"
    to_date = "2022-01-10"
    from_date = "2000-01-01"
    to_date = "2100-12-31"
    items = scan_all_items(from_date=from_date, to_date=to_date)
    predict(items, x, y)
    print(datetime.now())


def predict(items, x=0, y=0):
    balance_roi_career = count_career = min_balance = min_balance_temp = balance_when_min_balance = max_stake = 0
    monthly = {
        "01": 0,
        "02": 0,
        "03": 0,
        "04": 0,
        "05": 0,
        "06": 0,
        "07": 0,
        "08": 0,
        "09": 0,
        "10": 0,
        "11": 0,
        "12": 0,
    }
    data = []
    clay = 0
    clay_count = 1
    hard = 0
    hard_count = 1
    grass = 0
    grass_count = 1
    for i, item in enumerate(items):
        if i > LIMIT:
            break
        if not item["surface"] == "hard":
            continue
        try:
            surface = item["surfaceTimestamp"].split("#")[0]
            timestamp_org = item["surfaceTimestamp"].split("#")[1]
            timestamp = (datetime.strptime(
                timestamp_org, "%Y-%m-%d") - timedelta(1)).isoformat().split("T")[0]
            item["timestamp"] = timestamp
            roi_home = calc_roi(query_items_by_player_surface(
                item["playerName"], surface, to_date=timestamp, count=4))
            roi_enemy = calc_roi(query_items_by_player_surface(
                item["enemy"], surface, to_date=timestamp, count=4))
            h2h_home = h2h(item["playerName"],
                           item["enemy"], item["timestamp"])
            h2h_away = h2h(item["enemy"],
                           item["playerName"], item["timestamp"])
            odds = float(item["odds"])
            prize = float(item["prize"])
            if predict_home_win(item, surface, prize, odds, roi_home, roi_enemy, x, y):
                roi, stake = bet(item,
                                 roi_home, roi_enemy)
                balance_roi_career += float(roi)
                monthly[item["timestamp"][5:7]] += roi
                count_career += 1
                if surface == "clay":
                    clay += float(roi)
                    clay_count += 1
                if surface == "hard":
                    hard += float(roi)
                    hard_count += 1
                if surface == "grass":
                    grass += float(roi)
                    grass_count += 1
                data.append({
                    "timestamp": item["timestamp"],
                    "surface": surface,
                    "player": item["playerName"],
                    "enemy": item["enemy"],
                    "roi_home": roi_home,
                    "roi_enemy": roi_enemy,
                    "h2h_home": h2h_home,
                    "h2h_away": h2h_away,
                    "odds": item["odds"],
                    "match_roi": item["roi"],
                    "stake": stake,
                    "result": roi,
                })
            # print(item["playerName"], roi_home, item["enemy"],
            #       roi_enemy, roi, stake, balance_roi_career)
            # print(balance_roi_career)
        except Exception as e:
            print(traceback.format_exc())
            continue
    try:
        print("########################")
        print(f"ROI: {balance_roi_career}")
        print(f"試合数: {count_career}")
        print(f"ROI / 試合数: {balance_roi_career / count_career}")
        print(f"clay: {clay} / {clay_count} : {clay / clay_count}")
        print(f"hard: {hard} / {hard_count} : {hard / hard_count}")
        print(f"grass: {grass} / {grass_count} : {grass / grass_count}")
        print(f"min_balance: {min_balance}")
        print(f"balance_when_min_balance: {balance_when_min_balance}")
        print(monthly)
        return balance_roi_career / count_career
    except:
        return 0
    # df = pd.DataFrame(data)
    # df.to_csv("virtual_stake.csv", index=False)


def parse_set_count(set_string):
    if set_string == "":
        return ""
    return [int(x) for x in set_string.split(":")]


def predict_home_win(item, surface, prize, odds, roi_home, roi_enemy, x, y):
    if surface == "hard":
        if(prize < 500_0000 or odds < 1.3):
            return False
    h2h_win_count = h2h(item["playerName"],
                        item["enemy"], item["timestamp"])
    h2h_lose_count = h2h(item["enemy"], item["playerName"],  item["timestamp"])

    # return roi_home > (roi_enemy + x) and h2h_win_count >= (h2h_lose_count + 1)

    odds_home = average_odds(
        item["playerName"], surface, item["timestamp"])
    odds_diff = odds_home - odds
    if odds_diff == 0:
        return False
    if surface == "clay":
        return(
            prize < 1_000_000 and
            odds < 1.2 and
            odds_diff > 0.5
        )
    if surface == "hard":
        return (
            prize > 500_000 and
            odds_diff > 0.8
        )
    if surface == "grass":
        return (
            prize > 1_000_000 and
            odds > 1.3 and
            roi_home >= (roi_enemy + 0.5) and
            h2h_win_count > h2h_lose_count
        )
    # if surface == "clay":
    #     return roi_home - roi_enemy + x > 0
    # elif surface == "hard":
    #     return roi_home - roi_enemy + y > 0
    # elif surface == "grass":
    #     return roi_home - roi_enemy + z > 0
    # return roi_home - roi_enemy > 1


def h2h(home, away, to_date=None):
    items = query_h2h(
        home, away, to_date=to_date)
    return len([item for item in items if item["roi"] > 0])


@lru_cache(maxsize=None)
def average_odds(player, surface, to_date=None):
    items = query_items(player, surface, to_date=to_date)
    odds = [float(item["odds"]) for item in items]
    if len(odds) == 0:
        return 0
    return sum(odds) / len(odds)


def calc_roi(items, length=1):
    return float(sum(item["roi"] for item in items[0:length]))


def bet(item, roi_home, roi_enemy):
    match_roi = item["roi"]
    # player_roi_diff = roi_home - roi_enemy
    # stake = player_roi_diff * (h2h_win_count + 1)
    stake = 1
    result = stake * match_roi
    return result, stake


def scan_all_items(from_date="2000-01-01", to_date="2300-12-31"):
    response = dynamo_table.scan(
        FilterExpression=Attr('timestamp').between(
            from_date, to_date)
    )
    data = response['Items']
    while 'LastEvaluatedKey' in response:
        response = dynamo_table.scan(
            ExclusiveStartKey=response['LastEvaluatedKey'],
            FilterExpression=Attr('timestamp').between(
                from_date, to_date),
        )
        data.extend(response['Items'])
    return sorted(data, key=lambda x: x['timestamp'])


if __name__ == "__main__":
    main()
